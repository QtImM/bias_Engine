import pandas as pd

from src.features.feature_matrix import build_feature_matrix


def test_build_feature_matrix_pivots_factor_names_to_columns():
    factor_values = pd.DataFrame(
        [
            {"symbol": "STAR50", "ts": "2026-05-11", "factor_name": "return_5d", "value": 0.1, "available_at": "2026-05-11"},
            {"symbol": "STAR50", "ts": "2026-05-11", "factor_name": "rsi_14", "value": -0.2, "available_at": "2026-05-11"},
            {"symbol": "HSI", "ts": "2026-05-11", "factor_name": "return_5d", "value": 0.3, "available_at": "2026-05-11"},
        ]
    )

    matrix = build_feature_matrix(factor_values)

    assert list(matrix.columns) == ["symbol", "ts", "return_5d", "rsi_14"]
    assert matrix[matrix["symbol"] == "STAR50"].iloc[0]["rsi_14"] == -0.2
