"""Mean Reversion Factor: Bollinger Band z-score."""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..base import FactorContext, FactorSpec, FACTOR_OUTPUT_COLUMNS, rolling_zscore


class BollingerZFactor:
    """
    Distance from Bollinger middle band in z-score units.

    z > +2: price above upper band (overbought) => negative bias
    z < -2: price below lower band (oversold) => positive bias
    z ~ 0: near middle band => neutral

    Clipped to [-1, +1] by dividing by num_std.
    """

    def __init__(self, window: int = 20, num_std: float = 2.0, **kwargs):
        self.spec = FactorSpec(
            name="bollinger_z",
            version="1.0.0",
            family="mean_reversion",
            description=f"Bollinger z-score (window={window}, std={num_std})",
            inputs=["bars.close"],
            horizons=["D1"],
            lookback=window + 10,
            params={"window": window, "num_std": num_std},
        )
        self.window = window
        self.num_std = num_std

    def compute(self, ctx: FactorContext) -> pd.DataFrame:
        bars = ctx.load_bars(fields=["close"])
        if bars.empty:
            return pd.DataFrame(columns=FACTOR_OUTPUT_COLUMNS)

        results = []
        for symbol in bars["symbol"].unique():
            sym_bars = bars[bars["symbol"] == symbol].copy()
            sym_bars = sym_bars.sort_values("session_date")

            # Bollinger z-score
            ma = sym_bars["close"].rolling(window=self.window, min_periods=self.window // 2).mean()
            std = sym_bars["close"].rolling(window=self.window, min_periods=self.window // 2).std()
            z = (sym_bars["close"] - ma) / std.replace(0, np.nan)

            # Normalize: clip to [-1, +1] by dividing by num_std
            # Positive z (above band) => negative for mean reversion
            normalized = -(z / self.num_std).clip(-1, 1)

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
