from src.evolution.promotion_policy import evaluate_promotion


def test_promote_when_challenger_improves_without_material_degradation():
    decision = evaluate_promotion(
        champion_metrics={"D1": 0.50, "W1": 0.48, "M1": 0.44},
        challenger_metrics={"D1": 0.54, "W1": 0.50, "M1": 0.45},
    )

    assert decision.status == "promote"
    assert decision.risk_flags == []


def test_hold_when_one_horizon_materially_degrades():
    decision = evaluate_promotion(
        champion_metrics={"D1": 0.50, "W1": 0.48, "M1": 0.44},
        challenger_metrics={"D1": 0.56, "W1": 0.50, "M1": 0.35},
    )

    assert decision.status == "hold"
    assert "material_degradation:M1" in decision.risk_flags


def test_needs_more_data_when_metrics_are_missing():
    decision = evaluate_promotion(
        champion_metrics={"D1": 0.50, "W1": 0.48},
        challenger_metrics={"D1": 0.56, "W1": 0.50, "M1": 0.51},
    )

    assert decision.status == "needs_more_data"
