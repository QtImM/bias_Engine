"""
Label Engine: generates training labels from historical price data.

Labels are:
  +1 = bullish (forward volatility-adjusted return > theta)
   0 = neutral
  -1 = bearish (forward volatility-adjusted return < -theta)

Three horizons:
  D1: 3 trading days forward
  W1: 10 trading days forward
  M1: 40 trading days forward
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import yaml
from loguru import logger


class LabelEngine:
    """Generates forward-looking labels for model training."""

    def __init__(self, config_path: str | Path):
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)

        label_cfg = cfg.get("label_engine", {})
        self.horizons = label_cfg.get("horizons", {
            "D1": {"forward_days": 3},
            "W1": {"forward_days": 10},
            "M1": {"forward_days": 40},
        })
        self.theta = label_cfg.get("theta", 0.3)

    def compute_labels(
        self,
        bars: pd.DataFrame,
        symbol: str,
        horizon: str,
    ) -> pd.DataFrame:
        """
        Compute labels for a single symbol and horizon.

        Returns DataFrame with columns:
          symbol, ts, horizon, fwd_return, fwd_vol_adj_return, label
        """
        sym_bars = bars[bars["symbol"] == symbol].copy()
        sym_bars = sym_bars.sort_values("session_date").reset_index(drop=True)

        if len(sym_bars) < 20:
            logger.warning(f"Insufficient data for {symbol} labels ({len(sym_bars)} bars)")
            return pd.DataFrame()

        horizon_cfg = self.horizons.get(horizon)
        if horizon_cfg is None:
            raise ValueError(f"Unknown horizon: {horizon}")

        h = horizon_cfg["forward_days"]

        # Forward return: close[t+h] / close[t] - 1
        sym_bars["fwd_return"] = (
            sym_bars["close"].shift(-h) / sym_bars["close"] - 1
        )

        # Realized volatility (for volatility adjustment)
        log_ret = np.log(sym_bars["close"] / sym_bars["close"].shift(1))
        # Use a lookback that matches the horizon
        vol_window = max(h * 2, 20)
        sym_bars["realized_vol"] = (
            log_ret.rolling(window=vol_window, min_periods=vol_window // 2).std()
            * np.sqrt(252)
        )

        # Volatility-adjusted forward return
        sym_bars["fwd_vol_adj_return"] = (
            sym_bars["fwd_return"] / sym_bars["realized_vol"].replace(0, np.nan)
        )

        # Three-class label
        conditions = [
            sym_bars["fwd_vol_adj_return"] > self.theta,
            sym_bars["fwd_vol_adj_return"] < -self.theta,
        ]
        choices = [1, -1]
        sym_bars["label"] = np.select(conditions, choices, default=0)

        # Build output
        out = pd.DataFrame({
            "symbol": symbol,
            "ts": sym_bars["ts"],
            "session_date": sym_bars["session_date"],
            "horizon": horizon,
            "fwd_return": sym_bars["fwd_return"],
            "fwd_vol_adj_return": sym_bars["fwd_vol_adj_return"],
            "label": sym_bars["label"],
        })

        # Drop rows where we can't compute forward return (end of data)
        out = out.dropna(subset=["fwd_return", "label"])

        logger.info(
            f"{symbol}/{horizon}: {len(out)} labels, "
            f"distribution: {dict(out['label'].value_counts().sort_index())}"
        )

        return out

    def compute_all_labels(
        self,
        bars: pd.DataFrame,
        symbols: Optional[list[str]] = None,
        horizons: Optional[list[str]] = None,
    ) -> pd.DataFrame:
        """
        Compute labels for all symbols and horizons.

        Returns combined DataFrame.
        """
        if symbols is None:
            symbols = bars["symbol"].unique().tolist()
        if horizons is None:
            horizons = list(self.horizons.keys())

        all_labels = []
        for symbol in symbols:
            for horizon in horizons:
                try:
                    labels = self.compute_labels(bars, symbol, horizon)
                    if not labels.empty:
                        all_labels.append(labels)
                except Exception as e:
                    logger.error(f"Label computation failed for {symbol}/{horizon}: {e}")

        if not all_labels:
            return pd.DataFrame()

        combined = pd.concat(all_labels, ignore_index=True)
        return combined.sort_values(["symbol", "horizon", "session_date"]).reset_index(drop=True)

    def save_labels(self, labels: pd.DataFrame, output_dir: str | Path) -> Path:
        """Save labels to Parquet."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "labels.parquet"
        labels.to_parquet(output_path, index=False)
        logger.info(f"Saved {len(labels)} labels to {output_path}")
        return output_path

    def load_labels(self, labels_dir: str | Path) -> pd.DataFrame:
        """Load labels from Parquet."""
        labels_path = Path(labels_dir) / "labels.parquet"
        if not labels_path.exists():
            return pd.DataFrame()
        return pd.read_parquet(labels_path)
