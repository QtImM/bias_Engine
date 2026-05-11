from __future__ import annotations

import numpy as np
import pandas as pd


def bias_bucket(score: float) -> str:
    if score > 0.3:
        return "bullish"
    if score < -0.3:
        return "bearish"
    return "neutral"


def summarize_bias_buckets(df: pd.DataFrame) -> pd.DataFrame:
    work = df.copy()
    work["bucket"] = work["bias_score"].map(bias_bucket)
    report = (
        work.groupby("bucket", as_index=False)
        .agg(
            rows=("fwd_return", "size"),
            mean_return=("fwd_return", "mean"),
            hit_ratio=("fwd_return", lambda x: float((np.sign(x) > 0).mean())),
        )
        .sort_values("bucket")
        .reset_index(drop=True)
    )
    return report
