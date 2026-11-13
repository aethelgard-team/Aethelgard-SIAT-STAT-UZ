// "Savol bering" sahifasi: savol -> SSE voqealari -> bosqichlar, javob, manbalar.
// Har bir voqeaning maydonlari docs/sse-contract.md da.
import { ask } from '../api/client.js';
import { renderStages, setStageState, setStageDetail, failActiveStages } from './stagesPanel.js';
import { renderSeriesChart } from '../viz/seriesChart.js';
import { formatNumber, el } from '../core/format.js';

export function initAskView({ scene }) {
  const form = document.querySelector('#ask-form');
  const input = document.querySelector('#question');
  const button = form.querySelector('button');
  const stagesEl = document.querySelector('#stages');
  const searchEl = document.querySelector('#search-results');
  const chartEl = document.querySelector('#result-chart');
  const answerEl = document.querySelector('#answer');
  const verifyEl = document.querySelector('#verification');
  const sourcesEl = document.querySelector('#sources');

  renderStages(stagesEl);

  // Yangi savol — eski holatni to'liq tozalaymiz
  function reset() {
    renderStages(stagesEl);
    scene?.reset();
    searchEl.replaceChildren();
    chartEl.replaceChildren();
    verifyEl.replaceChildren();
    sourcesEl.replaceChildren();
    answerEl.textContent = '';
    answerEl.dataset.state = 'streaming';
  }

  // Har bir SSE voqeasi shu yerda ekranga ulanadi
  function handleEvent(name, d) {
    switch (name) {
      case 'stage.started':
        setStageState(stagesEl, d.stage, 'active');
        break;

      case 'stage.completed':
        setStageState(stagesEl, d.stage, 'done');
        if (d.stage === 'parse') {
          const parts = [`til: ${d.lang ?? '?'}`, `qidiruv: “${d.normalized_query ?? ''}”`];
          if (d.detected_period) parts.push(`davr: ${d.detected_period}`);
          if (d.detected_item_code) parts.push(`kod: ${d.detected_item_code}`);
          setStageDetail(stagesEl, 'parse', parts.join(' · '));
        }
        if (d.stage === 'dwh') {
          setStageDetail(stagesEl, 'dwh', `${d.table} · ${d.rows_count} qator · ${d.execution_ms} ms`);
        }
        break;

      case 'search.completed':
        setStageDetail(stagesEl, 'search', `${d.total_matches} ta topildi · ${d.execution_ms} ms`);
        renderSearchResults(searchEl, d.results ?? [], d.selected_indicator_id);
        if (d.selected_indicator_id) scene?.selectIndicator(d.selected_indicator_id);
        break;

      case 'tool.called':
        // "tool" bosqichi uchun alohida started/completed yo'q — chaqiruvning o'zi belgi
        setStageState(stagesEl, 'tool', 'done');
        setStageDetail(stagesEl, 'tool', `${d.tool}(${formatArgs(d.arguments)})`);
        scene?.highlightTool(d.tool);
        break;

      case 'tool.result':
        setStageState(stagesEl, 'result', 'done');
        setStageDetail(stagesEl, 'result', `${(d.data ?? []).length} qator · ${d.execution_ms} ms`);
        renderSeriesChart(chartEl, d.data ?? [], { unit: d.unit ?? '', sourceUrl: d.data?.[0]?.source_url ?? '' });
        scene?.showBars(d.data ?? [], { unit: d.unit ?? '', sourceUrl: d.data?.[0]?.source_url ?? '' });
        break;

      case 'generation.delta':
        answerEl.textContent += d.delta ?? '';
        break;

      case 'verification.completed':
        setStageDetail(stagesEl, 'verify', `${d.passed_count}/${d.total_sentences} jumla o‘tdi`);
        renderVerification(verifyEl, d.checklist ?? []);
        break;

      case 'done':
        // Yakuniy javob — faqat tekshiruvdan o'tgan jumlalar
        answerEl.textContent = d.answer || 'Bu haqda ma’lumot topilmadi.';
        answerEl.dataset.state = (d.sources ?? []).length ? 'done' : 'notfound';
        renderSources(sourcesEl, d.sources ?? []);
        break;

      case 'error':
        failActiveStages(stagesEl);
        answerEl.textContent = `Xato: ${d.message ?? 'noma’lum'}`;
        answerEl.dataset.state = 'error';
        break;
    }
  }

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const question = input.value.trim();
    if (!question) return;

    reset();
    button.disabled = true;
    let finished = false;
    try {
      await ask(question, (name, data) => {
        if (name === 'done' || name === 'error') finished = true;
        handleEvent(name, data);
      });
      if (!finished) handleEvent('error', { message: 'oqim "done" voqeasisiz tugadi' });
    } catch {
      // Qoida: backend bermagan narsa o'ylab topilmaydi
      failActiveStages(stagesEl);
      answerEl.textContent = 'Mavjud emas — backend javob bermadi.';
      answerEl.dataset.state = 'error';
    } finally {
      button.disabled = false;
    }
  });
}

function formatArgs(args = {}) {
  return Object.entries(args)
    .filter(([, v]) => v !== null && v !== undefined)
    .map(([k, v]) => `${k}=${JSON.stringify(v)}`)
    .join(', ');
}

function renderSearchResults(listEl, results, selectedId) {
  listEl.replaceChildren();
  for (const r of results) {
    const li = el('li');
    if (r.indicator_id === selectedId) li.dataset.selected = 'true';
    li.append(
      el('span', `#${r.indicator_id} ${r.name_uz ?? ''}`),
      el('small', `RRF ${Number(r.rrf_score ?? 0).toFixed(4)} · ${(r.matched_sources ?? []).join(', ')}`),
    );
    listEl.append(li);
  }
}

function renderVerification(listEl, checklist) {
  listEl.replaceChildren();
  for (const s of checklist) {
    const li = el('li');
    li.dataset.passed = String(Boolean(s.passed));
    li.append(el('span', s.passed ? '✓ ' : '✗ '), el('span', s.text));
    if (!s.passed && s.reason) li.append(el('small', ` — olib tashlandi: ${s.reason}`));
    listEl.append(li);
  }
}

function renderSources(listEl, sources) {
  listEl.replaceChildren();
  for (const s of sources) {
    const li = el('li');
    const a = el('a', s.name || s.url);
    a.href = s.url;
    a.target = '_blank';
    a.rel = 'noopener';
    li.append(el('span', `[${s.n}] `), a, el('small', ` · snapshot: ${s.snapshot_date}`));
    listEl.append(li);
  }
}
