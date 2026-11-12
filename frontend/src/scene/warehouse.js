// "Ombor" (DWH): har bir quti = bazadagi bitta haqiqiy ko'rsatkich.
// Qutilar soni /api/stats dagi total_indicators dan olinadi.
// Agar backend `categories: [{section, count, indicator_ids}]` bersa — javonlarga
// bo'linadi va topilgan ko'rsatkichning qutisi yonadi. Bermasa — bitta blok,
// kategoriya o'ylab topilmaydi.
import * as THREE from 'three';

const BOX = 0.1;
const STEP = 0.14;
const BASE = new THREE.Color(0x3a3f55);
const HIT = new THREE.Color(0xffb347);

export function createWarehouse() {
  const group = new THREE.Group();
  let mesh = null;
  let idToIndex = new Map();
  let lastHit = -1;
  let blocks = []; // [{ section, count, center: Vector3 }] — yorliqlar uchun

  function clear() {
    if (mesh) {
      group.remove(mesh);
      mesh.geometry.dispose();
      mesh.material.dispose();
      mesh = null;
    }
    for (const child of [...group.children]) {
      group.remove(child);
      child.geometry?.dispose();
      child.material?.dispose();
    }
    idToIndex = new Map();
    lastHit = -1;
    blocks = [];
  }

  function build(stats) {
    clear();
    const categories = Array.isArray(stats?.categories) && stats.categories.length
      ? stats.categories
      : [{ section: null, count: Number(stats?.total_indicators) || 0 }];
    const total = categories.reduce((s, c) => s + (Number(c.count) || 0), 0);
    if (!total) return blocks;

    mesh = new THREE.InstancedMesh(
      new THREE.BoxGeometry(BOX, BOX, BOX),
      new THREE.MeshStandardMaterial({ color: 0xffffff }),
      total,
    );

    // Bitta blok bo'lsa — 20 x 8 qavatlar, ko'p bo'lsa — kichik javonlar (8 x 4)
    const single = categories.length === 1;
    const cols = single ? 20 : 8;
    const depth = single ? 8 : 4;
    const perLevel = cols * depth;
    const shelvesPerRow = 3;
    const m = new THREE.Matrix4();
    let index = 0;

    categories.forEach((cat, ci) => {
      const count = Number(cat.count) || 0;
      const ox = single ? 0 : ((ci % shelvesPerRow) - (shelvesPerRow - 1) / 2) * (cols * STEP + 0.6);
      const oz = single ? 0 : Math.floor(ci / shelvesPerRow) * (depth * STEP + 0.8);
      const levels = Math.ceil(count / perLevel);

      // Javon taxtasi
      const shelf = new THREE.Mesh(
        new THREE.BoxGeometry(cols * STEP + 0.1, 0.04, depth * STEP + 0.1),
        new THREE.MeshStandardMaterial({ color: 0x23273a }),
      );
      shelf.position.set(ox, -0.04, oz);
      group.add(shelf);

      for (let k = 0; k < count; k++) {
        const level = Math.floor(k / perLevel);
        const inLevel = k % perLevel;
        const x = ox + ((inLevel % cols) - (cols - 1) / 2) * STEP;
        const z = oz + (Math.floor(inLevel / cols) - (depth - 1) / 2) * STEP;
        const y = BOX / 2 + level * STEP;
        m.makeTranslation(x, y, z);
        mesh.setMatrixAt(index, m);
        mesh.setColorAt(index, BASE);
        const id = cat.indicator_ids?.[k];
        if (id !== undefined) idToIndex.set(Number(id), index);
        index++;
      }
      blocks.push({ section: cat.section, count, center: new THREE.Vector3(ox, levels * STEP + 0.25, oz) });
    });

    mesh.instanceMatrix.needsUpdate = true;
    mesh.instanceColor.needsUpdate = true;
    group.add(mesh);
    return blocks;
  }

  // Topilgan ko'rsatkichning qutisi. Backend ID ro'yxatini bermagan bo'lsa — false.
  function highlight(indicatorId) {
    if (!mesh) return false;
    if (lastHit >= 0) mesh.setColorAt(lastHit, BASE);
    lastHit = idToIndex.get(Number(indicatorId)) ?? -1;
    if (lastHit >= 0) mesh.setColorAt(lastHit, HIT);
    mesh.instanceColor.needsUpdate = true;
    return lastHit >= 0;
  }

  function resetHighlight() {
    if (mesh && lastHit >= 0) {
      mesh.setColorAt(lastHit, BASE);
      mesh.instanceColor.needsUpdate = true;
    }
    lastHit = -1;
  }

  return { group, build, highlight, resetHighlight };
}
