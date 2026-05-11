# Bias Engine Open Source Evolution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the current `bias_engine` prototype into a reusable multi-timeframe bias research system that can add, disable, validate, and compare factors without rewriting the model core.

**Architecture:** Keep the existing local project as the main system, because it already has a factor registry, YAML configuration, data ingestion, labels, a rule model, and a dashboard. Borrow selected ideas from Qlib, PyBroker, vectorbt, and bt instead of migrating wholesale into a heavy framework.

**Tech Stack:** Python 3.10+, pandas, numpy, pyarrow, DuckDB, YAML, scikit-learn, LightGBM/CatBoost in phase 2, Streamlit, Plotly, optional vectorbt/PyBroker/bt adapters.

---

## Context Snapshot

Current project root:

```text
C:/Users/Tim/Desktop/gpt小人/自进化bias框架
```

Current useful files:

```text
bias_engine/run_pipeline.py
bias_engine/requirements.txt
bias_engine/config/instruments.yaml
bias_engine/config/data_sources.yaml
bias_engine/config/factors.yaml
bias_engine/config/models.yaml
bias_engine/src/data/ingest.py
bias_engine/src/data/normalize.py
bias_engine/src/factors/base.py
bias_engine/src/factors/registry.py
bias_engine/src/labels/make_labels.py
bias_engine/src/models/rule_model.py
bias_engine/src/dashboard/app.py
```

Current design already supports:

```text
FactorSpec
FactorContext
FactorRegistry.from_yaml(...)
enabled: true / false in config/factors.yaml
D1 / W1 / M1 horizons in config/models.yaml
rule_model_v1 predictions
local Parquet outputs under bias_engine/data
```

Open-source projects to use selectively:

```text
microsoft/qlib: borrow data/model workflow concepts and optional later adapter
edtechre/pybroker: borrow walk-forward validation pattern
polakowo/vectorbt: optional fast signal and bias bucket backtesting
pmorissette/bt: optional portfolio-level backtesting
QuantConnect/Lean: keep as future execution engine reference, not first-phase dependency
AI4Finance/FinRL: keep as later research reference, not first-phase dependency
```

## File Structure Target

Create these focused modules:

```text
bias_engine/src/core/schema.py
bias_engine/src/core/paths.py
bias_engine/src/storage/duckdb_store.py
bias_engine/src/quality/data_quality.py
bias_engine/src/quality/factor_quality.py
bias_engine/src/features/feature_matrix.py
bias_engine/src/models/model_registry.py
bias_engine/src/models/sklearn_model.py
bias_engine/src/validation/walk_forward.py
bias_engine/src/validation/backtest_report.py
bias_engine/src/integrations/vectorbt_adapter.py
bias_engine/src/integrations/pybroker_notes.md
bias_engine/docs/open_source_selection.md
bias_engine/docs/factor_lifecycle.md
```

Modify these existing files:

```text
bias_engine/requirements.txt
bias_engine/run_pipeline.py
bias_engine/config/models.yaml
bias_engine/config/factors.yaml
bias_engine/src/factors/base.py
bias_engine/src/factors/registry.py
bias_engine/src/models/rule_model.py
bias_engine/src/dashboard/app.py
```

Testing layout:

```text
bias_engine/tests/test_factor_registry.py
bias_engine/tests/test_available_at_guard.py
bias_engine/tests/test_feature_matrix.py
bias_engine/tests/test_walk_forward.py
bias_engine/tests/test_model_registry.py
```

---

### Task 1: Add Project-Level Schema and Paths

**Files:**
- Create: `bias_engine/src/core/__init__.py`
- Create: `bias_engine/src/core/schema.py`
- Create: `bias_engine/src/core/paths.py`
- Test: `bias_engine/tests/test_core_schema.py`

- [ ] **Step 1: Write the schema test**

```python
from src.core.schema import BiasHorizon, BiasLabel, PredictionRecord


def test_prediction_record_bias_score_is_probability_spread():
    record = PredictionRecord(
        symbol="STAR50",
        ts="2026-05-11",
        horizon=BiasHorizon.D1,
        model_name="rule_model",
        model_version="v1",
        p_down=0.2,
        p_neutral=0.3,
        p_up=0.5,
        confidence=0.4,
        top_factors_json="[]",
    )

    assert record.bias_score == 0.3
    assert record.label == BiasLabel.BULLISH
```

- [ ] **Step 2: Run test and verify it fails**

Run:

```powershell
cd "C:\Users\Tim\Desktop\gpt小人\自进化bias框架\bias_engine"
python -m pytest tests/test_core_schema.py -v
```

Expected: fail because `src.core.schema` does not exist.

- [ ] **Step 3: Create `schema.py`**

```python
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class BiasHorizon(str, Enum):
    D1 = "D1"
    W1 = "W1"
    M1 = "M1"


class BiasLabel(str, Enum):
    BULLISH = "bullish"
    NEUTRAL = "neutral"
    BEARISH = "bearish"


@dataclass(frozen=True)
class PredictionRecord:
    symbol: str
    ts: str
    horizon: BiasHorizon
    model_name: str
    model_version: str
    p_down: float
    p_neutral: float
    p_up: float
    confidence: float
    top_factors_json: str

    @property
    def bias_score(self) -> float:
        return round(self.p_up - self.p_down, 10)

    @property
    def label(self) -> BiasLabel:
        if self.bias_score > 0.3:
            return BiasLabel.BULLISH
        if self.bias_score < -0.3:
            return BiasLabel.BEARISH
        return BiasLabel.NEUTRAL
```

- [ ] **Step 4: Create `paths.py`**

```python
from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = PROJECT_ROOT / "config"
DATA_DIR = PROJECT_ROOT / "data"
DB_DIR = PROJECT_ROOT / "db"
```

- [ ] **Step 5: Run test and commit**

Run:

```powershell
python -m pytest tests/test_core_schema.py -v
```

Expected: pass.

Commit:

```powershell
git add bias_engine/src/core bias_engine/tests/test_core_schema.py
git commit -m "feat: add core bias schema"
```

If this folder is not a git repository, skip the commit and record the changed files in the session summary.

---

### Task 2: Add Point-in-Time Guard for `available_at`

**Files:**
- Modify: `bias_engine/src/factors/base.py`
- Create: `bias_engine/tests/test_available_at_guard.py`

- [ ] **Step 1: Write failing test for data leakage prevention**

```python
import datetime as dt

import pandas as pd

from src.factors.base import FactorContext


def test_load_bars_filters_by_available_at_when_prediction_time_is_set():
    bars = pd.DataFrame(
        [
            {
                "symbol": "NDX",
                "timeframe": "1d",
                "ts": pd.Timestamp("2026-05-08"),
                "session_date": dt.date(2026, 5, 8),
                "close": 100.0,
                "available_at": pd.Timestamp("2026-05-09 06:00:00"),
            },
            {
                "symbol": "NDX",
                "timeframe": "1d",
                "ts": pd.Timestamp("2026-05-11"),
                "session_date": dt.date(2026, 5, 11),
                "close": 110.0,
                "available_at": pd.Timestamp("2026-05-12 06:00:00"),
            },
        ]
    )
    ctx = FactorContext(
        symbols=["NDX"],
        start=dt.date(2026, 5, 1),
        end=dt.date(2026, 5, 11),
        bars=bars,
        prediction_time=pd.Timestamp("2026-05-11 20:00:00"),
    )

    result = ctx.load_bars(fields=["close"])

    assert result["session_date"].tolist() == [dt.date(2026, 5, 8)]
```

- [ ] **Step 2: Run test and verify it fails**

Run:

```powershell
python -m pytest tests/test_available_at_guard.py -v
```

Expected: fail because `FactorContext.__init__` does not accept `prediction_time`.

- [ ] **Step 3: Extend `FactorContext`**

Modify `bias_engine/src/factors/base.py`:

```python
    def __init__(
        self,
        symbols: list[str],
        start: dt.date,
        end: dt.date,
        bars: pd.DataFrame,
        prediction_time: pd.Timestamp | None = None,
    ):
        self.symbols = symbols
        self.start = start
        self.end = end
        self.prediction_time = prediction_time
        self._bars = bars.copy()
```

In `load_bars`, after date filtering and before selecting fields, add:

```python
        if self.prediction_time is not None and "available_at" in df.columns:
            available_at = pd.to_datetime(df["available_at"])
            df = df[available_at <= self.prediction_time]
```

- [ ] **Step 4: Pass `prediction_time` through registry sub-contexts**

Modify `bias_engine/src/factors/registry.py` inside `compute_all`:

```python
                sub_ctx = FactorContext(
                    symbols=active_symbols,
                    start=ctx.start,
                    end=ctx.end,
                    bars=sub_bars,
                    prediction_time=ctx.prediction_time,
                )
```

- [ ] **Step 5: Run tests**

Run:

```powershell
python -m pytest tests/test_available_at_guard.py tests/test_factor_registry.py -v
```

Expected: available-at test passes; if registry test does not exist yet, run only `tests/test_available_at_guard.py`.

---

### Task 3: Add DuckDB Store Without Replacing Parquet

**Files:**
- Create: `bias_engine/src/storage/__init__.py`
- Create: `bias_engine/src/storage/duckdb_store.py`
- Test: `bias_engine/tests/test_duckdb_store.py`

- [ ] **Step 1: Write storage test**

```python
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
```

- [ ] **Step 2: Run test and verify it fails**

Run:

```powershell
python -m pytest tests/test_duckdb_store.py -v
```

Expected: fail because `src.storage.duckdb_store` does not exist.

- [ ] **Step 3: Create DuckDB store**

```python
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
```

- [ ] **Step 4: Run storage test**

Run:

```powershell
python -m pytest tests/test_duckdb_store.py -v
```

Expected: pass.

---

### Task 4: Add Factor Quality Reports

**Files:**
- Create: `bias_engine/src/quality/__init__.py`
- Create: `bias_engine/src/quality/factor_quality.py`
- Test: `bias_engine/tests/test_factor_quality.py`

- [ ] **Step 1: Write quality test**

```python
import pandas as pd

from src.quality.factor_quality import summarize_factor_quality


def test_factor_quality_reports_coverage_and_extreme_share():
    factor_values = pd.DataFrame(
        {
            "symbol": ["STAR50", "STAR50", "HSI", "HSI"],
            "factor_name": ["rsi_14", "rsi_14", "rsi_14", "rsi_14"],
            "value": [0.1, 0.2, 100.0, None],
        }
    )

    report = summarize_factor_quality(factor_values)

    assert report.loc[0, "factor_name"] == "rsi_14"
    assert report.loc[0, "rows"] == 4
    assert report.loc[0, "coverage"] == 0.75
    assert report.loc[0, "extreme_share"] == 0.25
```

- [ ] **Step 2: Run test and verify it fails**

Run:

```powershell
python -m pytest tests/test_factor_quality.py -v
```

Expected: fail because quality module does not exist.

- [ ] **Step 3: Create factor quality module**

```python
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
```

- [ ] **Step 4: Add quality step to pipeline**

Modify `bias_engine/run_pipeline.py` with a new function:

```python
def step_factor_quality(factor_values: pd.DataFrame) -> pd.DataFrame:
    from src.quality.factor_quality import summarize_factor_quality

    logger.info("=== Factor Quality Report ===")
    report = summarize_factor_quality(factor_values)
    output_dir = DATA_DIR / "features"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "factor_quality.parquet"
    report.to_parquet(output_path, index=False)
    logger.info(f"Saved factor quality report to {output_path}")
    return report
```

Call it after `step_factors(bars)` in the `all` path:

```python
        factor_values = step_factors(bars)
        if not factor_values.empty:
            step_factor_quality(factor_values)
```

- [ ] **Step 5: Run tests**

Run:

```powershell
python -m pytest tests/test_factor_quality.py -v
```

Expected: pass.

---

### Task 5: Build a Feature Matrix Layer

**Files:**
- Create: `bias_engine/src/features/__init__.py`
- Create: `bias_engine/src/features/feature_matrix.py`
- Test: `bias_engine/tests/test_feature_matrix.py`

- [ ] **Step 1: Write matrix test**

```python
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
```

- [ ] **Step 2: Run test and verify it fails**

Run:

```powershell
python -m pytest tests/test_feature_matrix.py -v
```

Expected: fail because feature module does not exist.

- [ ] **Step 3: Create feature matrix builder**

```python
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
```

- [ ] **Step 4: Save feature matrix in pipeline**

Modify `bias_engine/run_pipeline.py` after factor computation:

```python
        from src.features.feature_matrix import build_feature_matrix

        feature_matrix = build_feature_matrix(factor_values)
        matrix_path = DATA_DIR / "features" / "feature_matrix.parquet"
        feature_matrix.to_parquet(matrix_path, index=False)
        logger.info(f"Saved feature matrix to {matrix_path}")
```

- [ ] **Step 5: Run tests**

Run:

```powershell
python -m pytest tests/test_feature_matrix.py -v
```

Expected: pass.

---

### Task 6: Add Walk-Forward Validation

**Files:**
- Create: `bias_engine/src/validation/__init__.py`
- Create: `bias_engine/src/validation/walk_forward.py`
- Test: `bias_engine/tests/test_walk_forward.py`

- [ ] **Step 1: Write split test**

```python
import pandas as pd

from src.validation.walk_forward import make_walk_forward_splits


def test_walk_forward_splits_use_embargo_gap():
    dates = pd.date_range("2026-01-01", periods=120, freq="D")
    splits = make_walk_forward_splits(
        dates=dates,
        train_size=60,
        test_size=20,
        embargo=10,
        step_size=20,
    )

    first = splits[0]
    assert first.train_start == dates[0]
    assert first.train_end == dates[59]
    assert first.test_start == dates[70]
    assert first.test_end == dates[89]
```

- [ ] **Step 2: Run test and verify it fails**

Run:

```powershell
python -m pytest tests/test_walk_forward.py -v
```

Expected: fail because validation module does not exist.

- [ ] **Step 3: Create walk-forward module**

```python
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class WalkForwardSplit:
    train_start: pd.Timestamp
    train_end: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp


def make_walk_forward_splits(
    dates: pd.DatetimeIndex,
    train_size: int,
    test_size: int,
    embargo: int,
    step_size: int,
) -> list[WalkForwardSplit]:
    unique_dates = pd.DatetimeIndex(sorted(pd.unique(dates)))
    splits: list[WalkForwardSplit] = []
    start = 0
    while True:
        train_start_idx = start
        train_end_idx = train_start_idx + train_size - 1
        test_start_idx = train_end_idx + embargo + 1
        test_end_idx = test_start_idx + test_size - 1
        if test_end_idx >= len(unique_dates):
            break
        splits.append(
            WalkForwardSplit(
                train_start=unique_dates[train_start_idx],
                train_end=unique_dates[train_end_idx],
                test_start=unique_dates[test_start_idx],
                test_end=unique_dates[test_end_idx],
            )
        )
        start += step_size
    return splits
```

- [ ] **Step 4: Run tests**

Run:

```powershell
python -m pytest tests/test_walk_forward.py -v
```

Expected: pass.

---

### Task 7: Add Model Registry for Reproducible Versions

**Files:**
- Create: `bias_engine/src/models/model_registry.py`
- Test: `bias_engine/tests/test_model_registry.py`

- [ ] **Step 1: Write registry test**

```python
from src.models.model_registry import ModelRegistry


def test_model_registry_writes_version_metadata(tmp_path):
    registry = ModelRegistry(tmp_path)
    record = registry.register(
        model_name="rule_model",
        model_version="rule_model_v1",
        feature_set_version="feature_set_v1",
        label_version="label_v1",
        metrics={"macro_f1": 0.42},
    )

    assert record["model_version"] == "rule_model_v1"
    assert (tmp_path / "model_registry.jsonl").exists()
```

- [ ] **Step 2: Run test and verify it fails**

Run:

```powershell
python -m pytest tests/test_model_registry.py -v
```

Expected: fail because `model_registry.py` does not exist.

- [ ] **Step 3: Create model registry**

```python
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class ModelRegistry:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "model_registry.jsonl"

    def register(
        self,
        model_name: str,
        model_version: str,
        feature_set_version: str,
        label_version: str,
        metrics: dict[str, Any],
    ) -> dict[str, Any]:
        record = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "model_name": model_name,
            "model_version": model_version,
            "feature_set_version": feature_set_version,
            "label_version": label_version,
            "metrics": metrics,
        }
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        return record
```

- [ ] **Step 4: Run tests**

Run:

```powershell
python -m pytest tests/test_model_registry.py -v
```

Expected: pass.

---

### Task 8: Add Supervised ML Model Behind the Existing Rule Baseline

**Files:**
- Modify: `bias_engine/requirements.txt`
- Create: `bias_engine/src/models/sklearn_model.py`
- Modify: `bias_engine/config/models.yaml`
- Test: `bias_engine/tests/test_sklearn_model.py`

- [ ] **Step 1: Add dependency**

Modify `bias_engine/requirements.txt`:

```text
lightgbm>=4.0.0
joblib>=1.3.0
```

Keep `scikit-learn>=1.3.0` because it is already present.

- [ ] **Step 2: Write model smoke test**

```python
import pandas as pd

from src.models.sklearn_model import train_multiclass_model


def test_train_multiclass_model_returns_probability_columns():
    X = pd.DataFrame(
        {
            "return_5d": [-1.0, -0.5, 0.0, 0.5, 1.0, 1.5],
            "rsi_14": [0.8, 0.6, 0.0, -0.2, -0.6, -0.8],
        }
    )
    y = pd.Series([-1, -1, 0, 0, 1, 1])

    model = train_multiclass_model(X, y, random_state=7)
    probabilities = model.predict_proba(X)

    assert probabilities.shape == (6, 3)
```

- [ ] **Step 3: Run test and verify it fails**

Run:

```powershell
python -m pytest tests/test_sklearn_model.py -v
```

Expected: fail because `sklearn_model.py` does not exist.

- [ ] **Step 4: Create sklearn model module**

```python
from __future__ import annotations

import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer


def train_multiclass_model(
    X: pd.DataFrame,
    y: pd.Series,
    random_state: int = 42,
) -> Pipeline:
    model = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            (
                "classifier",
                HistGradientBoostingClassifier(
                    max_iter=200,
                    learning_rate=0.05,
                    l2_regularization=0.05,
                    random_state=random_state,
                ),
            ),
        ]
    )
    model.fit(X, y)
    return model
```

- [ ] **Step 5: Add model config**

Append to `bias_engine/config/models.yaml`:

```yaml
  sklearn_model:
    name: "sklearn_hgb_v1"
    type: "hist_gradient_boosting"
    description: "Three-class supervised baseline using feature matrix and labels"
    random_state: 42
    min_train_rows: 120
```

- [ ] **Step 6: Run tests**

Run:

```powershell
python -m pytest tests/test_sklearn_model.py -v
```

Expected: pass.

---

### Task 9: Add Bias Bucket Backtest Report

**Files:**
- Create: `bias_engine/src/validation/backtest_report.py`
- Test: `bias_engine/tests/test_backtest_report.py`

- [ ] **Step 1: Write bucket test**

```python
import pandas as pd

from src.validation.backtest_report import summarize_bias_buckets


def test_summarize_bias_buckets_groups_forward_returns():
    df = pd.DataFrame(
        {
            "bias_score": [-0.8, -0.4, 0.0, 0.4, 0.8],
            "fwd_return": [-0.03, -0.01, 0.0, 0.02, 0.04],
        }
    )

    report = summarize_bias_buckets(df)

    assert set(report["bucket"]) == {"bearish", "neutral", "bullish"}
    assert report.loc[report["bucket"] == "bullish", "mean_return"].iloc[0] == 0.03
```

- [ ] **Step 2: Run test and verify it fails**

Run:

```powershell
python -m pytest tests/test_backtest_report.py -v
```

Expected: fail because report module does not exist.

- [ ] **Step 3: Create report module**

```python
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
```

- [ ] **Step 4: Run tests**

Run:

```powershell
python -m pytest tests/test_backtest_report.py -v
```

Expected: pass.

---

### Task 10: Add Optional vectorbt Adapter

**Files:**
- Modify: `bias_engine/requirements.txt`
- Create: `bias_engine/src/integrations/__init__.py`
- Create: `bias_engine/src/integrations/vectorbt_adapter.py`
- Test: `bias_engine/tests/test_vectorbt_adapter.py`

- [ ] **Step 1: Add optional dependency comment**

Modify `requirements.txt`:

```text
# Optional backtest adapter
# vectorbt>=1.0.0
```

Keep it commented at first because vectorbt has license and dependency implications.

- [ ] **Step 2: Write adapter test without requiring vectorbt**

```python
import pandas as pd

from src.integrations.vectorbt_adapter import make_long_only_signals


def test_make_long_only_signals_turns_bullish_bias_into_entries():
    predictions = pd.DataFrame(
        {
            "ts": pd.date_range("2026-05-01", periods=4),
            "symbol": ["NDX"] * 4,
            "bias_score": [0.1, 0.4, 0.5, -0.2],
        }
    )

    signals = make_long_only_signals(predictions, threshold=0.3)

    assert signals["entry"].tolist() == [False, True, False, False]
    assert signals["exit"].tolist() == [False, False, False, True]
```

- [ ] **Step 3: Create adapter**

```python
from __future__ import annotations

import pandas as pd


def make_long_only_signals(predictions: pd.DataFrame, threshold: float = 0.3) -> pd.DataFrame:
    work = predictions.sort_values(["symbol", "ts"]).copy()
    is_bullish = work["bias_score"] > threshold
    prev_bullish = is_bullish.groupby(work["symbol"]).shift(1, fill_value=False)
    work["entry"] = is_bullish & ~prev_bullish
    work["exit"] = ~is_bullish & prev_bullish
    return work[["symbol", "ts", "entry", "exit"]]
```

- [ ] **Step 4: Run adapter test**

Run:

```powershell
python -m pytest tests/test_vectorbt_adapter.py -v
```

Expected: pass.

---

### Task 11: Document Open-Source Selection

**Files:**
- Create: `bias_engine/docs/open_source_selection.md`

- [ ] **Step 1: Create docs directory**

Run:

```powershell
New-Item -ItemType Directory -Force "C:\Users\Tim\Desktop\gpt小人\自进化bias框架\bias_engine\docs"
```

- [ ] **Step 2: Write open-source selection document**

Content:

```markdown
# Open Source Selection

This project keeps `bias_engine` as the main system and borrows selected capabilities from existing projects.

## Adopt as Concepts

`microsoft/qlib` is the main conceptual reference. We borrow its separation between data, features, labels, model training, rolling validation, backtest analysis, and online-style prediction.

`edtechre/pybroker` is the validation reference. We borrow the walk-forward mindset and model registration pattern, but keep our own feature matrix because this project predicts multi-timeframe bias rather than directly executing trades.

## Optional Adapters

`polakowo/vectorbt` is useful for fast signal tests and bias bucket return experiments. It remains optional because it is not needed to generate daily bias predictions.

`pmorissette/bt` is useful for portfolio-level rebalancing tests after single-index bias quality is stable.

## Not First-Phase Dependencies

`QuantConnect/Lean` is a professional execution and backtesting engine, but it is too heavy for the first phase.

`AI4Finance/FinRL` is useful for later reinforcement learning research, but the current project should first prove that its factor and label pipeline is reliable.
```

- [ ] **Step 3: Confirm document exists**

Run:

```powershell
Test-Path "C:\Users\Tim\Desktop\gpt小人\自进化bias框架\bias_engine\docs\open_source_selection.md"
```

Expected: `True`.

---

### Task 12: Document Factor Lifecycle

**Files:**
- Create: `bias_engine/docs/factor_lifecycle.md`

- [ ] **Step 1: Write lifecycle document**

Content:

```markdown
# Factor Lifecycle

Every factor moves through the same lifecycle.

## Add

1. Create a factor class that exposes `spec` and `compute(ctx)`.
2. Register it in `config/factors.yaml`.
3. Run the factor step and save `factor_values.parquet`.
4. Run the factor quality report.
5. Build a feature matrix.
6. Train or score with the current model.
7. Compare against the previous champion model.

## Disable

Set `enabled: false` in `config/factors.yaml`.

Do not delete the factor file when disabling a factor. Historical model versions must remain reproducible.

## Promote

A factor can enter the champion feature set only when:

1. Coverage is high enough for the target symbols and horizons.
2. `available_at` is not later than prediction time.
3. Extreme values are explainable.
4. Correlation with existing factors is not redundant.
5. Walk-forward validation improves at least one target horizon without materially damaging the others.

## Version

Changing a factor formula changes `factor_version`.

Example:

```text
ema_slope v1.0.0 = EMA20 five-day slope
ema_slope v1.1.0 = EMA20 five-day slope divided by realized volatility
```
```

- [ ] **Step 2: Confirm document exists**

Run:

```powershell
Test-Path "C:\Users\Tim\Desktop\gpt小人\自进化bias框架\bias_engine\docs\factor_lifecycle.md"
```

Expected: `True`.

---

### Task 13: Dashboard Upgrade for Bias Explainability

**Files:**
- Modify: `bias_engine/src/dashboard/app.py`

- [ ] **Step 1: Add dashboard sections**

Add three visible sections:

```text
Current Bias Matrix
Bias History
Top Factor Contributions
```

- [ ] **Step 2: Ensure current bias matrix shows all horizons**

Expected table shape:

```text
symbol | D1_score | D1_label | W1_score | W1_label | M1_score | M1_label
```

- [ ] **Step 3: Add stale data warning**

If latest prediction date is more than 3 calendar days before current date, show:

```text
Data may be stale. Latest prediction date: <date>
```

- [ ] **Step 4: Run dashboard**

Run:

```powershell
cd "C:\Users\Tim\Desktop\gpt小人\自进化bias框架\bias_engine"
streamlit run src/dashboard/app.py
```

Expected: dashboard starts and shows no import errors.

---

### Task 14: End-to-End Verification Script

**Files:**
- Create: `bias_engine/scripts/verify_pipeline.ps1`

- [ ] **Step 1: Create scripts directory**

Run:

```powershell
New-Item -ItemType Directory -Force "C:\Users\Tim\Desktop\gpt小人\自进化bias框架\bias_engine\scripts"
```

- [ ] **Step 2: Create verification script**

Content:

```powershell
$ErrorActionPreference = "Stop"
Set-Location "C:\Users\Tim\Desktop\gpt小人\自进化bias框架\bias_engine"

python -m pytest tests -v
python run_pipeline.py --step all --start 2023-01-01

$required = @(
  "data/features/factor_values.parquet",
  "data/features/feature_matrix.parquet",
  "data/features/factor_quality.parquet",
  "data/labels/labels.parquet",
  "data/predictions/predictions.parquet"
)

foreach ($path in $required) {
  if (-not (Test-Path $path)) {
    throw "Missing expected output: $path"
  }
}

Write-Host "Bias engine verification passed."
```

- [ ] **Step 3: Run verification**

Run:

```powershell
.\scripts\verify_pipeline.ps1
```

Expected: tests pass, pipeline completes, required outputs exist.

---

## Phase Roadmap

### Phase 1: Reliable Rule-Based Bias Engine

Deliverables:

```text
D1/W1/M1 bias for STAR50, HSI, NDX
factor plugin registry
available_at guard
factor quality report
feature matrix
rule model predictions
Streamlit dashboard
```

Success criteria:

```text
Pipeline runs from ingestion to report
Every prediction has model_version and factor source
Every factor can be disabled from YAML
No prediction uses data with available_at after prediction_time
```

### Phase 2: ML Champion/Challenger

Deliverables:

```text
feature_matrix.parquet
labels.parquet
sklearn_hgb_v1 or LightGBM model
walk-forward validation
model_registry.jsonl
champion vs challenger comparison
```

Success criteria:

```text
ML model beats rule model on at least one horizon out-of-sample
No horizon materially degrades without being marked experimental
Training and validation windows are separated by embargo
```

### Phase 3: Cross-Market and Regime

Deliverables:

```text
VIX/VXN or ETF proxies
DXY and USD/CNH factors
QQQ / SOX / HSTECH proxies
regime labels: risk_on, risk_off, high_vol, trend, range
regime-adjusted ensemble
```

Success criteria:

```text
Dashboard explains both raw model bias and regime adjustment
Regime analysis shows where factors work or fail
```

### Phase 4: Breadth and Constituents

Deliverables:

```text
constituent universe tables
historical constituent handling
pct_above_ma20
pct_above_ma60
advance_decline_ratio
equal_weight_relative_strength
```

Success criteria:

```text
Breadth factors improve W1 or M1 validation
Survivorship bias is explicitly controlled or marked as a limitation
```

### Phase 5: Event and LLM Factors

Deliverables:

```text
news/event schema
policy support score
AI/semiconductor theme heat
region and sector sentiment
effective_horizon metadata
```

Success criteria:

```text
Event factors are stored with source URL, extraction time, confidence, and available_at
Event factors are not allowed into champion model without walk-forward evidence
```

---

## Verification Before Completion

Run these commands before calling the implementation complete:

```powershell
cd "C:\Users\Tim\Desktop\gpt小人\自进化bias框架\bias_engine"
python -m pytest tests -v
python run_pipeline.py --step all --start 2023-01-01
```

Manual checks:

```text
Open Streamlit dashboard
Confirm STAR50, HSI, NDX appear
Confirm D1, W1, M1 appear for each symbol
Disable one factor in config/factors.yaml and rerun factors
Confirm output changes without editing model code
Inspect factor_quality.parquet for coverage and extreme_share
Inspect predictions.parquet for model_version and top factor fields
```

## Self-Review

Spec coverage:

```text
Multi-timeframe bias: covered by schema, model config, dashboard tasks
Add/remove factors through interface: covered by FactorRegistry and factor lifecycle
Local storage: covered by Parquet plus DuckDB store
Open-source reuse: covered by selection doc and optional adapters
TradingView/data source flexibility: preserved by keeping charting separate from core data
Long-horizon framework: covered by D1/W1/M1 labels and walk-forward validation
```

Placeholder scan:

```text
No empty task bodies are intentionally left in this plan.
Every code-producing task includes concrete code or exact expected behavior.
```

Type consistency:

```text
Horizon names use D1, W1, M1 consistently.
Prediction probability fields use p_down, p_neutral, p_up consistently.
Factor matrix keys use symbol, ts, factor_name, value consistently.
```
