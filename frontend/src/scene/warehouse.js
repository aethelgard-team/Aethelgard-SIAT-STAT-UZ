// "Ombor" (DWH) — server xonasi: ikki qator server shkafi, old panelida miltillovchi chiroqlar.
// Qoida: shkaflar soni/ko'rinishi raqam deb o'qilmasin, agar u haqiqiy bo'lmasa.
//  - Backend `categories: [{section, count, indicator_ids}]` bersa: har bir shkaf = bitta
//    bo'lim (ko'pi bilan 12 ta); topilgan ko'rsatkich shkafi sariq yonadi.
//  - Bermasa: shkaflar faqat bezak; haqiqiy son faqat yorliqda (total_indicators).
import * as THREE from 'three';
import { gsap } from 'gsap';

const RACK_W = 0.5, RACK_H = 1.55, RACK_D = 0.55, GAP = 0.66;
const LED_COLORS = [0x10b981, 0x38bdf8, 0x10b981, 0xf59e0b];
const LEDS_PER_RACK = 18;

// Old panel teksturasi: server bloklari, shamollatish teshiklari, disk joylari
const FRONT = (() => {
  const c = document.createElement('canvas');
  c.width = 128;
  c.height = 400;
  const g = c.getContext('2d');
  g.fillStyle = '#0b1220';
  g.fillRect(0, 0, 128, 400);
  for (let u = 0; u < 12; u++) {
    const y = 10 + u * 32;
    g.fillStyle = u % 3 === 0 ? '#16233a' : '#121c2e';
    g.fillRect(8, y, 112, 28);
    g.strokeStyle = '#25385a';
    g.strokeRect(8.5, y + 0.5, 111, 27);
    // shamollatish chiziqlari
    g.fillStyle = '#0a111d';
    for (let k = 0; k < 7; k++) g.fillRect(44 + k * 10, y + 7, 5, 14);
    // disk joylari
    g.fillStyle = '#1d2c46';
    g.fillRect(14, y + 6, 22, 16);
  }
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
})();

export function createWarehouse() {
  const group = new THREE.Group();
  let racks = [];   // { body, strip, ids:Set|null, center }
  let leds = null;  // InstancedMesh
  let ledInfo = []; // { base: Color, rate, phase, rack }
  let lastHit = null;
  let blocks = [];
  let flash = 0;    // o'qish to'lqini kuchi (0..1)

  function clear() {
    for (const child of [...group.children]) {
      group.remove(child);
      child.traverse((o) => { o.geometry?.dispose(); if (o.material && o.material.map !== FRONT) o.material.dispose?.(); });
    }
    racks = [];
    leds = null;
    ledInfo = [];
    lastHit = null;
    blocks = [];
  }

  function addRack(x, z, extra = {}) {
    const body = new THREE.Mesh(
      new THREE.BoxGeometry(RACK_W, RACK_H, RACK_D),
      [
        new THREE.MeshStandardMaterial({ color: 0x1a2232, metalness: 0.75, roughness: 0.35 }),
        new THREE.MeshStandardMaterial({ color: 0x1a2232, metalness: 0.75, roughness: 0.35 }),
        new THREE.MeshStandardMaterial({ color: 0x222c3e, metalness: 0.7, roughness: 0.4 }),
        new THREE.MeshStandardMaterial({ color: 0x10161f, metalness: 0.6, roughness: 0.5 }),
        new THREE.MeshStandardMaterial({ map: FRONT, metalness: 0.4, roughness: 0.45, emissive: 0x0a1a2e, emissiveIntensity: 0.4 }),
        new THREE.MeshStandardMaterial({ color: 0x141b27, metalness: 0.7, roughness: 0.4 }),
      ],
    );
    body.position.set(x, RACK_H / 2, z);
    group.add(body);
    // Tepadagi nurli chiziq (shkaf "ishlayapti")
    const strip = new THREE.Mesh(
      new THREE.BoxGeometry(RACK_W * 0.92, 0.025, 0.03),
      new THREE.MeshBasicMaterial({ color: 0x38bdf8 }),
    );
    strip.position.set(x, RACK_H - 0.04, z + RACK_D / 2 + 0.005);
    group.add(strip);
    const r = { body, strip, x, z, center: new THREE.Vector3(x, RACK_H + 0.3, z), ...extra };
    racks.push(r);
    return r;
  }

  function build(stats) {
    clear();
    if (!stats) return blocks;
    const cats = Array.isArray(stats.categories) && stats.categories.length ? stats.categories.slice(0, 12) : null;
    const n = cats ? cats.length : 12;
    const perRow = Math.ceil(n / 2);
    for (let i = 0; i < n; i++) {
      const row = i < perRow ? 0 : 1;
      const col = row === 0 ? i : i - perRow;
      const count = row === 0 ? perRow : n - perRow;
      const x = (col - (count - 1) / 2) * GAP;
      const z = row === 0 ? -0.55 : 0.6;
      const c = cats?.[i];
      const r = addRack(x, z, c ? { ids: new Set((c.indicator_ids ?? []).map(Number)), section: c.section } : {});
      if (c) blocks.push({ section: c.section, count: c.count, center: r.center });
    }

    // Kabel tarnovi: shkaflar ustidan o'tadi
    for (const z of [-0.55, 0.6]) {
      const tray = new THREE.Mesh(
        new THREE.BoxGeometry(perRow * GAP + 0.2, 0.05, 0.16),
        new THREE.MeshStandardMaterial({ color: 0x2a3446, metalness: 0.8, roughness: 0.3 }),
      );
      tray.position.set(0, RACK_H + 0.12, z);
      group.add(tray);
    }

    // Chiroqlar: har shkafda ustun bo'ylab, har xil tezlikda miltillaydi
    leds = new THREE.InstancedMesh(
      new THREE.BoxGeometry(0.03, 0.018, 0.01),
      new THREE.MeshBasicMaterial({ color: 0xffffff }),
      racks.length * LEDS_PER_RACK,
    );
    const m = new THREE.Matrix4();
    let k = 0;
    racks.forEach((r, ri) => {
      for (let j = 0; j < LEDS_PER_RACK; j++) {
        const unit = Math.floor(j / 1.5);
        const y = RACK_H - 0.09 - unit * (RACK_H - 0.15) / 12 - 0.03;
        const x = r.x + RACK_W / 2 - 0.06 - (j % 2) * 0.05;
        m.makeTranslation(x, y, r.z + RACK_D / 2 + 0.008);
        leds.setMatrixAt(k, m);
        ledInfo.push({ base: new THREE.Color(LED_COLORS[(ri + j) % LED_COLORS.length]), rate: 1.5 + ((ri * 7 + j * 13) % 9), phase: j * 1.7 + ri, rack: r });
        leds.setColorAt(k, ledInfo[k].base);
        k++;
      }
    });
    leds.instanceMatrix.needsUpdate = true;
    group.add(leds);
    return blocks;
  }

  // Topilgan ko'rsatkich shkafi (faqat backend bo'lim ro'yxatini bersa). Aks holda false.
  function highlight(indicatorId) {
    resetHighlight();
    const r = racks.find((x) => x.ids?.has(Number(indicatorId)));
    if (!r) return false;
    r.strip.material.color.set(0xf59e0b);
    r.body.material[4].emissive.set(0x5a3a05);
    lastHit = r;
    return true;
  }

  function resetHighlight() {
    if (!lastHit) return;
    lastHit.strip.material.color.set(0x38bdf8);
    lastHit.body.material[4].emissive.set(0x0a1a2e);
    lastHit = null;
  }

  // Ombordan o'qilganda: barcha chiroqlar bir zumda yorishadi va tez miltillaydi
  function wave() {
    const w = { v: 1 };
    flash = 1;
    gsap.to(w, { v: 0, duration: 1.6, ease: 'power2.out', onUpdate: () => { flash = w.v; } });
  }

  const tmpC = new THREE.Color();
  const WHITE = new THREE.Color(0xffffff);
  function twinkle(t) {
    if (!leds) return;
    for (let i = 0; i < ledInfo.length; i++) {
      const L = ledInfo[i];
      const rate = L.rate * (1 + flash * 4);
      const on = Math.sin(t * rate + L.phase) > (flash > 0.05 ? -0.6 : 0.1);
      tmpC.copy(L.base).multiplyScalar(on ? 1 : 0.18);
      if (flash > 0.05) tmpC.lerp(WHITE, flash * 0.5);
      if (L.rack === lastHit) tmpC.set(0xf59e0b);
      leds.setColorAt(i, tmpC);
    }
    leds.instanceColor.needsUpdate = true;
  }

  return { group, build, highlight, resetHighlight, wave, twinkle };
}
