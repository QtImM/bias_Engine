"""Trend Factor: Drawdown from N-day high."""
from __future__ import annotations

import pandas as pd

from ..base import FactorContext, FactorSpec, FACTOR_OUTPUT_COLUMNS


class DrawdownFactor:
    """
    Measures drawdown from the N-day rolling high.

    Value range: (-inf, 0]
      0    = at the high (no drawdown)
      -0.1 = 10% below the high
      -0.3 = 30% below the high (deep drawdown)

    For bias: more negative = more bearish signal.
    """

    def __init__(self, window: int = 60, **kwargs):
        self.spec = FactorSpec(
            name=f"drawdown_from_{window}d_high",
            version="1.0.0",
            family="trend",
            description=f"Drawdown from {window}-day rolling high",
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

            # Rolling high
            rolling_high = sym_bars["close"].rolling(
                window=self.window, min_periods=self.window // 2
            ).max()

            # Drawdown: (close - high) / high
            drawdown = (sym_bars["close"] - rolling_high) / rolling_high

            out = pd.DataFrame({
                "symbol": symbol,
                "ts": sym_bars["ts"],
                "timeframe": "1d",
                "factor_name": self.spec.name,
                "factor_version": self.spec.version,
                "value": drawdown,
                "available_at": sym_bars["ts"],
                "quality_score": 1.0,
            })
            results.append(out)

        if not results:
            return pd.DataFrame(columns=FACTOR_OUTPUT_COLUMNS)
        return pd.concat(results, ignore_index=True).dropna(subset=["value"])
