"""
Rule-based model: weighted factor scoring.

This is the Phase 1 model. It uses manually configured weights to combine
factor scores into a bias prediction for each horizon.

bias_h = tanh(Σ weight_i,h × factor_score_i)

The rule model also outputs:
  - p_up, p_neutral, p_down (probabilities derived from bias_score)
  - confidence (derived from probability entropy)
  - top positive/negative contributing factors
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import yaml
from loguru import logger


class RuleModel:
    """Rule-based bias model with configurable weights."""

    def __init__(self, config_path: str | Path):
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)

        model_cfg = cfg.get("models", {}).get("rule_model", {})
        self.model_name = model_cfg.get("name", "rule_model_v1")
        self.horizon_weights = model_cfg.get("horizons", {})
        self.thresholds = model_cfg.get("thresholds", {"bullish": 0.3, "bearish": -0.3})

    def predict(
        self,
        factor_values: pd.DataFrame,
        symbol: str,
        horizon: str,
        as_of_date: Optional[dt.date] = None,
    ) -> dict:
        """
        Generate bias prediction for a single symbol and horizon.

        Args:
            factor_values: DataFrame with columns [symbol, ts or session_date, factor_name, value]
            symbol: Target symbol
            horizon: D1, W1, or M1
            as_of_date: Date to predict for (default: latest available)

        Returns: dict with bias_score, confidence, p_up, p_neutral, p_down,
                 top_positive_factors, top_negative_factors, label
        """
        horizon_cfg = self.horizon_weights.get(horizon)
        if horizon_cfg is None:
            raise ValueError(f"No weights configured for horizon: {horizon}")

        weights = horizon_cfg.get("weights", {})

        # Filter to target symbol
        sym_factors = factor_values[factor_values["symbol"] == symbol].copy()
        if sym_factors.empty:
            return self._empty_prediction(symbol, horizon)

        date_col = "session_date" if "session_date" in sym_factors.columns else "ts"
        if date_col not in sym_factors.columns:
            raise ValueError("factor_values must include either 'session_date' or 'ts'")
        sym_factors[date_col] = pd.to_datetime(sym_factors[date_col])

        # Get the latest date if not specified
        if as_of_date is not None:
            sym_factors = sym_factors[sym_factors[date_col] <= pd.Timestamp(as_of_date)]

        if sym_factors.empty:
            return self._empty_prediction(symbol, horizon)

        latest_date = sym_factors[date_col].max()
        latest_factors = sym_factors[sym_factors[date_col] == latest_date]

        # Compute weighted score
        factor_contributions = {}
        total_weight = 0.0
        weighted_sum = 0.0

        for factor_id, weight in weights.items():
            # Look for factor by name (factors.yaml id maps to factor.spec.name)
            # Try exact match first, then try common name patterns
            factor_row = latest_factors[latest_factors["factor_name"] == factor_id]

            if factor_row.empty:
                # Try with underscore variants
                for fname in latest_factors["factor_name"].unique():
                    if factor_id in fname or fname in factor_id:
                        factor_row = latest_factors[latest_factors["factor_name"] == fname]
                        break

            if factor_row.empty:
                continue

            value = factor_row["value"].mean()
            contribution = weight * value
            factor_contributions[factor_id] = {
                "value": float(value),
                "weight": weight,
                "contribution": float(contribution),
            }
            weighted_sum += contribution
            total_weight += abs(weight)

        if total_weight == 0:
            return self._empty_prediction(symbol, horizon)

        # Normalize and apply tanh
        raw_bias = weighted_sum / total_weight
        bias_score = float(np.tanh(raw_bias * 3))  # Scale for sharper signals

        # Derive probabilities from bias_score
        # bias_score in [-1, +1]
        # Map to 3-class probabilities
        p_up, p_neutral, p_down = self._bias_to_probs(bias_score)

        # Confidence: 1 - normalized entropy
        probs = np.array([p_down, p_neutral, p_up])
        probs = np.clip(probs, 1e-10, 1.0)
        probs = probs / probs.sum()
        entropy = -np.sum(probs * np.log(probs))
        max_entropy = np.log(3)
        confidence = float(1 - entropy / max_entropy)

        # Label
        if bias_score > self.thresholds.get("bullish", 0.3):
            label = "bullish"
        elif bias_score < self.thresholds.get("bearish", -0.3):
            label = "bearish"
        else:
            label = "neutral"

        # Top factors
        sorted_factors = sorted(
            factor_contributions.items(),
            key=lambda x: abs(x[1]["contribution"]),
            reverse=True,
        )
        top_positive = [
            {"name": k, "value": v["value"], "contribution": v["contribution"]}
            for k, v in sorted_factors
            if v["contribution"] > 0
        ][:5]
        top_negative = [
            {"name": k, "value": v["value"], "contribution": v["contribution"]}
            for k, v in sorted_factors
            if v["contribution"] < 0
        ][:5]

        return {
            "symbol": symbol,
            "as_of": str(latest_date.date()),
            "horizon": horizon,
            "bias_score": round(bias_score, 4),
            "label": label,
            "confidence": round(confidence, 4),
            "p_up": round(p_up, 4),
            "p_neutral": round(p_neutral, 4),
            "p_down": round(p_down, 4),
            "top_positive_factors": top_positive,
            "top_negative_factors": top_negative,
            "model_name": self.model_name,
            "model_version": self.model_name,
            "num_factors_used": len(factor_contributions),
            "total_weight_coverage": round(total_weight / sum(weights.values()), 4),
        }

    def predict_all(
        self,
        factor_values: pd.DataFrame,
        symbols: Optional[list[str]] = None,
        horizons: Optional[list[str]] = None,
        as_of_date: Optional[dt.date] = None,
    ) -> pd.DataFrame:
        """
        Generate predictions for all symbols and horizons.

        Returns DataFrame with one row per symbol/horizon.
        """
        if symbols is None:
            symbols = factor_values["symbol"].unique().tolist()
        if horizons is None:
            horizons = list(self.horizon_weights.keys())

        predictions = []
        for symbol in symbols:
            for horizon in horizons:
                try:
                    pred = self.predict(factor_values, symbol, horizon, as_of_date)
                    predictions.append(pred)
                except Exception as e:
                    logger.error(f"Prediction failed for {symbol}/{horizon}: {e}")

        if not predictions:
            return pd.DataFrame()

        return pd.DataFrame(predictions)

    def _bias_to_probs(self, bias_score: float) -> tuple[float, float, float]:
        """
        Convert bias_score in [-1, +1] to (p_up, p_neutral, p_down).

        Method: softmax-like mapping.
        bias > 0 => p_up higher
        bias < 0 => p_down higher
        bias ~ 0 => p_neutral higher
        """
        # Map bias to logits
        # bias_score * scale gives the strength
        scale = 2.0
        logit_up = bias_score * scale
        logit_down = -bias_score * scale
        logit_neutral = -abs(bias_score) * scale * 0.5  # neutral decreases with conviction

        # Softmax
        logits = np.array([logit_up, logit_neutral, logit_down])
        logits = logits - logits.max()  # numerical stability
        exp_logits = np.exp(logits)
        probs = exp_logits / exp_logits.sum()

        return float(probs[0]), float(probs[1]), float(probs[2])

    def _empty_prediction(self, symbol: str, horizon: str) -> dict:
        """Return an empty/neutral prediction."""
        return {
            "symbol": symbol,
            "as_of": None,
            "horizon": horizon,
            "bias_score": 0.0,
            "label": "neutral",
            "confidence": 0.0,
            "p_up": 0.333,
            "p_neutral": 0.333,
            "p_down": 0.334,
            "top_positive_factors": [],
            "top_negative_factors": [],
            "model_name": self.model_name,
            "model_version": self.model_name,
            "num_factors_used": 0,
            "total_weight_coverage": 0.0,
        }

    def save_predictions(self, predictions: pd.DataFrame, output_dir: str | Path) -> Path:
        """Save predictions to Parquet."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "predictions.parquet"
        predictions.to_parquet(output_path, index=False)
        logger.info(f"Saved {len(predictions)} predictions to {output_path}")
        return output_path

    def format_report(self, predictions: pd.DataFrame) -> str:
        """Format predictions into a human-readable report."""
        lines = ["=" * 60, "Multi-Timeframe Bias Report", "=" * 60, ""]

        for _, row in predictions.iterrows():
            symbol = row["symbol"]
            horizon = row["horizon"]
            score = row["bias_score"]
            label = row["label"]
            conf = row["confidence"]
            as_of = row["as_of"]

            # Color indicator
            if label == "bullish":
                indicator = "▲"
            elif label == "bearish":
                indicator = "▼"
            else:
                indicator = "●"

            lines.append(
                f"{symbol} / {horizon}: {indicator} {score:+.2f} ({label}) "
                f"[conf: {conf:.2f}] as of {as_of}"
            )

            # Top factors
            top_pos = row.get("top_positive_factors", [])
            top_neg = row.get("top_negative_factors", [])

            if isinstance(top_pos, list) and top_pos:
                pos_str = ", ".join(
                    f"{f['name']}({f['contribution']:+.3f})" for f in top_pos[:3]
                )
                lines.append(f"  + {pos_str}")
            if isinstance(top_neg, list) and top_neg:
                neg_str = ", ".join(
                    f"{f['name']}({f['contribution']:+.3f})" for f in top_neg[:3]
                )
                lines.append(f"  - {neg_str}")
            lines.append("")

        lines.append("=" * 60)
        return "\n".join(lines)
