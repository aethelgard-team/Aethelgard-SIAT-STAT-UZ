// Raqamlarni bir xil ko'rinishda chiqarish: 127857.3 -> "127 857,3"
// (roadmap: sayt va tekshiruvchi bir xil formatni ishlatadi).
const nf = new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 3 });

export function formatNumber(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return 'Mavjud emas';
  return nf.format(value);
}

// Kichik yordamchi: element yaratib, matnni textContent bilan qo'yadi.
// innerHTML ishlatilmaydi — backenddan kelgan matn HTML sifatida o'qilmaydi.
export function el(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined && text !== null) node.textContent = String(text);
  if (className) node.className = className;
  return node;
}

// Qatordagi davr (backend `period_key` beradi; bo'lmasa — bo'sh, "undefined" emas)
export function periodOf(row) {
  const v = row?.period_key ?? row?.period ?? '';
  return v === null || v === undefined ? '' : String(v);
}

// Faqat to'ldirilgan qismlarni " · " bilan qo'shadi: undefined, null, '' tashlab yuboriladi
export function joinParts(...parts) {
  return parts.filter((x) => x !== undefined && x !== null && String(x).trim() !== '' && String(x) !== 'undefined').join(' · ');
}

const MONTH_NAMES_UZ = {
  1: 'yanvar', 2: 'fevral', 3: 'mart', 4: 'aprel',
  5: 'may', 6: 'iyun', 7: 'iyul', 8: 'avgust',
  9: 'sentyabr', 10: 'oktyabr', 11: 'noyabr', 12: 'dekabr'
};
const MONTH_NAMES_CYRL = {
  1: 'январь', 2: 'февраль', 3: 'март', 4: 'апрель',
  5: 'май', 6: 'июнь', 7: 'июль', 8: 'август',
  9: 'сентябрь', 10: 'октябрь', 11: 'ноябрь', 12: 'декабрь'
};
const MONTH_NAMES_RU = {
  1: 'январь', 2: 'февраль', 3: 'март', 4: 'апрель',
  5: 'май', 6: 'июнь', 7: 'июль', 8: 'август',
  9: 'сентябрь', 10: 'октябрь', 11: 'ноябрь', 12: 'декабрь'
};

const MONTH_COMPACT = {
  1: 'yan', 2: 'fev', 3: 'mar', 4: 'apr',
  5: 'may', 6: 'iyn', 7: 'iyl', 8: 'avg',
  9: 'sen', 10: 'okt', 11: 'noy', 12: 'dek'
};

export function formatPeriodLabel(code, lang = 'uz_latn') {
  if (!code) return '';
  const str = String(code).trim();

  // 1. Oylik: YYYY-M01 .. YYYY-M12
  const mMatch = str.match(/^(\d{4})-M0?([1-9]|1[0-2])$/i);
  if (mMatch) {
    const year = mMatch[1];
    const mNum = parseInt(mMatch[2], 10);
    if (lang === 'ru') return `${MONTH_NAMES_RU[mNum]} ${year} года`;
    if (lang === 'uz_cyrl') return `${year} йил ${MONTH_NAMES_CYRL[mNum]} ойи`;
    return `${year}-yil ${MONTH_NAMES_UZ[mNum]} oyi`;
  }

  // 2. Choraklik: YYYY-Q01 .. YYYY-Q04
  const qMatch = str.match(/^(\d{4})-Q0?([1-4])$/i);
  if (qMatch) {
    const year = qMatch[1];
    const qNum = parseInt(qMatch[2], 10);
    if (lang === 'ru') return `${qNum}-й квартал ${year} года`;
    if (lang === 'uz_cyrl') return `${year} йил ${qNum}-чорак`;
    return `${year}-yil ${qNum}-chorak`;
  }

  // 3. Yillik: YYYY-Y00 yoki 4 ta raqam
  const yMatch = str.match(/^(\d{4})(?:-Y00)?$/i);
  if (yMatch) {
    const year = yMatch[1];
    if (lang === 'ru') return `${year} год`;
    if (lang === 'uz_cyrl') return `${year} йил`;
    return `${year}-yil`;
  }

  return str;
}

export function formatCompactPeriod(code, lang = 'uz_latn') {
  if (!code) return '';
  const str = String(code).trim();
  const mMatch = str.match(/^(\d{4})-M0?([1-9]|1[0-2])$/i);
  if (mMatch) {
    const year = mMatch[1];
    const mNum = parseInt(mMatch[2], 10);
    return `${year} ${MONTH_COMPACT[mNum] || ''}`.trim();
  }
  const qMatch = str.match(/^(\d{4})-Q0?([1-4])$/i);
  if (qMatch) {
    return `${qMatch[1]} Q${qMatch[2]}`;
  }
  const yMatch = str.match(/^(\d{4})(?:-Y00)?$/i);
  if (yMatch) {
    return yMatch[1];
  }
  return formatPeriodLabel(str, lang);
}
