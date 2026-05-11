# Git 初始化、提交并推送到 GitHub
# 使用前请确保已安装 git 并配置好 SSH key 或 token

$ErrorActionPreference = "Stop"
Set-Location "C:\Users\Tim\Desktop\gpt小人\自进化bias框架"

# 初始化 git（如果还没有）
if (-not (Test-Path ".git")) {
    Write-Host "初始化 Git 仓库..."
    git init
    git branch -M main
}

# 添加远程仓库
$remote = git remote get-url origin 2>$null
if (-not $remote) {
    Write-Host "添加远程仓库..."
    git remote add origin https://github.com/QtImM/bias_Engine.git
}

# 添加所有文件
Write-Host "添加文件..."
git add .

# 提交
Write-Host "提交..."
git commit -m "feat: 实现本地 HTML 可视化控制台 + bias engine 完整系统

可视化页面 (visual/):
- index.html: Control Room 风格静态页面，深墨绿主题
- Bias Matrix: STAR50/HSI/NDX 三标的 D1/W1/M1 仪表盘
- 多周期冲突分析: timeline + 自动叙事生成
- 数据质量面板: 因子覆盖率、极值、新鲜度检查
- assets/style.css: 仪器感视觉系统
- assets/app.js: 数据加载渲染、置信度动效
- scripts/export_visual_data.py: Parquet -> JSON 导出

核心模块 (src/):
- core/schema.py: PredictionRecord, BiasHorizon, BiasLabel
- core/paths.py: 项目路径常量
- storage/duckdb_store.py: DuckDB 读写封装
- quality/factor_quality.py: 因子质量报告
- features/feature_matrix.py: 因子 pivot 宽表
- validation/walk_forward.py: 带 embargo 滚动验证
- validation/backtest_report.py: bias bucket 回测
- models/model_registry.py: JSONL 模型版本注册
- models/sklearn_model.py: HistGradientBoosting 三分类
- integrations/vectorbt_adapter.py: 多头信号适配器

因子系统:
- 16 个因子: trend/mean_reversion/volatility/volume/cross_market
- FactorContext 增加 prediction_time 防未来函数
- 因子注册表从 YAML 加载，支持 enabled/disabled

测试与文档:
- tests/: 10 个测试文件覆盖核心模块
- docs/: 开源选择、因子生命周期、可视化步骤文档"

# 推送
Write-Host "推送到 GitHub..."
git push -u origin main

Write-Host "完成！"
