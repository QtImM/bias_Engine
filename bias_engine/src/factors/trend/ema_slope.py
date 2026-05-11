"""Trend Factor: EMA slope normalized by recent volatility."""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..base import FactorContext, FactorSpec, FACTOR_OUTPUT_COLUMNS


class EmaSlopeFactor:
    """Computes EMA slope normalized by volatility."""

    def __init__(self, window: int = 20, diff_period: int = 5, **kwargs):
        self.spec = FactorSpec(
            name=f"ema_slope_{window}",
            version="1.0.0",
            family="trend",
            description=f"EMA{window} slope over {diff_period} days, normalized by vol",
            inputs=["bars.close"],
            horizons=["D1", "W1", "M1"],
            lookback=window + diff_period + 20,
            params={"window": window, "diff_period": diff_period},
        )
        self.window = window
        self.diff_period = diff_period

    def compute(self, ctx: FactorContext) -> pd.DataFrame:
        bars = ctx.load_bars(fields=["close"])
        if bars.empty:
            return pd.DataFrame(columns=FACTOR_OUTPUT_COLUMNS)

        results = []
        for symbol in bars["symbol"].unique():
            sym_bars = bars[bars["symbol"] == symbol].copy()
            sym_bars = sym_bars.sort_values("session_date")

            # EMA
            ema = sym_bars["close"].ewm(span=self.window, adjust=False).mean()

            # Slope: difference of EMA over diff_period
            slope = ema.diff(self.diff_period)

            # Normalize by recent volatility (20-day rolling std of returns)
            returns = sym_bars["close"].pct_change()
            vol = returns.rolling(window=20, min_periods=10).std()
            vol = vol.replace(0, np.nan)

            # Normalize: slope / (price * vol * sqrt(diff_period))
            normalized = slope / (sym_bars["close"] * vol * np.sqrt(self.diff_period))

            out = pd.DataFrame({
                "symbol": symbol,
                "ts": sym_bars["ts"],
                "timeframe": "1d",
                "factor_name": self.spec.name,
                "factor_version": self.spec.version,
                "value": normalized,
                "available_at": sym_bars["ts"],
                "quality_score": 1.0,
            })
            results.append(out)

        if not results:
            return pd.DataFrame(columns=FACTOR_OUTPUT_COLUMNS)
        return pd.concat(results, ignore_index=True).dropna(subset=["value"])
