// Demo rejim (?demo=1): oldindan yozib olingan HAQIQIY javobni qayta ijro etadi.
// Qoidalar (roadmap 7-bo'lim):
//  - yozuv faqat haqiqiy backenddan olinadi (askView "Demo uchun saqlash" tugmasi);
//  - demo doim banner ostida ko'rsatiladi, jonli rejim bilan aralashmaydi;
//  - demo rejimida backendga savol yuborilmaydi.
// Yozuv fayli: frontend/public/demo/demo.json
//   { question, recorded_at, events: [{ name, data, t }] }   (t — ms)

export function isDemoMode() {
  return new URLSearchParams(location.search).get('demo') === '1';
}

export async function loadDemo() {
  try {
    const res = await fetch('/demo/demo.json', { cache: 'no-store' });
    if (!res.ok) return null;
    const rec = await res.json();
    return Array.isArray(rec?.events) && rec.events.length ? rec : null;
  } catch {
    return null;
  }
}

// Voqealarni yozilgan vaqt oralig'i bilan yuboradi (uzun pauzalar 1,5 s gacha qisqartiriladi)
export async function replay(rec, onEvent) {
  let prev = 0;
  for (const ev of rec.events) {
    const gap = Math.min(Math.max((ev.t ?? prev) - prev, 0), 1500);
    prev = ev.t ?? prev;
    if (gap) await new Promise((r) => setTimeout(r, gap));
    onEvent(ev.name, ev.data);
  }
}

// Haqiqiy javobni fayl qilib yuklab beradi — uni public/demo/demo.json ga qo'yasiz
export function downloadRecording(rec) {
  const blob = new Blob([JSON.stringify(rec, null, 2)], { type: 'application/json' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'demo.json';
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}
