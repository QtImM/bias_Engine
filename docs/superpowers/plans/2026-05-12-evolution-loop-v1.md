# Evolution Loop v1 受控进化循环实施计划

> **给 agentic worker 的要求：** 执行本计划时必须使用 `superpowers:subagent-driven-development`（推荐）或 `superpowers:executing-plans`。所有步骤都使用 checkbox（`- [ ]`）格式，方便逐项跟踪。

**目标：** 为 Bias Engine 建立第一版“受控进化循环”：自动生成下一轮优化候选实验、以 AI 可读/机器可解析的格式导出实验协议、评估 challenger 是否具备晋级条件、导出进化报告，但不自动替换 champion 模型。

**架构：** 新增一个独立的 `src/evolution/` 层，读取现有产物（`factor_quality.parquet`、预测结果、labels、model registry、验证指标），输出可人工 review、可复制给 AI 阅读、也可被程序解析的候选实验协议。第一版采用保守的规则驱动，不引入复杂 ML/LLM 自动决策，也不直接修改 `config/models.yaml`。候选建议只提出“待验证假设”，不判断好坏；好坏必须由严格的 point-in-time walk-forward 和回测指标决定。通过 `python run_pipeline.py --step evolution` 显式运行，并把报告写入 `data/evolution/`。

**技术栈：** Python 3.10+、pandas、pyarrow/parquet、dataclasses、JSON、Markdown、pytest。此阶段不新增重型机器学习框架。

---

## 1. 为什么下一阶段应该做这个

当前项目已经具备一个 bias 研究框架的基础能力：

```text
factor_quality：因子质量报告
feature_matrix：特征矩阵
labels：未来收益/方向标签
walk_forward：时间顺序验证切分工具
backtest_report：bias bucket 回测摘要
model_registry：模型版本记录
rule_model / sklearn_model：规则模型和监督学习 baseline
local HTML visualization：本地可视化控制台
```

现在缺的不是马上再加一个更复杂的模型，而是一个稳定的“研究决策层”：

```text
哪些因子质量差？
哪些因子值得下一轮实验？
新模型是否真的强于旧模型？
哪些 horizon 改善了？
哪些 symbol 或 horizon 退化了？
是否应该 promote challenger？
哪些实验失败了，失败原因是什么？
```

因此下一阶段应先做：

```text
Evolution Loop v1：受控进化循环
```

它的作用不是让模型“神秘地自己变强”，而是让系统开始具备实验意识：

```text
发现问题
提出候选实验
生成报告
等待人工确认
再进入下一轮验证
```

这会把项目从“能输出 bias”推进到“能判断自己下一步该怎么优化”。

## 2. 本阶段范围

本阶段要做：

```text
1. 定义进化循环的数据结构。
2. 根据 factor_quality 生成候选实验。
3. 定义 champion / challenger 晋级策略。
4. 输出 AI 可读、机器可解析的 JSON 候选实验协议。
5. 输出 Markdown 格式的进化报告。
6. 在 run_pipeline.py 中增加 --step evolution。
7. 增加测试，确保规则可复现、可维护。
8. 更新 README 和文档，说明新工作流。
```

本阶段不做：

```text
1. 不自动修改 config/models.yaml。
2. 不自动禁用因子。
3. 不自动 promote challenger。
4. 不做强化学习。
5. 不做 LLM 新闻/事件因子。
6. 不替换当前 rule_model。
7. 不引入复杂实验配置系统。
```

本阶段完成后，系统应该能回答：

```text
下一轮最值得测试哪 3 个实验？
每个实验为什么值得测试？
风险是什么？
这个实验应该如何被严格回测？
哪些数据约束能避免未来函数？
如何把候选实验复制给 AI 继续分析？
当前有没有模型可以晋级？
为什么不能自动晋级？
下一步应该运行什么命令？
```

## 3. 文件结构目标

新增文件：

```text
bias_engine/src/evolution/__init__.py
bias_engine/src/evolution/schema.py
bias_engine/src/evolution/candidate_generator.py
bias_engine/src/evolution/promotion_policy.py
bias_engine/src/evolution/evolution_report.py
bias_engine/src/evolution/runner.py

bias_engine/tests/test_evolution_schema.py
bias_engine/tests/test_candidate_generator.py
bias_engine/tests/test_promotion_policy.py
bias_engine/tests/test_evolution_report.py
bias_engine/tests/test_evolution_runner.py

bias_engine/docs/evolution_loop_v1.md
bias_engine/data/evolution/.gitkeep
```

修改文件：

```text
bias_engine/run_pipeline.py
.gitignore
README.md
bias_engine/docs/factor_lifecycle.md
```

本地生成但默认不提交的文件：

```text
bias_engine/data/evolution/evolution_candidates.json
bias_engine/data/evolution/evolution_report.json
bias_engine/data/evolution/evolution_report.md
```

## 4. 核心概念

### 4.0 AI 可读优化建议格式

本阶段生成的优化建议必须采用“AI 可读 + 机器可解析”的格式。用户应该可以直接复制 `evolution_candidates.json` 或报告中的候选实验片段给 AI，AI 能理解：

```text
这个实验想测试什么
它触发的证据是什么
它涉及哪些因子和 horizon
它必须遵守哪些 point-in-time 约束
它应该用什么回测协议验证
它不能被视为已经有效的结论
```

格式要求：

```text
1. JSON 字段稳定，便于程序读取。
2. 文本解释清晰，便于 AI 和人类阅读。
3. 每个候选实验都必须带 validation_protocol。
4. 每个候选实验都必须带 point_in_time_requirements。
5. 每个候选实验都必须声明“这是待验证假设，不是结论”。
6. 所有有效性判断都必须留给回测和 walk-forward 量化结果。
```

这意味着：

```text
AI 可以帮助读报告、拆实验、写配置、解释指标。
AI 不负责主观判断某个建议好不好。
是否有效只看严格量化验证。
```

### 4.1 AI 在自进化中的角色边界

AI 应该参与“生成实验”和“解释证据”，但不参与“主观裁决”。

本项目里的自进化流程应该是：

```text
AI 提出可验证假设
回测验证假设
规则判断是否满足晋级条件
人类批准关键变更
系统记录实验经验
```

AI 可以做：

```text
1. 读取 `evolution_candidates.json`。
2. 读取 `evolution_report.md`。
3. 将数据质量问题转成候选实验。
4. 把模糊想法整理成结构化实验协议。
5. 解释回测报告中的指标变化。
6. 总结实验历史和失败原因。
7. 帮助生成下一轮 `config/experiments/<date>-exp-xxx.yaml`。
8. 帮助检查候选实验是否缺少 point-in-time 约束。
9. 帮助把候选实验拆成可执行任务。
```

AI 不可以做：

```text
1. 不可以凭主观判断 promote challenger。
2. 不可以跳过 walk-forward / 回测。
3. 不可以忽略 `available_at <= prediction_time`。
4. 不可以把 labels 加入预测特征。
5. 不可以直接修改 champion 配置。
6. 不可以自动禁用因子。
7. 不可以把候选实验描述成已验证结论。
8. 不可以用“看起来合理”替代量化指标。
9. 不可以在没有版本记录的情况下覆盖模型或因子配置。
```

因此，AI 输出的每个建议都必须满足：

```text
它是 hypothesis，不是 conclusion。
它必须能被 walk-forward / backtest 检验。
它必须显式声明 point-in-time 约束。
它必须声明 challenger_vs_champion 比较方式。
它必须留下机器可读记录，方便未来复盘。
```

如果 AI 参与解释回测结果，它只能基于已有指标做解释。例如：

```text
D1 directional_hit_rate 提升 2.1%
W1 directional_hit_rate 下降 0.4%
M1 directional_hit_rate 下降 3.8%
```

AI 可以解释为：

```text
这个实验可能只适合作为 D1-only challenger。
```

但最终状态必须由规则决定：

```text
if M1_delta < -material_degradation:
    status = "hold"
```

一句话原则：

```text
AI 负责提出问题和整理证据。
回测负责回答问题。
规则负责裁决。
人类负责批准关键变更。
```

### 4.2 Candidate Experiment：候选实验

候选实验是“建议下一轮测试的改动”，不是已经应用的改动。

候选实验不能表达“这个改动一定更好”。它只能表达：

```text
这是一个可验证假设。
它应该用哪些历史窗口验证。
它必须遵守哪些 point-in-time 约束。
它需要通过哪些量化指标才能进入下一步。
```

换句话说，AI 可以生成、读取、解释候选实验，但不能凭主观判断决定好坏。好坏必须由严格回测和 walk-forward 验证决定。

示例：

```text
降低某个低覆盖率因子的权重
检查某个极值过多的因子
将某个因子限制在 W1 使用
测试去除某个高度冗余因子的版本
测试高波动 regime filter
测试 sklearn challenger 是否超过 rule champion
```

候选实验必须包含：

```text
experiment_id：实验 ID
candidate_type：实验类型
title：标题
rationale：为什么建议这个实验
target_factors：目标因子
target_horizons：目标周期
expected_effect：预期效果
risk_level：风险等级
evidence：证据
validation_protocol：必须执行的量化验证协议
point_in_time_requirements：避免未来函数的约束
ai_readable_summary：便于复制给 AI 阅读的摘要
```

候选实验 JSON 应该长这样：

```json
{
  "experiment_id": "exp-low-coverage-rsi_14",
  "candidate_type": "adjust_factor_weight",
  "title": "测试降低 rsi_14 权重",
  "rationale": "rsi_14 coverage 低于阈值，建议测试降权版本。",
  "target_factors": ["rsi_14"],
  "target_horizons": ["D1", "W1", "M1"],
  "expected_effect": "降低低覆盖率因子对 bias_score 的不稳定影响。",
  "risk_level": "medium",
  "evidence": {
    "coverage": 0.62,
    "coverage_threshold": 0.8
  },
  "validation_protocol": {
    "method": "walk_forward_backtest",
    "train_window": "rolling",
    "embargo_required": true,
    "primary_metrics": ["macro_f1", "directional_hit_rate", "mean_forward_return_by_bucket"],
    "required_comparison": "challenger_vs_champion",
    "promotion_rule": "no_material_horizon_degradation_and_positive_average_delta"
  },
  "point_in_time_requirements": [
    "factor_values.available_at <= prediction_time",
    "labels must not be joined into prediction features",
    "train/test split must follow chronological order",
    "no random shuffle across dates",
    "factor formula must use only data available at or before prediction_time"
  ],
  "ai_readable_summary": "请把这个候选实验视为待验证假设，而不是结论。只允许通过无未来函数 walk-forward 回测判断是否有效。"
}
```

### 4.3 Promotion Decision：晋级判断

晋级判断用于评估 challenger 是否可以替换 champion。

可能状态：

```text
promote：建议晋级
hold：暂缓，保留为实验
reject：不建议晋级
needs_more_data：数据或指标不足
```

第一版只输出判断，不自动执行晋级。

### 4.4 Evolution Report：进化报告

进化报告是给用户 review 的主要产物。它同时要服务两个读者：

```text
人：能快速理解下一轮该测试什么。
AI：能直接读取 JSON/Markdown，继续帮用户拆实验、写配置或解释报告。
```

报告应该包含：

```text
当前结论
数据来源摘要
候选实验列表
AI 可读候选实验 JSON 路径
point-in-time 约束
回测验证协议
晋级判断
风险标记
建议执行顺序
```

报告必须明确说明：

```text
候选实验不是结论。
AI 不负责判断候选实验好坏。
候选实验是否有效，只由严格 walk-forward / 回测指标决定。
所有验证必须避免未来函数。
```

---

## 任务 1：新增进化循环数据结构

**文件：**

```text
新增：bias_engine/src/evolution/__init__.py
新增：bias_engine/src/evolution/schema.py
新增测试：bias_engine/tests/test_evolution_schema.py
```

- [ ] **步骤 1：编写失败测试**

创建 `bias_engine/tests/test_evolution_schema.py`：

```python
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
```

- [ ] **步骤 2：运行测试，确认失败**

运行：

```powershell
cd "C:\Users\Tim\Desktop\gpt小人\自进化bias框架\bias_engine"
python -m pytest tests/test_evolution_schema.py -v
```

预期结果：

```text
失败，因为 src.evolution.schema 还不存在。
```

- [ ] **步骤 3：创建 evolution 包**

创建 `bias_engine/src/evolution/__init__.py`：

```python
"""Controlled evolution loop for Bias Engine."""
```

- [ ] **步骤 4：创建 schema.py**

创建 `bias_engine/src/evolution/schema.py`：

```python
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
```

- [ ] **步骤 5：运行测试，确认通过**

运行：

```powershell
python -m pytest tests/test_evolution_schema.py -v
```

预期结果：

```text
通过。
```

- [ ] **步骤 6：提交**

运行：

```powershell
git add bias_engine/src/evolution/__init__.py bias_engine/src/evolution/schema.py bias_engine/tests/test_evolution_schema.py
git commit -m "feat: 添加进化循环数据结构"
```

---

## 任务 2：根据因子质量生成候选实验

**文件：**

```text
新增：bias_engine/src/evolution/candidate_generator.py
新增测试：bias_engine/tests/test_candidate_generator.py
```

- [ ] **步骤 1：编写失败测试**

创建 `bias_engine/tests/test_candidate_generator.py`：

```python
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
```

- [ ] **步骤 2：运行测试，确认失败**

运行：

```powershell
python -m pytest tests/test_candidate_generator.py -v
```

预期结果：

```text
失败，因为 candidate_generator.py 还不存在。
```

- [ ] **步骤 3：实现 candidate_generator.py**

创建 `bias_engine/src/evolution/candidate_generator.py`：

```python
from __future__ import annotations

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
                        validation_protocol=DEFAULT_VALIDATION_PROTOCOL.copy(),
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
                        validation_protocol=DEFAULT_VALIDATION_PROTOCOL.copy(),
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
```

- [ ] **步骤 4：运行测试，确认通过**

运行：

```powershell
python -m pytest tests/test_candidate_generator.py -v
```

预期结果：

```text
通过。
```

- [ ] **步骤 5：提交**

运行：

```powershell
git add bias_engine/src/evolution/candidate_generator.py bias_engine/tests/test_candidate_generator.py
git commit -m "feat: 根据因子质量生成进化候选实验"
```

---

## 任务 3：新增 champion / challenger 晋级策略

**文件：**

```text
新增：bias_engine/src/evolution/promotion_policy.py
新增测试：bias_engine/tests/test_promotion_policy.py
```

- [ ] **步骤 1：编写失败测试**

创建 `bias_engine/tests/test_promotion_policy.py`：

```python
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
```

- [ ] **步骤 2：运行测试，确认失败**

运行：

```powershell
python -m pytest tests/test_promotion_policy.py -v
```

预期结果：

```text
失败，因为 promotion_policy.py 还不存在。
```

- [ ] **步骤 3：实现 promotion_policy.py**

创建 `bias_engine/src/evolution/promotion_policy.py`：

```python
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
```

- [ ] **步骤 4：运行测试，确认通过**

运行：

```powershell
python -m pytest tests/test_promotion_policy.py -v
```

预期结果：

```text
通过。
```

- [ ] **步骤 5：提交**

运行：

```powershell
git add bias_engine/src/evolution/promotion_policy.py bias_engine/tests/test_promotion_policy.py
git commit -m "feat: 添加模型晋级策略规则"
```

---

## 任务 4：新增进化报告导出

**文件：**

```text
新增：bias_engine/src/evolution/evolution_report.py
新增测试：bias_engine/tests/test_evolution_report.py
```

- [ ] **步骤 1：编写失败测试**

创建 `bias_engine/tests/test_evolution_report.py`：

```python
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
    assert "候选实验不是结论" in markdown
    assert "available_at <= prediction_time" in markdown
    assert payload["promotion_decision"]["status"] == "hold"
```

- [ ] **步骤 2：运行测试，确认失败**

运行：

```powershell
python -m pytest tests/test_evolution_report.py -v
```

预期结果：

```text
失败，因为 evolution_report.py 还不存在。
```

- [ ] **步骤 3：实现 evolution_report.py**

创建 `bias_engine/src/evolution/evolution_report.py`：

```python
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
```

- [ ] **步骤 4：运行测试，确认通过**

运行：

```powershell
python -m pytest tests/test_evolution_report.py -v
```

预期结果：

```text
通过。
```

- [ ] **步骤 5：提交**

运行：

```powershell
git add bias_engine/src/evolution/evolution_report.py bias_engine/tests/test_evolution_report.py
git commit -m "feat: 添加进化报告导出"
```

---

## 任务 5：新增进化评审运行器

**文件：**

```text
新增：bias_engine/src/evolution/runner.py
新增测试：bias_engine/tests/test_evolution_runner.py
```

- [ ] **步骤 1：编写失败测试**

创建 `bias_engine/tests/test_evolution_runner.py`：

```python
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
```

- [ ] **步骤 2：运行测试，确认失败**

运行：

```powershell
python -m pytest tests/test_evolution_runner.py -v
```

预期结果：

```text
失败，因为 runner.py 还不存在。
```

- [ ] **步骤 3：实现 runner.py**

创建 `bias_engine/src/evolution/runner.py`：

```python
from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from src.evolution.candidate_generator import generate_factor_quality_candidates
from src.evolution.evolution_report import write_evolution_report
from src.evolution.schema import PromotionDecision


def _read_parquet_if_exists(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_parquet(path)


def run_evolution_review(
    data_dir: str | Path,
    max_candidates: int = 3,
) -> dict[str, Any]:
    data_path = Path(data_dir)
    quality_path = data_path / "features" / "factor_quality.parquet"
    factor_quality = _read_parquet_if_exists(quality_path)

    if factor_quality.empty:
        candidates = []
        source_summary = {
            "factor_quality_path": str(quality_path),
            "factor_quality_rows": 0,
            "warning": "factor_quality.parquet missing or empty",
        }
    else:
        candidates = generate_factor_quality_candidates(
            factor_quality,
            max_candidates=max_candidates,
        )
        source_summary = {
            "factor_quality_path": str(quality_path),
            "factor_quality_rows": int(len(factor_quality)),
            "candidate_count": len(candidates),
        }

    promotion_decision = PromotionDecision(
        status="hold",
        reason="Evolution Loop v1 只生成候选实验，不自动晋级模型。",
        metrics={},
        risk_flags=["manual_review_required"],
    )

    report_paths = write_evolution_report(
        output_dir=data_path / "evolution",
        candidates=candidates,
        promotion_decision=promotion_decision,
        source_summary=source_summary,
    )

    return {
        "candidate_count": len(candidates),
        "report_paths": {key: str(value) for key, value in report_paths.items()},
    }
```

- [ ] **步骤 4：运行测试，确认通过**

运行：

```powershell
python -m pytest tests/test_evolution_runner.py -v
```

预期结果：

```text
通过。
```

- [ ] **步骤 5：提交**

运行：

```powershell
git add bias_engine/src/evolution/runner.py bias_engine/tests/test_evolution_runner.py
git commit -m "feat: 添加进化评审运行器"
```

---

## 任务 6：接入 run_pipeline.py

**文件：**

```text
修改：bias_engine/run_pipeline.py
```

- [ ] **步骤 1：在 CLI choices 中加入 evolution**

修改 `bias_engine/run_pipeline.py` 中的 parser：

```python
parser.add_argument("--step", choices=["ingest", "factors", "labels", "predict", "report", "evolution", "all"],
                   default="all", help="Which step to run")
```

- [ ] **步骤 2：新增 step_evolution 函数**

在 `main()` 之前加入：

```python
def step_evolution() -> dict:
    """Generate controlled evolution candidates and review report."""
    from src.evolution.runner import run_evolution_review

    logger.info("=== Evolution Review ===")
    result = run_evolution_review(DATA_DIR, max_candidates=3)
    logger.info(f"Generated {result['candidate_count']} evolution candidates")
    for key, path in result["report_paths"].items():
        logger.info(f"  {key}: {path}")
    return result
```

- [ ] **步骤 3：在 main 流程中调用 evolution**

在 `predict` block 之后、`report` block 之前加入：

```python
if args.step in ("evolution", "all"):
    step_evolution()
```

- [ ] **步骤 4：运行全部测试**

运行：

```powershell
python -m pytest tests -v
```

预期结果：

```text
全部通过。
```

- [ ] **步骤 5：运行 evolution step**

运行：

```powershell
python run_pipeline.py --step evolution
```

预期输出包含：

```text
=== Evolution Review ===
Generated <N> evolution candidates
json: ...\data\evolution\evolution_report.json
candidates: ...\data\evolution\evolution_candidates.json
markdown: ...\data\evolution\evolution_report.md
```

如果 `factor_quality.parquet` 不存在，也应该正常生成报告，只是 `candidate_count=0`，并在 JSON 中写入 warning。

- [ ] **步骤 6：提交**

运行：

```powershell
git add bias_engine/run_pipeline.py
git commit -m "feat: 接入进化评审流水线步骤"
```

---

## 任务 7：忽略进化循环生成文件

**文件：**

```text
修改：.gitignore
新增：bias_engine/data/evolution/.gitkeep
```

- [ ] **步骤 1：添加 .gitignore 规则**

在根目录 `.gitignore` 中加入：

```gitignore
# Evolution review outputs
bias_engine/data/evolution/*.json
bias_engine/data/evolution/*.md
!bias_engine/data/evolution/.gitkeep
```

- [ ] **步骤 2：新增目录占位文件**

创建：

```text
bias_engine/data/evolution/.gitkeep
```

- [ ] **步骤 3：确认生成文件被忽略**

运行：

```powershell
git status --short --ignored
```

预期生成文件显示为 ignored：

```text
!! bias_engine/data/evolution/evolution_candidates.json
!! bias_engine/data/evolution/evolution_report.json
!! bias_engine/data/evolution/evolution_report.md
```

`.gitkeep` 应该作为普通文件被跟踪。

- [ ] **步骤 4：提交**

运行：

```powershell
git add .gitignore bias_engine/data/evolution/.gitkeep
git commit -m "chore: 忽略进化评审生成文件"
```

---

## 任务 8：补充文档

**文件：**

```text
新增：bias_engine/docs/evolution_loop_v1.md
修改：README.md
修改：bias_engine/docs/factor_lifecycle.md
```

- [ ] **步骤 1：新增用户文档**

创建 `bias_engine/docs/evolution_loop_v1.md`：

```markdown
# Evolution Loop v1

Evolution Loop v1 是 Bias Engine 的第一版受控进化机制。

它不会自动修改模型，也不会自动替换 champion。

它做三件事：

1. 读取 `data/features/factor_quality.parquet`。
2. 根据规则生成下一轮候选实验。
3. 输出 `data/evolution/evolution_report.md` 供人工 review。

## 运行方式

```powershell
cd "C:\Users\Tim\Desktop\gpt小人\自进化bias框架\bias_engine"
python run_pipeline.py --step all --start 2023-01-01
```

或只运行进化评审：

```powershell
python run_pipeline.py --step evolution
```

## 输出文件

```text
data/evolution/evolution_candidates.json
data/evolution/evolution_report.json
data/evolution/evolution_report.md
```

这些文件是本地生成结果，默认不提交。

其中 `evolution_candidates.json` 是 AI 可读、机器可解析的候选实验协议。你可以直接复制某个候选实验给 AI，让 AI 帮你拆解实验配置、解释字段或生成后续实现计划。

但候选实验不是结论。AI 不判断它好坏，最终只看严格回测和 walk-forward 验证。

每个候选实验必须包含：

```text
validation_protocol
point_in_time_requirements
ai_readable_summary
```

验证时必须遵守：

```text
factor_values.available_at <= prediction_time
labels 不得进入预测特征
训练/测试必须按时间顺序切分
不得随机打乱日期
必须比较 challenger_vs_champion
```

## 候选实验类型

```text
adjust_factor_weight
disable_factor
horizon_specific_factor
redundancy_review
regime_filter
model_challenger
```

第一版主要生成 `adjust_factor_weight` 类型候选。

## 晋级原则

challenger 不能凭一次局部改善晋级。

至少需要满足：

```text
D1 / W1 / M1 没有任一周期明显退化
平均指标高于 champion
验证使用时间顺序切分
报告中没有高风险数据质量警告
```

第一版只给建议，不自动 promote。
```

- [ ] **步骤 2：在 README 增加运行说明**

在 `README.md` 中加入：

```markdown
## Evolution Loop v1

项目下一阶段加入受控进化机制：

```powershell
cd bias_engine
python run_pipeline.py --step evolution
```

它会读取因子质量报告，生成下一轮候选实验和进化报告：

```text
data/evolution/evolution_report.md
data/evolution/evolution_candidates.json
```

第一版不会自动修改模型配置，也不会自动晋级 champion。
```

- [ ] **步骤 3：扩展 factor lifecycle 文档**

在 `bias_engine/docs/factor_lifecycle.md` 中加入：

```markdown
## Evolution Review

因子进入 champion 之前，应先通过 Evolution Loop 生成或记录候选实验。

推荐顺序：

1. 观察 `factor_quality.parquet`。
2. 运行 `python run_pipeline.py --step evolution`。
3. 阅读 `data/evolution/evolution_report.md`。
4. 将候选实验复制为独立 experiment 配置。
5. 用 walk-forward 和 promotion policy 比较 champion / challenger。
6. 只有在没有明显退化时，才考虑 promote。
```

- [ ] **步骤 4：提交**

运行：

```powershell
git add README.md bias_engine/docs/factor_lifecycle.md bias_engine/docs/evolution_loop_v1.md
git commit -m "docs: 说明进化循环使用流程"
```

---

## 任务 9：完整验收

**文件：**

```text
无预期代码改动。
```

- [ ] **步骤 1：运行全部测试**

运行：

```powershell
cd "C:\Users\Tim\Desktop\gpt小人\自进化bias框架\bias_engine"
python -m pytest tests -v
```

预期结果：

```text
全部通过。
```

- [ ] **步骤 2：运行完整 pipeline**

运行：

```powershell
python run_pipeline.py --step all --start 2023-01-01
```

预期输出文件：

```text
data/features/factor_values.parquet
data/features/feature_matrix.parquet
data/features/factor_quality.parquet
data/labels/labels.parquet
data/predictions/predictions.parquet
data/evolution/evolution_report.md
data/evolution/evolution_report.json
data/evolution/evolution_candidates.json
```

- [ ] **步骤 3：检查进化报告**

打开：

```text
bias_engine/data/evolution/evolution_report.md
```

人工验收标准：

```text
报告包含生成时间。
报告列出候选实验，或者解释为什么没有候选实验。
候选实验 JSON 可以被 AI 直接读取和解释。
每个候选实验包含 validation_protocol。
每个候选实验包含 point_in_time_requirements。
报告明确说明候选实验不是结论。
报告明确说明好坏只由严格回测和 walk-forward 判断。
报告明确说明不会自动 promote。
报告包含 source_summary。
报告包含下一步执行建议。
```

- [ ] **步骤 4：检查 git 状态**

运行：

```powershell
git status --short
```

预期结果：

```text
除了有意修改的代码/文档外，没有额外 tracked 改动。
data/evolution/ 下的生成文件不应作为普通 untracked 文件出现。
```

- [ ] **步骤 5：如果验收过程中补充了文档，提交**

仅当验收中产生了有意保留的 tracked 改动时运行：

```powershell
git add <changed-files>
git commit -m "docs: 补充进化循环验收说明"
```

---

## 5. 完成标准

本阶段完成时，应该满足：

```text
1. python -m pytest tests -v 全部通过。
2. python run_pipeline.py --step evolution 可以生成进化报告。
3. python run_pipeline.py --step all --start 2023-01-01 会包含 evolution step。
4. 系统能根据 factor_quality 生成候选实验。
5. 晋级策略能区分 promote / hold / reject / needs_more_data。
6. 报告同时输出 JSON 和 Markdown。
7. data/evolution/ 下的生成文件被 git 忽略。
8. README 说明了如何运行新流程。
9. 第一版不会自动修改模型配置。
10. 第一版不会自动 promote challenger。
11. 候选实验采用 AI 可读、机器可解析格式。
12. 候选实验必须包含无未来函数约束。
13. 候选实验好坏只允许通过严格 walk-forward / 回测指标判断。
```

## 6. 推荐提交顺序

```text
feat: 添加进化循环数据结构
feat: 根据因子质量生成进化候选实验
feat: 添加模型晋级策略规则
feat: 添加进化报告导出
feat: 添加进化评审运行器
feat: 接入进化评审流水线步骤
chore: 忽略进化评审生成文件
docs: 说明进化循环使用流程
```

## 7. 本阶段完成后的下一阶段

Evolution Loop v1 稳定后，下一个阶段建议做：

```text
Experiment Config v1
```

目标是让候选实验可以落成独立配置，而不是只停留在报告里。

下一阶段可以新增：

```text
config/experiments/<date>-exp-001.yaml
experiment_runner：在内存中应用实验配置
champion/challenger validation records
horizon-level performance comparison
experiment history
failed experiment archive
```

到那一步之后，再考虑半自动 promote。

## 8. 自检

需求覆盖：

```text
本计划实现方向文件中的第一优先级：新增 evolution 层，让系统根据因子质量和验证概念生成下一轮优化实验。
计划保留人工 review，不允许自动替换 champion。
计划避免直接修改模型配置，确保可回滚。
```

占位检查：

```text
没有依赖未定义行为的任务。
所有代码任务都给出了具体代码。
所有验证任务都给出了命令和预期结果。
```

类型一致性：

```text
CandidateExperiment、CandidateType、PromotionDecision 在任务 1 定义，后续任务一致复用。
runner 返回 candidate_count 和 report_paths，与 pipeline 日志保持一致。
报告文件名在 runner、report writer、文档和验收标准中保持一致。
```
