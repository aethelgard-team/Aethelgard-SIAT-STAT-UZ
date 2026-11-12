// "Bazada nima bor" sahifasi: DWH statistikasi, katalog qidiruvi,
// ko'rsatkich sahifasi (metadata + 2D grafik /api/series dan).
import { getStats, searchIndicators, getIndicator, getSeries } from '../api/client.js';
import { renderSeriesChart } from '../viz/seriesChart.js';
import { formatNumber, el } from '../core/format.js';

export function initCatalogView() {
  const statsEl = document.querySelector('#db-stats');
  const form = document.querySelector('#catalog-form');
  const input = document.querySelector('#catalog-query');
  const listEl = document.querySelector('#catalog-results');
  const statusEl = document.querySelector('#catalog-status');

  let statsLoaded = false;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const q = input.value.trim();
    if (!q) return;
    statusEl.textContent = 'Qidirilmoqda…';
    listEl.replaceChildren();
    try {
      const res = await searchIndicators(q);
      statusEl.textContent = `${res.count} ta ko‘rsatkich topildi`;
      for (const r of res.results) {
        const li = el('li');
        const a = el('a', `#${r.indicator_id} ${r.name_uz ?? ''}`);
        a.href = `#/indicator/${r.indicator_id}`;
        li.append(a, el('small', `${r.unit ?? ''} · ${r.periodicity ?? ''}`));
        listEl.append(li);
      }
    } catch {
      statusEl.textContent = 'Mavjud emas — backend javob bermadi.';
    }
  });

  return {
    // Sahifa ochilganda bir marta statistikani yuklaymiz
    async show() {
      if (statsLoaded) return;
      try {
        const s = await getStats();
        statsEl.replaceChildren(
          stat('Ko‘rsatkichlar', s.total_indicators),
          stat('Klassifikator qatorlari', s.total_items),
          stat('Raqamlar (fakt)', s.total_facts),
          stat('Yaroqli qiymatlar', s.valid_facts),
        );
        statsLoaded = true;
      } catch {
        statsEl.replaceChildren(el('p', 'Statistika: mavjud emas — backend javob bermadi.', 'muted'));
      }
    },
  };
}

function stat(label, value) {
  const div = el('div', null, 'stat');
  div.append(el('strong', formatNumber(value)), el('span', label));
  return div;
}

// Ko'rsatkich sahifasi (#/indicator/1308)
export async function showIndicator(id) {
  const box = document.querySelector('#indicator');
  box.replaceChildren(el('p', 'Yuklanmoqda…', 'muted'));

  let meta;
  try {
    meta = await getIndicator(id);
  } catch {
    box.replaceChildren(el('p', `Ko‘rsatkich #${id}: mavjud emas — backend javob bermadi.`, 'muted'));
    return;
  }

  const back = el('a', '← Katalogga qaytish');
  back.href = '#/catalog';

  const dl = el('dl', null, 'meta');
  const fields = [
    ['Kod', meta.code],
    ['O‘lchov birligi', meta.unit_uz],
    ['Davriyligi', meta.periodicity],
    ['Mas’ul tashkilot', meta.organization],
    ['Oxirgi o‘zgarish', meta.last_modified_date],
    ['Jamlanma (yil boshidan)', meta.is_cumulative ? 'ha' : 'yo‘q'],
    ['Qatorlar soni', meta.total_items_count],
  ];
  for (const [k, v] of fields) {
    if (v === null || v === undefined || v === '') continue;
    dl.append(el('dt', k), el('dd', v));
  }

  // Qator (mahsulot/hudud) tanlash — backend 5 ta namunani beradi
  const select = el('select');
  select.id = 'item-select';
  for (const it of meta.sample_items ?? []) {
    const opt = el('option', `${it.item_code} — ${it.name_uz}`);
    opt.value = it.item_code;
    select.append(opt);
  }
  const label = el('label', 'Qator: ');
  label.htmlFor = 'item-select';

  const chartEl = el('div', null, 'chart-box');

  box.replaceChildren(
    back,
    el('h2', meta.name_uz ?? `Ko‘rsatkich #${id}`),
    dl,
    label, select,
    chartEl,
  );

  async function loadSeries() {
    chartEl.replaceChildren(el('p', 'Grafik yuklanmoqda…', 'muted'));
    try {
      const s = await getSeries(id, select.value || undefined);
      renderSeriesChart(chartEl, s.data, { unit: meta.unit_uz ?? '', sourceUrl: meta.source_url ?? '' });
    } catch {
      chartEl.replaceChildren(el('p', 'Grafik: mavjud emas — backend javob bermadi.', 'muted'));
    }
  }
  select.addEventListener('change', loadSeries);
  loadSeries();
}
