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
