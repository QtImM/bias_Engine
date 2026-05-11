/* ═══════════════════════════════════════════
   Bias Engine — Control Room App
   ═══════════════════════════════════════════ */

const DATA_PATHS = {
  predictions: './data/predictions.json',
  predictionsFallback: './data/sample_predictions.json',
  factorQuality: './data/factor_quality.json',
  factorQualityFallback: './data/sample_factor_quality.json',
};

const MARKET_TAGS = { STAR50: 'CN', HSI: 'HK', NDX: 'US' };
const HORIZONS = ['D1', 'W1', 'M1'];

// ── Data Loading ──

async function loadJson(path) {
  try {
    const res = await fetch(path);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (e) {
    console.warn(`Failed to load ${path}:`, e.message);
    return null;
  }
}

// ── Helpers ──

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

  const shortBull = d1 === 'bullish';
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

// ── Render: Topbar ──

function renderTopbar(predictions) {
  const el = document.getElementById('topbar');
  const latest = predictions.find(p => p.as_of);
  const asOf = latest?.as_of || 'N/A';
  const model = latest?.model_version || 'unknown';
  const stale = isStale(asOf);

  el.innerHTML = `
    <div class="topbar-left">
      <h1>Bias Engine <span>Market Regime Console</span></h1>
      <div class="subtitle">As of ${asOf} &middot; ${model} &middot; local research mode</div>
    </div>
    <div class="topbar-right">
      <div class="status-chip ${stale ? 'stale' : ''}">
        <div class="dot"></div>
        ${stale ? 'DATA STALE' : 'LIVE'}
      </div>
      <div class="status-chip">
        <div class="dot" style="background:var(--muted)"></div>
        ${predictions.length} predictions
      </div>
    </div>
  `;
}

// ── Render: Bias Matrix ──

function renderBiasMatrix(grouped) {
  const el = document.getElementById('bias-matrix');
  const symbols = Object.keys(grouped);

  let html = '<div class="matrix-grid">';
  // Header row
  html += '<div class="matrix-header">Symbol</div>';
  for (const h of HORIZONS) {
    html += `<div class="matrix-header">${h}</div>`;
  }

  for (const symbol of symbols) {
    const data = grouped[symbol];
    html += `<div class="matrix-symbol">${symbol} <span class="market-tag">${MARKET_TAGS[symbol] || ''}</span></div>`;

    for (const h of HORIZONS) {
      const p = data[h];
      if (!p) {
        html += '<div class="bias-cell is-neutral"><div class="score">--</div><div class="label">NO DATA</div></div>';
        continue;
      }
      const cls = getBiasClass(p.label);
      const confPct = Math.round((p.confidence || 0) * 100);
      html += `
        <div class="bias-cell ${cls}">
          <div class="score">${formatScore(p.bias_score)}</div>
          <div class="label">${(p.label || 'neutral').toUpperCase()}</div>
          <div class="confidence-track">
            <div class="confidence-fill" data-width="${confPct}%" style="width:0"></div>
          </div>
          <div style="font-size:0.68rem;color:var(--muted);font-family:'JetBrains Mono',monospace;margin-top:2px">conf ${confPct}%</div>
        </div>
      `;
    }
  }

  html += '</div>';
  el.innerHTML = html;

  // Animate confidence bars
  requestAnimationFrame(() => {
    setTimeout(() => {
      el.querySelectorAll('.confidence-fill').forEach(bar => {
        bar.style.width = bar.dataset.width;
      });
    }, 200);
  });
}

// ── Render: Conflict Board ──

function renderConflictBoard(grouped) {
  const el = document.getElementById('conflict-board');
  const symbols = Object.keys(grouped);
  let html = '';

  for (const symbol of symbols) {
    const data = grouped[symbol];
    const hasConflict = detectConflict(data);
    const narrative = generateNarrative(data);

    html += `<div class="conflict-card stagger-${symbols.indexOf(symbol) + 2}">`;
    html += `<div class="card-header">`;
    html += `<div class="card-symbol">${symbol}</div>`;
    html += `<div class="conflict-badge ${hasConflict ? 'has-conflict' : 'aligned'}">${hasConflict ? 'CONFLICT' : 'ALIGNED'}</div>`;
    html += `</div>`;

    // Timeline
    html += '<div class="timeline">';
    for (let i = 0; i < HORIZONS.length; i++) {
      const h = HORIZONS[i];
      const p = data[h];
      const label = p?.label || 'neutral';
      const dotLabel = label === 'bullish' ? '▲' : label === 'bearish' ? '▼' : '●';

      html += `<div class="timeline-segment">`;
      html += `<div class="timeline-dot ${label}">${dotLabel}</div>`;
      html += `<div class="timeline-label">${h}</div>`;
      html += `</div>`;

      if (i < HORIZONS.length - 1) {
        const nextH = HORIZONS[i + 1];
        const nextLabel = data[nextH]?.label || 'neutral';
        const lineConflict = (label !== nextLabel && label !== 'neutral' && nextLabel !== 'neutral');
        html += `<div class="timeline-line ${lineConflict ? 'conflict' : 'smooth'}"></div>`;
      }
    }
    html += '</div>';

    html += `<div class="conflict-narrative">${narrative}</div>`;
    html += '</div>';
  }

  el.innerHTML = html;
}

// ── Render: Factor Board ──

function renderFactorBoard(grouped) {
  const el = document.getElementById('factor-board');
  const symbols = Object.keys(grouped);
  let html = '';

  for (const symbol of symbols) {
    const data = grouped[symbol];
    // Use the horizon with highest confidence for factor display
    let bestH = 'D1';
    let bestConf = 0;
    for (const h of HORIZONS) {
      const conf = data[h]?.confidence || 0;
      if (conf > bestConf) { bestConf = conf; bestH = h; }
    }
    const p = data[bestH];
    if (!p) continue;

    const posFactors = (p.top_positive_factors || []).slice(0, 5);
    const negFactors = (p.top_negative_factors || []).slice(0, 5);
    const allContribs = [...posFactors, ...negFactors].map(f => Math.abs(f.contribution || 0));
    const maxContrib = Math.max(...allContribs, 0.001);

    html += `<div class="factor-card stagger-${symbols.indexOf(symbol) + 3}">`;
    html += `<div class="card-title">${symbol}</div>`;
    html += `<div class="card-subtitle">${bestH} horizon &middot; bias ${formatScore(p.bias_score)} &middot; ${(p.label || '').toUpperCase()}</div>`;

    if (posFactors.length) {
      html += '<div class="factor-label">POSITIVE DRIVERS</div>';
      for (const f of posFactors) {
        const pct = Math.round((Math.abs(f.contribution) / maxContrib) * 100);
        html += `
          <div class="factor-row">
            <div class="factor-name">${f.name}</div>
            <div class="factor-bar-track"><div class="factor-bar-fill positive" style="width:${pct}%"></div></div>
            <div class="factor-value" style="color:var(--bull)">${f.contribution >= 0 ? '+' : ''}${(f.contribution || 0).toFixed(4)}</div>
          </div>`;
      }
    }

    if (negFactors.length) {
      html += '<div class="factor-label">NEGATIVE DRIVERS</div>';
      for (const f of negFactors) {
        const pct = Math.round((Math.abs(f.contribution) / maxContrib) * 100);
        html += `
          <div class="factor-row">
            <div class="factor-name">${f.name}</div>
            <div class="factor-bar-track"><div class="factor-bar-fill negative" style="width:${pct}%"></div></div>
            <div class="factor-value" style="color:var(--bear)">${(f.contribution || 0).toFixed(4)}</div>
          </div>`;
      }
    }

    if (!posFactors.length && !negFactors.length) {
      html += '<div style="color:var(--muted);font-size:0.82rem">No factor data available</div>';
    }

    html += '</div>';
  }

  el.innerHTML = html;
}

// ── Render: Quality Board ──

function renderQualityBoard(quality, grouped) {
  const el = document.getElementById('quality-board');
  if (!quality || !quality.length) {
    el.innerHTML = '<div style="color:var(--muted)">No factor quality data. Run: python scripts/export_visual_data.py</div>';
    return;
  }

  // Aggregate quality per factor
  const factorNames = [...new Set(quality.map(q => q.factor_name))].sort();
  const avgCoverage = quality.reduce((s, q) => s + (q.coverage || 0), 0) / quality.length;
  const maxExtreme = Math.max(...quality.map(q => q.extreme_share || 0));

  let html = '';
  // Summary card
  const symbols = Object.keys(grouped);
  for (const symbol of symbols) {
    const data = grouped[symbol];
    const asOf = Object.values(data).find(p => p?.as_of)?.as_of;
    const stale = isStale(asOf);
    const health = stale ? 'warning' : 'healthy';

    html += `<div class="quality-card">`;
    html += `<div class="card-header"><div class="card-symbol">${symbol}</div><div class="health-dot ${health}"></div></div>`;
    html += `<div class="quality-metric"><span class="metric-label">Latest Date</span><span class="metric-value">${asOf || 'N/A'}</span></div>`;
    html += `<div class="quality-metric"><span class="metric-label">Predictions</span><span class="metric-value">${HORIZONS.filter(h => data[h]).length} / 3</span></div>`;
    html += '</div>';
  }

  // Overall quality card
  html += `<div class="quality-card">`;
  html += `<div class="card-header"><div class="card-symbol">Factor Quality</div><div class="health-dot ${maxExtreme > 0.05 ? 'warning' : 'healthy'}"></div></div>`;
  html += `<div class="quality-metric"><span class="metric-label">Factors</span><span class="metric-value">${factorNames.length}</span></div>`;
  html += `<div class="quality-metric"><span class="metric-label">Avg Coverage</span><span class="metric-value ${avgCoverage >= 0.95 ? 'good' : avgCoverage >= 0.8 ? 'warn' : 'bad'}">${(avgCoverage * 100).toFixed(1)}%</span></div>`;
  html += `<div class="quality-metric"><span class="metric-label">Max Extreme</span><span class="metric-value ${maxExtreme <= 0.01 ? 'good' : maxExtreme <= 0.05 ? 'warn' : 'bad'}">${(maxExtreme * 100).toFixed(2)}%</span></div>`;
  html += '</div>';

  el.innerHTML = html;
}

// ── Main ──

async function main() {
  const loading = document.getElementById('loading');

  // Load data (try pipeline output first, fallback to sample)
  let predictions = await loadJson(DATA_PATHS.predictions);
  if (!predictions || !predictions.length) {
    predictions = await loadJson(DATA_PATHS.predictionsFallback);
  }
  let quality = await loadJson(DATA_PATHS.factorQuality);
  if (!quality || !quality.length) {
    quality = await loadJson(DATA_PATHS.factorQualityFallback);
  }

  if (!predictions || !predictions.length) {
    loading.innerHTML = `
      <div style="text-align:center;color:var(--muted)">
        <p style="font-size:1.1rem;margin-bottom:12px">No prediction data found</p>
        <p style="font-size:0.82rem;font-family:'JetBrains Mono',monospace">
          Run: python run_pipeline.py --step all --start 2023-01-01<br>
          Then: python scripts/export_visual_data.py
        </p>
      </div>`;
    return;
  }

  const grouped = groupPredictions(predictions);

  // Render all sections
  renderTopbar(predictions);
  renderBiasMatrix(grouped);
  renderConflictBoard(grouped);
  renderFactorBoard(grouped);
  renderQualityBoard(quality, grouped);

  // Hide loading
  loading.classList.add('hidden');
  setTimeout(() => loading.remove(), 500);
}

main();
