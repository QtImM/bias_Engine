from __future__ import annotations

from copy import deepcopy
import math

import pandas as pd

from src.evolution.schema import CandidateExperiment, CandidateType


DEFAULT_VALIDATION_PROTOCOL = {
    "method": "walk_forward_backtest",
    "train_window": "rolling",
    "embargo_required": True,
    "primary_metrics": [
        "macro_f1",
        "directional_hit_rate",
        "mean_forward_return_by_bucket",
    ],
    "required_comparison": "challenger_vs_champion",
    "promotion_rule": "no_material_horizon_degradation_and_positive_average_delta",
}

DEFAULT_POINT_IN_TIME_REQUIREMENTS = [
    "factor_values.available_at <= prediction_time",
    "labels must not be joined into prediction features",
    "train/test split must follow chronological order",
    "no random shuffle across dates",
    "factor formula must use only data available at or before prediction_time",
]


def _clean_factor_name(value: object) -> str:
    return str(value).strip()


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    if math.isnan(result):
        return default
    return result


def generate_factor_quality_candidates(
    quality: pd.DataFrame,
    coverage_threshold: float = 0.80,
    extreme_threshold: float = 0.10,
    max_candidates: int = 3,
) -> list[CandidateExperiment]:
    required = {"factor_name", "coverage", "extreme_share"}
    missing = required - set(quality.columns)
    if missing:
        raise ValueError(f"factor quality missing columns: {sorted(missing)}")

    scored: list[tuple[float, CandidateExperiment]] = []

    for _, row in quality.iterrows():
        factor_name = _clean_factor_name(row["factor_name"])
        coverage = _safe_float(row["coverage"])
        extreme_share = _safe_float(row["extreme_share"])

        if coverage < coverage_threshold:
            severity = coverage_threshold - coverage
            scored.append(
                (
                    severity,
                    CandidateExperiment(
                        experiment_id=f"exp-low-coverage-{factor_name}",
                        candidate_type=CandidateType.ADJUST_FACTOR_WEIGHT,
                        title=f"测试降低 {factor_name} 权重",
                        rationale=(
                            f"{factor_name} coverage={coverage:.2f}，低于阈值 "
                            f"{coverage_threshold:.2f}。先测试降权，避免直接删除导致历史不可复现。"
                        ),
                        target_factors=[factor_name],
                        target_horizons=["D1", "W1", "M1"],
                        expected_effect="降低低覆盖率因子对 bias_score 的不稳定影响。",
                        risk_level="medium",
                        evidence={
                            "coverage": coverage,
                            "coverage_threshold": coverage_threshold,
                        },
                        validation_protocol=deepcopy(DEFAULT_VALIDATION_PROTOCOL),
                        point_in_time_requirements=DEFAULT_POINT_IN_TIME_REQUIREMENTS.copy(),
                        ai_readable_summary=(
                            f"这是关于 {factor_name} 的待验证降权实验，不是有效性结论。"
                            "请只通过无未来函数 walk-forward 回测判断是否有效。"
                        ),
                    ),
                )
            )

        if extreme_share > extreme_threshold:
            severity = 1.0 + (extreme_share - extreme_threshold)
            scored.append(
                (
                    severity,
                    CandidateExperiment(
                        experiment_id=f"exp-extreme-values-{factor_name}",
                        candidate_type=CandidateType.ADJUST_FACTOR_WEIGHT,
                        title=f"检查 {factor_name} 极值并测试稳健化",
                        rationale=(
                            f"{factor_name} extreme_share={extreme_share:.2f}，高于阈值 "
                            f"{extreme_threshold:.2f}。建议测试 winsorize、clip 或降权版本。"
                        ),
                        target_factors=[factor_name],
                        target_horizons=["D1", "W1", "M1"],
                        expected_effect="减少极端值对短期和中期 bias 的过度拉动。",
                        risk_level="high",
                        evidence={
                            "extreme_share": extreme_share,
                            "extreme_threshold": extreme_threshold,
                        },
                        validation_protocol=deepcopy(DEFAULT_VALIDATION_PROTOCOL),
                        point_in_time_requirements=DEFAULT_POINT_IN_TIME_REQUIREMENTS.copy(),
                        ai_readable_summary=(
                            f"这是关于 {factor_name} 极值稳健化的待验证实验，不是有效性结论。"
                            "请只通过无未来函数 walk-forward 回测判断是否有效。"
                        ),
                    ),
                )
            )

    scored.sort(key=lambda item: item[0], reverse=True)
    return [candidate for _, candidate in scored[:max_candidates]]
