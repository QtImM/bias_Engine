import json

from src.evolution.evolution_report import write_evolution_report
from src.evolution.schema import CandidateExperiment, CandidateType, PromotionDecision


def test_write_evolution_report_outputs_markdown_and_json(tmp_path):
    candidate = CandidateExperiment(
        experiment_id="exp-low-coverage-rsi_14",
        candidate_type=CandidateType.ADJUST_FACTOR_WEIGHT,
        title="测试降低 rsi_14 权重",
        rationale="coverage 过低。",
        target_factors=["rsi_14"],
        target_horizons=["D1"],
        expected_effect="降低噪声。",
        risk_level="medium",
        evidence={"coverage": 0.62},
        validation_protocol={"method": "walk_forward_backtest"},
        point_in_time_requirements=["factor_values.available_at <= prediction_time"],
        ai_readable_summary="这是待验证假设，不是有效性结论。",
    )
    decision = PromotionDecision(
        status="hold",
        reason="还没有 challenger 指标。",
        metrics={},
        risk_flags=["missing_challenger"],
    )

    paths = write_evolution_report(
        output_dir=tmp_path,
        candidates=[candidate],
        promotion_decision=decision,
        source_summary={"factor_quality_rows": 1},
    )

    markdown = paths["markdown"].read_text(encoding="utf-8")
    payload = json.loads(paths["json"].read_text(encoding="utf-8"))

    assert "Evolution Report" in markdown
    assert "测试降低 rsi_14 权重" in markdown
    assert "AI 可读候选实验" in markdown
    assert str(paths["candidates"]) in markdown
    assert "候选实验不是结论" in markdown
    assert "available_at <= prediction_time" in markdown
    assert payload["promotion_decision"]["status"] == "hold"
