/* ═══════════════════════════════════════════
   Bias Engine — 市场偏见控制台
   ═══════════════════════════════════════════ */

const DATA_PATHS = {
  predictions: './data/predictions.json',
  factorQuality: './data/factor_quality.json',
  factorLatest: './data/factor_latest.json',
};

const MARKET_TAGS = { STAR50: '科创50', HSI: '恒生', NDX: '纳指100' };
const HORIZONS = ['D1', 'W1', 'M1'];
const HORIZON_CN = { D1: '日线', W1: '周线', M1: '月线' };

// ── 数据加载 ──

async function loadJson(path) {
  try {
    const res = await fetch(path);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (e) {
    console.warn(`加载失败 ${path}:`, e.message);
    return null;
  }
}

// ── 工具函数 ──

function groupPredictions(predictions) {
  const grouped = {};
  for (const p of predictions) {
    if (!grouped[p.symbol]) grouped[p.symbol] = {};
    grouped[p.symbol][p.horizon] = p;
  }
  return grouped;
}

function getBiasClass(label) {
  if (label === 'bullish') return 'is-bullish';
  if (label === 'bearish') return 'is-bearish';
  return 'is-neutral';
}

function labelCN(label) {
  if (label === 'bullish') return '偏多';
  if (label === 'bearish') return '偏空';
  return '中性';
}

function formatScore(score) {
  const sign = score >= 0 ? '+' : '';
  return sign + score.toFixed(2);
}

function isStale(asOf) {
  if (!asOf) return true;
  const d = new Date(asOf);
  const now = new Date();
  return (now - d) / (1000 * 60 * 60 * 24) > 3;
}

function detectConflict(symbolData) {
  const labels = HORIZONS.map(h => symbolData[h]?.label).filter(Boolean);
  if (labels.length < 2) return false;
  const hasPos = labels.includes('bullish');
  const hasNeg = labels.includes('bearish');
  return hasPos && hasNeg;
}

function generateNarrative(symbolData) {
  const d1 = symbolData.D1?.label || 'neutral';
  const w1 = symbolData.W1?.label || 'neutral';
  const m1 = symbolData.M1?.label || 'neutral';
  const s = (l) => l === 'bullish' ? '偏多' : l === 'bearish' ? '偏空' : '中性';

  const longBull = (w1 === 'bullish' || m1 === 'bullish');
  const longBear = (w1 === 'bearish' || m1 === 'bearish');

  if (d1 === 'bullish' && longBear) return '短线反弹，中期趋势仍弱';
  if (d1 === 'bearish' && longBull) return '短线压力，中期结构仍偏强';
  if (d1 === 'bullish' && w1 === 'bullish' && m1 === 'bullish') return '多周期共振偏多';
  if (d1 === 'bearish' && w1 === 'bearish' && m1 === 'bearish') return '多周期共振偏空';
  if (d1 === 'neutral' && longBull) return '日线震荡，周/月偏多';
  if (d1 === 'neutral' && longBear) return '日线震荡，周/月偏空';
  return `日线${s(d1)}，周线${s(w1)}，月线${s(m1)}`;
}

// ── 渲染：顶部状态栏 ──

function renderTopbar(predictions) {
  const el = document.getElementById('topbar');
  const latest = predictions.find(p => p.as_of);
  const asOf = latest?.as_of || 'N/A';
  const model = latest?.model_version || 'unknown';
  const featureSet = latest?.feature_set_version || 'feature_set_v1';
  const stale = isStale(asOf);

  el.innerHTML = `
    <div class="topbar-left">
      <h1>Bias Engine <span>市场偏见控制台</span></h1>
      <div class="subtitle">数据截至 ${asOf} · 模型 ${model} · 特征集 ${featureSet} · 本地研究模式</div>
    </div>
    <div class="topbar-right">
      <div class="status-chip ${stale ? 'stale' : ''}">
        <div class="dot"></div>
        ${stale ? '数据过期' : '数据正常'}
      </div>
      <div class="status-chip">
        <div class="dot" style="background:var(--muted)"></div>
        ${predictions.length} 条预测
      </div>
    </div>
  `;
}

// ── 渲染：最强信号摘要 ──

function renderHeroSummary(grouped) {
  const el = document.getElementById('heroSummary');
  const symbols = Object.keys(grouped);

  let strongest = null;
  let strongestScore = 0;
  for (const symbol of symbols) {
    for (const h of HORIZONS) {
      const p = grouped[symbol][h];
      if (p && Math.abs(p.bias_score) > Math.abs(strongestScore)) {
        strongestScore = p.bias_score;
        strongest = { symbol, horizon: h, ...p };
      }
    }
  }

  if (!strongest) { el.innerHTML = ''; return; }

  const cls = getBiasClass(strongest.label);
  const confPct = Math.round((strongest.confidence || 0) * 100);
  el.innerHTML = `
    <div class="hero-card ${cls}">
      <div class="hero-label">最强信号</div>
      <div class="hero-symbol">${strongest.symbol} <span style="font-size:0.7em;color:var(--muted)">${MARKET_TAGS[strongest.symbol] || ''}</span></div>
      <div class="hero-score">${formatScore(strongest.bias_score)}</div>
      <div class="hero-detail">${HORIZON_CN[strongest.horizon] || strongest.horizon} · ${labelCN(strongest.label)} · 置信度 ${confPct}%</div>
    </div>
  `;
}

// ── 渲染：偏见矩阵 ──

function renderBiasMatrix(grouped) {
  const el = document.getElementById('biasMatrix');
  const symbols = Object.keys(grouped);

  let html = '<div class="matrix-grid">';
  html += '<div class="matrix-header">标的</div>';
  for (const h of HORIZONS) {
    html += `<div class="matrix-header">${HORIZON_CN[h] || h}</div>`;
  }

  for (const symbol of symbols) {
    const data = grouped[symbol];
    html += `<div class="matrix-symbol">${symbol} <span class="market-tag">${MARKET_TAGS[symbol] || ''}</span></div>`;

    for (const h of HORIZONS) {
      const p = data[h];
      if (!p) {
        html += '<div class="bias-cell is-neutral"><div class="score">--</div><div class="label">无数据</div></div>';
        continue;
      }
      const cls = getBiasClass(p.label);
      const confPct = Math.round((p.confidence || 0) * 100);
      html += `
        <div class="bias-cell ${cls}">
          <div class="score">${formatScore(p.bias_score)}</div>
          <div class="label">${labelCN(p.label)}</div>
          <div class="confidence-track">
            <div class="confidence-fill" data-width="${confPct}%" style="width:0"></div>
          </div>
          <div style="font-size:0.68rem;color:var(--muted);font-family:'JetBrains Mono',monospace;margin-top:2px">置信度 ${confPct}%</div>
        </div>
      `;
    }
  }

  html += '</div>';
  el.innerHTML = html;

  // 置信度条动画
  requestAnimationFrame(() => {
    setTimeout(() => {
      el.querySelectorAll('.confidence-fill').forEach(bar => {
        bar.style.width = bar.dataset.width;
      });
    }, 200);
  });
}

// ── 渲染：多周期冲突分析 ──

function renderConflictBoard(grouped) {
  const el = document.getElementById('conflictBoard');
  const symbols = Object.keys(grouped);
  let html = '';

  for (let si = 0; si < symbols.length; si++) {
    const symbol = symbols[si];
    const data = grouped[symbol];
    const hasConflict = detectConflict(data);
    const narrative = generateNarrative(data);

    html += `<div class="conflict-card stagger-${si + 3}">`;
    html += `<div class="card-header">`;
    html += `<div class="card-symbol">${symbol} <span style="font-size:0.75em;color:var(--muted);font-weight:400">${MARKET_TAGS[symbol] || ''}</span></div>`;
    html += `<div class="conflict-badge ${hasConflict ? 'has-conflict' : 'aligned'}">${hasConflict ? '方向冲突' : '方向一致'}</div>`;
    html += `</div>`;

    // 时间轴
    html += '<div class="timeline">';
    for (let i = 0; i < HORIZONS.length; i++) {
      const h = HORIZONS[i];
      const p = data[h];
      const lbl = p?.label || 'neutral';
      const dotLabel = lbl === 'bullish' ? '▲' : lbl === 'bearish' ? '▼' : '●';

      html += `<div class="timeline-segment">`;
      html += `<div class="timeline-dot ${lbl}">${dotLabel}</div>`;
      html += `<div class="timeline-label">${HORIZON_CN[h] || h}</div>`;
      html += `</div>`;

      if (i < HORIZONS.length - 1) {
        const nextH = HORIZONS[i + 1];
        const nextLabel = data[nextH]?.label || 'neutral';
        const lineConflict = (lbl !== nextLabel && lbl !== 'neutral' && nextLabel !== 'neutral');
        html += `<div class="timeline-line ${lineConflict ? 'conflict' : 'smooth'}"></div>`;
      }
    }
    html += '</div>';

    html += `<div class="conflict-narrative">${narrative}</div>`;
    html += '</div>';
  }

  el.innerHTML = html;
}

// ── 渲染：数据质量面板 ──

function renderQualityBoard(quality, factorLatest, grouped) {
  const el = document.getElementById('qualityBoard');
  const symbols = Object.keys(grouped);
  let html = '';

  // 每个标的健康卡片
  for (const symbol of symbols) {
    const data = grouped[symbol];
    const asOf = Object.values(data).find(p => p?.as_of)?.as_of;
    const stale = isStale(asOf);
    const health = stale ? 'warning' : 'healthy';
    const predCount = HORIZONS.filter(h => data[h]).length;

    html += `<div class="quality-card">`;
    html += `<div class="card-header"><div class="card-symbol">${symbol}</div><div class="health-dot ${health}"></div></div>`;
    html += `<div class="quality-metric"><span class="metric-label">最新日期</span><span class="metric-value">${asOf || '无'}</span></div>`;
    html += `<div class="quality-metric"><span class="metric-label">预测数</span><span class="metric-value">${predCount} / 3</span></div>`;

    if (factorLatest && factorLatest.length) {
      const symFactors = factorLatest.filter(f => f.symbol === symbol);
      if (symFactors.length) {
        html += `<div class="quality-metric"><span class="metric-label">因子数</span><span class="metric-value">${symFactors.length}</span></div>`;
      }
    }

    html += '</div>';
  }

  // 因子质量汇总卡片
  if (quality && quality.length) {
    const avgCoverage = quality.reduce((s, q) => s + (q.coverage || 0), 0) / quality.length;
    const maxExtreme = Math.max(...quality.map(q => q.extreme_share || 0));
    const factorNames = [...new Set(quality.map(q => q.factor_name))];

    html += `<div class="quality-card">`;
    html += `<div class="card-header"><div class="card-symbol">因子质量</div><div class="health-dot ${maxExtreme > 0.05 ? 'warning' : 'healthy'}"></div></div>`;
    html += `<div class="quality-metric"><span class="metric-label">因子总数</span><span class="metric-value">${factorNames.length}</span></div>`;
    html += `<div class="quality-metric"><span class="metric-label">平均覆盖率</span><span class="metric-value ${avgCoverage >= 0.95 ? 'good' : avgCoverage >= 0.8 ? 'warn' : 'bad'}">${(avgCoverage * 100).toFixed(1)}%</span></div>`;
    html += `<div class="quality-metric"><span class="metric-label">最大极值占比</span><span class="metric-value ${maxExtreme <= 0.01 ? 'good' : maxExtreme <= 0.05 ? 'warn' : 'bad'}">${(maxExtreme * 100).toFixed(2)}%</span></div>`;
    html += '</div>';
  }

  if (!html) {
    html = '<div style="color:var(--muted)">暂无质量数据。请运行: python scripts/export_visual_data.py</div>';
  }

  el.innerHTML = html;
}

// ── 主入口 ──

async function main() {
  const loading = document.getElementById('loading');

  const predictions = await loadJson(DATA_PATHS.predictions);
  const quality = await loadJson(DATA_PATHS.factorQuality);
  const factorLatest = await loadJson(DATA_PATHS.factorLatest);

  if (!predictions || !predictions.length) {
    loading.innerHTML = `
      <div style="text-align:center;color:var(--muted);max-width:480px">
        <p style="font-size:1.1rem;margin-bottom:16px">未找到预测数据</p>
        <p style="font-size:0.82rem;font-family:'JetBrains Mono',monospace;line-height:2">
          1. python run_pipeline.py --step all --start 2023-01-01<br>
          2. python scripts/export_visual_data.py<br>
          3. python -m http.server 8080 -d visual
        </p>
        <p style="font-size:0.78rem;margin-top:12px">然后打开 <a href="http://localhost:8080" style="color:var(--bull)">http://localhost:8080</a></p>
      </div>`;
    return;
  }

  const grouped = groupPredictions(predictions);

  renderTopbar(predictions);
  renderHeroSummary(grouped);
  renderBiasMatrix(grouped);
  renderConflictBoard(grouped);
  renderQualityBoard(quality, factorLatest, grouped);

  loading.classList.add('hidden');
  setTimeout(() => loading.remove(), 500);
}

main();
