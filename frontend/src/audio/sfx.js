// Ovoz effektlari: har bir jarayonga mos qisqa, tinch va jiddiy ovoz (o'yinga o'xshamasin).
// Faqat sinus, sekin kirish/chiqish, 1,6 kHz dan baland tovushlar kesilgan; keskin tovush yo'q.
// Tayyor audio fayl yo'q — hammasi Web Audio bilan shu yerda sintez qilinadi (litsenziya muammosi yo'q).
// Qoidalar:
//  - ovoz faqat foydalanuvchi birinchi marta bosgandan/yozgandan keyin (brauzer talabi);
//  - boshida OVOZSIZ; bitta 🔊/🔇 tugmasi bilan yoqiladi, tanlov eslab qolinadi (localStorage); ?mute=1 — ovozsiz;
//  - sahna ovozni o'zi chalmaydi, faqat "nom" bilan so'raydi: sfx.play('tool').

const KEY = 'aethelgard.mute';
let ctx = null;
let master = null;
// Boshida ovozsiz: foydalanuvchi o'zi 🔊 bilan yoqadi, tanlovi eslab qolinadi
let muted = (() => {
  if (new URLSearchParams(location.search).get('mute') === '1') return true;
  try { return localStorage.getItem(KEY) !== '0'; } catch { return true; }
})();

function ensureCtx() {
  if (ctx) return ctx;
  const AC = window.AudioContext || window.webkitAudioContext;
  if (!AC) return null;
  ctx = new AC();
  const comp = ctx.createDynamicsCompressor();
  comp.threshold.value = -18;
  comp.ratio.value = 4;
  master = ctx.createGain();
  master.gain.value = 0.3;
  // Iliq, "jiddiy" tembr: 2,5 kHz dan baland tovushlar yumshatiladi
  const warm = ctx.createBiquadFilter();
  warm.type = 'lowpass';
  warm.frequency.value = 1600;
  warm.Q.value = 0.5;
  master.connect(warm).connect(comp).connect(ctx.destination);
  return ctx;
}

// Birinchi bosish/yozishda ovoz tizimini "uyg'otamiz"
function unlock() {
  const c = ensureCtx();
  if (c && c.state === 'suspended') c.resume();
}
for (const ev of ['pointerdown', 'keydown']) window.addEventListener(ev, unlock, { capture: true, passive: true });

// ---------- Kichik "asboblar" ----------
function tone({ f = 440, f2 = null, dur = 0.3, type = 'sine', gain = 0.3, attack = 0.01, delay = 0 }) {
  const t0 = ctx.currentTime + delay;
  const o = ctx.createOscillator();
  const g = ctx.createGain();
  o.type = type;
  o.frequency.setValueAtTime(f, t0);
  if (f2) o.frequency.exponentialRampToValueAtTime(f2, t0 + dur);
  g.gain.setValueAtTime(0.0001, t0);
  g.gain.exponentialRampToValueAtTime(gain, t0 + attack);
  g.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);
  o.connect(g).connect(master);
  o.start(t0);
  o.stop(t0 + dur + 0.05);
}

let noiseBuf = null;
function noise({ dur = 0.6, from = 300, to = 1500, q = 1.2, gain = 0.25, delay = 0 }) {
  if (!noiseBuf) {
    noiseBuf = ctx.createBuffer(1, ctx.sampleRate * 2, ctx.sampleRate);
    const d = noiseBuf.getChannelData(0);
    for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
  }
  const t0 = ctx.currentTime + delay;
  const src = ctx.createBufferSource();
  src.buffer = noiseBuf;
  const bp = ctx.createBiquadFilter();
  bp.type = 'bandpass';
  bp.Q.value = q;
  bp.frequency.setValueAtTime(from, t0);
  bp.frequency.exponentialRampToValueAtTime(to, t0 + dur);
  const g = ctx.createGain();
  g.gain.setValueAtTime(0.0001, t0);
  g.gain.exponentialRampToValueAtTime(gain, t0 + dur * 0.35);
  g.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);
  src.connect(bp).connect(g).connect(master);
  src.start(t0);
  src.stop(t0 + dur + 0.05);
}


// ---------- Jarayon ovozlari: juda kam va juda yumshoq ----------
// Har bir tovush sekin kiradi (attack >= 0,1 s) va sekin so'nadi — keskin "tiq" yo'q.
// Qisqa, ketma-ket tovushlar (tool, chiziq, yopish, akkord) ataylab ovozsiz.
const SOUNDS = {
  // Globus O'zbekistonga yaqinlashadi — juda past havo oqimi
  compose() {
    noise({ dur: 1.2, from: 160, to: 420, q: 0.6, gain: 0.045 });
  },
  // Savol qabul qilindi — bitta past, sekin kiruvchi nota
  start() {
    tone({ f: 261.63, dur: 1.0, gain: 0.05, attack: 0.15 });
  },
  tool() {},
  // Ombordan o'qish — past, bo'g'iq g'uvillash
  warehouse() {
    tone({ f: 73.4, dur: 1.0, gain: 0.06, attack: 0.25 });
  },
  beam() {},
  digits() {},
  // Natija tayyor — ikki yumshoq nota
  settle() {
    tone({ f: 329.63, dur: 1.1, gain: 0.045, attack: 0.12 });
    tone({ f: 392.0, dur: 1.3, gain: 0.035, attack: 0.15, delay: 0.18 });
  },
  // Monitorga sho'ng'ish — juda past havo oqimi
  dive() {
    noise({ dur: 0.9, from: 180, to: 480, q: 0.6, gain: 0.04 });
  },
  open() {},
  close() {},
  // Xato — bitta past, sekin nota
  error() {
    tone({ f: 196, dur: 1.0, gain: 0.05, attack: 0.15 });
  },
};

export const sfx = {
  play(name, ...args) {
    if (muted || !SOUNDS[name]) return;
    const c = ensureCtx();
    if (!c || c.state !== 'running') return; // hali bosilmagan — jim
    try { SOUNDS[name](...args); } catch { /* ovoz bo'lmasa ham sayt ishlayveradi */ }
  },
  isMuted: () => muted,
  setMuted(on) {
    muted = on;
    try { localStorage.setItem(KEY, on ? '1' : '0'); } catch { /* eslab qolinmasa ham ishlaydi */ }
  },
};

// Tepadagi 🔊/🔇 tugmasi
export function initSoundToggle(btn) {
  if (!btn) return;
  const render = () => {
    const m = sfx.isMuted();
    btn.replaceChildren(
      Object.assign(document.createElement('span'), { textContent: m ? '🔇' : '🔊', ariaHidden: 'true' }),
      Object.assign(document.createElement('span'), { textContent: m ? 'Ovoz o‘chiq' : 'Ovoz yoqiq', className: 'sound-label' }),
    );
    btn.setAttribute('aria-pressed', String(!m));
    btn.setAttribute('aria-label', m ? 'Ovozni yoqish' : 'Ovozni o‘chirish');
    btn.title = m ? 'Ovoz o‘chiq' : 'Ovoz yoqiq';
  };
  btn.addEventListener('click', () => {
    sfx.setMuted(!sfx.isMuted());
    render();
    if (!sfx.isMuted()) { unlock(); sfx.play('start'); }
  });
  render();
}
