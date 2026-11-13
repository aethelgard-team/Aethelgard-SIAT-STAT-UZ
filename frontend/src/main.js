import './style.css';
import { checkHealth, getStats } from './api/client.js';
import { createAgentScene, hasWebGL } from './scene/agentScene.js';
import { createScene2D } from './scene/scene2d.js';
import { initAskView } from './ui/askView.js';
import { createInspector } from './ui/inspector.js';
import { initCatalogView, showIndicator } from './ui/catalogView.js';
import { isDemoMode, loadDemo } from './api/demo.js';
import { formatNumber } from './core/format.js';

// Sahna butun ekranda; panellar egallagan joyni hisobga olib, kamerani
// bo'sh joy markaziga suramiz (chap panel, o'ng panel, pastdagi natija).
function watchInsets(sc) {
  const left = document.querySelector('.panel-left');
  const right = document.querySelector('.panel-right');
  const result = document.querySelector('#result');
  const top = document.querySelector('.topbar');
  const update = () => {
    if (result?.classList.contains('full')) return;
    const W = window.innerWidth;
    const H = window.innerHeight;
    if (W <= 900 || !document.body.classList.contains('route-ask')) { sc.setInsets(0, 0, 0, 0); return; }
    const box = (n) => (n && n.getClientRects().length ? n.getBoundingClientRect() : null);
    const l = box(left), r = box(right), b = box(result), t = box(top);
    sc.setInsets(
      l ? l.right : 0,
      r ? W - r.left : 0,
      t ? t.bottom : 0,
      b ? Math.min(H - b.top, H * 0.5) : 0,
    );
  };
  const ro = new ResizeObserver(update);
  for (const n of [left, right, result, top]) if (n) ro.observe(n);
  window.addEventListener('resize', update);
  window.addEventListener('hashchange', () => requestAnimationFrame(update));
  update();
}

const params = new URLSearchParams(location.search);

// Sahna: WebGL bo'lsa 3D, bo'lmasa (yoki ?mode=2d) — 2D zaxira.
// Kam harakat (prefers-reduced-motion, ?quality=low) 3D ichida hal qilinadi.
let scene;
const want2D = params.get('mode') === '2d';
if (!want2D && hasWebGL()) {
  scene = createAgentScene(
    document.querySelector('#scene'),
    document.querySelector('#scene-labels'),
    document.querySelector('#scene-info'),
  );
  watchInsets(scene);
} else {
  document.body.classList.add('is-2d');
  scene = createScene2D(document.querySelector('#scene-fallback'), {
    reason: want2D ? '2D rejim (?mode=2d).' : 'WebGL ishlamayapti — 2D ko‘rinish.',
  });
}

const inspector = createInspector(document.querySelector('#inspector'));

// Demo rejim: doimiy banner, backendga savol yuborilmaydi
let demo = null;
if (isDemoMode()) {
  const rec = await loadDemo();
  demo = { rec };
  const banner = document.querySelector('#demo-banner');
  banner.textContent = rec
    ? `DEMO — yozib olingan haqiqiy javob (${rec.recorded_at?.slice(0, 10) ?? 'sana noma’lum'}). Jonli backend ishlatilmayapti.`
    : 'DEMO — yozuv topilmadi (public/demo/demo.json). Jonli rejim: ?demo ni olib tashlang.';
  banner.hidden = false;
  banner.title = banner.textContent;
  document.body.classList.add('has-demo');
}

initAskView({ scene, inspector, demo });
const catalog = initCatalogView();

// Backend va baza ishlayaptimi?
const statusEl = document.querySelector('#backend-status');
checkHealth().then(({ backend, database }) => {
  statusEl.textContent = !backend ? 'Backend: mavjud emas'
    : database ? 'Backend: ulangan' : 'Backend: ulangan, baza yo‘q';
  statusEl.dataset.ok = String(backend && database);

  // Ombor: qutilar soni = bazadagi haqiqiy ko'rsatkichlar soni
  if (backend && database) {
    getStats().then((s) => {
      scene?.setStats(s);
      document.querySelector('#k-indicators').textContent = formatNumber(s?.total_indicators);
    }).catch(() => scene?.setStats(null));
  } else {
    scene?.setStats(null);
  }
});

// Oddiy router: #/ask, #/catalog, #/indicator/1308
const views = {
  ask: document.querySelector('#view-ask'),
  catalog: document.querySelector('#view-catalog'),
  indicator: document.querySelector('#view-indicator'),
};

function route() {
  const [, page = 'ask', id] = location.hash.split('/');
  const name = views[page] ? page : 'ask';
  for (const [key, node] of Object.entries(views)) node.hidden = key !== name;
  document.body.classList.toggle('route-ask', name === 'ask');
  for (const link of document.querySelectorAll('.tabs a')) {
    const active = link.getAttribute('href') === `#/${name === 'indicator' ? 'catalog' : name}`;
    if (active) link.setAttribute('aria-current', 'page');
    else link.removeAttribute('aria-current');
  }
  if (name === 'catalog') catalog.show();
  if (name === 'indicator' && id) showIndicator(id);
}
window.addEventListener('hashchange', route);
route();
