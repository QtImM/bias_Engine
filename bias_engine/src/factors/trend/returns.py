"""Trend Factor: N-day return."""
from __future__ import annotations

import pandas as pd

from ..base import FactorContext, FactorSpec, FACTOR_OUTPUT_COLUMNS


class ReturnFactor:
    """Computes N-day price return for each symbol."""

    def __init__(self, window: int = 5, **kwargs):
        self.spec = FactorSpec(
            name=f"return_{window}d",
            version="1.0.0",
            family="trend",
            description=f"{window}-day price return",
            inputs=["bars.close"],
            horizons=["D1", "W1", "M1"],
            lookback=window + 5,
            params={"window": window},
        )
        self.window = window

    def compute(self, ctx: FactorContext) -> pd.DataFrame:
        bars = ctx.load_bars(fields=["close"])
        if bars.empty:
            return pd.DataFrame(columns=FACTOR_OUTPUT_COLUMNS)

        results = []
        for symbol in bars["symbol"].unique():
            sym_bars = bars[bars["symbol"] == symbol].copy()
            sym_bars = sym_bars.sort_values("session_date")

            # N-day return: close[t] / close[t-N] - 1
            sym_bars["value"] = sym_bars["close"].pct_change(periods=self.window)

            out = pd.DataFrame({
                "symbol": symbol,
                "ts": sym_bars["ts"],
                "timeframe": "1d",
                "factor_name": self.spec.name,
                "factor_version": self.spec.version,
                "value": sym_bars["value"],
                "available_at": sym_bars["ts"],
                "quality_score": 1.0,
            })
            results.append(out)

        if not results:
            return pd.DataFrame(columns=FACTOR_OUTPUT_COLUMNS)
        return pd.concat(results, ignore_index=True).dropna(subset=["value"])
