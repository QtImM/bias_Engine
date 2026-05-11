# 本地 HTML 可视化页面实现步骤

## 目标

做一个可以直接在本地打开的 `HTML` 可视化页面，用来展示 `bias_engine` 生成的多周期 bias 结果。它不是普通后台表格，而是一个“市场气象台 / Bias Control Room”：让用户快速看见三个标的在 `D1 / W1 / M1` 上的方向冲突、置信度、因子驱动和数据新鲜度。

页面第一版只读本地静态数据，不做后端服务。推荐输出文件：

```text
bias_engine/visual/index.html
bias_engine/visual/assets/style.css
bias_engine/visual/assets/app.js
bias_engine/visual/data/sample_predictions.json
```

## 设计方向

采用 **“冷静研究终端 + 高级金融海报”** 的视觉方向。

视觉关键词：

```text
深色墨绿背景
微弱网格与经纬线
牛市用荧光湖绿
熊市用朱砂红
中性用雾灰
关键数字像仪表读数
因子贡献像雷达扫描
多周期冲突用张力线表达
```

不要做成默认 Bootstrap dashboard，也不要做白底蓝按钮的后台系统。页面应该像一个研究员收盘后打开的“市场偏见雷达”，克制、锋利、有一点仪器感。

推荐字体：

```text
标题：Space Grotesk / Sora / IBM Plex Sans
数字：JetBrains Mono / IBM Plex Mono
中文：思源黑体 / Noto Sans SC
```

推荐色板：

```css
:root {
  --bg: #07110f;
  --panel: #0d1b18;
  --panel-soft: #13231f;
  --ink: #e8efe8;
  --muted: #83928b;
  --bull: #55f0a2;
  --bear: #ff5d5d;
  --neutral: #9aa39d;
  --warning: #f4c76b;
  --line: rgba(232, 239, 232, 0.12);
}
```

## 页面信息架构

页面按从“全局判断”到“解释细节”的顺序组织。

### 1. 顶部状态栏

展示：

```text
Bias Engine
数据日期
模型版本
feature_set_version
更新时间
数据新鲜度状态
```

设计要求：

```text
左侧是产品名和一句状态摘要
右侧是小型运行状态芯片
如果数据超过 3 天未更新，芯片变成 warning
```

示例文案：

```text
Bias Engine / Market Regime Console
As of 2026-05-11 · rule_model_v1 · local research mode
```

### 2. Bias Matrix 主视图

这是页面核心。

结构：

```text
行：STAR50 / HSI / NDX
列：D1 / W1 / M1
每个单元格展示：
  bias_score
  bullish / neutral / bearish
  confidence
```

视觉规则：

```text
bias_score > 0.3：绿色
bias_score < -0.3：红色
其他：灰色
confidence 越高，单元格发光越强
D1/W1/M1 方向冲突时，在行尾显示 Conflict 标签
```

重点：不要只做表格。每个单元格应该像一块小仪表盘，有数字、有方向、有置信度进度线。

### 3. 多周期冲突解释区

用途是解释类似：

```text
D1 bearish, W1 bullish, M1 bullish
```

展示方式：

```text
每个 symbol 一张横向 timeline card
D1 / W1 / M1 三个点用线连接
方向一致时线条平滑
方向冲突时线条出现折角或颜色断裂
```

卡片文案示例：

```text
NDX: short-term pressure, medium-term trend intact.
STAR50: daily neutral, weekly/monthly recovering.
```

第一版可以用规则生成：

```text
短周期空 + 中长周期多 = “短线压力，中期结构仍偏强”
短周期多 + 中长周期空 = “短线反弹，中期趋势仍弱”
三周期同多 = “多周期共振偏多”
三周期同空 = “多周期共振偏空”
```

### 4. 因子贡献面板

展示每个标的当前 bias 的主要驱动。

结构：

```text
左侧：Positive Factors
右侧：Negative Factors
每个因子展示：
  factor_name
  value
  contribution
```

视觉规则：

```text
正贡献：绿色条
负贡献：红色条
贡献绝对值越大，条越长
因子 family 用小标签区分：trend / volatility / cross_market / mean_reversion
```

第一版如果 `predictions.parquet` 里的 `top_positive_factors` / `top_negative_factors` 不方便直接读，就先用导出的 JSON 字段。不要在页面里硬编码假因子。

### 5. 数据新鲜度与质量区

展示：

```text
每个标的最新 bars 日期
factor coverage
extreme_share
预测是否可用
```

视觉形式：

```text
三个小卡片
每张卡片像系统健康检查
coverage = 1.00 显示绿色
extreme_share > 0.05 显示黄色
缺失预测显示红色
```

## 数据准备步骤

### Step 1：从 Parquet 导出 JSON

新增一个简单导出脚本：

```text
bias_engine/scripts/export_visual_data.py
```

读取：

```text
bias_engine/data/predictions/predictions.parquet
bias_engine/data/features/factor_quality.parquet
bias_engine/data/features/factor_values.parquet
```

输出：

```text
bias_engine/visual/data/predictions.json
bias_engine/visual/data/factor_quality.json
bias_engine/visual/data/factor_latest.json
```

第一版页面只依赖 JSON，避免浏览器直接读 Parquet。

### Step 2：定义 JSON 结构

`predictions.json`：

```json
[
  {
    "symbol": "NDX",
    "as_of": "2026-05-11",
    "horizon": "W1",
    "bias_score": 0.956,
    "label": "bullish",
    "confidence": 0.72,
    "p_up": 0.82,
    "p_neutral": 0.10,
    "p_down": 0.08,
    "model_version": "rule_model_v1",
    "top_positive_factors": [],
    "top_negative_factors": []
  }
]
```

`factor_quality.json`：

```json
[
  {
    "factor_name": "return_20d",
    "rows": 2409,
    "coverage": 1.0,
    "extreme_share": 0.0
  }
]
```

## HTML 实现步骤

### Step 1：创建静态页面目录

```text
bias_engine/visual/
  index.html
  assets/
    style.css
    app.js
  data/
    predictions.json
    factor_quality.json
```

### Step 2：写 `index.html` 骨架

页面区域：

```html
<main class="shell">
  <header class="topbar"></header>
  <section class="hero-summary"></section>
  <section class="bias-matrix"></section>
  <section class="conflict-board"></section>
  <section class="factor-board"></section>
  <section class="quality-board"></section>
</main>
```

要求：

```text
不要引入大型 UI 框架
可以用原生 HTML/CSS/JS
可以用 Plotly，但第一版不必须
页面应支持 file:// 打开；如果 fetch 本地 JSON 被浏览器拦截，则使用 python 静态服务器
```

### Step 3：写 CSS 视觉系统

重点样式：

```text
body 背景使用 radial-gradient + grid overlay
panel 使用半透明深色和细边框
数字使用 mono 字体
卡片 hover 时轻微抬升和 glow
bullish / bearish / neutral 使用明确 class
```

关键 class：

```text
.shell
.topbar
.status-chip
.matrix-grid
.bias-cell
.bias-cell.is-bullish
.bias-cell.is-bearish
.bias-cell.is-neutral
.confidence-track
.conflict-card
.factor-bar
.quality-card
```

### Step 4：写 JS 渲染逻辑

`app.js` 负责：

```text
加载 predictions.json
按 symbol + horizon 分组
渲染 Bias Matrix
计算多周期是否冲突
渲染 conflict cards
渲染 top factor contribution
加载 factor_quality.json
渲染质量卡片
```

核心函数建议：

```js
async function loadJson(path) {}
function groupPredictions(predictions) {}
function getBiasClass(label) {}
function renderTopbar(predictions) {}
function renderBiasMatrix(grouped) {}
function renderConflictBoard(grouped) {}
function renderFactorBoard(grouped) {}
function renderQualityBoard(quality) {}
```

### Step 5：加入页面动效

动效要少，但要有含义。

推荐：

```text
页面加载时 topbar 淡入
Bias Matrix 单元格 stagger reveal
confidence track 从 0 增长到当前值
冲突卡片的连接线轻微扫描
hover 时只增强光，不做花哨弹跳
```

不要做：

```text
大面积旋转
随机粒子乱飞
每个图标都跳动
无意义数字滚动
```

## 本地运行方式

推荐运行：

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

如果不想启动服务，也可以直接打开：

```text
bias_engine/visual/index.html
```

但部分浏览器会限制 `fetch("./data/predictions.json")`，所以本地 server 更稳。

## 验收标准

第一版完成后应满足：

```text
页面能在本地打开
显示 STAR50 / HSI / NDX
每个标的都有 D1 / W1 / M1
颜色能区分 bullish / bearish / neutral
confidence 有视觉强弱
能看出多周期方向冲突
能展示数据 as_of 日期和模型版本
数据文件来自 pipeline 输出，不手写假数据
移动端宽度下不崩，至少可以纵向浏览
```

## 设计自检清单

实现完后按这个清单检查：

```text
是否一眼能看出哪个标的最强？
是否一眼能看出哪个周期在冲突？
是否能区分“方向强”和“置信度强”？
是否避免了普通后台模板感？
是否没有多余图标和装饰数据？
是否所有数字都有来源？
是否能解释今天 bias 为什么变化？
```

## 推荐迭代顺序

第一轮：

```text
静态 HTML + JSON 数据 + Bias Matrix
```

第二轮：

```text
加入多周期冲突解释 + 因子贡献条
```

第三轮：

```text
加入历史 bias sparkline + factor quality
```

第四轮：

```text
加入主题切换：Control Room / Paper Terminal / Heatmap Wall
```

第五轮：

```text
把页面接到 Streamlit 或 FastAPI，变成实时可刷新页面
```

## 视觉变体备选

如果第一版还想更大胆，可以准备三个主题变量：

```text
Control Room：深绿黑底，仪器感，适合长期使用
Paper Terminal：米白纸感，像研究报告，适合打印/复盘
Heatmap Wall：大面积色块和强对比，适合快速盘后扫视
```

默认推荐 `Control Room`。它最适合多周期 bias 的核心气质：冷静、克制、可解释，但不无聊。
