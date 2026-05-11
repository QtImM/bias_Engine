from __future__ import annotations

import pandas as pd


def build_feature_matrix(factor_values: pd.DataFrame) -> pd.DataFrame:
    required = {"symbol", "ts", "factor_name", "value"}
    missing = required - set(factor_values.columns)
    if missing:
        raise ValueError(f"factor_values missing columns: {sorted(missing)}")

    matrix = (
        factor_values.pivot_table(
            index=["symbol", "ts"],
            columns="factor_name",
            values="value",
            aggfunc="last",
        )
        .reset_index()
    )
    matrix.columns.name = None
    feature_cols = sorted([c for c in matrix.columns if c not in {"symbol", "ts"}])
    return matrix[["symbol", "ts", *feature_cols]]
