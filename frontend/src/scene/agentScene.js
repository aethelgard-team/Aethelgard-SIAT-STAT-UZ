// 3D sahna (butun ekran foni): chapda "Ombor" (DWH), markazda "Agent" — O'zbekiston
// xaritasi (gologramma) + 6 ta MCP tool,
// o'ngda natijaning 3D ustunlari.
// Qoida: har bir harakat (nur, to'lqin, yonish) faqat backenddan kelgan haqiqiy
// voqeaga javob. Yorug'lik o'lchov emas — u faqat "hozir shu qadam bo'ldi" deydi.
// Har bir yorliq va bosiladigan joy — 3D nuqtaga bog'langan HTML tugma.
import * as THREE from 'three';
import { gsap } from 'gsap';
import { TOOLS } from '../core/stages.js';
import { formatNumber, el } from '../core/format.js';
import { createWarehouse } from './warehouse.js';
import { createBars } from './bars3d.js';
import { UZ_OUTLINE } from './uzbekistan.js';
import { WORLD_BORDERS } from './worldBorders.js';

export function hasWebGL() {
  try {
    const c = document.createElement('canvas');
    return !!(window.WebGLRenderingContext && (c.getContext('webgl2') || c.getContext('webgl')));
  } catch {
    return false;
  }
}

const BLUE = 0x38bdf8;
const GREEN = 0x10b981;
const AMBER = 0xf59e0b;
const RED = 0xf87171;
const NODE_IDLE = 0x1e2a40;
const BG = 0x060a12;

const SIDE_X = 6;          // ombor va ustunlar markazdan shuncha uzoqda
const HALF_WIDTH = 8.4;    // sahna kengligining yarmi (kamera shunga moslanadi)
const HALF_HEIGHT = 3.0;   // sahna balandligining yarmi
const AGENT_Y = 2.0;
const RING_R = 2.6;

// Bir xil ko'rinish uchun urug'li tasodifiy son (yulduzlar har safar bir xil)
function seeded(seed) {
  return () => {
    seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// Yumshoq yorug'lik dog'i (glow) uchun radial gradient tekstura
const GLOW = (() => {
  const c = document.createElement('canvas');
  c.width = c.height = 128;
  const g = c.getContext('2d');
  const grd = g.createRadialGradient(64, 64, 0, 64, 64, 64);
  grd.addColorStop(0, 'rgba(255,255,255,1)');
  grd.addColorStop(0.18, 'rgba(255,255,255,.65)');
  grd.addColorStop(0.45, 'rgba(255,255,255,.16)');
  grd.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = grd;
  g.fillRect(0, 0, 128, 128);
  return new THREE.CanvasTexture(c);
})();
const additive = { transparent: true, depthWrite: false, blending: THREE.AdditiveBlending };
function glowSprite(color, size, opacity = 0.6) {
  const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: GLOW, color, opacity, ...additive }));
  sp.scale.set(size, size, 1);
  return sp;
}
function circle(r, n = 128) {
  const pts = [];
  for (let i = 0; i <= n; i++) {
    const a = (i / n) * Math.PI * 2;
    pts.push(new THREE.Vector3(Math.cos(a) * r, 0, Math.sin(a) * r));
  }
  return new THREE.BufferGeometry().setFromPoints(pts);
}
// Zona ostidagi nurli halqa
function padRing(radius, color, opacity = 0.5) {
  const ring = new THREE.Line(circle(radius, 160), new THREE.LineBasicMaterial({ color, opacity, ...additive }));
  ring.position.y = 0.02;
  return ring;
}

export function createAgentScene(container, labelsEl, infoEl) {
  const params = new URLSearchParams(location.search);
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    || params.get('quality') === 'low';
  const rand = seeded(42);

  const scene = new THREE.Scene();
  scene.fog = new THREE.Fog(BG, 20, 60);
  const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 400);
  const target = new THREE.Vector3(0.4, 1.6, 0);
  const camBase = { dist: 22, lift: 0 }; // intro animatsiyasi uchun

  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance' });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.15;
  container.append(renderer.domElement);

  // ---------------- Yorug'lik ----------------
  scene.add(new THREE.AmbientLight(0x1a2a44, 1.2));
  scene.add(new THREE.HemisphereLight(0x9fd8ff, BG, 0.6));
  const key = new THREE.DirectionalLight(0xc4e8ff, 1.3);
  key.position.set(6, 10, 6);
  scene.add(key);
  const rim = new THREE.DirectionalLight(AMBER, 0.5);
  rim.position.set(-10, 4, -8);
  scene.add(rim);
  const whLight = new THREE.PointLight(GREEN, 6, 10, 1.6);
  whLight.position.set(-SIDE_X, 2.5, 2);
  scene.add(whLight);

  // ---------------- Yulduzlar va chang ----------------
  {
    const n = 1600;
    const pos = new Float32Array(n * 3);
    for (let i = 0; i < n; i++) {
      const r = 70 + rand() * 90, th = rand() * Math.PI * 2, ph = Math.acos(2 * rand() - 1);
      pos[i * 3] = r * Math.sin(ph) * Math.cos(th);
      pos[i * 3 + 1] = Math.abs(r * Math.cos(ph)) * 0.8 - 6;
      pos[i * 3 + 2] = r * Math.sin(ph) * Math.sin(th);
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    scene.add(new THREE.Points(g, new THREE.PointsMaterial({ color: 0xaecbf0, size: 0.55, map: GLOW, opacity: 0.7, fog: false, ...additive })));
  }
  const dust = (() => {
    const n = 220;
    const pos = new Float32Array(n * 3);
    for (let i = 0; i < n; i++) {
      pos[i * 3] = (rand() - 0.5) * 26;
      pos[i * 3 + 1] = rand() * 8;
      pos[i * 3 + 2] = (rand() - 0.5) * 14;
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    const p = new THREE.Points(g, new THREE.PointsMaterial({ color: 0x7dd3fc, size: 0.07, map: GLOW, opacity: 0.5, ...additive }));
    scene.add(p);
    return p;
  })();

  // ---------------- Nurli pol (shader to'r) ----------------
  const floorMat = new THREE.ShaderMaterial({
    transparent: true, depthWrite: false,
    uniforms: {
      uTime: { value: 0 },
      uColor: { value: new THREE.Color(BLUE) },
      uAgent: { value: new THREE.Vector2(0, 0) },
      uWh: { value: new THREE.Vector2(-SIDE_X, 0) },
      uWhGlow: { value: 0 },
      uWave: { value: 0 },
    },
    vertexShader: /* glsl */`
      varying vec3 vW;
      void main(){ vec4 w = modelMatrix * vec4(position, 1.0); vW = w.xyz; gl_Position = projectionMatrix * viewMatrix * w; }`,
    fragmentShader: /* glsl */`
      uniform float uTime; uniform vec3 uColor; uniform vec2 uAgent; uniform vec2 uWh; uniform float uWhGlow; uniform float uWave;
      varying vec3 vW;
      float grid(vec2 p, float s){ vec2 q = p / s; vec2 g = abs(fract(q - 0.5) - 0.5) / fwidth(q); return 1.0 - min(min(g.x, g.y), 1.0); }
      void main(){
        vec2 p = vW.xz;
        float fade = smoothstep(32.0, 3.0, length(p));
        float g1 = grid(p, 1.0) * 0.12;
        float g2 = grid(p, 5.0) * 0.32;
        float da = length(p - uAgent);
        float ring = exp(-pow((da - uWave * 22.0) * 0.9, 2.0)) * (1.0 - uWave) * step(0.001, uWave);
        float under = exp(-pow(da / 2.6, 2.0));
        float wh = exp(-pow(length((p - uWh) * vec2(0.6, 0.8)) / 2.0, 2.0));
        vec3 col = mix(uColor, vec3(0.063, 0.725, 0.506), clamp(wh * (0.35 + uWhGlow), 0.0, 1.0));
        float a = (g1 + g2) * fade * (1.0 + ring * 3.0 + under * 1.6 + wh * uWhGlow * 2.0)
                + under * 0.12 + wh * (0.04 + uWhGlow * 0.16);
        gl_FragColor = vec4(col, a);
      }`,
  });
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(140, 140), floorMat);
  floor.rotation.x = -Math.PI / 2;
  floor.position.y = -0.01;
  scene.add(floor);

  // ---------------- HTML yorliqlar (3D nuqtaga bog'langan) ----------------
  const labels = []; // { obj, offset, node, kind }
  function addLabel(obj, node, { offset = 0, kind = 'static' } = {}) {
    node.classList.add('scene-label');
    labelsEl.append(node);
    labels.push({ obj, offset, node, kind });
    return node;
  }
  function removeLabels(kind) {
    for (let i = labels.length - 1; i >= 0; i--) {
      if (labels[i].kind === kind) {
        labels[i].node.remove();
        labels.splice(i, 1);
      }
    }
  }
  const tmp = new THREE.Vector3();
  function updateLabels() {
    const w = container.clientWidth;
    const h = container.clientHeight;
    for (const l of labels) {
      l.obj.getWorldPosition(tmp);
      tmp.y += l.offset;
      tmp.project(camera);
      let shown = true;
      for (let o = l.obj; o; o = o.parent) if (!o.visible) { shown = false; break; }
      const visible = shown && tmp.z < 1 && Math.abs(tmp.x) <= 1.05 && Math.abs(tmp.y) <= 1.05;
      l.node.hidden = !visible;
      if (visible) {
        const half = l.node.offsetWidth / 2 + 8;
        const x = Math.min(Math.max(((tmp.x + 1) / 2) * w, half), w - half);
        l.node.style.transform = `translate(${x.toFixed(1)}px, ${(((1 - tmp.y) / 2) * h).toFixed(1)}px) translate(-50%, -100%)`;
      }
    }
  }

  // ---------------- Markaz: Agent — O'zbekiston xaritasi (gologramma) ----------------
  // Agent faqat O'zbekiston statistikasi bilan ishlaydi, shuning uchun uning "yuzi" — xarita.
  const agentGroup = new THREE.Group();
  agentGroup.position.y = AGENT_Y;
  scene.add(agentGroup);
  const map = new THREE.Group();
  map.rotation.y = -0.15;
  agentGroup.add(map);

  // lon/lat -> xarita tekisligi (markaz 0,0; kenglik bo'yicha cos tuzatish)
  const MAP_K = 0.3, MAP_LON = 64.5, MAP_LAT = 41.2;
  const COS_LAT = Math.cos(THREE.MathUtils.degToRad(MAP_LAT));
  const mp = (lon, lat) => new THREE.Vector2((lon - MAP_LON) * MAP_K * COS_LAT, (lat - MAP_LAT) * MAP_K);
  const uzShape = new THREE.Shape(UZ_OUTLINE.slice(0, -1).map(([lon, lat]) => mp(lon, lat)));

  // Tana: qalinligi bor shaffof plita
  const slab = new THREE.ExtrudeGeometry(uzShape, { depth: 0.1, bevelEnabled: true, bevelSize: 0.015, bevelThickness: 0.015, bevelSegments: 2 });
  slab.translate(0, 0, -0.05);
  const slabMat = new THREE.MeshPhysicalMaterial({
    color: 0x0b2a44, emissive: BLUE, emissiveIntensity: 0.25, roughness: 0.3, metalness: 0.2,
    clearcoat: 1, transparent: true, opacity: 0.92,
  });
  map.add(new THREE.Mesh(slab, slabMat));

  // Old yuza: gologramma to'ri + pastdan tepaga yuruvchi skaner chizig'i; uPulse — agent "o'ylaganda"
  const coreMat = new THREE.ShaderMaterial({
    transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
    uniforms: { uTime: { value: 0 }, uPulse: { value: 0 }, uColA: { value: new THREE.Color(BLUE) } },
    vertexShader: /* glsl */`
      varying vec2 vP;
      void main(){ vP = position.xy; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
    fragmentShader: /* glsl */`
      uniform float uTime; uniform float uPulse; uniform vec3 uColA;
      varying vec2 vP;
      void main(){
        vec2 q = vP * 3.0;
        vec2 g = abs(fract(q - 0.5) - 0.5) / fwidth(q);
        float line = 1.0 - min(min(g.x, g.y), 1.0);
        float scan = exp(-pow((vP.y - (mod(uTime * 0.6, 3.4) - 1.7)) * 6.0, 2.0));
        float stripes = 0.5 + 0.5 * sin(vP.y * 40.0);
        float a = line * 0.35 + stripes * 0.05 + scan * 0.45 + uPulse * 0.6;
        gl_FragColor = vec4(uColA * a, 1.0);
      }`,
  });
  const core = new THREE.Mesh(new THREE.ShapeGeometry(uzShape), coreMat);
  core.position.z = 0.07;
  map.add(core);

  // Nurli chegara
  const edge = UZ_OUTLINE.map(([lon, lat]) => { const v = mp(lon, lat); return new THREE.Vector3(v.x, v.y, 0.075); });
  const edgeMat = new THREE.LineBasicMaterial({ color: 0x9fe4ff });
  map.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(edge), edgeMat));
  const edgeHaloMat = new THREE.PointsMaterial({ color: BLUE, size: 0.32, map: GLOW, opacity: 0.45, ...additive });
  map.add(new THREE.Points(new THREE.BufferGeometry().setFromPoints(edge), edgeHaloMat));

  const agentGlow = glowSprite(BLUE, 6.5, 0.35);
  agentGlow.position.z = -0.4;
  agentGroup.add(agentGlow);
  // ---------------- Boshlang'ich holat: aylanuvchi Yer shari ----------------
  // Savol joyiga bosilganda globus O'zbekistonga buriladi va xaritaga almashadi.
  const GLOBE_R = 1.45;
  const sph = (lon, lat, r) => {
    const a = THREE.MathUtils.degToRad(lon), b = THREE.MathUtils.degToRad(lat);
    return new THREE.Vector3(r * Math.cos(b) * Math.sin(a), r * Math.sin(b), r * Math.cos(b) * Math.cos(a));
  };
  const globe = new THREE.Group();
  agentGroup.add(globe);
  const globeSpin = new THREE.Group();   // y bo'yicha aylanadi
  globeSpin.rotation.order = 'XYZ';
  globeSpin.rotation.x = THREE.MathUtils.degToRad(22);
  globe.add(globeSpin);
  const globeMats = []; // [material, asosiy shaffoflik] — yo'qolish/paydo bo'lish uchun
  const gmat = (m, o) => { m.transparent = true; m.opacity = o; globeMats.push([m, o]); return m; };
  globeSpin.add(new THREE.Mesh(
    new THREE.SphereGeometry(GLOBE_R, 64, 48),
    gmat(new THREE.MeshPhongMaterial({ color: 0x0a1a30, emissive: 0x071426, shininess: 40, specular: 0x3a6a9a }), 1),
  ));
  {
    const gm = gmat(new THREE.LineBasicMaterial({ color: BLUE, ...additive }), 0.12);
    for (let lat = -60; lat <= 60; lat += 30) {
      globeSpin.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(Array.from({ length: 121 }, (_, i) => sph(i * 3, lat, GLOBE_R * 1.001))), gm));
    }
    for (let lon = 0; lon < 360; lon += 30) {
      globeSpin.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(Array.from({ length: 61 }, (_, i) => sph(lon, -90 + i * 3, GLOBE_R * 1.001))), gm));
    }
    const cm = gmat(new THREE.LineBasicMaterial({ color: 0x5fb8e0, ...additive }), 0.5);
    for (const r of WORLD_BORDERS) {
      globeSpin.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(r.map(([x, y]) => sph(x, y, GLOBE_R * 1.003))), cm));
    }
    // O'zbekiston globusda sariq yonadi
    const pts2 = UZ_OUTLINE.slice(0, -1).map(([x, y]) => new THREE.Vector2(x, y));
    const pos = [];
    for (const t of THREE.ShapeUtils.triangulateShape(pts2, [])) {
      for (const k of t) { const v = sph(pts2[k].x, pts2[k].y, GLOBE_R * 1.006); pos.push(v.x, v.y, v.z); }
    }
    const fg = new THREE.BufferGeometry();
    fg.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
    globeSpin.add(new THREE.Mesh(fg, gmat(new THREE.MeshBasicMaterial({ color: AMBER, side: THREE.DoubleSide, depthWrite: false }), 0.9)));
    globeSpin.add(new THREE.Line(
      new THREE.BufferGeometry().setFromPoints(UZ_OUTLINE.map(([x, y]) => sph(x, y, GLOBE_R * 1.008))),
      gmat(new THREE.LineBasicMaterial({ color: 0xffd27a }), 1),
    ));
    const uzGlow = glowSprite(AMBER, 1.4, 0.8);
    uzGlow.position.copy(sph(64, 41, GLOBE_R * 1.02));
    globeMats.push([uzGlow.material, 0.8]);
    globeSpin.add(uzGlow);
  }
  // Atmosfera: chetidan ko'k nur
  const atmMat = new THREE.ShaderMaterial({
    transparent: true, depthWrite: false, side: THREE.BackSide, blending: THREE.AdditiveBlending,
    uniforms: { uFade: { value: 1 } },
    vertexShader: 'varying vec3 n; void main(){ n = normalize(normalMatrix * normal); gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
    fragmentShader: 'uniform float uFade; varying vec3 n; void main(){ float i = pow(0.75 - dot(n, vec3(0.0, 0.0, 1.0)), 3.0); gl_FragColor = vec4(0.22, 0.74, 0.97, 1.0) * i * uFade; }',
  });
  globe.add(new THREE.Mesh(new THREE.SphereGeometry(GLOBE_R * 1.12, 64, 48), atmMat));
  const globeState = { fade: 1, spin: true };
  // Birinchi savoldan keyin: globus yo'q, xarita tayyor turadi (2-savolda qayta ochilish animatsiyasi yo'q)
  function ensureMap() {
    if (mode === 'idle') return;
    gsap.killTweensOf([globeState, globe.scale, map.scale, globeSpin.rotation]);
    globeState.spin = false;
    globeState.fade = 0;
    globe.scale.setScalar(1);
    map.visible = true;
    map.scale.setScalar(1.25);
    applyGlobeFade();
  }
  function applyGlobeFade() {
    for (const [m, o] of globeMats) m.opacity = o * globeState.fade;
    atmMat.uniforms.uFade.value = globeState.fade;
    globe.visible = globeState.fade > 0.01;
  }

  const agentLight = new THREE.PointLight(BLUE, 8, 12, 1.6);
  agentLight.position.z = 1.2;
  agentGroup.add(agentLight);
  const agentLabel = addLabel(core, el('span', 'AI agent · O‘zbekiston', 'scene-title'), { offset: 1.95 });

  // Xarita ostidagi taglik va yorug'lik konusi
  {
    const base = new THREE.Mesh(
      new THREE.CylinderGeometry(1.1, 1.3, 0.12, 64),
      new THREE.MeshStandardMaterial({ color: 0x0b1626, emissive: BLUE, emissiveIntensity: 0.2, metalness: 0.5, roughness: 0.3 }),
    );
    base.position.y = 0.06;
    scene.add(base);
    const cone = new THREE.Mesh(
      new THREE.CylinderGeometry(1.9, 0.9, 1.0, 48, 1, true),
      new THREE.MeshBasicMaterial({ color: BLUE, opacity: 0.06, side: THREE.DoubleSide, ...additive }),
    );
    cone.position.y = 0.6;
    scene.add(cone);
  }

  // Agent ostidagi halqalar va nur ustuni
  const floorRings = [[1.3, 0.4, BLUE], [2.1, 0.22, GREEN], [3.4, 0.12, BLUE]].map(([r, o, c]) => {
    const ring = padRing(r, c, o);
    scene.add(ring);
    return ring;
  });
  {
    const col = new THREE.Mesh(
      new THREE.CylinderGeometry(0.02, 0.35, AGENT_Y, 24, 1, true),
      new THREE.MeshBasicMaterial({ color: BLUE, opacity: 0.05, side: THREE.DoubleSide, ...additive }),
    );
    col.position.y = AGENT_Y / 2;
    scene.add(col);
  }

  // ---------------- 6 ta MCP tool (agent atrofida orbitada) ----------------
  const ring = new THREE.Group();
  ring.rotation.set(0.22, 0, -0.08);
  agentGroup.add(ring);
  ring.add(new THREE.Line(circle(RING_R, 160), new THREE.LineBasicMaterial({ color: BLUE, opacity: 0.14, ...additive })));
  const spin = { v: 1 }; // orbita tezligi (tool chaqirilganda to'xtaydi)
  const nodes = new Map(); // tool nomi -> { mesh, label, glow }
  let onToolClick = null;  // inspektor ochish uchun (askView beradi)
  TOOLS.forEach((name, i) => {
    const angle = (i / TOOLS.length) * Math.PI * 2;
    const mesh = new THREE.Mesh(
      new THREE.SphereGeometry(0.17, 32, 16),
      new THREE.MeshStandardMaterial({ color: NODE_IDLE, emissive: BLUE, emissiveIntensity: 0.35, roughness: 0.3, metalness: 0.3 }),
    );
    mesh.position.set(Math.cos(angle) * RING_R, 0, Math.sin(angle) * RING_R);
    ring.add(mesh);
    const glow = glowSprite(BLUE, 0.9, 0.35);
    mesh.add(glow);
    const label = el('button', name);
    label.type = 'button';
    label.setAttribute('aria-pressed', 'false');
    label.title = 'Bu tool hali chaqirilmagan';
    label.addEventListener('click', () => onToolClick?.(name, label));
    addLabel(mesh, label, { offset: 0.34 });
    nodes.set(name, { mesh, label, glow });
  });
  let activeTool = null;

  // ---------------- Chap: Ombor (DWH) ----------------
  const warehouse = createWarehouse();
  warehouse.group.position.set(-SIDE_X, 0, 0);
  scene.add(warehouse.group);
  const whPlate = new THREE.Mesh(
    new THREE.PlaneGeometry(5.1, 3.3),
    new THREE.MeshBasicMaterial({ color: 0x0a1a2a, transparent: true, opacity: 0.55, depthWrite: false }),
  );
  whPlate.rotation.x = -Math.PI / 2;
  whPlate.position.set(-SIDE_X, 0.005, 0);
  scene.add(whPlate);
  const whBorder = (() => {
    const hw = 2.55, hd = 1.65;
    const b = new THREE.LineLoop(new THREE.BufferGeometry().setFromPoints([
      new THREE.Vector3(-hw, 0.01, -hd), new THREE.Vector3(hw, 0.01, -hd),
      new THREE.Vector3(hw, 0.01, hd), new THREE.Vector3(-hw, 0.01, hd),
    ]), new THREE.LineBasicMaterial({ color: GREEN, opacity: 0.6, ...additive }));
    b.position.x = -SIDE_X;
    scene.add(b);
    return b;
  })();
  const warehouseAnchor = new THREE.Object3D();
  warehouseAnchor.position.set(-SIDE_X, -0.1, 2.3);
  scene.add(warehouseAnchor);
  const warehouseTitle = addLabel(warehouseAnchor, el('span', 'Ombor (DWH): yuklanmoqda…', 'scene-title caption wh'));
  const whTop = new THREE.Vector3(-SIDE_X, 1.8, 0); // nur shu yerdan chiqadi

  // ---------------- O'ng: 3D ustunlar ----------------
  const bars = createBars();
  bars.group.position.set(SIDE_X, 0, 0);
  scene.add(bars.group);
  const barsPad = padRing(2.6, AMBER, 0.45);
  barsPad.position.x = SIDE_X;
  scene.add(barsPad);
  const barsAnchor = new THREE.Object3D();
  barsAnchor.position.set(SIDE_X, -0.1, 2.7);
  scene.add(barsAnchor);
  const barsTitle = addLabel(barsAnchor, el('span', 'Natija: hali yo‘q', 'scene-title caption res'));
  let barsTop = new THREE.Vector3(SIDE_X, 1.5, 0);

  // Aylanib turadigan uzuq-uzuq halqalar (ombor, agent va natija atrofida)
  function dashedRing(r, color, opacity) {
    const line = new THREE.Line(circle(r, 180), new THREE.LineDashedMaterial({
      color, dashSize: 0.22, gapSize: 0.16, opacity, ...additive,
    }));
    line.computeLineDistances();
    return line;
  }
  const spinners = [];
  [[-SIDE_X, 2.9, GREEN, 0.35, 0.18], [-SIDE_X, 3.3, GREEN, 0.15, -0.1],
    [SIDE_X, 2.95, AMBER, 0.35, -0.16], [SIDE_X, 3.35, AMBER, 0.15, 0.09],
    [0, 4.0, BLUE, 0.18, 0.06]].forEach(([x, r, c, o, sp]) => {
    const d = dashedRing(r, c, o);
    d.position.set(x, 0.03, 0);
    d.userData.speed = sp;
    d.userData.zone = x < 0 ? 'warehouse' : x > 0 ? 'bars' : 'agent';
    scene.add(d);
    spinners.push(d);
  });

  const scanRings = [...spinners, ...floorRings, ring.children[0]];
  for (const r of scanRings) r.userData.baseColor = r.material.color.clone();
  let scanning = false;
  // Qidiruv paytida: xarita atrofidagi halqalar yorqinroq bo'ladi va ranglari almashadi;
  // xarita chegarasi va chaqirilmagan toollar ham rang almashtiradi. Natija chiqqach — asl rang.
  for (const r of scanRings) r.userData.baseOpacity = r.material.opacity;
  function setScanning(on) {
    bars.scan?.(on);
    scanning = on && !reduceMotion;
    if (scanning) {
      for (const r of scanRings) r.material.opacity = Math.max(r.userData.baseOpacity, 0.75);
      return;
    }
    for (const r of scanRings) {
      r.material.color.copy(r.userData.baseColor);
      r.material.opacity = r.userData.baseOpacity;
    }
    edgeMat.color.set(coreMat.uniforms.uColA.value.getHex() === RED ? RED : 0x9fe4ff);
    edgeHaloMat.color.set(BLUE);
    for (const [name, n] of nodes) {
      if (name === activeTool) continue;
      n.mesh.material.emissive.set(BLUE);
      n.glow.material.color.set(BLUE);
    }
  }

  // ---------------- Holatlar: 'idle' (faqat xarita) -> 'compose' (yozilmoqda) -> 'active' ----------------
  const whZone = new THREE.Group();
  whZone.position.set(-SIDE_X, 0, 0);
  scene.add(whZone);
  const barsZone = new THREE.Group();
  barsZone.position.set(SIDE_X, 0, 0);
  scene.add(barsZone);
  for (const o of [warehouse.group, whPlate, whBorder, warehouseAnchor, ...spinners.filter((d) => d.userData.zone === 'warehouse')]) whZone.attach(o);
  for (const o of [bars.group, barsPad, barsAnchor, ...spinners.filter((d) => d.userData.zone === 'bars')]) barsZone.attach(o);
  const zones = { warehouse: whZone, tools: ring, bars: barsZone };
  function showZone(name, on, instant = false) {
    const g = zones[name];
    if (g.userData.on === on) return;
    g.userData.on = on;
    gsap.killTweensOf(g.scale);
    if (instant || reduceMotion) {
      g.visible = on;
      g.scale.setScalar(on ? 1 : 0.001);
    } else if (on) {
      g.visible = true;
      gsap.fromTo(g.scale, { x: 0.001, y: 0.001, z: 0.001 }, { x: 1, y: 1, z: 1, duration: 0.9, ease: 'back.out(1.6)' });
    } else {
      gsap.to(g.scale, { x: 0.001, y: 0.001, z: 0.001, duration: 0.5, ease: 'power2.in', onComplete: () => { if (!g.userData.on) g.visible = false; } });
    }
  }
  let mode = 'idle';

  // Fokus: hozir qaysi obyekt ishlayotgan bo'lsa, ostida sariq halqa va nur ustuni
  const focus = new THREE.Group();
  const focusRing = new THREE.Mesh(
    new THREE.RingGeometry(0.92, 1.0, 96),
    new THREE.MeshBasicMaterial({ color: AMBER, opacity: 0, side: THREE.DoubleSide, ...additive }),
  );
  focusRing.rotation.x = -Math.PI / 2;
  const focusBeam = new THREE.Mesh(
    new THREE.CylinderGeometry(0.9, 0.9, 6, 48, 1, true),
    new THREE.MeshBasicMaterial({ color: AMBER, opacity: 0, side: THREE.DoubleSide, ...additive }),
  );
  focusBeam.position.y = 3;
  focus.add(focusRing, focusBeam);
  focus.position.set(0, 0.04, 0);
  scene.add(focus);
  let focusOn = null;            // () => Vector3 — kuzatilayotgan obyekt
  let focusSize = 1;
  let activeLabel = null;

  // Kamera fokusdagi qismga uchib boradi; boost — o'sha qism atrofi tez aylanadi
  const cam = { x: target.x, y: target.y, z: target.z, zoom: 1 };
  const boost = { agent: 1, warehouse: 1, bars: 1 };
  const CAM = {
    agent: [0, AGENT_Y, 0, 0.8],
    warehouse: [-SIDE_X, 0.6, 0, 0.75],
    tool: [0, AGENT_Y, 0, 0.8],
    bars: [SIDE_X, 1.4, 0, 0.75],
  };
  const MODE_CAM = {
    idle: [0, AGENT_Y, 0, 0.6],          // aylanuvchi Yer shari
    compose: [0, AGENT_Y, 0, 0.42],      // faqat O'zbekiston xaritasi, yaqindan
    active: [target.x, target.y, target.z, 1], // hammasi
  };
  function flyTo(name) {
    const [x, y, z, zoom] = name ? CAM[name] : MODE_CAM[mode];
    gsap.to(cam, { x, y, z, zoom, duration: reduceMotion ? 0 : 0.8, ease: 'power2.inOut', overwrite: true });
    const zone = name === 'tool' ? 'agent' : name;
    for (const k of Object.keys(boost)) {
      gsap.to(boost, { [k]: k === zone && !reduceMotion ? 7 : 1, duration: 0.8 });
    }
  }

  // ---------------- Nurlar, to'lqinlar, puls ----------------
  // Nurning uchlari funksiya: tool aylanib yursa ham nur unga ergashadi.
  const beams = [];
  const waves = [];
  const _p = new THREE.Vector3();
  const SEG = 64;
  // fadeOut: true — nur yetib borgach butunlay yo'qoladi (iz qolmaydi)
  function createBeam(fromFn, toFn, color, lift = 1.5, { fadeOut = false } = {}) {
    const curve = new THREE.QuadraticBezierCurve3(new THREE.Vector3(), new THREE.Vector3(), new THREE.Vector3());
    const g = new THREE.Group();
    scene.add(g);
    const arr = new Float32Array((SEG + 1) * 3);
    const coreGeo = new THREE.BufferGeometry();
    coreGeo.setAttribute('position', new THREE.BufferAttribute(arr, 3));
    const haloGeo = new THREE.BufferGeometry();
    haloGeo.setAttribute('position', new THREE.BufferAttribute(arr, 3));
    const coreM = new THREE.LineBasicMaterial({ color: new THREE.Color(color).lerp(new THREE.Color(0xffffff), 0.55), opacity: 0.95, ...additive });
    const haloM = new THREE.PointsMaterial({ color, size: 0.42, map: GLOW, opacity: 0.35, ...additive });
    const coreLine = new THREE.Line(coreGeo, coreM);
    const halo = new THREE.Points(haloGeo, haloM);
    coreLine.frustumCulled = false;
    halo.frustumCulled = false;
    g.add(coreLine, halo);
    const N = reduceMotion ? 0 : 50;
    const pos = new Float32Array(N * 3);
    const pg = new THREE.BufferGeometry();
    pg.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    const pm = new THREE.PointsMaterial({ color, size: 0.18, map: GLOW, opacity: 1, ...additive });
    const pts = new THREE.Points(pg, pm);
    pts.frustumCulled = false;
    g.add(pts);
    const head = glowSprite(color, 1.1, 1);
    g.add(head);
    const b = {
      g, curve, fromFn, toFn, lift, arr, coreGeo, haloGeo, pg, pos, N, head,
      progress: reduceMotion ? 1 : 0, speed: 0.7,
      offs: Array.from({ length: N }, () => Math.random()),
      jit: Array.from({ length: N * 3 }, () => (Math.random() - 0.5) * 0.12),
      mats: [coreM, haloM, pm, head.material],
    };
    beams.push(b);
    if (!reduceMotion) gsap.to(b, { progress: 1, duration: 0.6, ease: 'power2.inOut' });
    if (fadeOut) {
      gsap.to(b.mats, { opacity: 0, duration: 0.6, delay: 0.9 });
      return b;
    }
    // Bir oz porlab turadi, keyin xira "yo'l" bo'lib qoladi (qaysi yo'ldan o'tgani ko'rinsin)
    gsap.to(haloM, { opacity: 0.06, duration: 1.2, delay: 2 });
    gsap.to(coreM, { opacity: 0.3, duration: 1.2, delay: 2 });
    gsap.to([pm, head.material], { opacity: 0, duration: 1.2, delay: 2.4 });
    return b;
  }
  function updateBeams(t) {
    for (const b of beams) {
      const a = b.fromFn();
      const c = b.toFn();
      if (!a || !c) continue;
      b.curve.v0.copy(a);
      b.curve.v2.copy(c);
      b.curve.v1.copy(a).lerp(c, 0.5);
      b.curve.v1.y += b.lift;
      for (let i = 0; i <= SEG; i++) {
        b.curve.getPoint(i / SEG, _p);
        b.arr[i * 3] = _p.x;
        b.arr[i * 3 + 1] = _p.y;
        b.arr[i * 3 + 2] = _p.z;
      }
      const n = Math.max(1, Math.floor(SEG * b.progress) + 1);
      b.coreGeo.setDrawRange(0, n);
      b.haloGeo.setDrawRange(0, n);
      b.coreGeo.attributes.position.needsUpdate = true;
      b.haloGeo.attributes.position.needsUpdate = true;
      b.curve.getPoint(Math.max(b.progress, 0.001), _p);
      b.head.position.copy(_p);
      for (let k = 0; k < b.N; k++) {
        const u = ((b.offs[k] + t * b.speed) % 1) * b.progress;
        b.curve.getPoint(u, _p);
        b.pos[k * 3] = _p.x + b.jit[k * 3];
        b.pos[k * 3 + 1] = _p.y + b.jit[k * 3 + 1];
        b.pos[k * 3 + 2] = _p.z + b.jit[k * 3 + 2];
      }
      if (b.N) b.pg.attributes.position.needsUpdate = true;
    }
  }
  function clearBeams() {
    for (const b of beams.splice(0)) {
      gsap.killTweensOf(b);
      gsap.killTweensOf(b.mats);
      scene.remove(b.g);
      b.coreGeo.dispose();
      b.haloGeo.dispose();
      b.pg.dispose();
      b.mats.forEach((m) => m.dispose());
    }
  }
  function shockwave(pos, color, size = 3.4) {
    if (reduceMotion) return;
    const m = new THREE.MeshBasicMaterial({ color, opacity: 0.9, side: THREE.DoubleSide, ...additive });
    const w = new THREE.Mesh(new THREE.RingGeometry(0.92, 1.0, 96), m);
    w.position.copy(pos);
    scene.add(w);
    waves.push(w);
    gsap.to(w.scale, { x: size, y: size, z: size, duration: 1.2, ease: 'power2.out' });
    gsap.to(m, {
      opacity: 0, duration: 1.2, ease: 'power2.out',
      onComplete: () => { scene.remove(w); w.geometry.dispose(); m.dispose(); waves.splice(waves.indexOf(w), 1); },
    });
  }
  function pulse(strength = 1) {
    if (reduceMotion) return;
    gsap.fromTo(coreMat.uniforms.uPulse, { value: 0 }, { value: strength, duration: 0.22, yoyo: true, repeat: 1, ease: 'power2.out' });
    gsap.fromTo(agentGlow.scale, { x: 6.5, y: 6.5 }, { x: 6.5 + 3 * strength, y: 6.5 + 3 * strength, duration: 0.25, yoyo: true, repeat: 1 });
    gsap.fromTo(agentLight, { intensity: 8 }, { intensity: 8 + 10 * strength, duration: 0.25, yoyo: true, repeat: 1 });
  }
  function floorWave() {
    if (reduceMotion) return;
    gsap.fromTo(floorMat.uniforms.uWave, { value: 0.001 }, { value: 1, duration: 2.2, ease: 'none', onComplete: () => { floorMat.uniforms.uWave.value = 0; } });
  }
  const agentPos = () => agentGroup.getWorldPosition(new THREE.Vector3());
  const toolPos = (name) => nodes.get(name)?.mesh.getWorldPosition(new THREE.Vector3());
  const whPos = () => whTop;
  const barsPos = () => barsTop;

  // Fokusni obyektga o'tkazish: 'agent' | 'warehouse' | 'tool' | 'bars' | null
  const FOCUS = {
    agent: { pos: agentPos, size: 1.9 },
    warehouse: { pos: () => new THREE.Vector3(-SIDE_X, 0, 0), size: 2.7 },
    tool: { pos: () => (activeTool && toolPos(activeTool)) || agentPos(), size: 0.6 },
    bars: { pos: () => new THREE.Vector3(SIDE_X, 0, 0), size: 2.6 },
  };
  function setFocus(name) {
    flyTo(name);
    activeLabel?.removeAttribute('data-active');
    activeLabel = null;
    if (!name) {
      focusOn = null;
      gsap.to([focusRing.material, focusBeam.material], { opacity: 0, duration: 0.6 });
      return;
    }
    const f = FOCUS[name];
    focusOn = f.pos;
    focusSize = f.size;
    gsap.to(focusRing.material, { opacity: 0.9, duration: 0.35 });
    gsap.to(focusBeam.material, { opacity: 0.07, duration: 0.35 });
    if (!reduceMotion) {
      gsap.fromTo(focusRing.scale, { x: focusSize * 1.6, y: focusSize * 1.6 }, { x: focusSize, y: focusSize, duration: 0.5, ease: 'power3.out' });
    }
    activeLabel = {
      agent: agentLabel,
      warehouse: warehouseTitle,
      bars: barsTitle,
      tool: activeTool ? nodes.get(activeTool)?.label : null,
    }[name] ?? null;
    activeLabel?.setAttribute('data-active', 'true');
  }

  // Kamera monitor ekrani markaziga yaqinlashadi (javob to'liq ekranga ochilishidan oldin)
  function diveToMonitor() {
    const cs = bars.screenCorners().map((c) => bars.group.localToWorld(c));
    const c = cs.reduce((a, v) => a.add(v), new THREE.Vector3()).multiplyScalar(1 / cs.length);
    gsap.to(cam, { x: c.x, y: c.y - 0.6, z: c.z, zoom: 0.34, duration: reduceMotion ? 0 : 0.8, ease: 'power2.in', overwrite: true });
  }

  // Navbat: har qadam kamida "hold" ms ko'rinadi, keyin keyingisi.
  // PACE — umumiy tezlik: odam backenddan ortiq kutib qolmasin, bosh aylanmasin (0.5 = 2 baravar tez)
  const PACE = 1; // qadam vaqtlari quyida aniq yozilgan: har bir ko'rinadigan sahna kamida 0,8 s
  // Navbat: har qadam kamida "hold" ms ko'rinadi, keyin keyingisi
  let queue = [];
  let queueTimer = 0;
  let queueBusy = false;
  let idleWaiters = [];
  let fastMode = false; // "Javobni darhol ko'rsatish" bosilsa — qolgan qadamlar kutmasdan bajariladi
  const wakeIdle = () => idleWaiters.splice(0).forEach((f) => f());
  function step(fn, hold = 700) {
    queue.push([fn, hold]);
    if (!queueBusy) pump();
  }
  function pump() {
    const next = queue.shift();
    if (!next) {
      queueBusy = false;
      wakeIdle();
      return;
    }
    queueBusy = true;
    next[0]();
    queueTimer = setTimeout(pump, reduceMotion || fastMode ? 0 : next[1] * PACE);
  }
  function clearQueue() {
    clearTimeout(queueTimer);
    queue = [];
    queueBusy = false;
    wakeIdle();
  }

  // ---------------- Ma'lumot paneli (ustun bosilganda) ----------------
  function showInfo(row, unit, sourceUrl) {
    infoEl.replaceChildren(
      el('strong', `${formatNumber(row.value)}${unit ? ` ${unit}` : ''}`),
      el('span', `${row.item_name ?? row.item_code} · ${row.period_key}`),
      el('span', `status: ${row.status ?? '—'}${row.snapshot_date ? ` · snapshot: ${row.snapshot_date}` : ''}`),
    );
    const url = row.source_url || sourceUrl;
    if (url) {
      const a = el('a', 'Manba: siat.stat.uz');
      a.href = url;
      a.target = '_blank';
      a.rel = 'noopener';
      infoEl.append(a);
    }
    const close = el('button', 'Yopish', 'secondary');
    close.type = 'button';
    close.addEventListener('click', hideInfo);
    infoEl.append(close);
    infoEl.hidden = false;
  }
  function hideInfo() {
    infoEl.hidden = true;
    infoEl.replaceChildren();
  }
  window.addEventListener('keydown', (e) => { if (e.key === 'Escape' && !infoEl.hidden) hideInfo(); });

  // ---------------- O'lcham va kamera ----------------
  // Panellar egallagan joy (px): sahna bo'sh joy markazida, o'sha joyga sig'adigan qilib
  const insets = { l: 0, r: 0, t: 0, b: 0 };
  let fitDist = 22;
  function resize() {
    const w = container.clientWidth;
    const h = container.clientHeight;
    if (!w || !h) return;
    renderer.setSize(w, h);
    camera.aspect = w / h;
    const freeW = Math.max(w - insets.l - insets.r, w * 0.35);
    const freeH = Math.max(h - insets.t - insets.b, h * 0.35);
    const tan = Math.tan(THREE.MathUtils.degToRad(camera.fov / 2));
    fitDist = Math.max((HALF_WIDTH * h) / (tan * freeW), (HALF_HEIGHT * h) / (tan * freeH), 12);
    scene.fog.near = fitDist * 0.9;
    scene.fog.far = fitDist * 2.8;
    const ox = -(insets.l - insets.r) / 2;
    const oy = (insets.b - insets.t) / 2;
    if (ox || oy) camera.setViewOffset(w, h, ox, oy, w, h);
    else camera.clearViewOffset();
    camera.updateProjectionMatrix();
  }
  new ResizeObserver(resize).observe(container);
  resize();

  const mouse = { x: 0, y: 0, tx: 0, ty: 0 };
  if (!reduceMotion) {
    window.addEventListener('pointermove', (e) => {
      mouse.tx = (e.clientX / window.innerWidth - 0.5) * 2;
      mouse.ty = (e.clientY / window.innerHeight - 0.5) * 2;
    });
    gsap.from(camBase, { dist: 18, lift: 8, duration: 2.6, ease: 'power3.out' });
  }

  // Boshlanish holati: faqat aylanuvchi Yer shari
  map.scale.setScalar(0.001);
  map.visible = false;
  showZone('warehouse', false, true);
  showZone('tools', false, true);
  showZone('bars', false, true);
  Object.assign(cam, { x: MODE_CAM.idle[0], y: MODE_CAM.idle[1], z: MODE_CAM.idle[2], zoom: MODE_CAM.idle[3] });

  const clock = new THREE.Clock();
  let paused = false;
  renderer.setAnimationLoop(() => {
    if (paused) return;
    const dt = Math.min(clock.getDelta(), 0.05);
    const t = clock.elapsedTime;
    if (!reduceMotion) {
      coreMat.uniforms.uTime.value = t;
      floorMat.uniforms.uTime.value = t;
      agentGroup.position.y = AGENT_Y + Math.sin(t * 1.2) * 0.05;
      map.rotation.y = -0.15 + Math.sin(t * 0.35) * 0.22;
      if (globeState.spin) globeSpin.rotation.y += dt * 0.25;
      if (scanning) {
        scanRings.forEach((r, i) => r.material.color.setHSL((t * 0.45 + i * 0.13) % 1, 0.9, 0.6));
        edgeMat.color.setHSL((t * 0.45) % 1, 0.9, 0.7);
        edgeHaloMat.color.setHSL((t * 0.45 + 0.1) % 1, 0.9, 0.55);
        let i = 0;
        for (const [name, n] of nodes) {
          i++;
          if (name === activeTool) continue;
          n.mesh.material.emissive.setHSL((t * 0.45 + i / 6) % 1, 0.9, 0.5);
          n.glow.material.color.copy(n.mesh.material.emissive);
        }
      }
      ring.rotation.y += dt * 0.12 * spin.v * boost.agent;
      warehouse.twinkle(t);
      floorRings.forEach((r, i) => { r.rotation.y += dt * (i % 2 ? -0.1 : 0.15); });
      for (const d of spinners) d.rotation.y += dt * d.userData.speed * spin.v * boost[d.userData.zone];
      focusBeam.rotation.y += dt * 0.6;
      const dp = dust.geometry.attributes.position;
      for (let i = 0; i < dp.count; i++) {
        let y = dp.getY(i) + dt * 0.12;
        if (y > 8) y = 0;
        dp.setY(i, y);
      }
      dp.needsUpdate = true;
      mouse.x += (mouse.tx - mouse.x) * 0.04;
      mouse.y += (mouse.ty - mouse.y) * 0.04;
    }
    // intro: camBase.dist 18 -> 22; cam.zoom < 1 — fokusdagi qismga yaqinlashish
    const dist = (fitDist + camBase.dist - 22) * cam.zoom;
    camera.position.set(
      cam.x + mouse.x * 0.8,
      cam.y + dist * 0.36 + 0.8 + camBase.lift - mouse.y * 0.4,
      cam.z + dist,
    );
    camera.lookAt(cam.x, cam.y, cam.z);
    if (focusOn) {
      const fp = focusOn();
      const k = reduceMotion ? 1 : 0.12;
      focus.position.x += (fp.x - focus.position.x) * k;
      focus.position.z += (fp.z - focus.position.z) * k;
      if (!reduceMotion) {
        const sz = focusSize * (1 + Math.sin(t * 4) * 0.04);
        focusRing.scale.x += (sz - focusRing.scale.x) * 0.15;
        focusRing.scale.y += (sz - focusRing.scale.y) * 0.15;
      } else {
        focusRing.scale.set(focusSize, focusSize, 1);
      }
      focusBeam.scale.set(focusRing.scale.x, 1, focusRing.scale.x);
    }
    updateBeams(t);
    for (const wv of waves) wv.quaternion.copy(camera.quaternion);
    renderer.render(scene, camera);
    updateLabels();
  });

  return {
    // Panellar o'lchami (px): chap, o'ng, tepa, past
    setInsets(l, r, t, b) {
      Object.assign(insets, { l, r, t, b });
      resize();
    },

    // 'idle' — faqat xarita; 'compose' — xarita kattalashadi, ombor va toollar chiqadi;
    // 'active' — savol yuborildi: natija joyi ham ochiladi
    setMode(m, instant = false) {
      if (m === mode && !instant) return;
      const prev = mode;
      mode = m;
      // Ombor, toollar va natija — faqat qidiruv bosilgandan keyin
      showZone('warehouse', m === 'active', instant);
      showZone('tools', m === 'active', instant);
      showZone('bars', m === 'active', instant);
      const fast = instant || reduceMotion;
      gsap.killTweensOf([globeState, map.scale, globeSpin.rotation, globe.scale]);
      if (m === 'idle') {
        // Xarita yo'qoladi, globus qaytib aylana boshlaydi
        globeState.spin = true;
        if (fast) { map.scale.setScalar(0.001); map.visible = false; globeState.fade = 1; globe.scale.setScalar(1); applyGlobeFade(); }
        else {
          gsap.to(map.scale, { x: 0.001, y: 0.001, z: 0.001, duration: 0.5, ease: 'power2.in', onComplete: () => { if (mode === 'idle') map.visible = false; } });
          gsap.to(globe.scale, { x: 1, y: 1, z: 1, duration: 0.9, ease: 'power2.out' });
          gsap.to(globeState, { fade: 1, duration: 0.8, delay: 0.2, onUpdate: applyGlobeFade });
        }
      } else if (prev === 'idle' || instant) {
        // Globus O'zbekistonga buriladi, kattalashib "ichiga kiriladi", xarita ochiladi
        globeState.spin = false;
        map.visible = true;
        if (fast) { globeState.fade = 0; applyGlobeFade(); map.scale.setScalar(1.25); }
        else {
          const cur = globeSpin.rotation.y;
          const want = THREE.MathUtils.degToRad(-64);
          const turn = want + Math.round((cur - want) / (Math.PI * 2)) * Math.PI * 2;
          gsap.to(globeSpin.rotation, { y: turn, x: THREE.MathUtils.degToRad(41), duration: 0.8, ease: 'power2.inOut' });
          gsap.to(globe.scale, { x: 2.4, y: 2.4, z: 2.4, duration: 0.8, delay: 0.6, ease: 'power2.in' });
          gsap.to(globeState, { fade: 0, duration: 0.55, delay: 0.85, onUpdate: applyGlobeFade });
          gsap.fromTo(map.scale, { x: 0.3, y: 0.3, z: 0.3 }, { x: 1.25, y: 1.25, z: 1.25, duration: 0.9, delay: 0.9, ease: 'back.out(1.4)' });
        }
      }
      if (!focusOn) flyTo(null);
    },

    // To'liq ekrandagi javob yopilganda — umumiy ko'rinishga qaytish
    overview() {
      setFocus(null);
    },

    // Monitor ekranining sahifadagi joyi (px) — javob kartasi shu yerdan kattalashib chiqadi
    monitorRect() {
      if (!barsZone.visible) return null;
      const box = container.getBoundingClientRect();
      const w = container.clientWidth, h = container.clientHeight;
      let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
      for (const c of bars.screenCorners()) {
        const v = bars.group.localToWorld(c).project(camera);
        const x = ((v.x + 1) / 2) * w + box.left;
        const y = ((1 - v.y) / 2) * h + box.top;
        x0 = Math.min(x0, x); y0 = Math.min(y0, y); x1 = Math.max(x1, x); y1 = Math.max(y1, y);
      }
      return { left: x0, top: y0, width: x1 - x0, height: y1 - y0 };
    },

    // Barcha sahna qadamlari tugaganda bajariladi (javob kartasi shundan keyin chiqadi)
    whenIdle() {
      return new Promise((res) => {
        if (!queueBusy && !queue.length) res();
        else idleWaiters.push(res);
      });
    },

    // Tool yorlig'i bosilganda chaqiriladi: fn(toolNomi, tugma)
    setToolClickHandler(fn) { onToolClick = fn; },

    // Bosqich holati (askView har bir haqiqiy voqeada chaqiradi)
    stage(id, state) {
      if (id === 'parse' && state === 'active') {
        step(() => { setScanning(true); setFocus('agent'); pulse(0.6); shockwave(agentPos(), BLUE, 2.6); floorWave(); }, 800);
      }
      if (id === 'search' && state === 'active') {
        // Katalogdan qidirish: kamera agentda qoladi (omborga faqat bir marta — o'qishda boriladi)
        step(() => { pulse(0.4); gsap.to(floorMat.uniforms.uWhGlow, { value: 0.6, duration: 0.4 }); }, 0);
      }
      if (id === 'dwh' && state === 'done') {
        // Tool ombordan o'qidi: ombor -> tool nuri
        step(() => {
          setFocus('warehouse');
          gsap.fromTo(floorMat.uniforms.uWhGlow, { value: 1 }, { value: 0.15, duration: 1.6 });
          warehouse.wave();
          gsap.fromTo(whLight, { intensity: 6 }, { intensity: 22, duration: 0.35, yoyo: true, repeat: 3 });
          createBeam(whPos, () => (activeTool && toolPos(activeTool)) || agentPos(), GREEN, 2.2);
        }, 800);
      }
      if (id === 'generate' && state === 'active') {
        // Kamera natija (monitor)da qoladi — javob shu yerdan chiqadi; agent faqat pulslaydi
        step(() => { gsap.to(spin, { v: 2.4, duration: 0.8 }); pulse(0.5); }, 0);
      }
      if (id === 'verify' && state === 'active') {
        step(() => { pulse(0.4); }, 0);
      }
      if (id === 'all') {
        step(() => {
          setScanning(false);
          ensureMap();
          gsap.to(spin, { v: 1, duration: 1.2 });
          gsap.to(floorMat.uniforms.uWhGlow, { value: 0, duration: 1.2 });
          if (state === 'error') {
            setFocus(null);
            coreMat.uniforms.uColA.value.set(RED);
            edgeMat.color.set(RED);
            shockwave(agentPos(), RED, 3.6);
          } else {
            // Kamera monitor ekraniga sho'ng'iydi (avval sekin, keyin tez);
            // shundan keyin javob shu ekrandan butun ekranga ochiladi
            pulse(1);
            setFocus(null);
            diveToMonitor();
          }
        }, state === 'error' ? 0 : 800);
      }
    },

    // tool.called: agentdan toolga nur, tool yonadi (orbitada aylanishda davom etadi)
    highlightTool(name) {
      const n = nodes.get(name);
      if (!n) return;
      step(() => {
        activeTool = name;
        n.mesh.material.color.set(AMBER);
        n.mesh.material.emissive.set(AMBER);
        gsap.to(n.mesh.material, { emissiveIntensity: 2.6, duration: 0.5 });
        n.glow.material.color.set(AMBER);
        gsap.to(n.glow.material, { opacity: 1, duration: 0.5 });
        gsap.to(n.glow.scale, { x: 2.4, y: 2.4, duration: 0.5 });
        if (!reduceMotion) {
          gsap.fromTo(n.mesh.scale, { x: 1, y: 1, z: 1 }, { x: 1.5, y: 1.5, z: 1.5, duration: 0.6, ease: 'back.out(2.5)' });
        }
        n.label.setAttribute('aria-pressed', 'true');
        n.label.dataset.called = 'true';
        n.label.title = 'Shu savolda chaqirildi';
        setFocus('tool');
        pulse(0.7);
        createBeam(agentPos, () => toolPos(name), BLUE, 0.8);
      }, 800);
    },

    // /api/stats natijasi (null bo'lsa — backend bermadi)
    setStats(stats) {
      removeLabels('shelf');
      if (!stats) {
        warehouse.build(null);
        warehouseTitle.textContent = 'Ombor (DWH): mavjud emas';
        return;
      }
      const blocks = warehouse.build(stats);
      warehouseTitle.textContent = `Ombor (DWH) · ${formatNumber(stats.total_indicators)} ko‘rsatkich`;
      if (blocks.length > 1) {
        for (const b of blocks) {
          const anchor = new THREE.Object3D();
          anchor.position.copy(b.center);
          warehouse.group.add(anchor);
          addLabel(anchor, el('span', `${b.section} · ${formatNumber(b.count)}`, 'scene-title small'), { kind: 'shelf' });
        }
      }
    },

    // search.completed: tanlangan ko'rsatkich qutisini yondirish
    selectIndicator(id) {
      step(() => {
        const found = warehouse.highlight(id);
        warehouseTitle.dataset.selected = found ? 'true' : 'false';
        const base = warehouseTitle.textContent.split(' → ')[0];
        warehouseTitle.textContent = `${base} → #${id}`;
      }, 0);
    },

    // tool.result: tool -> agent (raqamlar agentga qaytadi), keyin agent -> natija ustunlari
    showBars(rows, { unit = '', sourceUrl = '' } = {}) {
      // Raqamlar tooldan agentga qaytadi (kamera agentda — toolga qayta bormaymiz)
      step(() => {
        setFocus('agent');
        const from = () => (activeTool && toolPos(activeTool)) || agentPos();
        createBeam(from, agentPos, AMBER, 0.6);
        setTimeout(() => pulse(0.8), reduceMotion ? 0 : 300);
      }, 300);
      step(() => {
        removeLabels('bar');
        hideInfo();
        const items = bars.build(rows, { unit });
        barsTitle.textContent = items.length
          ? `Natija · ${items[0].row.item_name ?? items[0].row.item_code} · ${items.length} davr · past = arzon`
          : 'Natija: mavjud emas';
        let maxY = 1.5;
        for (const it of items) {
          maxY = Math.max(maxY, it.top.y);
          const anchor = new THREE.Object3D();
          anchor.position.copy(it.top);
          bars.group.add(anchor);
          const btn = el('button', '', 'bar-label');
          btn.type = 'button';
          btn.setAttribute('aria-label', `${it.row.period_key}: ${formatNumber(it.row.value)} ${unit}`);
          btn.title = `${it.row.period_key}: ${formatNumber(it.row.value)}`;
          btn.addEventListener('click', () => { bars.select(it); showInfo(it.row, unit, sourceUrl); });
          btn.addEventListener('focus', () => bars.select(it));
          addLabel(anchor, btn, { kind: 'bar' });
        }
        setFocus('bars');
        if (items.length) {
          // Nur monitor ramkasining yuqori chetiga tegadi va yo'qoladi — ekranni kesib o'tmaydi
          barsZone.updateMatrixWorld(true);
          barsTop = bars.group.localToWorld(bars.edgeTop());
          createBeam(agentPos, barsPos, AMBER, 1.2, { fadeOut: true });
          if (!reduceMotion) {
            items.forEach((it, i) => {
              if (it.mesh) gsap.from(it.mesh.scale, { y: 0.001, duration: 0.6, delay: 0.3 + i * 0.04, ease: 'power3.out' });
            });
          }
          shockwave(barsTop, AMBER, 2.4);
        }
      }, 800);
    },

    // Yangi savol — hammasini boshlang'ich holatga qaytarish
    // To'liq ekrandagi javob butun sahnani yopganda chizish to'xtaydi; yopilganda davom etadi
    setPaused(on) {
      paused = on;
      if (!on) clock.getDelta();
    },

    // Qolgan barcha sahna qadamlarini darhol bajaradi (holat to'g'ri qoladi, faqat kutish yo'q)
    skip() {
      fastMode = true;
      clearTimeout(queueTimer);
      while (queue.length) queue.shift()[0]();
      queueBusy = false;
      wakeIdle();
    },

    reset() {
      clearQueue();
      fastMode = false;
      ensureMap();
      setScanning(false);
      clearBeams();
      setFocus(null);
      activeTool = null;
      gsap.to(spin, { v: 1, duration: 0.8 });
      coreMat.uniforms.uColA.value.set(BLUE);
      edgeMat.color.set(0x9fe4ff);
      for (const { mesh, label, glow } of nodes.values()) {
        gsap.killTweensOf([mesh.material, glow.material, glow.scale, mesh.scale]);
        mesh.material.color.set(NODE_IDLE);
        mesh.material.emissive.set(BLUE);
        mesh.material.emissiveIntensity = 0.35;
        mesh.scale.set(1, 1, 1);
        glow.material.color.set(BLUE);
        glow.material.opacity = 0.35;
        glow.scale.set(0.9, 0.9, 1);
        label.setAttribute('aria-pressed', 'false');
        delete label.dataset.called;
        label.title = 'Bu tool hali chaqirilmagan';
      }
      warehouse.resetHighlight();
      warehouseTitle.textContent = warehouseTitle.textContent.split(' → ')[0];
      delete warehouseTitle.dataset.selected;
      removeLabels('bar');
      bars.clear();
      barsTitle.textContent = 'Natija: hali yo‘q';
      hideInfo();
    },
  };
}
