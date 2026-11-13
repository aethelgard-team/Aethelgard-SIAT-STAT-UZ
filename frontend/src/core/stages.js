// Roadmap 7-bo'lim, 1-kun: bosqichlar jadvali.
// Har bir bosqich: tomoshabin savoli va unga javob beradigan SSE voqeasi.
// Voqealar va ularning maydonlari: docs/sse-contract.md (Siddiq tasdiqlagan).

export const STAGES = [
  { id: 'parse',    title: 'Savolni tahlil',           question: 'AI nimani tushundi?' },
  { id: 'search',   title: 'Katalogdan qidirish',      question: 'Qaysi ko‘rsatkichlar topildi?' },
  { id: 'tool',     title: 'MCP tool chaqiruvi',       question: 'AI qaysi asbobni, qanday parametr bilan chaqirdi?' },
  { id: 'dwh',      title: 'DWH’dan o‘qish', question: 'Raqam qayerdan keldi?' },
  { id: 'result',   title: 'Natija',                   question: 'Raqamlar qanday?' },
  { id: 'generate', title: 'Javob yozish',             question: 'Model nima yozyapti?' },
  { id: 'verify',   title: 'Tekshirish',               question: 'Har bir jumlaga ishonsa bo‘ladimi?' },
];

// Backenddagi 6 ta MCP tool (mcp_server/server.py dagi @mcp.tool() lar).
// Hammasi faqat o'qiydi.
export const TOOLS = [
  'search_indicators',
  'get_indicator_metadata',
  'get_data',
  'compare_regions',
  'time_series',
  'get_available_periods',
];
