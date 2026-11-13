// "Savol bering" sahifasi: savol -> SSE voqealari -> jarayon, natija kartasi, manbalar.
// Har bir voqeaning maydonlari docs/sse-contract.md da.
// Qoida: ekrandagi har bir raqam backend voqeasidan olinadi; bo'lmasa "Mavjud emas".
import { ask, searchIndicators } from '../api/client.js';
import { replay, downloadRecording } from '../api/demo.js';
import { renderStages, setStageState, setStageDetail, failActiveStages } from './stagesPanel.js';
import { renderSeriesChart } from '../viz/seriesChart.js';
import { formatNumber, el } from '../core/format.js';
import { STAGES, TOOLS } from '../core/stages.js';

// Qaysi voqea qaysi bosqichga tegishli (inspektor uchun)
function stageOf(name, d) {
  if (name.startsWith('stage.')) return d.stage;
  return {
    'search.completed': 'search',
    'tool.called': 'tool',
    'tool.result': 'result',
    'verification.completed': 'verify',
    'done': 'generate',
  }[name];
}

const $ = (s) => document.querySelector(s);

// demo: null — jonli rejim; { rec } — demo rejim (rec = null bo'lsa yozuv yo'q)
export function initAskView({ scene, inspector, demo = null }) {
  const form = $('#ask-form');
  const input = $('#question');
  const button = form.querySelector('button');
  const stagesEl = $('#stages');
  const searchEl = $('#search-results');
  const chartEl = $('#result-chart');
  const answerEl = $('#answer');
  const verifyEl = $('#verification');
  const sourcesEl = $('#sources');
  const saveDemoBtn = $('#save-demo');
  const resultEl = $('#result');
  const progressEl = document.querySelector('.progress');
  const pipeBar = $('#pipe-bar');
  const pipeText = $('#pipe-text');
  const pipeState = $('#pipe-state');
  const agentState = $('#agent-state');
  const statusBadge = $('#r-status');

  // Shu savoldagi barcha voqealar: [{ name, data, t }] — inspektor va demo yozuvi uchun
  let log = [];
  let startedAt = 0;
  let lastQuestion = '';
  let parsed = {};      // parse bosqichi: detected_period, detected_item_code
  let tableName = '';   // dwh bosqichi: qaysi jadval
  let runId = 0;        // eski savolning kechikkan natijasi yangisini buzmasin

  // ---------------- Inspektor ----------------
  function inspectStage(stageId, btn) {
    const stage = STAGES.find((s) => s.id === stageId);
    let events = log.filter((e) => stageOf(e.name, e.data) === stageId);
    if (stageId === 'generate') {
      // generation.delta lar ko'p — bittaga jamlab ko'rsatamiz
      const deltas = log.filter((e) => e.name === 'generation.delta');
      if (deltas.length) {
        events = [{
          name: `generation.delta × ${deltas.length}`,
          t: deltas[0].t,
          data: { matn_uzunligi: deltas.reduce((n, e) => n + (e.data.delta ?? '').length, 0) },
        }, ...events];
      }
    }
    inspector.open(`${stage.title} — ${stage.question}`, events, btn);
  }

  function inspectTool(name, btn) {
    // Shu tool'ning chaqiruvi va unga mos natija (call_id bo'yicha)
    const events = [];
    log.forEach((e, i) => {
      if (e.name === 'tool.called' && e.data.tool === name) {
        events.push(e);
        const res = log.slice(i + 1).find((r) => r.name === 'tool.result'
          && (!e.data.call_id || r.data.call_id === e.data.call_id));
        if (res) events.push(res);
      }
    });
    inspector.open(`MCP tool: ${name}`, events, btn, 'Bu savolda bu tool chaqirilmagan.');
  }
  scene?.setToolClickHandler?.(inspectTool);

  // ---------------- O'ng panel: 6 ta tool ----------------
  const toolButtons = new Map();
  const toolList = $('#tool-list');
  for (const name of TOOLS) {
    const btn = el('button');
    btn.type = 'button';
    btn.append(el('span', '', 'tdot'), el('span', name, 'tname'), el('span', 'kutmoqda', 'tstat'));
    btn.setAttribute('aria-label', `${name}: chaqiruv ma’lumoti`);
    btn.addEventListener('click', () => inspectTool(name, btn));
    const li = el('li');
    li.append(btn);
    toolList.append(li);
    toolButtons.set(name, btn);
  }
  function markTool(name) {
    const btn = toolButtons.get(name);
    if (!btn) return;
    btn.dataset.called = 'true';
    btn.querySelector('.tstat').textContent = 'chaqirildi';
  }

  // ---------------- Ixcham jarayon ----------------
  const done = new Set();
  function updateProgress(activeId) {
    const pct = Math.round((done.size / STAGES.length) * 100);
    pipeBar.style.width = `${pct}%`;
    const active = STAGES.find((s) => s.id === activeId);
    if (active) {
      pipeText.replaceChildren(el('b', `${done.size}/${STAGES.length}`), document.createTextNode(` · ${active.title}…`));
      agentState.textContent = `agent · ${active.title.toLowerCase()}`;
    }
  }
  function setRunState(state) {
    progressEl.dataset.state = state;
    agentState.dataset.busy = String(state === 'running');
    pipeState.textContent = { running: 'ISHLAYAPTI', done: 'TAYYOR', error: 'XATO', idle: 'KUTMOQDA' }[state];
    if (state !== 'running') agentState.textContent = 'agent · kutmoqda';
    document.body.classList.toggle('busy', state === 'running');
  }
  function stage(id, state) {
    setStageState(stagesEl, id, state);
    if (state === 'done') done.add(id);
    updateProgress(state === 'active' ? id : null);
    scene?.stage?.(id, state);
  }

  renderStages(stagesEl, inspectStage);

  // ---------------- Natija kartasi ----------------
  const kpi = (id, v) => { $(id).textContent = v; };
  function setMeta(id, v) { $(id).textContent = v ?? '—'; }

  function showFigure(rows, unit) {
    const fig = $('#r-figure');
    const valid = rows.filter((r) => r.value !== null && r.value !== undefined && !Number.isNaN(Number(r.value)));
    if (!valid.length) { fig.hidden = true; return; }

    // Asosiy raqam: savoldagi davr va mahsulot; topilmasa — eng oxirgi davr
    const sorted = [...valid].sort((a, b) => String(a.period_key).localeCompare(String(b.period_key)));
    const main = sorted.find((r) => r.period_key === parsed.detected_period
      && (!parsed.detected_item_code || r.item_code === parsed.detected_item_code))
      ?? sorted.findLast((r) => !parsed.detected_item_code || r.item_code === parsed.detected_item_code)
      ?? sorted.at(-1);
    const series = sorted.filter((r) => r.item_code === main.item_code);

    $('#r-label').textContent = `${main.item_name ?? main.item_code ?? ''} · ${main.period_key}`;
    $('#r-value').textContent = formatNumber(Number(main.value));
    $('#r-unit').textContent = unit || '';

    // Oldingi davrga nisbatan o'zgarish (ikkala qiymat ham backenddan)
    const idx = series.indexOf(main);
    const prev = idx > 0 ? series[idx - 1] : null;
    const deltaEl = $('#r-delta');
    const capEl = $('#r-delta-cap');
    if (prev && Number(prev.value)) {
      const pct = ((Number(main.value) - Number(prev.value)) / Math.abs(Number(prev.value))) * 100;
      deltaEl.className = `delta ${pct > 0.05 ? 'up' : pct < -0.05 ? 'down' : 'flat'}`;
      deltaEl.textContent = `${pct > 0 ? '▲' : pct < 0 ? '▼' : '•'} ${Math.abs(pct).toFixed(1).replace('.', ',')}%`;
      capEl.textContent = `${prev.period_key} ga nisbatan`;
    } else {
      deltaEl.textContent = '';
      capEl.textContent = '';
    }

    drawSpark($('#r-spark'), series.map((r) => Number(r.value)), series.indexOf(main));
    // To'liq ekran uchun: monitordagi kabi ustunlar (qiymatsiz oylar ham — "yo'q")
    const allRows = rows
      .filter((r) => r.item_code === main.item_code)
      .sort((a, b) => String(a.period_key).localeCompare(String(b.period_key)));
    drawBars($('#r-bars'), allRows, main, unit);
    $('#r-spark-cap').textContent = series.length > 1
      ? `${series[0].period_key} — ${series.at(-1).period_key} · ${series.length} davr`
      : '';
    fig.hidden = false;
  }

  // Yangi savol — eski holatni to'liq tozalaymiz
  function reset(question) {
    log = [];
    parsed = {};
    tableName = '';
    done.clear();
    startedAt = performance.now();
    saveDemoBtn.hidden = true;
    renderStages(stagesEl, inspectStage);
    scene?.reset();
    for (const btn of toolButtons.values()) {
      delete btn.dataset.called;
      btn.querySelector('.tstat').textContent = 'kutmoqda';
    }
    searchEl.replaceChildren();
    chartEl.replaceChildren();
    verifyEl.replaceChildren();
    sourcesEl.replaceChildren();
    answerEl.textContent = '';
    answerEl.dataset.state = 'streaming';
    $('#r-figure').hidden = true;
    $('#r-question').textContent = question;
    statusBadge.textContent = 'Ishlanmoqda…';
    delete statusBadge.dataset.state;
    for (const id of ['#m-tool', '#m-table', '#m-dwh', '#m-verify']) setMeta(id, '—');
    for (const id of ['#k-found', '#k-rows', '#k-time']) kpi(id, '—');
    $('#r-latency').textContent = '—';
    runId++;
    // Javob kartasi darhol chiqmaydi: avval sahnada butun yo'l ko'rsatiladi
    resultEl.hidden = true;
    setFull(false);
    scene?.setPaused?.(false);
    pipeBar.style.width = '0%';
    pipeText.textContent = 'Savol yuborildi…';
    setRunState('running');
    skipBtn.hidden = false;
  }

  function finish(state) {
    const secs = ((performance.now() - startedAt) / 1000).toFixed(2).replace('.', ',');
    $('#r-latency').textContent = `${secs} s`;
    kpi('#k-time', `${secs} s`);
    statusBadge.dataset.state = state;
    statusBadge.textContent = { done: '✓ Manbali javob', notfound: 'Topilmadi', error: 'Xato' }[state];
    scene?.stage?.('all', state);

    // Sahna animatsiyasi tugashini kutamiz (ko'pi bilan 20 s), keyin karta chiqadi
    const run = runId;
    pipeBar.style.width = '100%';
    pipeText.textContent = 'Natija ko‘rsatilmoqda…';
    // Oldindan tayyorlash: karta ko'rinmas holda to'liq ekran o'lchamida joylashtiriladi,
    // shunda ochilish paytida brauzer hech narsani qayta hisoblamaydi (kadr uzilmaydi)
    if (state !== 'error') {
      resultEl.classList.add('full', 'pending');
      resultEl.hidden = false;
    }
    const idle = scene?.whenIdle?.() ?? Promise.resolve();
    Promise.race([idle, new Promise((r) => setTimeout(r, 20000))]).then(() => {
      if (run === runId) reveal(state, secs);
    });
  }

  // To'liq ekran rejimi: monitor ekrani butun ekranni egallaydi
  function setFull(on) {
    resultEl.classList.toggle('full', on);
    resultEl.classList.remove('pending');
    if (!on) document.body.classList.remove('result-full');
    $('#r-close').hidden = !on;
  }
  function closeFull() {
    if (!resultEl.classList.contains('full')) return;
    scene?.setPaused?.(false);
    setFull(false);
    scene?.overview?.();
  }
  $('#r-close').addEventListener('click', closeFull);
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && resultEl.classList.contains('full') && !document.querySelector('dialog[open]')) closeFull();
  });

  function reveal(state, secs) {
    skipBtn.hidden = true;
    // Javob monitor ekranidan butun ekranga ochiladi: avval sekin, keyin tez (≈0,7 s)
    const from = state === 'error' ? null : scene?.monitorRect?.();
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const full = Boolean(from && from.width > 4);
    resultEl.classList.toggle('flip', full && !reduce);
    const done = () => {
      // Ochilib bo'lgach: orqadagi panellar yashiriladi, 3D chizish to'xtaydi
      resultEl.style.willChange = '';
      if (resultEl.classList.contains('full')) {
        document.body.classList.add('result-full');
        scene?.setPaused?.(true);
      }
    };
    if (full && !reduce) {
      const to = resultEl.getBoundingClientRect(); // oldindan joylashgan — arzon
      resultEl.style.willChange = 'transform, opacity';
      setFull(true);
      resultEl.hidden = false;
      // Tez, lekin silliq ease-out: boshida tez, oxirida yumshoq to'xtaydi (0,6 s)
      const anim = resultEl.animate([
        { transformOrigin: 'top left', opacity: 0.9, transform: `translate(${from.left - to.left}px, ${from.top - to.top}px) scale(${from.width / to.width}, ${from.height / to.height})` },
        { transformOrigin: 'top left', opacity: 1, transform: 'translate(0, 0) scale(1, 1)' },
      ], { duration: 600, easing: 'cubic-bezier(.22, 1, .36, 1)' });
      anim.finished.then(done, done);
    } else {
      setFull(full);
      resultEl.hidden = false;
      done();
    }
    if (full) $('#r-close').focus({ preventScroll: true });
    rollNumber($('#r-value'));
    if (state === 'error') {
      setRunState('error');
      pipeText.textContent = 'To‘xtadi — xato. Sababi: «AI buni qanday topdi?» ichida.';
    } else {
      setRunState('done');
      pipeBar.style.width = '100%';
      pipeText.replaceChildren(el('b', 'Tayyor'), document.createTextNode(` · ${secs} s`));
    }
  }

  // Har bir SSE voqeasi shu yerda ekranga ulanadi
  function handleEvent(name, d) {
    log.push({ name, data: d, t: Math.round(performance.now() - startedAt) });
    switch (name) {
      case 'stage.started':
        stage(d.stage, 'active');
        break;

      case 'stage.completed':
        stage(d.stage, 'done');
        if (d.stage === 'parse') {
          parsed = d;
          const parts = [`til: ${d.lang ?? '?'}`, `qidiruv: “${d.normalized_query ?? ''}”`];
          if (d.detected_period) parts.push(`davr: ${d.detected_period}`);
          if (d.detected_item_code) parts.push(`kod: ${d.detected_item_code}`);
          setStageDetail(stagesEl, 'parse', parts.join(' · '));
        }
        if (d.stage === 'dwh') {
          tableName = d.table ?? '';
          setStageDetail(stagesEl, 'dwh', `${d.table} · ${d.rows_count} qator · ${d.execution_ms} ms`);
          setMeta('#m-table', d.table);
          setMeta('#m-dwh', d.execution_ms !== undefined ? `${d.execution_ms} ms` : null);
          kpi('#k-rows', formatNumber(d.rows_count));
        }
        break;

      case 'search.completed':
        setStageDetail(stagesEl, 'search', `${d.total_matches} ta topildi · ${d.execution_ms} ms`);
        kpi('#k-found', formatNumber(d.total_matches));
        renderSearchResults(searchEl, d.results ?? [], d.selected_indicator_id);
        if (d.selected_indicator_id) scene?.selectIndicator(d.selected_indicator_id);
        break;

      case 'tool.called':
        // "tool" bosqichi uchun alohida started/completed yo'q — chaqiruvning o'zi belgi
        stage('tool', 'done');
        setStageDetail(stagesEl, 'tool', `${d.tool}(${formatArgs(d.arguments)})`);
        setMeta('#m-tool', d.tool);
        markTool(d.tool);
        scene?.highlightTool(d.tool);
        break;

      case 'tool.result': {
        stage('result', 'done');
        const rows = d.data ?? [];
        setStageDetail(stagesEl, 'result', `${rows.length} qator · ${d.execution_ms} ms`);
        const opts = { unit: d.unit ?? '', sourceUrl: rows[0]?.source_url ?? '' };
        renderSeriesChart(chartEl, rows, opts);
        scene?.showBars(rows, opts);
        showFigure(rows, d.unit ?? '');
        if (!tableName && $('#m-table').textContent === '—') setMeta('#m-table', d.indicator_name);
        break;
      }

      case 'generation.delta':
        answerEl.textContent += d.delta ?? '';
        break;

      case 'verification.completed':
        setStageDetail(stagesEl, 'verify', `${d.passed_count}/${d.total_sentences} jumla o‘tdi`);
        setMeta('#m-verify', `${d.passed_count}/${d.total_sentences} jumla`);
        renderVerification(verifyEl, d.checklist ?? []);
        break;

      case 'done': {
        // Yakuniy javob — faqat tekshiruvdan o'tgan jumlalar
        answerEl.textContent = d.answer || 'Bu haqda ma’lumot topilmadi.';
        const state = (d.sources ?? []).length ? 'done' : 'notfound';
        answerEl.dataset.state = state;
        renderSources(sourcesEl, d.sources ?? []);
        finish(state);
        break;
      }

      case 'error':
        failActiveStages(stagesEl);
        answerEl.textContent = `Xato: ${d.message ?? 'noma’lum'}`;
        answerEl.dataset.state = 'error';
        finish('error');
        break;
    }
  }

  // ---------------- Kiritish ----------------
  if (demo) {
    if (demo.rec) input.value = demo.rec.question;
    input.readOnly = true;
    for (const chip of document.querySelectorAll('.chip')) chip.hidden = true;
  }
  // ---------------- 1) Animatsiyani o'tkazib yuborish ----------------
  const skipBtn = $('#skip-anim');
  skipBtn.addEventListener('click', () => {
    skipBtn.hidden = true;
    pipeText.textContent = 'Javob kutilmoqda…';
    scene?.skip?.(); // backend tugagan bo'lsa — javob darhol chiqadi; tugamagan bo'lsa — kelishi bilan
  });

  // ---------------- 2) Yozayotganda tavsiya: bazadagi haqiqiy ko'rsatkichlar ----------------
  const sugBox = $('#suggest-box');
  const sugList = $('#suggest');
  let sugItems = [];
  let sugActive = -1;
  let sugSeq = 0;
  let sugTimer = 0;
  function closeSuggest() {
    sugBox.hidden = true;
    sugItems = [];
    sugActive = -1;
    input.setAttribute('aria-expanded', 'false');
    input.removeAttribute('aria-activedescendant');
  }
  function markActive(i) {
    sugActive = i;
    [...sugList.children].forEach((li, k) => li.setAttribute('aria-selected', String(k === i)));
    if (i >= 0) input.setAttribute('aria-activedescendant', `sug-${i}`);
    else input.removeAttribute('aria-activedescendant');
  }
  function pickSuggest(i) {
    const r = sugItems[i];
    if (!r) return;
    input.value = `${r.name_uz} `;
    closeSuggest();
    input.focus();
    input.setSelectionRange(input.value.length, input.value.length);
    input.dispatchEvent(new Event('input'));
  }
  function showSuggest(results) {
    sugList.replaceChildren();
    sugItems = results.slice(0, 6);
    if (!sugItems.length) { closeSuggest(); return; }
    sugItems.forEach((r, i) => {
      const li = el('li', '', 'sug-item');
      li.id = `sug-${i}`;
      li.setAttribute('role', 'option');
      li.setAttribute('aria-selected', 'false');
      li.append(el('span', r.name_uz ?? `#${r.indicator_id}`), el('small', [r.unit, r.periodicity].filter(Boolean).join(' · ')));
      li.addEventListener('mousedown', (e) => { e.preventDefault(); pickSuggest(i); });
      sugList.append(li);
    });
    sugBox.hidden = false;
    input.setAttribute('aria-expanded', 'true');
    markActive(-1);
  }
  input.addEventListener('input', (e) => {
    if (demo) return;
    clearTimeout(sugTimer);
    const q = input.value.trim();
    if (q.length < 3 || button.disabled) { closeSuggest(); return; }
    sugTimer = setTimeout(async () => {
      const my = ++sugSeq;
      try {
        const res = await searchIndicators(q, 6);
        if (my === sugSeq && document.activeElement === input) showSuggest(res?.results ?? []);
      } catch {
        closeSuggest(); // backend javob bermasa — tavsiya ko'rsatilmaydi, hech narsa o'ylab topilmaydi
      }
    }, 250);
  });
  input.addEventListener('blur', () => setTimeout(closeSuggest, 120));

  // ---------------- 3) Oxirgi savollar (localStorage, faqat shu brauzerda) ----------------
  const RECENT_KEY = 'aethelgard.recent';
  const recentBox = $('#recent');
  const recentList = $('#recent-list');
  const loadRecent = () => {
    try { return JSON.parse(localStorage.getItem(RECENT_KEY) || '[]').filter((x) => typeof x === 'string'); } catch { return []; }
  };
  const saveRecent = (arr) => { try { localStorage.setItem(RECENT_KEY, JSON.stringify(arr)); } catch { /* saqlanmasa ham ishlayveradi */ } };
  function renderRecent() {
    const items = loadRecent();
    recentList.replaceChildren();
    for (const q of items) {
      const b = el('button', q, 'recent-item');
      b.type = 'button';
      b.title = 'Shu savolni qayta berish';
      b.addEventListener('click', () => { input.value = q; autosize?.(); form.requestSubmit(); });
      const li = el('li');
      li.append(b);
      recentList.append(li);
    }
    recentBox.hidden = demo !== null || !items.length;
  }
  function rememberQuestion(q) {
    if (demo) return;
    saveRecent([q, ...loadRecent().filter((x) => x !== q)].slice(0, 5));
    renderRecent();
  }
  $('#recent-clear').addEventListener('click', () => { saveRecent([]); renderRecent(); });
  renderRecent();

  // Sahna holati: savol yozilmaguncha faqat xarita; yozila boshlasa ombor va toollar chiqadi
  let started = false;
  const compose = () => { if (!started) scene?.setMode?.('compose'); };
  input.addEventListener('focus', compose);
  input.addEventListener('input', compose);
  input.addEventListener('blur', () => {
    if (!started && !input.value.trim()) scene?.setMode?.('idle');
  });

  // Savol maydoni matnga qarab o'sadi (scroll chiqmasin)
  const autosize = () => {
    input.style.height = 'auto';
    input.style.height = `${Math.min(input.scrollHeight, 128)}px`;
  };
  input.addEventListener('input', autosize);
  requestAnimationFrame(autosize);
  input.addEventListener('keydown', (e) => {
    // Tavsiya ro'yxati ochiq bo'lsa: ↑/↓ tanlash, Enter — tanlanganni olish, Esc — yopish
    if (!sugBox.hidden && sugItems.length) {
      if (e.key === 'ArrowDown') { e.preventDefault(); markActive((sugActive + 1) % sugItems.length); return; }
      if (e.key === 'ArrowUp') { e.preventDefault(); markActive((sugActive - 1 + sugItems.length) % sugItems.length); return; }
      if (e.key === 'Escape') { e.preventDefault(); closeSuggest(); return; }
      if (e.key === 'Enter' && sugActive >= 0) { e.preventDefault(); pickSuggest(sugActive); return; }
    }
    if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) {
      e.preventDefault();
      form.requestSubmit();
    }
  });
  for (const chip of document.querySelectorAll('.chip')) {
    chip.addEventListener('click', () => {
      input.value = chip.dataset.q;
      autosize();
      form.requestSubmit();
    });
  }

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const question = input.value.trim();
    if (!question) {
      form.classList.remove('shake');
      void form.offsetWidth;
      form.classList.add('shake');
      input.focus();
      return;
    }
    if (button.disabled) return;

    closeSuggest();
    rememberQuestion(question);
    reset(question);
    started = true;
    scene?.setMode?.('active');
    button.disabled = true;
    lastQuestion = question;

    // Demo: backendga so'rov yo'q, faqat yozib olingan haqiqiy voqealar
    if (demo) {
      if (demo.rec) await replay(demo.rec, handleEvent);
      else {
        failActiveStages(stagesEl);
        answerEl.textContent = 'Demo yozuvi hali yo‘q (public/demo/demo.json).';
        answerEl.dataset.state = 'error';
        finish('error');
      }
      button.disabled = false;
      return;
    }

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
      finish('error');
    } finally {
      button.disabled = false;
      // Faqat manbali, to'liq javobni demo uchun saqlash mumkin
      saveDemoBtn.hidden = answerEl.dataset.state !== 'done';
    }
  });

  saveDemoBtn.addEventListener('click', () => {
    downloadRecording({ question: lastQuestion, recorded_at: new Date().toISOString(), events: log });
  });
}

// Katta raqam o'yindagidek aylanadi va chapdan o'ngga bittalab to'xtaydi (oxirida — haqiqiy qiymat)
function rollNumber(node) {
  const text = node.textContent;
  if (!/\d/.test(text) || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  const t0 = performance.now();
  const dur = 650; // katta oyna ochilib bo'lishi (700 ms) bilan bir vaqtda to'xtaydi
  const step = () => {
    const k = Math.min((performance.now() - t0) / dur, 1);
    const lockN = Math.floor(k * text.length);
    node.textContent = [...text].map((ch, i) => (i < lockN || !/\d/.test(ch) ? ch : String(Math.floor(Math.random() * 10)))).join('');
    if (k < 1) setTimeout(step, 50);
    else node.textContent = text;
  };
  step();
}

// Ustunli grafik (to'liq ekran): arzon oy past, qimmat oy baland — monitordagi bilan bir xil.
// Balandlik qiymatlar orasidagi farqni ko'rsatadi (0 dan emas) — shuni pastda yozib qo'yamiz.
function drawBars(box, rows, main, unit) {
  box.replaceChildren();
  // null (qiymat yo'q) 0 deb hisoblanmasin — aks holda shkala noldan boshlanib, farq ko'rinmaydi
  const vals = rows.filter((r) => r.value !== null && r.value !== undefined).map((r) => Number(r.value)).filter((v) => r_ok(v));
  if (!vals.length) return;
  const min = Math.min(...vals), max = Math.max(...vals);
  const list = el('ol', '', 'bars-list');
  list.setAttribute('aria-label', `Davrlar bo‘yicha qiymat${unit ? `, ${unit}` : ''}`);
  for (const r of rows) {
    const v = Number(r.value);
    const has = r.value !== null && r.value !== undefined && r_ok(v);
    const k = has ? (max > min ? (v - min) / (max - min) : 1) : 0;
    const li = el('li', '', 'bar-item');
    if (r === main) li.dataset.main = 'true';
    if (!has) li.dataset.missing = 'true';
    const val = el('span', has ? formatNumber(v) : 'yo‘q', 'bar-val');
    const col = el('span', '', 'bar-col');
    col.style.setProperty('--h', has ? `${12 + k * 88}%` : '60%');
    col.style.setProperty('--k', k.toFixed(3));
    const per = el('span', String(r.period_key ?? '').replace(/^20/, ''), 'bar-per');
    li.title = `${r.period_key}: ${has ? `${formatNumber(v)} ${unit}` : 'bazada qiymat yo‘q'}`;
    li.append(val, col, per);
    list.append(li);
  }
  box.append(list, el('p', 'past = arzon · balandlik farqni ko‘rsatadi (0 dan emas)', 'bars-note'));
}
function r_ok(v) { return typeof v === 'number' && !Number.isNaN(v); }

// Kichik chiziqli grafik (sparkline) — faqat backend qatorlaridan
const SVG_NS = 'http://www.w3.org/2000/svg';
function drawSpark(svg, values, markIndex) {
  svg.replaceChildren();
  if (values.length < 2) return;
  const w = 210, h = 64, pad = 6;
  const min = Math.min(...values), max = Math.max(...values);
  const pts = values.map((v, i) => [
    pad + (i * (w - pad * 2)) / (values.length - 1),
    h - pad - ((v - min) / (max - min || 1)) * (h - pad * 2),
  ]);
  const d = pts.map((p, i) => `${i ? 'L' : 'M'}${p[0].toFixed(1)} ${p[1].toFixed(1)}`).join(' ');
  const mk = (tag, attrs) => {
    const n = document.createElementNS(SVG_NS, tag);
    for (const [k, v] of Object.entries(attrs)) n.setAttribute(k, v);
    return n;
  };
  const defs = mk('defs', {});
  const fill = mk('linearGradient', { id: 'spark-fill', x1: 0, y1: 0, x2: 0, y2: 1 });
  fill.append(mk('stop', { offset: 0, 'stop-color': '#38bdf8', 'stop-opacity': '.35' }), mk('stop', { offset: 1, 'stop-color': '#38bdf8', 'stop-opacity': '0' }));
  const stroke = mk('linearGradient', { id: 'spark-stroke', x1: 0, y1: 0, x2: 1, y2: 0 });
  stroke.append(mk('stop', { offset: 0, 'stop-color': '#10b981' }), mk('stop', { offset: 1, 'stop-color': '#38bdf8' }));
  defs.append(fill, stroke);
  const last = pts.at(-1);
  const area = mk('path', { d: `${d} L${last[0]} ${h} L${pts[0][0]} ${h} Z`, fill: 'url(#spark-fill)' });
  const line = mk('path', { d, fill: 'none', stroke: 'url(#spark-stroke)', 'stroke-width': 2, 'stroke-linecap': 'round', 'stroke-linejoin': 'round', 'vector-effect': 'non-scaling-stroke' });
  const m = pts[markIndex] ?? last;
  const dot = mk('circle', { cx: m[0], cy: m[1], r: 3.5, fill: '#f59e0b' });
  svg.append(defs, area, line, dot);
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
    li.append(el('span', `[${s.n}] `), a, el('small', ` · ${s.snapshot_date}`));
    listEl.append(li);
  }
}
