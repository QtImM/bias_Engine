"""Volatility Factor: Realized volatility."""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..base import FactorContext, FactorSpec, FACTOR_OUTPUT_COLUMNS, rolling_zscore


class RealizedVolFactor:
    """
    20-day realized volatility (annualized).

    Returns the vol z-score: how unusual current vol is relative to history.
    High vol => negative signal (uncertainty increases)
    Low vol => slight positive signal (stability)
    """

    def __init__(self, window: int = 20, **kwargs):
        self.spec = FactorSpec(
            name="realized_vol_20d",
            version="1.0.0",
            family="volatility",
            description=f"{window}-day realized volatility z-score",
            inputs=["bars.close"],
            horizons=["D1", "W1", "M1"],
            lookback=window * 3,
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

            # Daily log returns
            log_ret = np.log(sym_bars["close"] / sym_bars["close"].shift(1))

            # Realized vol: annualized rolling std
            vol = log_ret.rolling(window=self.window, min_periods=self.window // 2).std() * np.sqrt(252)

            # Z-score: how unusual is current vol vs history
            # Use longer lookback for z-score normalization
            vol_z = rolling_zscore(vol, window=120)

            # Invert: high vol z-score => negative (bearish)
            normalized = -vol_z.clip(-3, 3) / 3

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
