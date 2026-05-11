from __future__ import annotations

from src.evolution.schema import PromotionDecision


DEFAULT_HORIZONS = ("D1", "W1", "M1")


def evaluate_promotion(
    champion_metrics: dict[str, float],
    challenger_metrics: dict[str, float],
    horizons: tuple[str, ...] = DEFAULT_HORIZONS,
    min_average_improvement: float = 0.01,
    material_degradation: float = 0.03,
) -> PromotionDecision:
    missing = [
        horizon
        for horizon in horizons
        if horizon not in champion_metrics or horizon not in challenger_metrics
    ]
    if missing:
        return PromotionDecision(
            status="needs_more_data",
            reason=f"缺少 horizon 指标: {', '.join(missing)}。",
            metrics={},
            risk_flags=[f"missing_metric:{h}" for h in missing],
        )

    deltas = {
        horizon: float(challenger_metrics[horizon]) - float(champion_metrics[horizon])
        for horizon in horizons
    }
    average_delta = sum(deltas.values()) / len(deltas)

    risk_flags = [
        f"material_degradation:{horizon}"
        for horizon, delta in deltas.items()
        if delta < -material_degradation
    ]

    metrics = {f"{horizon}_delta": delta for horizon, delta in deltas.items()}
    metrics["average_delta"] = average_delta

    if risk_flags:
        return PromotionDecision(
            status="hold",
            reason="challenger 有 horizon 明显退化，建议保留为实验，不晋级 champion。",
            metrics=metrics,
            risk_flags=risk_flags,
        )

    if average_delta >= min_average_improvement:
        return PromotionDecision(
            status="promote",
            reason="challenger 平均表现超过 champion，且没有 horizon 明显退化。",
            metrics=metrics,
            risk_flags=[],
        )

    return PromotionDecision(
        status="reject",
        reason="challenger 没有达到最小平均提升要求。",
        metrics=metrics,
        risk_flags=[],
    )
