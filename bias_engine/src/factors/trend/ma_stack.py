"""Trend Factor: MA stack score (moving average alignment)."""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..base import FactorContext, FactorSpec, FACTOR_OUTPUT_COLUMNS


class MaStackScoreFactor:
    """
    Measures how well multiple moving averages are aligned.

    Score:
      +1.0 = perfect bullish alignment (MA5 > MA20 > MA60 > MA120)
      -1.0 = perfect bearish alignment (MA5 < MA20 < MA60 < MA120)
       0.0 = mixed / no clear alignment

    Computed by counting pairwise inversions.
    """

    def __init__(self, windows: list[int] | None = None, **kwargs):
        if windows is None:
            windows = [5, 20, 60, 120]
        self.windows = windows
        self.spec = FactorSpec(
            name="ma_stack_score",
            version="1.0.0",
            family="trend",
            description=f"MA alignment score using windows {windows}",
            inputs=["bars.close"],
            horizons=["W1", "M1"],
            lookback=max(windows) + 10,
            params={"windows": windows},
        )

    def compute(self, ctx: FactorContext) -> pd.DataFrame:
        bars = ctx.load_bars(fields=["close"])
        if bars.empty:
            return pd.DataFrame(columns=FACTOR_OUTPUT_COLUMNS)

        results = []
        for symbol in bars["symbol"].unique():
            sym_bars = bars[bars["symbol"] == symbol].copy()
            sym_bars = sym_bars.sort_values("session_date")

            # Compute all MAs
            ma_values = {}
            for w in self.windows:
                ma_values[w] = sym_bars["close"].rolling(window=w, min_periods=w // 2).mean()

            # Compute pairwise alignment score
            n_pairs = 0
            score = pd.Series(0.0, index=sym_bars.index)

            for i in range(len(self.windows)):
                for j in range(i + 1, len(self.windows)):
                    short_ma = ma_values[self.windows[i]]
                    long_ma = ma_values[self.windows[j]]
                    # +1 if short > long (bullish), -1 if short < long (bearish)
                    pair_score = np.sign(short_ma - long_ma)
                    score += pair_score
                    n_pairs += 1

            # Normalize to [-1, +1]
            if n_pairs > 0:
                score = score / n_pairs

            out = pd.DataFrame({
                "symbol": symbol,
                "ts": sym_bars["ts"],
                "timeframe": "1d",
                "factor_name": self.spec.name,
                "factor_version": self.spec.version,
                "value": score,
                "available_at": sym_bars["ts"],
                "quality_score": 1.0,
            })
            results.append(out)

        if not results:
            return pd.DataFrame(columns=FACTOR_OUTPUT_COLUMNS)
        return pd.concat(results, ignore_index=True).dropna(subset=["value"])
