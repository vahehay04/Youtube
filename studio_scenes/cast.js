// cast.js — Pip, Lulu & Bo as sprites, beat sync, effects, kinetic titles and lyric lines.
// Everything is a pure function of time (frames render in any order).
import { E, clamp, rng, circle, seg, poly, rr, text, alpha, measure } from '/engine/core.js';
import { spring, squashAt, kText } from '/engine/motion.js';

// ---------- data prepared by agent/studio.py ----------
export const LINES = await (await fetch('/project/timeline/sentences.json')).json();
export const BEAT = await (await fetch('/project/timeline/beat.json')).json();   // {bpm, t0}

// ---------- sprites ----------
const NAMES = ['pip', 'lulu', 'bo'], POSES = ['standing', 'waving', 'dancing', 'jumping'];
export const IMG = {};
await Promise.all(NAMES.flatMap(n => POSES.map(p => new Promise(res => {
  const im = new Image(); im.onload = res; im.onerror = res; im.src = `/project/assets/${n}_${p}.png`; IMG[`${n}_${p}`] = im;
}))));
export const SIZE = { pip: 1.0, lulu: 1.1, bo: 0.8 };

// ---------- beat ----------
const SPB = 60 / (BEAT.bpm || 110), B0 = BEAT.t0 || 0;
export const beatPhase = (gt) => (((gt - B0) / SPB) % 1 + 1) % 1;
export const onBeat = (gt) => Math.pow(1 - beatPhase(gt), 3);
const MOVE = { standing: [10, 0.025], waving: [16, 0.05], dancing: [34, 0.09], jumping: [70, 0.04] };

// hero(g, {name, pose, x, y (feet), h, t, gt, enter, facing, phase, hop, a})
export function hero(g, o) {
  const { name, pose = 'standing', x, y, h = 700, t = 0, gt = 0, enter = null, facing = 1, phase = 0, a = 1, hop = 1 } = o;
  const im = IMG[`${name}_${pose}`] || IMG[`${name}_standing`]; if (!im || !im.width) return;
  const H = h * (SIZE[name] || 1), W = H * im.width / im.height;
  const [amp, sway] = MOVE[pose] || MOVE.standing;
  const bp = beatPhase(gt + phase * SPB), A = amp * (H / 1000) * hop;
  const up = Math.sin(bp * Math.PI) * A, land = Math.pow(1 - clamp(bp / 0.18), 2) * 0.07 * hop;
  const rot = Math.sin((gt + phase) * Math.PI / SPB) * sway;
  let s = 1, dy = 0;
  if (enter != null) { if (t < enter) return; const sp = spring(t, enter, { freq: 2.4, damp: 0.42 }); s = Math.max(0, sp); dy = (1 - Math.min(1, sp)) * H * 0.35; }
  g.save(); g.globalAlpha = a * 0.22 * s * (1 - 0.4 * (A ? up / A : 0));
  g.fillStyle = '#2a4a1a'; g.beginPath(); g.ellipse(x, y + 4, W * 0.36, H * 0.035, 0, 0, Math.PI * 2); g.fill(); g.restore();
  g.save(); g.globalAlpha *= a;
  squashAt(g, x, y, land - (s < 1 ? (1 - s) * 0.2 : 0), g2 => { g2.translate(x, y - up + dy); g2.rotate(rot); g2.scale(s * facing, s); g2.drawImage(im, -W / 2, -H, W, H); });
  g.restore();
}

// ---------- effects ----------
export function heart(g, x, y, r, col = '#ff6b8a', a = 1) { g.save(); g.globalAlpha *= a; g.translate(x, y); g.scale(r / 30, r / 30); g.fillStyle = col; g.beginPath(); g.moveTo(0, 22); g.bezierCurveTo(-40, -6, -22, -40, 0, -18); g.bezierCurveTo(22, -40, 40, -6, 0, 22); g.fill(); g.restore(); }
function note(g, x, y, s, col = '#ffffff', a = 1) { g.save(); g.globalAlpha *= a; g.translate(x, y); g.scale(s, s); g.fillStyle = col; g.beginPath(); g.ellipse(0, 0, 16, 12, -0.4, 0, Math.PI * 2); g.fill(); g.fillRect(12, -64, 6, 62); g.fillRect(12, -64, 30, 10); g.restore(); }
function sparkle(g, x, y, s, col, a) { g.save(); g.globalAlpha *= a; g.translate(x, y); g.scale(s, s); poly(g, [[0, -30], [8, -8], [30, 0], [8, 8], [0, 30], [-8, 8], [-30, 0], [-8, -8]], col); g.restore(); }
function bubble(g, x, y, r, a) { g.save(); g.globalAlpha *= a; g.strokeStyle = 'rgba(160,220,255,.95)'; g.lineWidth = 5; g.beginPath(); g.arc(x, y, r, 0, Math.PI * 2); g.stroke(); circle(g, x - r * 0.35, y - r * 0.35, r * 0.18, 'rgba(255,255,255,.8)'); g.restore(); }
export function butterfly(g, x, y, s, t, col = '#ff8ad0') {
  const f = Math.abs(Math.sin(t * 14)) * 0.8 + 0.2; g.save(); g.translate(x, y); g.scale(s, s);
  for (const d of [-1, 1]) { g.save(); g.scale(d * f, 1); g.fillStyle = col; g.beginPath(); g.ellipse(22, -10, 24, 18, 0.4, 0, Math.PI * 2); g.fill(); g.fillStyle = alpha(col, 0.8); g.beginPath(); g.ellipse(18, 14, 15, 12, -0.4, 0, Math.PI * 2); g.fill(); g.restore(); }
  seg(g, [[0, -22], [0, 22]], 6, '#3a2e4a'); g.restore();
}
const PAL = ['#ff6b6b', '#ffc94a', '#5fd39a', '#3a8bff', '#b48cff', '#ff8ad0'];
export function fx(g, t, kind, seed = 7) {
  const r = rng(seed);
  if (kind === 'confetti') { for (let i = 0; i < 80; i++) { const x0 = r() * E.W, sp = 260 + r() * 260, ph = r() * 3, lt = t - r() * 0.6; if (lt < 0) continue; const y = -60 + lt * sp; if (y > E.H + 60) continue;
      g.save(); g.translate(x0 + Math.sin(lt * 3 + ph) * 40, y); g.rotate(lt * 6 + ph); g.fillStyle = PAL[i % 6]; g.fillRect(-9, -5, 18, 10); g.restore(); } return; }
  if (kind === 'butterflies') { for (let i = 0; i < 4; i++) butterfly(g, E.W * (0.15 + i * 0.24) + Math.sin(t * 1.3 + i) * 60, E.H * 0.42 + Math.cos(t * 1.7 + i * 2) * 120, 1, t + i, PAL[(i + 4) % 6]); return; }
  if (kind === 'balloons') { for (let i = 0; i < 9; i++) { const x = E.W * (0.08 + i * 0.105) + Math.sin(t + i) * 20, y = E.H * 0.95 - t * (190 + (i % 3) * 50) - (i % 2) * 140;
      g.strokeStyle = 'rgba(255,255,255,.8)'; g.lineWidth = 3; g.beginPath(); g.moveTo(x, y + 60); g.quadraticCurveTo(x + 15, y + 130, x, y + 200); g.stroke(); g.fillStyle = PAL[i % 6]; g.beginPath(); g.ellipse(x, y, 46, 58, 0, 0, Math.PI * 2); g.fill(); } return; }
  // rising things
  for (let i = 0; i < 12; i++) {
    const st = r() * 1.6, lt = t - st; const rx = r(), rs = r(); if (lt < 0) continue; const p = (lt % 2.4) / 2.4, a = Math.sin(p * Math.PI);
    const x = rx * E.W + Math.sin(lt * 2 + i) * 30, y = E.H * 0.72 - p * 640;
    if (kind === 'hearts') heart(g, x, y, 22 + rs * 18, PAL[[0, 5, 0][i % 3]], a);
    else if (kind === 'notes') note(g, x, y, 0.8 + rs * 0.5, '#ffffff', a);
    else if (kind === 'stars') sparkle(g, x, y, 0.8 + rs * 0.6, '#fff2a0', a);
    else if (kind === 'bubbles') bubble(g, x, y, 18 + rs * 26, a);
  }
}

// ---------- kinetic title (two lines max) ----------
export function title(g, t, str, o = {}) {
  if (!str) return; const words = String(str).toUpperCase().split(/\s+/);
  let lines = [words.join(' ')]; if (lines[0].length > 11 && words.length > 1) { const h = Math.ceil(words.length / 2); lines = [words.slice(0, h).join(' '), words.slice(h).join(' ')]; }
  const cols = o.colors || ['#ffffff', '#ffd23a'];
  lines.forEach((ln, i) => {
    const size0 = i === 0 && lines.length > 1 ? 130 : 150, sz = size0 * Math.min(1, (E.W * 0.9) / (measure(g, ln, size0) + ln.length * 6));
    g.save(); g.shadowColor = 'rgba(58,46,74,.9)'; g.shadowBlur = 4; g.shadowOffsetY = 9;
    kText(g, t, ln, E.W / 2, (o.y ?? 330) + i * 165, { start: (o.start ?? 0.15) + i * 0.35, mode: i === lines.length - 1 && lines.length > 1 ? 'slam' : (o.mode || 'drop'), size: sz, color: cols[i % cols.length], spacing: 6, stagger: 0.04 });
    g.restore();
  });
}

// ---------- lyric line captions ----------
export function lyric(g, gt) {
  const L = LINES; if (!L || !L.length) return;
  let i = -1; for (let k = 0; k < L.length; k++) if (gt >= L[k].start - 0.1 && gt < (L[k + 1] ? L[k + 1].start - 0.1 : L[k].end + 1.2)) i = k;
  if (i < 0) return; const ln = L[i], str = ln.text;
  const pop = spring(gt, ln.start - 0.1, { freq: 3, damp: 0.5 }), size = 60, sz = size * Math.min(1, (E.W * 0.84) / measure(g, str, size));
  const w = measure(g, str, sz) + 70, h = sz * 1.7, y = E.H - 300;
  g.save(); g.translate(E.W / 2, y); g.scale(0.85 + 0.15 * pop, 0.85 + 0.15 * pop); g.globalAlpha *= clamp(pop * 1.5);
  rr(g, -w / 2, -h / 2, w, h, h / 2); g.fillStyle = 'rgba(255,255,255,.92)'; g.fill(); g.lineWidth = 6; g.strokeStyle = 'rgba(58,46,74,.12)'; g.stroke();
  text(g, str, 0, 3, { size: sz, color: '#3a2e4a', weight: 700 }); g.restore();
}
