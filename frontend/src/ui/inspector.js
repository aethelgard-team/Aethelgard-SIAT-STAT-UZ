// Inspektor: bosqich yoki tool bosilganda o'sha joyning HAQIQIY ma'lumoti.
// Faqat backend yuborgan voqealardagi maydonlar ko'rsatiladi — hech narsa qo'shilmaydi.
// <dialog>: Esc yopadi, yopilgandan keyin fokus bosilgan tugmaga qaytadi.
import { el } from '../core/format.js';

export function createInspector(dialog) {
  const titleEl = el('h3');
  const bodyEl = el('div', '', 'inspector-body');
  const close = el('button', 'Yopish (Esc)', 'inspector-close');
  close.type = 'button';
  dialog.append(titleEl, bodyEl, close);

  let opener = null;
  close.addEventListener('click', () => dialog.close());
  dialog.addEventListener('close', () => {
    // Brauzer o'zi ham fokusni qaytaradi — undan keyin aniq tugmaga qo'yamiz
    const back = opener;
    opener = null;
    setTimeout(() => back?.focus(), 0);
  });
  // Dialog tashqarisiga bosilsa ham yopiladi
  dialog.addEventListener('click', (e) => { if (e.target === dialog) dialog.close(); });

  // events: [{ name, data, t }] — t = savol yuborilgandan beri ms
  function open(title, events, from, emptyText = 'Bu bosqich uchun hali ma’lumot kelmagan.') {
    opener = from ?? document.activeElement;
    titleEl.textContent = title;
    bodyEl.replaceChildren();
    if (!events.length) {
      bodyEl.append(el('p', emptyText, 'muted'));
    }
    for (const ev of events) {
      const box = el('section', '', 'inspector-event');
      box.append(el('h4', `${ev.name}${ev.t !== undefined ? ` · +${ev.t} ms` : ''}`));
      const dl = el('dl');
      for (const [k, v] of Object.entries(ev.data ?? {})) {
        dl.append(el('dt', k), el('dd', describe(v)));
      }
      box.append(dl);
      bodyEl.append(box);
    }
    if (dialog.open) dialog.close();
    dialog.showModal();
    close.focus();
  }

  return { open };
}

// Katta ro'yxatlar to'liq chiqmaydi — soni va birinchi elementi ko'rsatiladi
function describe(v) {
  if (v === null || v === undefined) return 'Mavjud emas';
  if (Array.isArray(v)) {
    if (!v.length) return '0 ta';
    return `${v.length} ta · 1-si: ${short(v[0])}`;
  }
  return short(v);
}

function short(v) {
  const s = typeof v === 'object' ? JSON.stringify(v) : String(v);
  return s.length > 240 ? `${s.slice(0, 240)}…` : s;
}
