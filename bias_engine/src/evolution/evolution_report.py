from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.evolution.schema import CandidateExperiment, PromotionDecision


def _candidate_markdown(candidate: CandidateExperiment, index: int) -> str:
    evidence = "\n".join(
        f"  - `{key}`: `{value}`" for key, value in candidate.evidence.items()
    )
    if not evidence:
        evidence = "  - 无额外证据"

    validation_protocol = json.dumps(
        candidate.validation_protocol,
        ensure_ascii=False,
        indent=2,
    )
    point_in_time_requirements = "\n".join(
        f"  - {item}" for item in candidate.point_in_time_requirements
    )
    if not point_in_time_requirements:
        point_in_time_requirements = "  - 必须补充 point-in-time 约束后才能执行"

    return f"""### {index}. {candidate.title}

- 实验 ID: `{candidate.experiment_id}`
- 类型: `{candidate.candidate_type.value}`
- 目标因子: `{", ".join(candidate.target_factors) or "无"}`
- 目标周期: `{", ".join(candidate.target_horizons) or "无"}`
- 风险等级: `{candidate.risk_level}`
- 理由: {candidate.rationale}
- 预期效果: {candidate.expected_effect}
- 证据:
{evidence}
- AI 可读摘要: {candidate.ai_readable_summary or "这是待验证假设，不是有效性结论。"}
- 避免未来函数约束:
{point_in_time_requirements}
- 量化验证协议:

```json
{validation_protocol}
```
"""


def write_evolution_report(
    output_dir: str | Path,
    candidates: list[CandidateExperiment],
    promotion_decision: PromotionDecision,
    source_summary: dict[str, Any],
) -> dict[str, Path]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    created_at = datetime.now(timezone.utc).isoformat()
    payload = {
        "created_at": created_at,
        "source_summary": source_summary,
        "candidates": [candidate.to_dict() for candidate in candidates],
        "promotion_decision": promotion_decision.to_dict(),
    }

    json_path = output_path / "evolution_report.json"
    candidates_path = output_path / "evolution_candidates.json"
    markdown_path = output_path / "evolution_report.md"

    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    candidates_path.write_text(
        json.dumps(payload["candidates"], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    candidate_sections = "\n".join(
        _candidate_markdown(candidate, index)
        for index, candidate in enumerate(candidates, start=1)
    )
    if not candidate_sections:
        candidate_sections = "当前没有生成候选实验。"

    risk_flags = promotion_decision.risk_flags or ["无"]
    markdown = f"""# Evolution Report

生成时间：`{created_at}`

## 当前结论

- 晋级状态: `{promotion_decision.status}`
- 晋级理由: {promotion_decision.reason}
- 风险标记: `{", ".join(risk_flags)}`

## 数据来源摘要

```json
{json.dumps(source_summary, ensure_ascii=False, indent=2)}
```

## AI 可读候选实验

候选实验 JSON：`{candidates_path}`

你可以直接复制这个文件里的单个候选实验给 AI 阅读。候选实验只是待验证假设，不是有效性结论。

## 下一轮候选实验

{candidate_sections}

## 判断原则

候选实验不是结论。AI 可以读取、解释、拆解候选实验，但不能主观判断它好坏。

有效性只能通过严格的无未来函数验证决定：

```text
factor_values.available_at <= prediction_time
labels 只能用于训练和评估，不能进入预测特征
训练集和测试集必须按时间顺序切分
不能随机打乱日期
必须使用 walk-forward / embargo / champion_vs_challenger 比较
```

## 建议执行顺序

1. 先人工阅读候选实验，确认它只是待验证假设。
2. 选择 1 个低风险实验复制为 `config/experiments/<date>-exp-001.yaml`。
3. 跑完整 pipeline 和无未来函数 walk-forward 验证。
4. 用 promotion policy 比较 champion 和 challenger。
5. 只在没有明显退化时考虑晋级。
"""
    markdown_path.write_text(markdown, encoding="utf-8")

    return {
        "json": json_path,
        "candidates": candidates_path,
        "markdown": markdown_path,
    }
