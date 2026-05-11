"""Volatility Factor: ATR as percentage of close."""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..base import FactorContext, FactorSpec, FACTOR_OUTPUT_COLUMNS, rolling_zscore


class AtrPctFactor:
    """
    Average True Range as percentage of closing price.

    ATR% is a normalized volatility measure that allows cross-symbol comparison.
    Returns the z-score of ATR% to detect unusual volatility regimes.
    """

    def __init__(self, window: int = 14, **kwargs):
        self.spec = FactorSpec(
            name="atr_pct",
            version="1.0.0",
            family="volatility",
            description=f"ATR({window}) as % of close, z-scored",
            inputs=["bars.open", "bars.high", "bars.low", "bars.close"],
            horizons=["D1", "W1"],
            lookback=window * 3,
            params={"window": window},
        )
        self.window = window

    def compute(self, ctx: FactorContext) -> pd.DataFrame:
        bars = ctx.load_bars(fields=["open", "high", "low", "close"])
        if bars.empty:
            return pd.DataFrame(columns=FACTOR_OUTPUT_COLUMNS)

        results = []
        for symbol in bars["symbol"].unique():
            sym_bars = bars[bars["symbol"] == symbol].copy()
            sym_bars = sym_bars.sort_values("session_date")

            # True Range
            high = sym_bars["high"]
            low = sym_bars["low"]
            prev_close = sym_bars["close"].shift(1)

            tr1 = high - low
            tr2 = (high - prev_close).abs()
            tr3 = (low - prev_close).abs()
            true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

            # ATR (EMA of True Range)
            atr = true_range.ewm(span=self.window, adjust=False).mean()

            # ATR as % of close
            atr_pct = atr / sym_bars["close"]

            # Z-score of ATR%
            atr_z = rolling_zscore(atr_pct, window=120)

            # High ATR z => high uncertainty => negative
            normalized = -atr_z.clip(-3, 3) / 3

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
