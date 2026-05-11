from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from src.evolution.candidate_generator import generate_factor_quality_candidates
from src.evolution.evolution_report import write_evolution_report
from src.evolution.schema import PromotionDecision


def _read_parquet_if_exists(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_parquet(path)


def run_evolution_review(
    data_dir: str | Path,
    max_candidates: int = 3,
) -> dict[str, Any]:
    data_path = Path(data_dir)
    quality_path = data_path / "features" / "factor_quality.parquet"
    factor_quality = _read_parquet_if_exists(quality_path)

    if factor_quality.empty:
        candidates = []
        source_summary = {
            "factor_quality_path": str(quality_path),
            "factor_quality_rows": 0,
            "warning": "factor_quality.parquet missing or empty",
        }
    else:
        candidates = generate_factor_quality_candidates(
            factor_quality,
            max_candidates=max_candidates,
        )
        source_summary = {
            "factor_quality_path": str(quality_path),
            "factor_quality_rows": int(len(factor_quality)),
            "candidate_count": len(candidates),
        }

    promotion_decision = PromotionDecision(
        status="hold",
        reason="Evolution Loop v1 只生成候选实验，不自动晋级模型。",
        metrics={},
        risk_flags=["manual_review_required"],
    )

    report_paths = write_evolution_report(
        output_dir=data_path / "evolution",
        candidates=candidates,
        promotion_decision=promotion_decision,
        source_summary=source_summary,
    )

    return {
        "candidate_count": len(candidates),
        "report_paths": {key: str(value) for key, value in report_paths.items()},
    }
