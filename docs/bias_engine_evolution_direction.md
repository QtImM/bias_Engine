# Bias Engine Evolution Direction

## 核心判断

这个项目的长期方向可以是“自进化”，但第一目标不应该是让模型自己不断改自己。

更准确的目标是：

```text
构建一个会持续验证、筛选、替换、记录经验的 bias 预测研究框架。
```

自进化是这个框架逐步长出来的能力，不是最开始就直接追求的形态。真正需要持续进化的，不只是模型参数，而是整个研究系统：

```text
因子库
特征组合
模型权重
不同 horizon 的预测逻辑
市场 regime 判断
验证标准
失效检测
模型版本管理
```

最终目标始终是：

```text
可验证、可回滚、可解释地提升 D1 / W1 / M1 bias 预测质量。
```

## 为什么不直接追求完全自动自进化

如果一开始就让系统自动加因子、调参数、换模型，容易出现几个问题：

1. 历史过拟合：在旧数据上越来越好，在新数据上失效。
2. 复杂度膨胀：因子和模型越来越多，但不知道哪些真的有贡献。
3. 无法回滚：模型变好或变坏都缺少清晰版本记录。
4. 解释变差：系统给出 bias，但说不清楚为什么。
5. 数据泄漏：如果没有 point-in-time 约束，回测结果会虚高。

所以第一阶段要追求的是“受控进化”，不是“完全自动进化”。

## 推荐路线

### 阶段一：可验证的 bias 预测系统

目标是让每一次预测都有证据。

系统需要回答：

```text
当前 bias 是 bullish / neutral / bearish 的哪一种？
bias_score 和 confidence 分别是多少？
哪些因子推动了这个 bias？
这些因子在历史上是否有效？
这个 horizon 上过去表现如何？
```

这一阶段的重点不是追求最强模型，而是建立可靠的验证基础。

关键能力：

```text
factor_quality
feature_matrix
labels
walk_forward validation
backtest_report
available_at guard
model_registry
```

### 阶段二：Champion / Challenger 机制

目标是让系统可以比较新旧版本，而不是凭感觉替换模型。

定义：

```text
champion = 当前稳定使用的模型或因子组合
challenger = 新的候选模型、因子组合或权重方案
```

每个 challenger 必须经过相同验证流程：

```text
1. 使用历史数据生成特征和 labels
2. 使用 walk-forward 做时间顺序验证
3. 与 champion 比较 D1 / W1 / M1 表现
4. 检查是否有单一 symbol 或 horizon 明显退化
5. 输出 challenger report
6. 由用户决定是否 promote
```

第一版不建议自动 promote。系统可以自动建议，但最终晋级由人工确认。

### 阶段三：自动实验生成

目标是让系统开始提出下一轮优化方向。

候选实验可以来自规则，而不是一开始就依赖 LLM。

示例：

```text
如果某因子 coverage 过低，建议禁用或降低权重。
如果某因子只在 W1 有效，建议只用于 W1。
如果两个因子相关性过高，建议保留表现更稳定的一个。
如果某模型在高波动环境下明显失效，建议引入 regime filter。
如果 challenger 在 D1 提升但 M1 退化，建议只作为 D1 专用模型。
```

实验结果应写入独立记录，而不是直接覆盖当前配置。

建议结构：

```text
config/experiments/
  2026-05-12-exp-001.yaml
  2026-05-12-exp-002.yaml

data/evolution/
  experiment_results.parquet
  evolution_reports/
```

### 阶段四：受控自进化

当验证、报告、版本管理都稳定后，系统可以进入半自动自进化。

它可以自动完成：

```text
生成实验配置
运行 pipeline
验证 challenger
输出 promote 建议
记录失败实验原因
维护模型和因子表现历史
```

但仍然不建议直接自动覆盖 champion，除非未来已经有非常严格的保护条件。

## 回测和因子有效性验证

回测的本质是：

```text
用历史日线、周线、月线数据，按时间顺序模拟当时能看到的信息，
计算因子，再观察后面的收益或方向，
判断因子和模型是否对未来 bias 有预测力。
```

关键约束：

```text
因子只能使用当时已经 available 的数据。
label 可以来自未来，但只能用于训练和评估，不能进入预测特征。
验证要按时间切分，不能随机打乱。
要使用 walk-forward，而不是全历史一起训练和评估。
```

需要分三层验证：

```text
单因子验证：一个因子单独是否有效。
组合因子验证：多个因子组合后的 bias_score 是否有效。
模型版本验证：challenger 是否真的超过 champion。
```

## 第一优先级建议

下一步最值得做的是新增一个 evolution 层，但保持第一版简单。

建议模块：

```text
bias_engine/src/evolution/
  candidate_generator.py
  experiment_runner.py
  promotion_policy.py
  evolution_report.py
```

第一版只做一件事：

```text
根据 factor_quality、walk_forward 结果和 model_registry，
自动生成下一轮最值得测试的 3 个优化实验。
```

这一步完成后，系统就会从“只会输出 bias”进化到“会判断自己哪里值得优化”。

## 成功标准

长期成功不应该只看某一次预测是否准确，而应该看系统是否持续变强。

可以用这些标准衡量：

```text
每个预测都有 model_version 和 feature_set_version。
每个因子都有 factor_version 和 enabled 状态。
每个 challenger 都有验证报告。
每次 promote 都能追溯原因。
坏因子可以被发现并降权或禁用。
新模型必须证明比 champion 更好才可晋级。
D1 / W1 / M1 可以拥有不同的最佳因子组合。
系统能记录失败实验，而不是只保留成功结果。
```

## 方向总结

项目方向可以概括为：

```text
不是做一个会神秘自我修改的模型，
而是做一个会持续做实验、会评估实验、会沉淀经验、会建议下一步优化的 bias 研究框架。
```

当这个框架足够稳定后，“自进化”会自然出现：

```text
它知道自己当前表现如何。
它知道哪些因子正在失效。
它知道哪些实验值得尝试。
它知道 challenger 是否真的强于 champion。
它知道什么时候应该建议替换旧模型。
```

这才是通向更好 bias 预测能力的稳健路径。
