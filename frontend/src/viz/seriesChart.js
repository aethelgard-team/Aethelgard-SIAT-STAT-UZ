// 2D SVG grafik. WebGL kerak emas — har qanday brauzerda ishlaydi.
// rows: backenddan kelgan qatorlar [{ period_key, value, item_name, status }]
// Qoida: faqat haqiqiy qiymat chiziladi; value = null bo'lsa nuqta qo'yilmaydi.
import { formatNumber, el } from '../core/format.js';

const SVG = 'http://www.w3.org/2000/svg';
const W = 640, H = 260, PAD = { l: 70, r: 16, t: 16, b: 40 };

function svgEl(tag, attrs = {}) {
  const node = document.createElementNS(SVG, tag);
  for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  return node;
}

export function renderSeriesChart(container, rows, { unit = '', sourceUrl = '' } = {}) {
  container.replaceChildren();

  if (!rows || rows.length === 0) {
    container.append(el('p', 'Mavjud emas — backend qator qaytarmadi.', 'muted'));
    return;
  }

  // Bir nechta qator (mahsulot/hudud) bo'lsa — birinchisini chizamiz
  const firstItem = rows[0].item_code;
  const series = rows
    .filter((r) => r.item_code === firstItem)
    .sort((a, b) => String(a.period_key).localeCompare(String(b.period_key)));
  const itemName = series[0].item_name ?? firstItem;

  const caption = el('p', `${itemName}${unit ? ` · ${unit}` : ''}`, 'chart-caption');
  container.append(caption);

  // Bitta qiymat bo'lsa grafik emas, katta raqam ko'rsatamiz
  if (series.length === 1) {
    const r = series[0];
    const card = el('div', null, 'value-card');
    card.append(el('strong', formatNumber(r.value)), el('span', `${r.period_key} · status: ${r.status}`));
    container.append(card);
    appendSource(container, sourceUrl);
    return;
  }

  const values = series.map((r) => r.value).filter((v) => v !== null && v !== undefined);
  if (values.length === 0) {
    container.append(el('p', 'Bu davrlarda qiymat yo‘q (zero_marked).', 'muted'));
    return;
  }
  // O'q haqiqiy qiymatlar oralig'iga moslanadi (narx o'zgarishi ko'rinsin)
  const lo = Math.min(...values);
  const hi = Math.max(...values);
  const pad = (hi - lo) * 0.1 || Math.abs(hi) * 0.1 || 1;
  const min = lo - pad;
  const max = hi + pad;
  const span = max - min;

  const x = (i) => PAD.l + (i / (series.length - 1)) * (W - PAD.l - PAD.r);
  const y = (v) => PAD.t + (1 - (v - min) / span) * (H - PAD.t - PAD.b);

  const svg = svgEl('svg', { viewBox: `0 0 ${W} ${H}`, class: 'chart', role: 'img' });
  const title = svgEl('title');
  title.textContent = `${itemName}: ${series.length} ta davr`;
  svg.append(title);

  // O'qlar va yorliqlar
  svg.append(svgEl('line', { x1: PAD.l, y1: H - PAD.b, x2: W - PAD.r, y2: H - PAD.b, class: 'axis' }));
  for (const v of [lo, hi]) {
    const t = svgEl('text', { x: PAD.l - 8, y: y(v) + 4, 'text-anchor': 'end', class: 'tick' });
    t.textContent = formatNumber(v);
    svg.append(t);
  }
  for (const i of [0, series.length - 1]) {
    const t = svgEl('text', { x: x(i), y: H - PAD.b + 18, 'text-anchor': i === 0 ? 'start' : 'end', class: 'tick' });
    t.textContent = series[i].period_key;
    svg.append(t);
  }

  // Chiziq: null qiymatlarda uziladi (yo'q narsani chizmaymiz)
  let d = '';
  let pen = false;
  series.forEach((r, i) => {
    if (r.value === null || r.value === undefined) { pen = false; return; }
    d += `${pen ? 'L' : 'M'}${x(i).toFixed(1)},${y(r.value).toFixed(1)} `;
    pen = true;
  });
  svg.append(svgEl('path', { d, class: 'line' }));

  // Nuqtalar — sichqoncha bilan ustiga borilsa aniq qiymat va davr
  series.forEach((r, i) => {
    if (r.value === null || r.value === undefined) return;
    const dot = svgEl('circle', { cx: x(i), cy: y(r.value), r: 3.5, class: 'dot' });
    const tip = svgEl('title');
    tip.textContent = `${r.period_key}: ${formatNumber(r.value)}${unit ? ` ${unit}` : ''}`;
    dot.append(tip);
    svg.append(dot);
  });

  container.append(svg);
  appendSource(container, sourceUrl);
}

function appendSource(container, url) {
  if (!url) return;
  const p = el('p', 'Manba: ', 'chart-source');
  const a = el('a', 'siat.stat.uz');
  a.href = url;
  a.target = '_blank';
  a.rel = 'noopener';
  p.append(a, el('span', ' (CC BY 4.0)'));
  container.append(p);
}
