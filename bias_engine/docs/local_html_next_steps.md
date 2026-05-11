# 本地 HTML 可视化页面下一步执行清单

## 当前状态

现在已经有：

```text
bias_engine/docs/local_html_visualization_steps.md
```

这份文档定义了本地 HTML 可视化页面的设计方向、信息架构、数据结构和验收标准。

还没有实现：

```text
bias_engine/scripts/export_visual_data.py
bias_engine/visual/index.html
bias_engine/visual/assets/style.css
bias_engine/visual/assets/app.js
bias_engine/visual/data/*.json
```

所以接下来不是继续讨论设计，而是进入第一版可运行实现。

## 目标

做出一个可以通过本地浏览器打开的静态页面：

```text
http://localhost:8080
```

页面展示：

```text
STAR50 / HSI / NDX
D1 / W1 / M1 bias
bias_score
bullish / neutral / bearish
confidence
as_of
model_version
feature_set_version
多周期冲突提示
因子质量摘要
```

第一版不追求功能很多，重点是：

```text
能跑
能读真实 pipeline 数据
视觉方向成立
不是普通后台表格
```

## 执行顺序

### Step 1：确认 pipeline 能生成数据

先运行：

```powershell
cd "C:\Users\Tim\Desktop\gpt小人\自进化bias框架\bias_engine"
python run_pipeline.py --step all --start 2023-01-01
```

确认这些文件存在：

```text
bias_engine/data/predictions/predictions.parquet
bias_engine/data/features/factor_quality.parquet
bias_engine/data/features/factor_values.parquet
```

如果不存在，先不要写 HTML，先修 pipeline。

### Step 2：实现 JSON 导出脚本

新增：

```text
bias_engine/scripts/export_visual_data.py
```

职责：

```text
读取 predictions.parquet
读取 factor_quality.parquet
读取 factor_values.parquet
导出 visual/data/predictions.json
导出 visual/data/factor_quality.json
导出 visual/data/factor_latest.json
```

关键要求：

```text
如果 predictions 没有 feature_set_version，补 feature_set_v1
如果 parquet 文件缺失，要给出清晰错误
JSON 必须 force_ascii=False，方便中文和符号显示
不要把假数据写死到页面里
```

验收命令：

```powershell
python scripts/export_visual_data.py
```

验收文件：

```text
bias_engine/visual/data/predictions.json
bias_engine/visual/data/factor_quality.json
bias_engine/visual/data/factor_latest.json
```

### Step 3：创建静态页面目录

新增：

```text
bias_engine/visual/
  index.html
  assets/
    style.css
    app.js
  data/
    predictions.json
    factor_quality.json
    factor_latest.json
```

注意：

```text
visual/data/*.json 是本地生成数据，默认不建议提交
visual/index.html / style.css / app.js 应提交
```

如果 `.gitignore` 需要补规则，建议：

```text
bias_engine/visual/data/*.json
!bias_engine/visual/data/.gitkeep
```

### Step 4：实现 index.html 骨架

页面区域：

```html
<main class="shell">
  <header id="topbar" class="topbar"></header>
  <section id="heroSummary" class="hero-summary"></section>
  <section id="biasMatrix" class="bias-matrix"></section>
  <section id="conflictBoard" class="conflict-board"></section>
  <section id="qualityBoard" class="quality-board"></section>
</main>
```

第一版先不做复杂图表，先把核心结构跑通。

### Step 5：实现 style.css 视觉系统

视觉方向：

```text
Control Room
深墨绿背景
细网格
荧光绿 / 朱砂红 / 雾灰
卡片像仪表盘，不像后台表格
```

必须有这些 class：

```text
.shell
.topbar
.status-chip
.matrix-grid
.bias-cell
.is-bullish
.is-bearish
.is-neutral
.confidence-track
.conflict-card
.quality-card
```

第一版视觉验收：

```text
打开页面后，一眼能看出强弱
不是白底表格
不是默认 Bootstrap 风
颜色和 confidence 有明确层级
```

### Step 6：实现 app.js 数据渲染

读取：

```js
const predictions = await loadJson("./data/predictions.json")
const quality = await loadJson("./data/factor_quality.json")
const factorLatest = await loadJson("./data/factor_latest.json")
```

核心函数：

```js
async function loadJson(path) {}
function groupPredictions(predictions) {}
function renderTopbar(predictions) {}
function renderBiasMatrix(grouped) {}
function renderConflictBoard(grouped) {}
function renderQualityBoard(quality) {}
```

第一版需要渲染：

```text
顶部状态
Bias Matrix
多周期冲突提示
factor quality 摘要
```

因子贡献面板可以放到第二版，因为当前 `rule_model` 的 top factors 字段可能还需要进一步清洗。

### Step 7：本地启动页面

运行：

```powershell
cd "C:\Users\Tim\Desktop\gpt小人\自进化bias框架\bias_engine"
python -m http.server 8080 -d visual
```

打开：

```text
http://localhost:8080
```

不要把 `file://` 作为第一版验收方式，因为浏览器可能拦截本地 JSON fetch。

### Step 8：用浏览器验收

验收清单：

```text
页面能打开
没有控制台 JS 报错
显示 STAR50 / HSI / NDX
每个标的都有 D1 / W1 / M1
颜色能区分 bullish / bearish / neutral
confidence 有进度条或强弱表达
能看到 as_of 和 model_version
能看到 feature_set_version
多周期冲突有 Conflict 或解释文案
factor_quality 能显示 coverage / extreme_share
```

当前 in-app browser 已经开在：

```text
http://localhost:8501/
```

这是 Streamlit dashboard。HTML 静态页面会使用：

```text
http://localhost:8080/
```

两个端口不要混在一起。

## 第一版完成标准

完成后应该能按这个顺序跑：

```powershell
cd "C:\Users\Tim\Desktop\gpt小人\自进化bias框架\bias_engine"
python run_pipeline.py --step all --start 2023-01-01
python scripts/export_visual_data.py
python -m http.server 8080 -d visual
```

然后打开：

```text
http://localhost:8080
```

看到一个可用的 `Bias Control Room` 页面。

## 推荐提交拆分

建议分 3 个 commit：

```text
1. 添加可视化数据导出脚本
2. 添加本地 HTML 可视化页面
3. 完善可视化运行说明和验收清单
```

如果希望一次性提交，也可以：

```text
实现本地HTML可视化页面
```

## 暂不做的事

第一版先不要做：

```text
复杂历史曲线
拖拽交互
主题切换
自动刷新
FastAPI 接口
真实交易信号
```

原因：先把真实数据链路和核心视觉跑通，再逐步加复杂度。这里别贪，贪了就会变成一锅金融仪表盘粥。

## 第二版方向

第一版跑通后，再做：

```text
历史 bias sparkline
top positive / negative factors
symbol 详情抽屉
Control Room / Paper Terminal / Heatmap Wall 主题切换
一键重新导出 JSON
```

## 相关文档

```text
bias_engine/docs/local_html_visualization_steps.md
README.md
bias_engine/docs/factor_lifecycle.md
```
