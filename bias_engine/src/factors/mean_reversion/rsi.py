"""Mean Reversion Factor: RSI (Relative Strength Index)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..base import FactorContext, FactorSpec, FACTOR_OUTPUT_COLUMNS


class RsiFactor:
    """
    RSI normalized to [-1, +1].

    RSI > 70 => overbought => negative bias (mean reversion down)
    RSI < 30 => oversold => positive bias (mean reversion up)
    RSI 50 => neutral => 0

    Mapping: (RSI - 50) / 50 * -1
      RSI 80 => -0.6 (overbought, bearish)
      RSI 20 => +0.6 (oversold, bullish)
    """

    def __init__(self, window: int = 14, **kwargs):
        self.spec = FactorSpec(
            name="rsi_14",
            version="1.0.0",
            family="mean_reversion",
            description=f"RSI({window}) normalized to [-1, +1]",
            inputs=["bars.close"],
            horizons=["D1"],
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

            # Calculate RSI
            delta = sym_bars["close"].diff()
            gain = delta.where(delta > 0, 0.0)
            loss = (-delta).where(delta < 0, 0.0)

            avg_gain = gain.ewm(alpha=1 / self.window, min_periods=self.window).mean()
            avg_loss = loss.ewm(alpha=1 / self.window, min_periods=self.window).mean()

            rs = avg_gain / avg_loss.replace(0, np.nan)
            rsi = 100 - (100 / (1 + rs))

            # Normalize to [-1, +1]: (RSI - 50) / 50 * -1
            # High RSI (overbought) => negative (bearish for mean reversion)
            # Low RSI (oversold) => positive (bullish for mean reversion)
            normalized = -(rsi - 50) / 50

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
