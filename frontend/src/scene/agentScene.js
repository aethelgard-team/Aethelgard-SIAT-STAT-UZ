// 3D sahna: chapda "Ombor" (DWH), markazda "Agent" + 6 ta MCP tool, o'ngda 3D grafik.
// Hamma narsa faqat backenddan kelgan haqiqiy voqea bilan o'zgaradi.
// Har bir yorliq va bosiladigan joy — 3D nuqtaga bog'langan HTML tugma
// (sichqoncha ham, klaviatura ham ishlaydi).
import * as THREE from 'three';
import { gsap } from 'gsap';
import { TOOLS } from '../core/stages.js';
import { formatNumber, el } from '../core/format.js';
import { createWarehouse } from './warehouse.js';
import { createBars } from './bars3d.js';

export function hasWebGL() {
  try {
    const c = document.createElement('canvas');
    return !!(window.WebGLRenderingContext && (c.getContext('webgl2') || c.getContext('webgl')));
  } catch {
    return false;
  }
}

const NODE_IDLE = 0x3a3f55;
const NODE_HOT = 0xffb347;
const HALF_WIDTH = 10.5; // sahna kengligining yarmi (kamera shunga moslanadi)
const SIDE_X = 7;       // ombor va grafik markazdan shuncha uzoqda

export function createAgentScene(container, labelsEl, infoEl) {
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    || new URLSearchParams(location.search).get('quality') === 'low';

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 200);
  const target = new THREE.Vector3(0, 1.8, 0);

  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  container.append(renderer.domElement);

  scene.add(new THREE.AmbientLight(0xffffff, 0.7));
  const light = new THREE.DirectionalLight(0xffffff, 1.6);
  light.position.set(4, 10, 8);
  scene.add(light);

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
      const visible = tmp.z < 1 && Math.abs(tmp.x) <= 1.05 && Math.abs(tmp.y) <= 1.05;
      l.node.hidden = !visible;
      if (visible) {
        l.node.style.transform = `translate(${((tmp.x + 1) / 2) * w}px, ${((1 - tmp.y) / 2) * h}px) translate(-50%, -100%)`;
      }
    }
  }

  // ---------------- Markaz: Agent + 6 ta tool ----------------
  const agentGroup = new THREE.Group();
  scene.add(agentGroup);
  const agent = new THREE.Mesh(
    new THREE.IcosahedronGeometry(1, 1),
    new THREE.MeshStandardMaterial({ color: 0x6c8cff, flatShading: true }),
  );
  agent.position.y = 1.2;
  agentGroup.add(agent);
  addLabel(agent, el('span', 'Agent', 'scene-title'), { offset: 1.5 });

  const ring = new THREE.Group();
  ring.position.y = 1.2;
  agentGroup.add(ring);
  const nodes = new Map(); // tool nomi -> { mesh, label }
  TOOLS.forEach((name, i) => {
    const angle = (i / TOOLS.length) * Math.PI * 2;
    const mesh = new THREE.Mesh(
      new THREE.SphereGeometry(0.32, 24, 16),
      new THREE.MeshStandardMaterial({ color: NODE_IDLE, emissive: 0x000000 }),
    );
    mesh.position.set(Math.cos(angle) * 3.2, 0, Math.sin(angle) * 3.2);
    ring.add(mesh);
    ring.add(new THREE.Line(
      new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(), mesh.position]),
      new THREE.LineBasicMaterial({ color: NODE_IDLE }),
    ));
    const label = el('button', name);
    label.type = 'button';
    label.setAttribute('aria-pressed', 'false');
    label.title = 'Bu tool hali chaqirilmagan';
    addLabel(mesh, label, { offset: 0.45 });
    nodes.set(name, { mesh, label });
  });

  // ---------------- Chap: Ombor (DWH) ----------------
  const warehouse = createWarehouse();
  warehouse.group.position.set(-SIDE_X, 0, 0);
  scene.add(warehouse.group);
  const warehouseAnchor = new THREE.Object3D();
  warehouseAnchor.position.set(-SIDE_X, 3.6, 0);
  scene.add(warehouseAnchor);
  const warehouseTitle = addLabel(warehouseAnchor, el('span', 'Ombor (DWH): yuklanmoqda…', 'scene-title'));

  // ---------------- O'ng: 3D grafik ----------------
  const bars = createBars();
  bars.group.position.set(SIDE_X, 0, 0);
  scene.add(bars.group);
  const barsAnchor = new THREE.Object3D();
  barsAnchor.position.set(SIDE_X, 5.2, 0);
  scene.add(barsAnchor);
  const barsTitle = addLabel(barsAnchor, el('span', 'Natija: hali yo‘q', 'scene-title'));

  // ---------------- Zarrachalar: Agent -> tool ----------------
  const particleGeo = new THREE.SphereGeometry(0.06, 8, 6);
  function sendParticles(mesh) {
    if (reduceMotion) return;
    for (let i = 0; i < 14; i++) {
      const p = new THREE.Mesh(particleGeo, new THREE.MeshBasicMaterial({ color: NODE_HOT }));
      ring.add(p);
      gsap.to(p.position, {
        x: mesh.position.x, y: mesh.position.y, z: mesh.position.z,
        duration: 0.9, delay: i * 0.06, ease: 'power1.inOut',
        onComplete: () => { ring.remove(p); p.material.dispose(); },
      });
    }
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
    const close = el('button', 'Yopish');
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
  function resize() {
    const w = container.clientWidth;
    const h = container.clientHeight;
    if (!w || !h) return;
    renderer.setSize(w, h);
    camera.aspect = w / h;
    // Butun sahna (ombor + agent + grafik) kenglikka sig'sin
    const dist = HALF_WIDTH / (Math.tan(THREE.MathUtils.degToRad(camera.fov / 2)) * camera.aspect);
    camera.position.set(0, dist * 0.22 + 2.5, Math.max(dist, 9));
    camera.lookAt(target);
    camera.updateProjectionMatrix();
  }
  new ResizeObserver(resize).observe(container);
  resize();

  renderer.setAnimationLoop(() => {
    if (!reduceMotion) {
      ring.rotation.y += 0.002;
      agent.rotation.y -= 0.004;
    }
    renderer.render(scene, camera);
    updateLabels();
  });

  return {
    // tool.called voqeasi kelganda
    highlightTool(name) {
      const n = nodes.get(name);
      if (!n) return;
      n.mesh.material.emissive.set(NODE_HOT);
      n.label.setAttribute('aria-pressed', 'true');
      n.label.dataset.called = 'true';
      n.label.title = 'Shu savolda chaqirildi';
      sendParticles(n.mesh);
      if (!reduceMotion) {
        gsap.fromTo(n.mesh.scale, { x: 1, y: 1, z: 1 }, { x: 1.4, y: 1.4, z: 1.4, yoyo: true, repeat: 1, duration: 0.3 });
      }
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
      warehouseTitle.textContent = `Ombor (DWH): ${formatNumber(stats.total_indicators)} ko‘rsatkich`;
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
      const found = warehouse.highlight(id);
      warehouseTitle.dataset.selected = found ? 'true' : 'false';
      const base = warehouseTitle.textContent.split(' → ')[0];
      warehouseTitle.textContent = `${base} → #${id}`;
    },

    // tool.result: 3D ustunlar
    showBars(rows, { unit = '', sourceUrl = '' } = {}) {
      removeLabels('bar');
      hideInfo();
      const items = bars.build(rows);
      barsTitle.textContent = items.length
        ? `Natija: ${items[0].row.item_name ?? items[0].row.item_code} (${items.length} davr)`
        : 'Natija: mavjud emas';
      for (const it of items) {
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
    },

    // Yangi savol — hammasini boshlang'ich holatga qaytarish
    reset() {
      for (const { mesh, label } of nodes.values()) {
        mesh.material.emissive.set(0x000000);
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
