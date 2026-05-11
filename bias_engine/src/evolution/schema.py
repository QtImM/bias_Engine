from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class CandidateType(str, Enum):
    DISABLE_FACTOR = "disable_factor"
    ADJUST_FACTOR_WEIGHT = "adjust_factor_weight"
    HORIZON_SPECIFIC_FACTOR = "horizon_specific_factor"
    REDUNDANCY_REVIEW = "redundancy_review"
    REGIME_FILTER = "regime_filter"
    MODEL_CHALLENGER = "model_challenger"


@dataclass(frozen=True)
class CandidateExperiment:
    experiment_id: str
    candidate_type: CandidateType
    title: str
    rationale: str
    target_factors: list[str]
    target_horizons: list[str]
    expected_effect: str
    risk_level: str
    evidence: dict[str, Any] = field(default_factory=dict)
    validation_protocol: dict[str, Any] = field(default_factory=dict)
    point_in_time_requirements: list[str] = field(default_factory=list)
    ai_readable_summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["candidate_type"] = self.candidate_type.value
        return data


@dataclass(frozen=True)
class PromotionDecision:
    status: str
    reason: str
    metrics: dict[str, float]
    risk_flags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
