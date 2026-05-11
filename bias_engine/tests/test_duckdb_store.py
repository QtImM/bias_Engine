import pandas as pd

from src.storage.duckdb_store import DuckDbStore


def test_store_roundtrips_factor_values(tmp_path):
    db_path = tmp_path / "bias_engine.duckdb"
    store = DuckDbStore(db_path)
    df = pd.DataFrame(
        [
            {
                "symbol": "STAR50",
                "ts": pd.Timestamp("2026-05-11"),
                "timeframe": "1d",
                "factor_name": "return_5d",
                "factor_version": "1.0.0",
                "value": 0.12,
                "available_at": pd.Timestamp("2026-05-11 15:30:00"),
                "quality_score": 1.0,
            }
        ]
    )

    store.write_table("factor_values", df)
    result = store.read_table("factor_values")

    assert result.shape[0] == 1
    assert result.loc[0, "factor_name"] == "return_5d"
