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
