// Natija ekrani: tagligi bor 3D monitor, ekranida tool.result dagi haqiqiy qatorlar.
// Ekranda: ko'rsatkich nomi, tanlangan davr qiymati (katta raqam) va davrlar grafigi.
// Ustun balandligi qiymatlar ORASIDAGI farqni ko'rsatadi: eng arzon davr — past,
// eng qimmat — baland (grafik 0 dan boshlanmaydi — ekranda shu yozib qo'yilgan).
// value = null (zero_marked) bo'lsa — kulrang past belgi, raqam o'ylab topilmaydi.
// Qidiruv paytida ekranda raqamlar o'yindagidek aylanib turadi ("Aniqlanmoqda…" yozuvi bilan —
// bu raqamlar ma'lumot emas); natija kelganda raqamlar chapdan o'ngga bittalab to'xtaydi.
import * as THREE from 'three';
import { gsap } from 'gsap';
import { formatNumber } from '../core/format.js';

const MAX_BARS = 24;
const SCREEN_W = 4.0, SCREEN_H = 2.25; // 16:9
const CW = 1024, CH = 576;            // kanvas o'lchami
const CHART = { x0: 48, x1: 976, y0: 250, y1: 500 };
const LOW = new THREE.Color(0x0e7490);
const HIGH = new THREE.Color(0x38bdf8);
const PICK = '#f59e0b';
const SCREEN_Y = 1.85;                // ekran markazining balandligi

export function createBars() {
  const group = new THREE.Group();
  group.rotation.y = -0.28;

  // ---- Monitor korpusi: ramka, taglik, ustun ----
  const metal = new THREE.MeshStandardMaterial({ color: 0x1a2232, metalness: 0.8, roughness: 0.3 });
  const frame = new THREE.Mesh(new THREE.BoxGeometry(SCREEN_W + 0.16, SCREEN_H + 0.16, 0.12), metal);
  frame.position.set(0, SCREEN_Y, -0.07);
  const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.08, SCREEN_Y - SCREEN_H / 2, 24), metal);
  pole.position.set(0, (SCREEN_Y - SCREEN_H / 2) / 2, -0.12);
  const foot = new THREE.Mesh(new THREE.CylinderGeometry(0.55, 0.65, 0.06, 48), metal);
  foot.position.set(0, 0.03, -0.12);
  // Ekran chetidagi nurli chiziq
  const rim = new THREE.LineLoop(
    new THREE.BufferGeometry().setFromPoints([
      [-1, -1], [1, -1], [1, 1], [-1, 1],
    ].map(([x, y]) => new THREE.Vector3((x * (SCREEN_W + 0.04)) / 2, SCREEN_Y + (y * (SCREEN_H + 0.04)) / 2, 0.002))),
    new THREE.LineBasicMaterial({ color: 0x38bdf8, transparent: true, opacity: 0.6 }),
  );
  group.add(frame, pole, foot, rim);

  // ---- Ekran (kanvas tekstura) ----
  const canvas = document.createElement('canvas');
  canvas.width = CW;
  canvas.height = CH;
  const g = canvas.getContext('2d');
  const tex = new THREE.CanvasTexture(canvas);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.anisotropy = 4;
  const screen = new THREE.Mesh(new THREE.PlaneGeometry(SCREEN_W, SCREEN_H), new THREE.MeshBasicMaterial({ map: tex, toneMapped: false }));
  screen.position.set(0, SCREEN_Y, 0);
  group.add(screen);

  let items = [];
  let series = [];
  let meta = { unit: '', title: '' };
  let picked = null;
  const anim = { grow: 1, lock: 1 };
  let phase = 'idle'; // 'idle' | 'scan' (qidirilmoqda) | 'settle' (to'xtamoqda) | 'done'
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    || new URLSearchParams(location.search).get('quality') === 'low';
  const rnd = (n) => Math.floor(Math.random() * n);
  // Raqamlarni aralashtirish: lockFrac qismi (chapdan) allaqachon to'xtagan
  const scramble = (text, lockFrac) => {
    const k = Math.floor(lockFrac * text.length);
    return [...text].map((ch, i) => (i < k || !/\d/.test(ch) ? ch : String(rnd(10)))).join('');
  };

  // kanvas nuqtasi -> group ichidagi 3D nuqta
  const toLocal = (px, py) => new THREE.Vector3(
    (px / CW - 0.5) * SCREEN_W,
    SCREEN_Y + (0.5 - py / CH) * SCREEN_H,
    0.02,
  );

  function drawIdle(text) {
    const grd = g.createLinearGradient(0, 0, 0, CH);
    grd.addColorStop(0, '#071423');
    grd.addColorStop(1, '#0b2036');
    g.fillStyle = grd;
    g.fillRect(0, 0, CW, CH);
    g.fillStyle = 'rgba(56,189,248,.06)';
    for (let y = 0; y < CH; y += 4) g.fillRect(0, y, CW, 1); // ekran chiziqlari
    if (text) {
      g.fillStyle = '#5b6b85';
      g.font = '500 30px Inter, system-ui, sans-serif';
      g.textAlign = 'center';
      g.fillText(text, CW / 2, CH / 2);
      g.textAlign = 'left';
    }
    tex.needsUpdate = true;
  }

  function layout() {
    const n = series.length;
    const vals = series.map((r) => r.value).filter((v) => typeof v === 'number' && v > 0);
    const min = vals.length ? Math.min(...vals) : 0;
    const max = vals.length ? Math.max(...vals) : 1;
    const slot = (CHART.x1 - CHART.x0) / Math.max(n, 1);
    const bw = Math.min(slot * 0.62, 56);
    return series.map((row, i) => {
      const has = typeof row.value === 'number' && row.value > 0;
      const k = has ? (max > min ? (row.value - min) / (max - min) : 1) : 0;
      const h = has ? (0.12 + k * 0.88) * (CHART.y1 - CHART.y0) : 6;
      const cx = CHART.x0 + slot * (i + 0.5);
      return { row, has, k, h, cx, bw };
    });
  }

  function draw() {
    drawIdle('');
    if (!series.length) return;
    const bars = layout();
    const sel = picked ?? series.at(-1);

    // Sarlavha
    g.fillStyle = '#9fb3cc';
    g.font = '600 26px Inter, system-ui, sans-serif';
    g.fillText(meta.title || (sel.item_name ?? sel.item_code ?? ''), 48, 58);
    g.fillStyle = '#5b6b85';
    g.font = '500 20px Inter, system-ui, sans-serif';
    g.textAlign = 'right';
    g.fillText('siat.stat.uz', CW - 48, 58);
    g.textAlign = 'left';

    // Katta raqam: tanlangan davr (boshida — oxirgi davr)
    g.fillStyle = '#ffffff';
    g.font = '600 76px "JetBrains Mono", Consolas, monospace';
    const lock = phase === 'settle' ? anim.lock : 1;
    const big = scramble(typeof sel.value === 'number' ? formatNumber(sel.value) : 'Mavjud emas', lock);
    g.fillText(big, 48, 150);
    const bigW = g.measureText(big).width;
    g.fillStyle = '#8a97ad';
    g.font = '500 26px Inter, system-ui, sans-serif';
    g.fillText(meta.unit || '', 48 + bigW + 16, 150);
    g.fillStyle = PICK;
    g.font = '600 22px "JetBrains Mono", Consolas, monospace';
    g.fillText(scramble(String(sel.period_key ?? ''), lock), 48, 192);

    // Grafik
    g.strokeStyle = 'rgba(255,255,255,.08)';
    g.beginPath();
    g.moveTo(CHART.x0, CHART.y1 + 0.5);
    g.lineTo(CHART.x1, CHART.y1 + 0.5);
    g.stroke();
    bars.forEach((b, i) => {
      const h = b.h * anim.grow;
      const isSel = b.row === sel;
      if (!b.has) g.fillStyle = '#2b3a52';
      else if (isSel) g.fillStyle = PICK;
      else g.fillStyle = `#${LOW.clone().lerp(HIGH, b.k).getHexString()}`;
      g.fillRect(b.cx - b.bw / 2, CHART.y1 - h, b.bw, h);
      if (!b.has) {
        // Qiymat yo'q (zero_marked): bo'sh joy tushunarli bo'lsin — punktir va "yo'q"
        // Videoda ham ko'rinsin: qizg'ish punktir, ichida chiziqlar, tepasida katta "yo'q"
        const ph = (CHART.y1 - CHART.y0) * 0.6;
        const x = b.cx - b.bw / 2;
        g.save();
        g.fillStyle = 'rgba(248,113,113,.10)';
        g.fillRect(x, CHART.y1 - ph, b.bw, ph);
        g.beginPath();
        g.rect(x, CHART.y1 - ph, b.bw, ph);
        g.clip();
        g.strokeStyle = 'rgba(248,113,113,.35)';
        g.lineWidth = 3;
        for (let d = -ph; d < b.bw + ph; d += 14) {
          g.beginPath();
          g.moveTo(x + d, CHART.y1);
          g.lineTo(x + d + ph, CHART.y1 - ph);
          g.stroke();
        }
        g.restore();
        g.save();
        g.setLineDash([8, 6]);
        g.lineWidth = 3;
        g.strokeStyle = '#f87171';
        g.strokeRect(x + 1.5, CHART.y1 - ph, b.bw - 3, ph);
        g.restore();
        g.fillStyle = '#fca5a5';
        g.font = '700 20px Inter, system-ui, sans-serif';
        g.textAlign = 'center';
        g.fillText('yo‘q', b.cx, CHART.y1 - ph - 10);
        g.textAlign = 'left';
      }
      // davr nomi (ko'p bo'lsa — har uchinchisi)
      if (bars.length <= 12 || i % 3 === 0 || i === bars.length - 1) {
        g.fillStyle = isSel ? PICK : '#5b6b85';
        g.font = '500 15px "JetBrains Mono", Consolas, monospace';
        g.textAlign = 'center';
        g.fillText(String(b.row.period_key ?? '').replace(/^20/, ''), b.cx, CHART.y1 + 24);
        g.textAlign = 'left';
      }
    });
    g.fillStyle = '#56627a';
    g.font = '500 16px Inter, system-ui, sans-serif';
    g.textAlign = 'right';
    const missing = bars.some((b) => !b.has);
    g.fillText(missing
      ? 'past = arzon · yo‘q = bu oy bazada qiymat yo‘q'
      : 'past = arzon · balandlik farqni ko‘rsatadi', CW - 48, 222);
    g.textAlign = 'left';
    tex.needsUpdate = true;
  }

  // Qidiruv paytidagi ekran: aylanuvchi raqamlar va sakrovchi ustunlar
  function drawScan() {
    drawIdle('');
    g.fillStyle = '#38bdf8';
    g.font = '600 26px Inter, system-ui, sans-serif';
    g.fillText('Aniqlanmoqda…', 48, 58);
    g.fillStyle = 'rgba(255,255,255,.85)';
    g.font = '600 76px "JetBrains Mono", Consolas, monospace';
    g.fillText(`${rnd(900) + 100} ${String(rnd(1000)).padStart(3, '0')},${rnd(10)}`, 48, 150);
    g.fillStyle = '#56627a';
    g.font = '600 22px "JetBrains Mono", Consolas, monospace';
    g.fillText(`20${rnd(10)}${rnd(10)}-M${String(rnd(12) + 1).padStart(2, '0')}`, 48, 192);
    const n = 12;
    const slot = (CHART.x1 - CHART.x0) / n;
    for (let i = 0; i < n; i++) {
      const h = (0.15 + Math.random() * 0.85) * (CHART.y1 - CHART.y0);
      g.fillStyle = `#${LOW.clone().lerp(HIGH, Math.random()).getHexString()}`;
      g.globalAlpha = 0.55;
      g.fillRect(CHART.x0 + slot * (i + 0.5) - slot * 0.31, CHART.y1 - h, slot * 0.62, h);
      g.globalAlpha = 1;
    }
    g.fillStyle = '#56627a';
    g.font = '500 16px Inter, system-ui, sans-serif';
    g.textAlign = 'right';
    g.fillText('raqamlar hali ma’lumot emas — qidirilmoqda', CW - 48, 222);
    g.textAlign = 'left';
    tex.needsUpdate = true;
  }

  // Taxminan 20 kadr/s: o'yindagidek "chiq-chiq" almashish
  let lastFrame = 0;
  gsap.ticker.add(() => {
    if (phase !== 'scan' && phase !== 'settle') return;
    const now = performance.now();
    if (now - lastFrame < 55) return;
    lastFrame = now;
    if (phase === 'scan') drawScan();
    else draw();
  });

  // Qidiruv boshlandi / tugadi (natija kelmagan bo'lsa ekran bo'sh holatga qaytadi)
  function scan(on) {
    if (on && !reduceMotion) { phase = 'scan'; drawScan(); return; }
    if (on) { phase = 'idle'; drawIdle('Aniqlanmoqda…'); return; }
    if (phase === 'scan') { phase = series.length ? 'done' : 'idle'; if (!series.length) drawIdle('Natija shu yerda chiqadi'); }
  }

  function clearAnchors() {
    for (const it of items) group.remove(it.anchor);
    items = [];
  }

  function clear() {
    clearAnchors();
    series = [];
    picked = null;
    phase = 'idle';
    drawIdle('Natija shu yerda chiqadi');
  }

  // Qaytaradi: [{ row, top: Vector3 (group ichida) }] — bosiladigan joylar uchun
  function build(rows, { unit = '' } = {}) {
    clearAnchors();
    picked = null;
    if (!rows?.length) {
      series = [];
      drawIdle('Mavjud emas');
      return items;
    }
    // Birinchi qator (mahsulot/hudud) bo'yicha, oxirgi 24 ta davr
    const firstItem = rows[0].item_code;
    series = rows
      .filter((r) => r.item_code === firstItem)
      .sort((a, b) => String(a.period_key).localeCompare(String(b.period_key)))
      .slice(-MAX_BARS);
    meta = { unit, title: series[0]?.item_name ?? '' };
    for (const b of layout()) {
      const top = toLocal(b.cx, CHART.y1 - b.h);
      const anchor = new THREE.Object3D();
      anchor.position.copy(top);
      group.add(anchor);
      items.push({ row: b.row, top, anchor });
    }
    // Ustunlar pastdan o'sib chiqadi, raqamlar chapdan o'ngga bittalab to'xtaydi
    gsap.killTweensOf(anim);
    if (reduceMotion) {
      anim.grow = 1;
      anim.lock = 1;
      phase = 'done';
      draw();
      return items;
    }
    anim.grow = 0;
    anim.lock = 0;
    phase = 'settle';
    gsap.to(anim, { grow: 1, duration: 1.1, ease: 'power3.out' });
    gsap.to(anim, { lock: 1, duration: 0.9, ease: 'none', onComplete: () => { phase = 'done'; draw(); } });
    draw();
    return items;
  }

  function select(item) {
    picked = item?.row ?? null;
    draw();
  }

  drawIdle('Natija shu yerda chiqadi');
  // Monitor ramkasining yuqori cheti (group ichida) — nur shu yerga tegadi
  const edgeTop = () => new THREE.Vector3(0, SCREEN_Y + SCREEN_H / 2 + 0.08, -0.07);

  // Ekranning 4 burchagi (group ichida)
  const screenCorners = () => [[-1, -1], [1, -1], [1, 1], [-1, 1]].map(([x, y]) => new THREE.Vector3(
    (x * SCREEN_W) / 2, SCREEN_Y + (y * SCREEN_H) / 2, 0,
  ));

  return { group, build, clear, select, scan, edgeTop, screenCorners };
}
