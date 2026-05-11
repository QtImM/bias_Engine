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
git commit -m "feat: 添加本地 HTML 可视化控制台 + 完整 bias engine 系统

- 新增 visual/ 目录: Control Room 风格的静态 HTML 可视化页面
  - index.html: Bias Matrix / 多周期冲突分析 / 因子贡献 / 数据质量
  - assets/style.css: 深墨绿主题，仪表盘风格
  - assets/app.js: 数据加载、渲染逻辑、动效
  - data/: 示例预测数据和因子质量数据
- 新增 scripts/export_visual_data.py: Parquet -> JSON 导出脚本
- 新增 src/core/schema.py: PredictionRecord, BiasHorizon, BiasLabel
- 新增 src/core/paths.py: 项目路径常量
- 新增 src/storage/duckdb_store.py: DuckDB 读写封装
- 新增 src/quality/factor_quality.py: 因子覆盖率和极值报告
- 新增 src/features/feature_matrix.py: 因子 pivot 宽表
- 新增 src/validation/walk_forward.py: 带 embargo 的滚动验证
- 新增 src/validation/backtest_report.py: bias bucket 回测
- 新增 src/models/model_registry.py: JSONL 模型版本注册
- 新增 src/models/sklearn_model.py: HistGradientBoosting 三分类
- 新增 src/integrations/vectorbt_adapter.py: 多头信号适配器
- 新增 tests/: 10 个测试文件覆盖核心模块
- 新增 docs/: 开源选择和因子生命周期文档
- 更新 src/factors/base.py: 添加 prediction_time 防未来函数
- 更新 src/factors/registry.py: 传递 prediction_time
- 更新 config/models.yaml: 添加 sklearn_model 配置
- 更新 requirements.txt: 添加 lightgbm, joblib, pytest
- 更新 run_pipeline.py: 集成因子质量报告和 feature matrix
- 更新 dashboard: 添加 Bias Matrix 表格和数据过期警告"

# 推送
Write-Host "推送到 GitHub..."
git push -u origin main

Write-Host "完成！"
