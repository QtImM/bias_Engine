"""Cross-Market Factor: Relative strength between indices."""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..base import FactorContext, FactorSpec, FACTOR_OUTPUT_COLUMNS


class RelativeStrengthFactor:
    """
    Relative strength of a symbol vs a benchmark over a rolling window.

    Positive: symbol outperforming benchmark (bullish for symbol)
    Negative: symbol underperforming benchmark (bearish for symbol)

    Normalized to roughly [-1, +1] via z-scoring.
    """

    def __init__(self, benchmark: str = "NDX", window: int = 20, **kwargs):
        self.benchmark = benchmark
        self.window = window
        self.spec = FactorSpec(
            name=f"relative_strength_vs_{benchmark.lower()}",
            version="1.0.0",
            family="cross_market",
            description=f"Relative strength vs {benchmark} over {window} days",
            inputs=["bars.close"],
            horizons=["W1", "M1"],
            lookback=window + 20,
            params={"benchmark": benchmark, "window": window},
        )

    def compute(self, ctx: FactorContext) -> pd.DataFrame:
        bars = ctx.load_bars(fields=["close"])
        if bars.empty:
            return pd.DataFrame(columns=FACTOR_OUTPUT_COLUMNS)

        # Get benchmark data
        bench_bars = bars[bars["symbol"] == self.benchmark].copy()
        if bench_bars.empty:
            return pd.DataFrame(columns=FACTOR_OUTPUT_COLUMNS)

        bench_bars = bench_bars.sort_values("session_date")
        bench_bars["bench_cumret"] = (
            bench_bars["close"].pct_change().add(1).cumprod()
        )

        # For each target symbol, compute relative strength
        results = []
        target_symbols = [s for s in ctx.symbols if s != self.benchmark]

        for symbol in target_symbols:
            sym_bars = bars[bars["symbol"] == symbol].copy()
            sym_bars = sym_bars.sort_values("session_date")

            # Cumulative return for symbol
            sym_bars["sym_cumret"] = (
                sym_bars["close"].pct_change().add(1).cumprod()
            )

            # Align dates using merge
            merged = pd.merge(
                sym_bars[["ts", "session_date", "sym_cumret"]],
                bench_bars[["session_date", "bench_cumret"]],
                on="session_date",
                how="inner",
            ).sort_values("session_date")

            if merged.empty:
                continue

            # Rolling relative strength: difference in rolling returns
            sym_rolling = merged["sym_cumret"].pct_change(self.window)
            bench_rolling = merged["bench_cumret"].pct_change(self.window)
            rel_strength = sym_rolling - bench_rolling

            # Z-score normalize (approximate)
            mean = rel_strength.rolling(120, min_periods=40).mean()
            std = rel_strength.rolling(120, min_periods=40).std()
            normalized = ((rel_strength - mean) / std.replace(0, np.nan)).clip(-3, 3) / 3

            out = pd.DataFrame({
                "symbol": symbol,
                "ts": merged["ts"],
                "timeframe": "1d",
                "factor_name": self.spec.name,
                "factor_version": self.spec.version,
                "value": normalized,
                "available_at": merged["ts"],
                "quality_score": 1.0,
            })
            results.append(out)

        if not results:
            return pd.DataFrame(columns=FACTOR_OUTPUT_COLUMNS)
        return pd.concat(results, ignore_index=True).dropna(subset=["value"])
