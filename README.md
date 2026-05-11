# Bias Engine

一个可插拔因子的多周期市场偏见框架，用来给 `STAR50`、`HSI`、`NDX` 输出不同时间框架下的 bias：

```text
D1：未来 1-3 个交易日
W1：未来 5-10 个交易日
M1：未来 20-40 个交易日
```

它不是直接给“买/卖”信号，而是输出：

```text
bias_score
bullish / neutral / bearish
confidence
model_version
top factor drivers
```

核心目标是让模型可以通过不断添加、禁用、替换因子来进化，而不是每次重写预测逻辑。

## 当前实现

已经实现：

```text
数据接入：AKShare、yfinance
本地存储：Parquet，预留 DuckDB store
标的配置：STAR50、HSI、NDX
因子插件：通过 config/factors.yaml 注册和启停
基础因子：趋势、均值回归、波动率、成交量、跨市场相对强弱
标签生成：D1 / W1 / M1 forward labels
模型：rule_model_v1 规则加权模型
质量报告：factor_quality
特征矩阵：feature_matrix
验证：pytest 测试
展示：Streamlit dashboard
规划：本地 HTML 可视化页面实现步骤
```

## 项目结构

```text
bias_engine/
  config/
    instruments.yaml      # 标的和 provider symbol 映射
    factors.yaml          # 因子注册、启停、参数
    models.yaml           # horizon、规则模型权重、标签配置
    data_sources.yaml     # 数据源配置

  src/
    data/                 # 数据抓取、标准化、交易日历、symbol 映射
    factors/              # 因子接口、注册器、各类因子实现
    labels/               # 标签生成
    models/               # rule model、sklearn baseline、model registry
    features/             # feature matrix
    quality/              # 因子质量报告
    storage/              # DuckDB store
    validation/           # walk-forward、bucket report
    dashboard/            # Streamlit dashboard

  data/
    raw/                  # 本地行情数据，默认不提交
    features/             # factor_values、feature_matrix，默认不提交
    labels/               # labels，默认不提交
    predictions/          # predictions，默认不提交

  tests/                  # 单元测试
  docs/                   # 设计和实现文档
  run_pipeline.py         # 主流程入口
```

## 安装

推荐 Python 3.10+。

```powershell
cd "C:\Users\Tim\Desktop\gpt小人\自进化bias框架\bias_engine"
python -m pip install -r requirements.txt
```

如果是从 GitHub clone 到新目录：

```powershell
git clone https://github.com/QtImM/bias_Engine.git
cd bias_Engine\bias_engine
python -m pip install -r requirements.txt
```

## 一键运行主流程

```powershell
cd "C:\Users\Tim\Desktop\gpt小人\自进化bias框架\bias_engine"
python run_pipeline.py --step all --start 2023-01-01
```

这会依次执行：

```text
1. 拉取行情数据
2. 计算启用的因子
3. 生成 feature_matrix
4. 生成 factor_quality
5. 生成 D1 / W1 / M1 labels
6. 运行 rule_model_v1
7. 输出 bias report
```

输出文件会写到：

```text
bias_engine/data/raw/
bias_engine/data/features/
bias_engine/data/labels/
bias_engine/data/predictions/
```

这些数据文件默认被 `.gitignore` 排除，不会提交到仓库。

## 分步骤运行

```powershell
python run_pipeline.py --step ingest
python run_pipeline.py --step factors
python run_pipeline.py --step labels
python run_pipeline.py --step predict
python run_pipeline.py --step report
```

常用组合：

```powershell
python run_pipeline.py --step all --start 2023-01-01
python run_pipeline.py --step report
```

## 启动 Dashboard

```powershell
cd "C:\Users\Tim\Desktop\gpt小人\自进化bias框架\bias_engine"
streamlit run src/dashboard/app.py
```

浏览器一般会打开：

```text
http://localhost:8501
```

如果 dashboard 没有数据，先运行：

```powershell
python run_pipeline.py --step all --start 2023-01-01
```

## 运行测试

```powershell
cd "C:\Users\Tim\Desktop\gpt小人\自进化bias框架\bias_engine"
python -m pytest tests -v
```

当前验证过的结果：

```text
13 passed
```

## 添加或关闭因子

因子通过 YAML 注册，不建议直接删代码。

打开：

```text
bias_engine/config/factors.yaml
```

关闭某个因子：

```yaml
- id: return_5d
  class_path: factors.trend.returns.ReturnFactor
  enabled: false
```

新增因子的标准流程：

```text
1. 在 src/factors/ 下新增因子类
2. 实现 spec 和 compute(ctx)
3. 在 config/factors.yaml 注册
4. 运行 python run_pipeline.py --step factors
5. 检查 factor_quality
6. 再运行 predict / all
```

## 关键设计原则

```text
因子只描述市场状态，不写买卖逻辑
模型负责学习或组合因子与未来 bias 的关系
所有数据必须带 available_at，避免未来函数
所有因子和模型都要有 version
禁用因子用 enabled: false，不直接删除
```

## 本地 HTML 可视化页面

目前 HTML 页面还没有正式实现，已经有设计和实现步骤文档：

```text
bias_engine/docs/local_html_visualization_steps.md
```

目标页面会是一个本地静态 `Bias Control Room`，读取 pipeline 导出的 JSON：

```text
bias_engine/visual/index.html
bias_engine/visual/data/predictions.json
bias_engine/visual/data/factor_quality.json
bias_engine/visual/data/factor_latest.json
```

第一版建议通过本地静态服务器运行：

```powershell
cd bias_engine
python run_pipeline.py --step all --start 2023-01-01
python scripts/export_visual_data.py
python -m http.server 8080 -d visual
```

然后打开：

```text
http://localhost:8080
```

注意：`scripts/export_visual_data.py` 和 `visual/index.html` 是下一步要实现的内容。

## 重要文档

```text
plan.txt
docs/superpowers/plans/2026-05-11-bias-engine-open-source-evolution.md
bias_engine/docs/open_source_selection.md
bias_engine/docs/factor_lifecycle.md
bias_engine/docs/local_html_visualization_steps.md
```

## 数据源说明

当前原型阶段使用：

```text
STAR50：AKShare
HSI：yfinance
NDX：yfinance
```

研究原型可以接受一定延迟。后续如果用于严肃生产或交易，应替换为授权数据源，并继续保留 `available_at` 约束。

## 免责声明

本项目是研究和分析工具，不构成投资建议。输出的 bias 只表示模型在当前因子集合下的方向性偏见和置信度，不等同于交易指令。
