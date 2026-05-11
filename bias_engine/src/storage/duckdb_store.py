from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd


class DuckDbStore:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def write_table(self, table_name: str, df: pd.DataFrame) -> None:
        with duckdb.connect(str(self.db_path)) as conn:
            conn.register("input_df", df)
            conn.execute(f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM input_df")

    def append_table(self, table_name: str, df: pd.DataFrame) -> None:
        with duckdb.connect(str(self.db_path)) as conn:
            conn.register("input_df", df)
            exists = conn.execute(
                "SELECT count(*) FROM information_schema.tables WHERE table_name = ?",
                [table_name],
            ).fetchone()[0]
            if exists:
                conn.execute(f"INSERT INTO {table_name} SELECT * FROM input_df")
            else:
                conn.execute(f"CREATE TABLE {table_name} AS SELECT * FROM input_df")

    def read_table(self, table_name: str) -> pd.DataFrame:
        with duckdb.connect(str(self.db_path)) as conn:
            return conn.execute(f"SELECT * FROM {table_name}").df()
