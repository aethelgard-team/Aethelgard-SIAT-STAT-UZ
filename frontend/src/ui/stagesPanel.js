// 2D bosqichlar ro'yxati. WebGL ishlamasa ham shu ko'rinish qoladi.
// Qoida: matn faqat textContent bilan qo'yiladi, innerHTML bilan emas.
import { STAGES } from '../core/stages.js';
import { el } from '../core/format.js';

// onInspect(stageId, tugma) — "Batafsil" bosilganda (inspektor ochiladi)
export function renderStages(listEl, onInspect) {
  listEl.replaceChildren();
  for (const stage of STAGES) {
    const li = document.createElement('li');
    li.dataset.stage = stage.id;
    li.dataset.state = 'idle';
    li.append(
      el('strong', stage.title),
      el('span', stage.question),
      el('small', '', 'detail'),
    );
    if (onInspect) {
      const btn = el('button', 'Batafsil', 'inspect-btn');
      btn.type = 'button';
      btn.setAttribute('aria-label', `${stage.title}: batafsil ma’lumot`);
      btn.addEventListener('click', () => onInspect(stage.id, btn));
      li.append(btn);
    }
    listEl.append(li);
  }
}

// state: 'idle' | 'active' | 'done' | 'error'
export function setStageState(listEl, stageId, state) {
  const li = listEl.querySelector(`[data-stage="${stageId}"]`);
  if (li) li.dataset.state = state;
}

// Bosqich ostiga haqiqiy ma'lumot (vaqt, qatorlar soni, parametrlar)
export function setStageDetail(listEl, stageId, text) {
  const detail = listEl.querySelector(`[data-stage="${stageId}"] .detail`);
  if (detail) detail.textContent = text;
}

// Oqim tugaganda hali "active" turgan bosqichlarni xato deb belgilaymiz
export function failActiveStages(listEl) {
  for (const li of listEl.querySelectorAll('[data-state="active"]')) li.dataset.state = 'error';
}
