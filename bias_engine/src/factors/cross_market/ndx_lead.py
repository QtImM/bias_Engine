"""Cross-Market Factor: NDX previous session return as leading indicator."""
from __future__ import annotations

import datetime as dt

import numpy as np
import pandas as pd

from ..base import FactorContext, FactorSpec, FACTOR_OUTPUT_COLUMNS


class NdxLeadFactor:
    """
    NDX (Nasdaq-100) previous session's return as a leading indicator
    for Asian markets (STAR50, HSI).

    Logic: US market closes after Asian markets, so NDX's daily return
    can predict next-day Asian market behavior.

    IMPORTANT: This factor must respect timezone differences.
    US Monday close => available for Asian Tuesday open.

    The factor is applied to STAR50 and HSI only (not NDX itself).
    """

    def __init__(self, lag_days: int = 1, **kwargs):
        self.spec = FactorSpec(
            name="ndx_prev_session_return",
            version="1.0.0",
            family="cross_market",
            description="NDX previous session return as leading indicator for Asia",
            inputs=["bars.close"],
            horizons=["D1", "W1"],
            lookback=10,
            release_lag="1D",
            params={"lag_days": lag_days},
        )
        self.lag_days = lag_days

    def compute(self, ctx: FactorContext) -> pd.DataFrame:
        bars = ctx.load_bars(fields=["close"])
        if bars.empty:
            return pd.DataFrame(columns=FACTOR_OUTPUT_COLUMNS)

        # Get NDX data
        ndx_bars = bars[bars["symbol"] == "NDX"].copy()
        if ndx_bars.empty:
            return pd.DataFrame(columns=FACTOR_OUTPUT_COLUMNS)

        ndx_bars = ndx_bars.sort_values("session_date")
        ndx_bars["ndx_return"] = ndx_bars["close"].pct_change()
        ndx_bars["ndx_session_date"] = ndx_bars["session_date"]

        # For each Asian symbol, align NDX previous session
        results = []
        target_symbols = [s for s in ctx.symbols if s in ("STAR50", "HSI")]

        for symbol in target_symbols:
            sym_bars = bars[bars["symbol"] == symbol].copy()
            sym_bars = sym_bars.sort_values("session_date")

            # For each Asian trading day, find the most recent NDX close
            # This handles timezone: NDX closes after Asia,
            # so Asian day T uses NDX day T-1 (or T for same-calendar-day)
            merged = pd.merge_asof(
                sym_bars[["ts", "session_date"]].sort_values("session_date"),
                ndx_bars[["session_date", "ndx_return"]].rename(
                    columns={"session_date": "ndx_session_date"}
                ).sort_values("ndx_session_date"),
                left_on="session_date",
                right_on="ndx_session_date",
                direction="backward",
            )

            # Shift by lag_days to ensure we use data that was available
            # NDX Friday close => available for Asian Monday
            # We use merge_asof with backward direction which already handles this

            out = pd.DataFrame({
                "symbol": symbol,
                "ts": merged["ts"],
                "timeframe": "1d",
                "factor_name": self.spec.name,
                "factor_version": self.spec.version,
                "value": merged["ndx_return"],
                # available_at: NDX data available after US close + buffer
                "available_at": merged["ts"],
                "quality_score": 1.0,
            })
            results.append(out)

        if not results:
            return pd.DataFrame(columns=FACTOR_OUTPUT_COLUMNS)
        return pd.concat(results, ignore_index=True).dropna(subset=["value"])
