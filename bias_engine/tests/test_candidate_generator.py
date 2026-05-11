import pandas as pd

from src.evolution.candidate_generator import generate_factor_quality_candidates


def test_generate_candidate_for_low_coverage_factor():
    quality = pd.DataFrame(
        [
            {
                "factor_name": "rsi_14",
                "coverage": 0.62,
                "extreme_share": 0.01,
                "rows": 100,
            },
            {
                "factor_name": "return_5d",
                "coverage": 0.95,
                "extreme_share": 0.0,
                "rows": 100,
            },
        ]
    )

    candidates = generate_factor_quality_candidates(quality, max_candidates=3)

    assert len(candidates) == 1
    assert candidates[0].experiment_id == "exp-low-coverage-rsi_14"
    assert candidates[0].target_factors == ["rsi_14"]
    assert candidates[0].risk_level == "medium"


def test_generate_candidate_for_extreme_factor_values():
    quality = pd.DataFrame(
        [
            {
                "factor_name": "volume_zscore",
                "coverage": 0.98,
                "extreme_share": 0.16,
                "rows": 100,
            }
        ]
    )

    candidates = generate_factor_quality_candidates(quality, max_candidates=3)

    assert candidates[0].experiment_id == "exp-extreme-values-volume_zscore"
    assert candidates[0].risk_level == "high"


def test_candidate_generator_limits_result_count_by_severity():
    quality = pd.DataFrame(
        [
            {"factor_name": "a", "coverage": 0.50, "extreme_share": 0.20, "rows": 100},
            {"factor_name": "b", "coverage": 0.70, "extreme_share": 0.01, "rows": 100},
            {"factor_name": "c", "coverage": 0.99, "extreme_share": 0.11, "rows": 100},
        ]
    )

    candidates = generate_factor_quality_candidates(quality, max_candidates=2)

    assert len(candidates) == 2
    assert candidates[0].target_factors == ["a"]


def test_candidate_validation_protocols_do_not_share_nested_lists():
    quality = pd.DataFrame(
        [
            {"factor_name": "a", "coverage": 0.50, "extreme_share": 0.01, "rows": 100},
            {"factor_name": "b", "coverage": 0.60, "extreme_share": 0.01, "rows": 100},
        ]
    )

    candidates = generate_factor_quality_candidates(quality, max_candidates=2)
    candidates[0].validation_protocol["primary_metrics"].append("temporary_metric")

    assert "temporary_metric" not in candidates[1].validation_protocol["primary_metrics"]
