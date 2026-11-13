// Backend bilan aloqa. Hamma so'rov /api orqali ketadi (vite.config.js uni
// FastAPI'ga yo'naltiradi), chunki siat.stat.uz da CORS yo'q — brauzer
// u yerdan to'g'ridan-to'g'ri ma'lumot ololmaydi.

async function getJSON(url) {
  const res = await fetch(url, { signal: AbortSignal.timeout(15000) });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

// GET /health -> { status: 'ok' | 'degraded', database_connected }
export async function checkHealth() {
  try {
    const data = await getJSON('/health');
    return { backend: true, database: data.database_connected === true };
  } catch {
    return { backend: false, database: false };
  }
}

// GET /api/stats -> { total_indicators, total_items, total_facts, ... }
export const getStats = () => getJSON('/api/stats');

// GET /api/indicators/search -> { query, count, results: [{ indicator_id, name_uz, unit, periodicity, rrf_score }] }
export const searchIndicators = (q, limit = 20) =>
  getJSON(`/api/indicators/search?${new URLSearchParams({ q, limit })}`);

// GET /api/indicators/{id} -> metadata + sample_items
export const getIndicator = (id) => getJSON(`/api/indicators/${encodeURIComponent(id)}`);

// GET /api/series -> { total_returned, data: [{ item_code, item_name, period_key, value, status, ... }] }
export const getSeries = (indicatorId, itemCode) => {
  const params = new URLSearchParams({ indicator_id: indicatorId, limit: 1000 });
  if (itemCode) params.set('item_codes', itemCode);
  return getJSON(`/api/series?${params}`);
};

// POST /api/ask — javob SSE oqimi sifatida keladi.
// EventSource faqat GET qiladi, shuning uchun fetch + stream o'qiymiz.
// onEvent(nom, ma'lumot) har bir voqea uchun chaqiriladi.
export async function ask(question, onEvent) {
  const res = await fetch('/api/ask', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
    body: JSON.stringify({ question }),
  });
  if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`);

  const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = '';
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += value.replace(/\r\n/g, '\n');
    // SSE: voqealar bo'sh qator bilan ajratiladi
    let sep;
    while ((sep = buffer.indexOf('\n\n')) !== -1) {
      const block = buffer.slice(0, sep);
      buffer = buffer.slice(sep + 2);
      let name = 'message';
      let data = '';
      for (const line of block.split('\n')) {
        if (line.startsWith('event:')) name = line.slice(6).trim();
        else if (line.startsWith('data:')) data += line.slice(5).trim();
      }
      let parsed = {};
      try { parsed = JSON.parse(data); } catch { parsed = { raw: data }; }
      onEvent(name, parsed);
    }
  }
}
