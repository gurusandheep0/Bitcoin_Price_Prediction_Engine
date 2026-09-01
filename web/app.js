const state = { summary: null, history: [], backtest: [], features: [] };
const $ = selector => document.querySelector(selector);
const $$ = selector => [...document.querySelectorAll(selector)];
const usd = value => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(Number(value));
const number = value => Number(value).toLocaleString('en-US', { maximumFractionDigits: 2 });
const percent = value => `${Number(value).toFixed(2)}%`;
const pretty = value => String(value).replaceAll('_', ' ').replace(/\b\w/g, char => char.toUpperCase());

function showTab(id) {
  $$('.tab').forEach(tab => tab.classList.toggle('active', tab.id === id));
  $$('.nav').forEach(button => button.classList.toggle('active', button.dataset.tab === id));
  window.scrollTo({ top: 0, behavior: 'smooth' });
  if (id === 'backtest') setTimeout(() => drawBacktest(state.backtest), 80);
}
$$('.nav').forEach(button => button.addEventListener('click', () => showTab(button.dataset.tab)));

function canvasSetup(canvas) {
  const ratio = window.devicePixelRatio || 1;
  const width = canvas.clientWidth || 900;
  const height = Number(canvas.getAttribute('height')) * (width / Number(canvas.getAttribute('width')));
  canvas.width = width * ratio; canvas.height = height * ratio;
  const ctx = canvas.getContext('2d'); ctx.scale(ratio, ratio);
  return { ctx, width, height };
}
function plotLines(canvas, series, options = {}) {
  const { ctx, width, height } = canvasSetup(canvas); const pad = { l: 60, r: 18, t: 25, b: 36 };
  const values = series.flatMap(item => item.values).filter(Number.isFinite); if (!values.length) return;
  let low = Math.min(...values), high = Math.max(...values); const margin = (high - low || 1) * .12; low -= margin; high += margin;
  ctx.clearRect(0, 0, width, height); ctx.font = '10px DM Mono'; ctx.strokeStyle = '#202936'; ctx.fillStyle = '#748090'; ctx.lineWidth = 1;
  for (let step = 0; step <= 4; step++) { const y = pad.t + (height - pad.t - pad.b) * step / 4; ctx.beginPath(); ctx.moveTo(pad.l, y); ctx.lineTo(width - pad.r, y); ctx.stroke(); const label = high - (high - low) * step / 4; ctx.fillText(`$${Math.round(label / 1000)}k`, 4, y + 3); }
  series.forEach(item => { ctx.beginPath(); ctx.strokeStyle = item.color; ctx.lineWidth = item.width || 2; item.values.forEach((value, index) => { const x = pad.l + (width - pad.l - pad.r) * index / Math.max(item.values.length - 1, 1); const y = pad.t + (high - value) / (high - low) * (height - pad.t - pad.b); index ? ctx.lineTo(x, y) : ctx.moveTo(x, y); }); ctx.stroke(); });
  if (options.marker !== undefined) { const x = pad.l + (width - pad.l - pad.r) * options.marker / Math.max(series[0].values.length - 1, 1); ctx.strokeStyle = '#f4f1e9'; ctx.setLineDash([3, 5]); ctx.beginPath(); ctx.moveTo(x, pad.t); ctx.lineTo(x, height - pad.b); ctx.stroke(); ctx.setLineDash([]); }
}
function renderSummary(data) {
  state.summary = data; const forecast = data.latest_forecast; const selected = data.leaderboard.find(row => row.model === data.selected_model);
  $('#selected-model').textContent = pretty(data.selected_model); $('#forecast-date').textContent = forecast.forecast_for;
  $('#forecast-price').textContent = usd(forecast.predicted_close_usd); $('#forecast-change').textContent = `${forecast.predicted_change_percent >= 0 ? '+' : ''}${percent(forecast.predicted_change_percent)} modeled change`;
  $('#last-close').textContent = usd(forecast.last_close_usd); $('#as-of').textContent = `as of ${forecast.as_of}`;
  $('#range-low').textContent = usd(forecast.interval_low_usd); $('#range-high').textContent = usd(forecast.interval_high_usd); $('#coverage-label').textContent = `${data.holdout.interval_empirical_coverage_percent}% observed`;
  $('#metric-mae').textContent = usd(selected.mae_usd); $('#metric-rmse').textContent = usd(selected.rmse_usd); $('#metric-direction').textContent = percent(selected.directional_accuracy_percent); $('#metric-interval').textContent = percent(data.holdout.interval_empirical_coverage_percent);
  $('#market-return').textContent = percent(data.market_30d.return_percent); $('#market-vol').textContent = percent(data.market_30d.realized_volatility_percent); $('#market-drawdown').textContent = percent(data.market_30d.max_drawdown_percent); $('#market-volume').textContent = `${number(data.market_30d.average_volume_btc)} BTC`;
  $('#deployment-state').textContent = pretty(data.deployment_status); $('#baseline-note').textContent = `${data.baseline_improvement_percent >= 0 ? '+' : ''}${data.baseline_improvement_percent}% MAE improvement versus persistence.`;
  $('#interval-radius').textContent = `± ${usd(data.holdout.interval_radius_usd)}`; $('#data-range').textContent = `${data.data.start} → ${data.data.end} · ${number(data.data.candles)} daily candles`; $('#validation-method').textContent = data.validation;
  const leaderboard = [...data.leaderboard].sort((a, b) => a.mae_usd - b.mae_usd);
  $('#model-table').innerHTML = leaderboard.map((row, index) => `<tr class="${row.model === data.selected_model ? 'selected' : ''}"><td>0${index + 1}</td><td><b>${pretty(row.model)}</b></td><td>${usd(row.mae_usd)}</td><td>${usd(row.rmse_usd)}</td><td>${percent(row.mape_percent)}</td><td>${percent(row.directional_accuracy_percent)}</td><td>${row.is_baseline ? 'baseline' : row.model === data.selected_model ? 'selected ML' : 'challenger'}</td></tr>`).join('');
  const maxMae = Math.max(...leaderboard.map(row => row.mae_usd)); $('#comparison-bars').innerHTML = leaderboard.map(row => `<div><span>${pretty(row.model)}</span><div><i style="width:${row.mae_usd / maxMae * 100}%"></i></div><b>${usd(row.mae_usd)}</b></div>`).join('');
}
async function loadHistory(days = 365) { const response = await fetch(`/api/history?days=${days}`); const data = await response.json(); state.history = data.candles; plotLines($('#history-chart'), [{ values: data.candles.map(row => Number(row.close)), color: '#ff7849', width: 2.2 }]); $('#history-window').textContent = `${data.candles[0].date} — ${data.candles.at(-1).date}`; }
function drawBacktest(rows, marker) { if (!rows.length) return; plotLines($('#backtest-chart'), [{ values: rows.map(row => Number(row.target_close)), color: '#f4f1e9', width: 2 }, { values: rows.map(row => Number(row.predicted_close)), color: '#ff7849', width: 2 }, { values: rows.map(row => Number(row.baseline_close)), color: '#60d8ff', width: 1 }], { marker }); }
function renderDay(index) { const row = state.backtest[index]; if (!row) return; $('#explorer-date').textContent = row.target_date; $('#day-actual').textContent = usd(row.target_close); $('#day-predicted').textContent = usd(row.predicted_close); $('#day-baseline').textContent = usd(row.baseline_close); $('#day-error').textContent = usd(row.absolute_error); drawBacktest(state.backtest, index); }
async function loadBacktest() { const response = await fetch('/api/backtest?days=180'); const data = await response.json(); state.backtest = data.rows; const slider = $('#day-slider'); slider.max = Math.max(data.rows.length - 1, 0); slider.value = slider.max; renderDay(Number(slider.value)); }
async function loadFeatures() { const response = await fetch('/api/features?limit=12'); const data = await response.json(); state.features = data.features; const max = Math.max(...data.features.map(row => Number(row.importance)), .0001); $('#feature-bars').innerHTML = data.features.map(row => `<div><span>${pretty(row.feature)}</span><div><i style="width:${Number(row.importance) / max * 100}%"></i></div><b>${(Number(row.importance) * 100).toFixed(1)}%</b></div>`).join(''); }
$$('[data-days]').forEach(button => button.addEventListener('click', async () => { $$('[data-days]').forEach(item => item.classList.remove('active')); button.classList.add('active'); await loadHistory(button.dataset.days); }));
$('#day-slider').addEventListener('input', event => renderDay(Number(event.target.value)));
window.addEventListener('resize', () => { if (state.history.length) plotLines($('#history-chart'), [{ values: state.history.map(row => Number(row.close)), color: '#ff7849', width: 2.2 }]); if (state.backtest.length && $('#backtest').classList.contains('active')) renderDay(Number($('#day-slider').value)); });
async function boot() { try { const [health, summary] = await Promise.all([fetch('/api/health').then(r => r.json()), fetch('/api/summary').then(r => r.json())]); if (health.status !== 'ready') throw new Error('Model artifacts unavailable'); $('#engine-state').textContent = 'READY'; renderSummary(summary); await Promise.all([loadHistory(), loadBacktest(), loadFeatures()]); } catch (error) { $('#engine-state').textContent = 'SETUP REQUIRED'; const toast = $('#toast'); toast.textContent = `${error.message}. Run ./scripts/reproduce.sh`; toast.classList.add('show'); } }
boot();
