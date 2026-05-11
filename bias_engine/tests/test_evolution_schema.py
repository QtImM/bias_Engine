from src.evolution.schema import CandidateExperiment, CandidateType, PromotionDecision


def test_candidate_experiment_serializes_to_dict():
    candidate = CandidateExperiment(
        experiment_id="exp-low-coverage-rsi_14",
        candidate_type=CandidateType.ADJUST_FACTOR_WEIGHT,
        title="降低 rsi_14 权重",
        rationale="coverage 低于阈值，先测试降权而不是删除。",
        target_factors=["rsi_14"],
        target_horizons=["D1"],
        expected_effect="降低不稳定因子对 D1 bias 的影响。",
        risk_level="medium",
        evidence={"coverage": 0.62, "threshold": 0.8},
        validation_protocol={
            "method": "walk_forward_backtest",
            "embargo_required": True,
        },
        point_in_time_requirements=[
            "factor_values.available_at <= prediction_time",
            "labels must not be joined into prediction features",
        ],
        ai_readable_summary="这是待验证假设，不是有效性结论。",
    )

    data = candidate.to_dict()

    assert data["experiment_id"] == "exp-low-coverage-rsi_14"
    assert data["candidate_type"] == "adjust_factor_weight"
    assert data["target_factors"] == ["rsi_14"]
    assert data["evidence"]["coverage"] == 0.62
    assert data["validation_protocol"]["method"] == "walk_forward_backtest"
    assert "available_at" in data["point_in_time_requirements"][0]
    assert "待验证假设" in data["ai_readable_summary"]


def test_promotion_decision_accepts_hold_status():
    decision = PromotionDecision(
        status="hold",
        reason="D1 improved but M1 degraded too much.",
        metrics={"D1_delta": 0.04, "M1_delta": -0.08},
        risk_flags=["material_m1_degradation"],
    )

    assert decision.to_dict()["status"] == "hold"
