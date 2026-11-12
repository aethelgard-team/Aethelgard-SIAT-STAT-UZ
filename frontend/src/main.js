import './style.css';
import { checkHealth, getStats } from './api/client.js';
import { createAgentScene, hasWebGL } from './scene/agentScene.js';
import { initAskView } from './ui/askView.js';
import { initCatalogView, showIndicator } from './ui/catalogView.js';

// 3D sahna — WebGL bo'lmasa 2D ro'yxat yetarli
let scene = null;
if (hasWebGL()) {
  scene = createAgentScene(
    document.querySelector('#scene'),
    document.querySelector('#scene-labels'),
    document.querySelector('#scene-info'),
  );
} else {
  document.querySelector('#scene-fallback').hidden = false;
}

initAskView({ scene });
const catalog = initCatalogView();

// Backend va baza ishlayaptimi?
const statusEl = document.querySelector('#backend-status');
checkHealth().then(({ backend, database }) => {
  statusEl.textContent = !backend ? 'Backend: mavjud emas'
    : database ? 'Backend: ulangan' : 'Backend: ulangan, baza yo‘q';
  statusEl.dataset.ok = String(backend && database);

  // Ombor: qutilar soni = bazadagi haqiqiy ko'rsatkichlar soni
  if (backend && database) {
    getStats().then((s) => scene?.setStats(s)).catch(() => scene?.setStats(null));
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
