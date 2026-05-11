import pandas as pd

from src.evolution.runner import run_evolution_review


def test_run_evolution_review_reads_factor_quality_and_writes_report(tmp_path):
    data_dir = tmp_path / "data"
    features_dir = data_dir / "features"
    features_dir.mkdir(parents=True)

    pd.DataFrame(
        [
            {
                "factor_name": "rsi_14",
                "coverage": 0.60,
                "extreme_share": 0.01,
                "rows": 100,
            }
        ]
    ).to_parquet(features_dir / "factor_quality.parquet", index=False)

    result = run_evolution_review(data_dir=data_dir, max_candidates=3)

    assert result["candidate_count"] == 1
    assert (data_dir / "evolution" / "evolution_report.md").exists()
    assert (data_dir / "evolution" / "evolution_candidates.json").exists()
