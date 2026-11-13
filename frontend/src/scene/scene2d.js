// 2D zaxira sahna: WebGL yo'q bo'lsa yoki ?mode=2d bo'lsa.
// 3D sahna bilan bir xil API — askView qaysi biri ishlayotganini bilmaydi.
// Natija grafigi natija kartasidagi 2D SVG grafikda.
import { formatNumber, el } from '../core/format.js';

export function createScene2D(container, { reason = '' } = {}) {
  container.replaceChildren();
  container.hidden = false;
  container.classList.add('scene-2d');

  if (reason) container.append(el('p', reason, 'muted'));

  // 6 ta tool o'ng paneldagi ro'yxatda (u WebGL'siz ham ishlaydi)
  container.append(el('h3', 'Sahna (2D)'));

  const warehouseEl = el('p', 'Ombor (DWH): yuklanmoqda…', 'warehouse-2d');
  container.append(warehouseEl);
  const resultEl = el('p', 'Natija: hali yo‘q', 'muted');
  container.append(resultEl);

  let base = warehouseEl.textContent;

  return {
    setToolClickHandler() {}, // toollar o'ng panelda bosiladi
    highlightTool(name) {
      resultEl.dataset.tool = name;
    },
    setStats(stats) {
      base = stats
        ? `Ombor (DWH): ${formatNumber(stats.total_indicators)} ko‘rsatkich`
        : 'Ombor (DWH): mavjud emas';
      warehouseEl.textContent = base;
    },
    selectIndicator(id) {
      warehouseEl.textContent = `${base} → #${id}`;
    },
    showBars(rows) {
      resultEl.textContent = rows?.length
        ? `Natija: ${rows.length} qator — natija kartasida`
        : 'Natija: mavjud emas';
    },
    reset() {
      warehouseEl.textContent = base;
      resultEl.textContent = 'Natija: hali yo‘q';
    },
  };
}
