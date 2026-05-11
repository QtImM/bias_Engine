from __future__ import annotations

import numpy as np
import pandas as pd


def summarize_factor_quality(factor_values: pd.DataFrame, extreme_abs: float = 10.0) -> pd.DataFrame:
    rows = []
    for factor_name, group in factor_values.groupby("factor_name"):
        values = pd.to_numeric(group["value"], errors="coerce")
        non_null = values.notna()
        rows.append(
            {
                "factor_name": factor_name,
                "rows": int(len(group)),
                "coverage": float(non_null.mean()) if len(group) else 0.0,
                "mean": float(values.mean()) if non_null.any() else np.nan,
                "std": float(values.std()) if non_null.sum() > 1 else np.nan,
                "min": float(values.min()) if non_null.any() else np.nan,
                "max": float(values.max()) if non_null.any() else np.nan,
                "extreme_share": float((values.abs() > extreme_abs).mean()) if len(group) else 0.0,
            }
        )
    return pd.DataFrame(rows).sort_values("factor_name").reset_index(drop=True)
