// shots/gen.js — one generic renderer for every shot, driven by shot.params from story/shots.json:
//   { type: title|group|solo|duo|close|pass|sky|end, set, cast:[{name,pose}], props:[{kind,color,n,letter}],
//     title, colors, fx: hearts|notes|stars|bubbles|confetti|butterflies|balloons|null, cam: push|pull|panL|panR|down|up|still }
import { E, registerShot, layer, ease, prog, lerp } from '/engine/core.js';
import { camPath, spring, drift, camAdd } from '/engine/motion.js';
import { world } from '../sets/world.js';
import { hero, heart, fx, title, lyric } from '../cast.js';
import { drawProp, FLYING } from '../props.js';

const W = E.W;
const ROW = { 1: [0.5], 2: [0.3, 0.7], 3: [0.2, 0.5, 0.8] };
const pop = (t, t0) => Math.max(0, spring(t, t0, { freq: 3, damp: 0.4 }));

function camera(kind, t, dur, seed) {
  const k = {
    push: [[0, { z: 1.0 }], [dur, { z: 1.09 }]], pull: [[0, { z: 1.12 }], [dur, { z: 1.0 }]],
    panL: [[0, { z: 1.06, x: 50 }], [dur, { z: 1.06, x: -50 }]], panR: [[0, { z: 1.06, x: -50 }], [dur, { z: 1.06, x: 50 }]],
    down: [[0, { y: -520, z: 1.12 }], [Math.min(2.2, dur * 0.7), { y: -60, z: 1.0 }], [dur, { y: 0, z: 1.03 }]],
    up: [[0, { y: 0 }], [dur, { y: -380 }]], still: [[0, { z: 1.02 }], [dur, { z: 1.03 }]],
  }[kind] || [[0, { z: 1.0 }], [dur, { z: 1.06 }]];
  return camAdd(camPath(t, k), drift(t, 5, seed));
}

function render(g, t, info) {
  const p = info.shot.params || {}, dur = info.dur, gt = info.shot.start + t, seed = info.shot.seed || 1;
  const cast = (p.cast && p.cast.length ? p.cast : [{ name: 'pip', pose: 'standing' }]).slice(0, 3);
  const props = (p.props || []).slice(0, 3);
  const cam = camera(p.cam || (p.type === 'title' ? 'down' : p.type === 'sky' ? 'up' : 'push'), t, dur, seed);
  const { gy } = world(g, t, cam, p.set || 'playground');
  if (p.fx === 'balloons') fx(g, t, 'balloons', seed);   // behind the heroes
  const ph = [0, 0.5, 0.25];

  layer(g, cam, 1, g => {
    const type = p.type || 'group';
    if (type === 'title' || type === 'group' || type === 'pass' || type === 'end') {
      const n = cast.length, xs = ROW[n], h = type === 'title' ? 470 : { 1: 860, 2: 720, 3: 600 }[n];
      cast.forEach((c, i) => hero(g, { ...c, x: W * xs[i], y: gy + (i === 1 ? 30 : 0), h, t, gt, phase: ph[i], enter: type === 'title' ? 0.6 + i * 0.2 : null }));
      const passQ = props.find(q => !FLYING.has(q.kind) && q.kind !== 'number');
      if (type === 'pass' && passQ && n > 1) {
        const seg = Math.min(n - 2, Math.floor(t / 0.9)), u = prog(t - seg * 0.9, 0, 0.9), a = xs[seg], b = xs[seg + 1];
        drawProp(g, passQ.kind, lerp(W * a, W * b, u), gy - 330 - Math.sin(u * Math.PI) * 300 + 90, 0.45, t * 4, passQ);
      } else if (type === 'group' || type === 'end') {
        const many = props.find(q => (q.n || 1) > 1 && q.kind !== 'number');
        if (many) { const n = Math.min(5, many.n); for (let i = 0; i < n; i++) { const u = n === 1 ? 0.5 : i / (n - 1); drawProp(g, many.kind, W * (0.16 + 0.68 * u), gy - 820 - Math.sin(u * Math.PI) * 140, 0.48, t, { ...many, pop: pop(t, 0.4 + i * 0.35) }); } }
        const big = props.find(q => q.kind === 'number'); if (big) drawProp(g, 'number', W / 2, gy - 520, 0.9, t, { ...big, pop: pop(t, 0.5) });
        const ground = props.filter(q => !FLYING.has(q.kind) && q !== many && q !== big), fly = props.filter(q => FLYING.has(q.kind));
        const gx = ground.length === 1 ? [0.5] : ground.length === 2 ? [0.35, 0.65] : [0.27, 0.5, 0.73];
        ground.forEach((q, i) => drawProp(g, q.kind, W * gx[i], gy + 25, 0.5, t, { ...q, pop: pop(t, 0.6 + i * 0.3) }));
        fly.forEach((q, i) => drawProp(g, q.kind, W * (0.3 + i * 0.4), gy - 820 + Math.sin(t * 1.5 + i) * 30, 0.7, t, { ...q, pop: pop(t, 0.4 + i * 0.3) }));
      }
      if (type === 'end') heart(g, W / 2, 230, 70 * pop(t, 0.2), '#ff6b8a');
    } else if (type === 'solo') {
      const c = cast[0], q = props[0];
      hero(g, { ...c, x: W * (q ? 0.36 : 0.5), y: gy + 70, h: 900, t, gt });
      if (q) {
        const n = Math.max(1, Math.min(5, q.n || 1));
        if (q.kind !== 'number' && n > 1) { // counting: n copies pop in one by one in an arc above
          for (let i = 0; i < n; i++) { const u = n === 1 ? 0.5 : i / (n - 1), x = W * (0.16 + 0.68 * u), y = gy - 760 - Math.sin(u * Math.PI) * 140; drawProp(g, q.kind, x, y, 0.5, t, { ...q, pop: pop(t, 0.4 + i * 0.4) }); }
        } else if (FLYING.has(q.kind)) drawProp(g, q.kind, W * 0.74, gy - 420 + Math.sin(t * 1.6) * 30, 0.9, t, { ...q, pop: pop(t, 0.4) });
        else drawProp(g, q.kind, W * 0.77, gy - 20, q.kind === 'number' ? 1.1 : 0.8, t, { ...q, pop: pop(t, 0.45) });
      }
    } else if (type === 'duo') {
      const [a, b] = [cast[0], cast[1] || cast[0]];
      hero(g, { ...a, x: W * 0.3, y: gy + 200, h: 900, t, gt });
      hero(g, { ...b, x: W * 0.72, y: gy + 200, h: 900, t, gt, phase: 0.5, facing: -1 });
    } else if (type === 'close') {
      hero(g, { ...cast[0], x: W * 0.5, y: gy + 380, h: 1250, t, gt, hop: 0.5 });
    } else if (type === 'sky') {
      const c = cast[0], q = props[0] || { kind: 'balloon' }, u = ease.inOut(t / dur);
      hero(g, { ...c, x: W * 0.3, y: gy + 60, h: 720, t, gt });
      const kx = W * 0.66 + Math.sin(t * 1.5) * 40, ky = lerp(gy - 380, gy - 860, u);
      if (q.kind === 'kite') { g.strokeStyle = 'rgba(255,255,255,.8)'; g.lineWidth = 3; g.beginPath(); g.moveTo(W * 0.38, gy - 560); g.quadraticCurveTo(W * 0.5, ky - 100, kx, ky - 190); g.stroke(); }
      drawProp(g, q.kind, kx, ky, 1.2, t, q);
    }
  });

  if (p.type === 'end') title(g, t, p.title || 'BYE BYE!', { y: 400, start: 0.3, colors: p.colors });
  else if (p.title) title(g, t, p.title, { start: 0.15, colors: p.colors });
  if (p.fx && p.fx !== 'balloons') fx(g, t, p.fx, seed);
  lyric(g, gt);
}

for (const s of E.shots) registerShot(s.id, { draw: render });
