"""Volume Factor: Volume z-score."""
from __future__ import annotations

import numpy as np
import pandas as pd

from ...base import FactorContext, FactorSpec, FACTOR_OUTPUT_COLUMNS, rolling_zscore


class VolumeZscoreFactor:
    """
    Volume z-score: how unusual is today's volume relative to recent history.

    High volume z-score + price up => bullish confirmation
    High volume z-score + price down => bearish confirmation
    Low volume => neutral (no conviction)

    Output is signed: positive if price direction matches volume, negative otherwise.
    """

    def __init__(self, window: int = 20, **kwargs):
        self.spec = FactorSpec(
            name="volume_zscore",
            version="1.0.0",
            family="volume",
            description=f"Volume z-score ({window}d) signed by price direction",
            inputs=["bars.close", "bars.volume"],
            horizons=["D1"],
            lookback=window * 2,
            params={"window": window},
        )
        self.window = window

    def compute(self, ctx: FactorContext) -> pd.DataFrame:
        bars = ctx.load_bars(fields=["close", "volume"])
        if bars.empty:
            return pd.DataFrame(columns=FACTOR_OUTPUT_COLUMNS)

        results = []
        for symbol in bars["symbol"].unique():
            sym_bars = bars[bars["symbol"] == symbol].copy()
            sym_bars = sym_bars.sort_values("session_date")

            # Volume z-score
            vol_z = rolling_zscore(sym_bars["volume"], window=self.window)

            # Price direction (1-day return sign)
            price_dir = np.sign(sym_bars["close"].pct_change())

            # Signed volume z-score:
            # high volume + up => positive
            # high volume + down => negative
            # low volume => near zero
            signed_vol_z = vol_z * price_dir

            # Normalize to roughly [-1, +1]
            normalized = signed_vol_z.clip(-3, 3) / 3

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
