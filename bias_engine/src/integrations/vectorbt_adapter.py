from __future__ import annotations

import pandas as pd


def make_long_only_signals(predictions: pd.DataFrame, threshold: float = 0.3) -> pd.DataFrame:
    work = predictions.sort_values(["symbol", "ts"]).copy()
    is_bullish = work["bias_score"] > threshold
    prev_bullish = is_bullish.groupby(work["symbol"]).shift(1, fill_value=False)
    work["entry"] = is_bullish & ~prev_bullish
    work["exit"] = ~is_bullish & prev_bullish
    return work[["symbol", "ts", "entry", "exit"]]
