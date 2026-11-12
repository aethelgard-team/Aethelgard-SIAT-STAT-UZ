// 3D ustunli grafik: tool.result dagi haqiqiy qatorlar.
// Ustun balandligi = qiymat / eng katta qiymat (0 dan boshlanadi — nisbat to'g'ri).
// value = null (zero_marked) bo'lsa ustun chizilmaydi, faqat yerda kulrang belgi.
import * as THREE from 'three';

const MAX_H = 4.5;
const W = 0.3;
const STEP = 0.42;
const MAX_BARS = 24;

export function createBars() {
  const group = new THREE.Group();
  let items = [];

  function clear() {
    for (const child of [...group.children]) {
      group.remove(child);
      child.geometry?.dispose();
      child.material?.dispose();
    }
    items = [];
  }

  // Qaytaradi: [{ row, top: Vector3 (group ichida), mesh }]
  function build(rows) {
    clear();
    if (!rows?.length) return items;

    // Birinchi qator (mahsulot/hudud) bo'yicha, oxirgi 24 ta davr
    const firstItem = rows[0].item_code;
    const series = rows
      .filter((r) => r.item_code === firstItem)
      .sort((a, b) => String(a.period_key).localeCompare(String(b.period_key)))
      .slice(-MAX_BARS);

    const values = series.map((r) => r.value).filter((v) => typeof v === 'number' && v > 0);
    const max = values.length ? Math.max(...values) : 1;
    const offset = ((series.length - 1) * STEP) / 2;

    series.forEach((row, i) => {
      const x = i * STEP - offset;
      const has = typeof row.value === 'number' && row.value > 0;
      const h = has ? Math.max((row.value / max) * MAX_H, 0.02) : 0.02;
      const mesh = new THREE.Mesh(
        new THREE.BoxGeometry(W, h, W),
        new THREE.MeshStandardMaterial({ color: has ? 0x6c8cff : 0x3a3f55 }),
      );
      mesh.position.set(x, h / 2, 0);
      group.add(mesh);
      items.push({ row, mesh, top: new THREE.Vector3(x, h + 0.05, 0) });
    });

    // Asos chizig'i
    const base = new THREE.Mesh(
      new THREE.BoxGeometry(series.length * STEP + 0.2, 0.02, 0.6),
      new THREE.MeshStandardMaterial({ color: 0x23273a }),
    );
    base.position.y = -0.01;
    group.add(base);
    return items;
  }

  function select(item) {
    for (const it of items) {
      const has = typeof it.row.value === 'number' && it.row.value > 0;
      it.mesh.material.color.set(it === item ? 0xffb347 : has ? 0x6c8cff : 0x3a3f55);
    }
  }

  return { group, build, clear, select };
}
