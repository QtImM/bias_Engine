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
