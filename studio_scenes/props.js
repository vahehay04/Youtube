// props.js — flat, bright toddler props. Every prop is drawn with its BOTTOM-CENTRE at (0,0),
// about 200 logical px tall at s = 1. drawProp(g, kind, x, y, s, t, opts).
import { circle, ring, seg, poly, rr, text, alpha } from '/engine/core.js';

const C = { red: '#ff5a5a', orange: '#ff9a3d', yellow: '#ffd23a', green: '#5fd39a', blue: '#3a8bff', purple: '#b48cff', pink: '#ff8ad0', brown: '#b07a4a', white: '#ffffff', black: '#3a2e4a' };
export const COLORS = C;
const col = (o, d) => C[o.color] || o.color || d;
const INK = '#3a2e4a';

function eye(g, x, y, r = 7) { circle(g, x, y, r, INK); circle(g, x + r * 0.3, y - r * 0.3, r * 0.35, '#fff'); }

const P = {
  ball(g, t, o) { const r = 90; circle(g, 0, -r, r, col(o, C.red)); g.save(); g.translate(0, -r); g.rotate(t * 2);
    g.strokeStyle = '#fff'; g.lineWidth = 14; g.beginPath(); g.arc(0, 0, 56, -0.6, 0.9); g.stroke(); g.beginPath(); g.arc(0, 0, 56, 2.5, 4.0); g.stroke(); g.restore();
    circle(g, -30, -r - 34, 16, 'rgba(255,255,255,.6)'); },
  car(g, t, o) { const c = col(o, C.blue); rr(g, -120, -96, 240, 70, 28); g.fillStyle = c; g.fill(); rr(g, -66, -150, 132, 66, 24); g.fillStyle = c; g.fill();
    rr(g, -50, -138, 44, 40, 10); g.fillStyle = '#d8f1ff'; g.fill(); rr(g, 6, -138, 44, 40, 10); g.fill();
    for (const dx of [-66, 66]) { circle(g, dx, -26, 30, INK); circle(g, dx, -26, 12, '#ddd'); } circle(g, 110, -70, 9, '#ffe08a'); },
  bus(g, t, o) { rr(g, -150, -190, 300, 165, 26); g.fillStyle = col(o, C.yellow); g.fill(); for (let i = 0; i < 4; i++) { rr(g, -130 + i * 66, -170, 52, 50, 8); g.fillStyle = '#d8f1ff'; g.fill(); }
    g.fillStyle = INK; g.fillRect(-150, -100, 300, 10); for (const dx of [-90, 90]) { circle(g, dx, -26, 30, INK); circle(g, dx, -26, 12, '#ddd'); } },
  boat(g, t, o) { g.save(); g.rotate(Math.sin(t * 2) * 0.05); poly(g, [[-140, -80], [140, -80], [100, 0], [-100, 0]], col(o, C.red)); seg(g, [[0, -80], [0, -260]], 8, INK); poly(g, [[6, -250], [110, -110], [6, -110]], '#fff'); g.restore(); },
  train(g, t, o) { rr(g, -150, -130, 200, 105, 16); g.fillStyle = col(o, C.green); g.fill(); rr(g, 30, -200, 90, 175, 16); g.fillStyle = C.red; g.fill(); rr(g, -120, -230, 40, 100, 8); g.fillStyle = INK; g.fill();
    rr(g, 46, -186, 58, 50, 8); g.fillStyle = '#d8f1ff'; g.fill(); for (const dx of [-110, -40, 70]) { circle(g, dx, -26, 28, INK); circle(g, dx, -26, 10, '#ddd'); } },
  duck(g, t, o) { g.save(); g.rotate(Math.sin(t * 5) * 0.06); g.fillStyle = col(o, C.yellow); g.beginPath(); g.ellipse(0, -60, 100, 60, 0, 0, Math.PI * 2); g.fill();
    circle(g, 60, -130, 52, col(o, C.yellow)); poly(g, [[100, -136], [150, -122], [100, -110]], C.orange); eye(g, 72, -142, 9); g.restore(); },
  chick(g, t, o) { circle(g, 0, -70, 70, col(o, C.yellow)); circle(g, 0, -150, 50, col(o, C.yellow)); poly(g, [[40, -150], [74, -140], [40, -130]], C.orange); eye(g, 18, -160);
    seg(g, [[-20, 0], [-20, -10]], 8, C.orange); seg(g, [[20, 0], [20, -10]], 8, C.orange); },
  cow(g, t, o) { rr(g, -130, -190, 220, 130, 50); g.fillStyle = '#fff'; g.fill(); circle(g, -60, -150, 30, INK); circle(g, 20, -110, 26, INK);
    for (const dx of [-100, -40, 30, 70]) { rr(g, dx - 12, -80, 24, 80, 10); g.fillStyle = '#fff'; g.fill(); }
    rr(g, 70, -250, 110, 110, 44); g.fillStyle = '#fff'; g.fill(); rr(g, 92, -180, 92, 48, 22); g.fillStyle = '#ffb3c7'; g.fill(); eye(g, 108, -220); eye(g, 150, -220);
    poly(g, [[78, -250], [62, -282], [96, -252]], '#f2d38a'); poly(g, [[168, -250], [184, -282], [150, -252]], '#f2d38a'); },
  pig(g, t, o) { rr(g, -120, -170, 210, 120, 56); g.fillStyle = '#ffb3c7'; g.fill(); for (const dx of [-90, -40, 20, 60]) { rr(g, dx - 12, -70, 24, 70, 10); g.fillStyle = '#ffb3c7'; g.fill(); }
    circle(g, 100, -150, 64, '#ffb3c7'); rr(g, 120, -150, 60, 40, 18); g.fillStyle = '#ff8aa8'; g.fill(); circle(g, 140, -130, 6, INK); circle(g, 160, -130, 6, INK); eye(g, 90, -178); eye(g, 128, -178);
    poly(g, [[60, -200], [70, -236], [90, -206]], '#ff8aa8'); },
  sheep(g, t, o) { for (const [dx, dy, r] of [[-80, -110, 50], [-20, -130, 58], [40, -110, 52], [-40, -80, 46], [20, -80, 46]]) circle(g, dx, dy, r, '#ffffff');
    for (const dx of [-60, 30]) seg(g, [[dx, -40], [dx, 0]], 14, INK); circle(g, 100, -140, 42, INK); eye(g, 112, -150, 7); },
  fish(g, t, o) { const c = col(o, C.orange); g.save(); g.translate(0, -100); g.rotate(Math.sin(t * 3) * 0.08); g.fillStyle = c; g.beginPath(); g.ellipse(0, 0, 110, 66, 0, 0, Math.PI * 2); g.fill();
    poly(g, [[-90, 0], [-170, -60], [-170, 60]], c); eye(g, 54, -14, 11); g.restore(); },
  crab(g, t, o) { const c = col(o, C.red); g.fillStyle = c; g.beginPath(); g.ellipse(0, -70, 110, 64, 0, 0, Math.PI * 2); g.fill();
    for (const d of [-1, 1]) { seg(g, [[d * 90, -90], [d * 150, -150]], 16, c); circle(g, d * 160, -165, 30, c); for (let k = 0; k < 3; k++) seg(g, [[d * 70, -40 - k * 18], [d * 130, -10 - k * 22]], 10, c);
      seg(g, [[d * 30, -120], [d * 34, -160]], 8, c); eye(g, d * 34, -168, 10); } },
  octopus(g, t, o) { const c = col(o, C.purple); circle(g, 0, -150, 90, c); for (let k = 0; k < 6; k++) { const x = -80 + k * 32; seg(g, [[x, -90], [x + Math.sin(t * 3 + k) * 16, -40], [x + 10, 0]], 22, c); }
    eye(g, -30, -160, 12); eye(g, 30, -160, 12); },
  kite(g, t, o) { const c = col(o, C.blue); g.save(); g.translate(0, -320); g.rotate(Math.sin(t * 2.2) * 0.12);
    poly(g, [[0, -110], [70, 0], [0, 130], [-70, 0]], c); poly(g, [[0, -110], [70, 0], [0, 0]], alpha('#ffffff', 0.35)); seg(g, [[0, -110], [0, 130]], 4, '#fff'); seg(g, [[-70, 0], [70, 0]], 4, '#fff'); g.restore();
    const pts = []; for (let i = 0; i <= 8; i++) pts.push([i * 12 + Math.sin(t * 4 + i * 0.8) * 16, -190 + i * 24]); seg(g, pts, 3, '#fff'); },
  balloon(g, t, o) { g.strokeStyle = 'rgba(255,255,255,.9)'; g.lineWidth = 3; g.beginPath(); g.moveTo(0, -170); g.quadraticCurveTo(14, -90, 0, 0); g.stroke();
    g.fillStyle = col(o, C.red); g.beginPath(); g.ellipse(0, -240, 62, 78, 0, 0, Math.PI * 2); g.fill(); g.fillStyle = 'rgba(255,255,255,.45)'; g.beginPath(); g.ellipse(-22, -268, 12, 20, -0.4, 0, Math.PI * 2); g.fill(); },
  blocks(g, t, o) { const B = [[-80, 0, C.red, 'A'], [0, 0, C.yellow, 'B'], [80, 0, C.green, 'C'], [-40, -78, C.blue, '1'], [40, -78, C.purple, '2']];
    for (const [dx, dy, c, l] of B) { rr(g, dx - 38, dy - 76, 76, 76, 12); g.fillStyle = c; g.fill(); text(g, l, dx, dy - 38, { size: 46, color: '#fff' }); } },
  teddy(g, t, o) { const c = col(o, C.brown); circle(g, 0, -70, 70, c); circle(g, 0, -170, 56, c); circle(g, -44, -214, 22, c); circle(g, 44, -214, 22, c); circle(g, 0, -150, 22, '#e8c39a'); eye(g, -18, -180); eye(g, 18, -180); circle(g, 0, -158, 7, INK); },
  apple(g, t, o) { const c = col(o, C.red); circle(g, -34, -90, 80, c); circle(g, 34, -90, 80, c); seg(g, [[0, -168], [8, -210]], 10, C.brown); g.fillStyle = C.green; g.beginPath(); g.ellipse(36, -200, 34, 16, -0.4, 0, Math.PI * 2); g.fill(); circle(g, -60, -120, 16, 'rgba(255,255,255,.5)'); },
  banana(g, t, o) { g.strokeStyle = col(o, C.yellow); g.lineWidth = 60; g.lineCap = 'round'; g.beginPath(); g.arc(0, -220, 180, 0.55 * Math.PI, 0.95 * Math.PI, false); g.stroke(); circle(g, -168, -168, 10, C.brown); },
  carrot(g, t, o) { poly(g, [[-46, -200], [46, -200], [0, 0]], col(o, C.orange)); for (const dx of [-24, 0, 24]) seg(g, [[dx * 0.5, -200], [dx, -250]], 14, C.green); },
  strawberry(g, t, o) { g.fillStyle = col(o, C.red); g.beginPath(); g.moveTo(0, 0); g.bezierCurveTo(-130, -110, -80, -200, 0, -190); g.bezierCurveTo(80, -200, 130, -110, 0, 0); g.fill();
    for (let i = 0; i < 8; i++) circle(g, -40 + (i % 4) * 26, -150 + Math.floor(i / 4) * 50, 5, '#ffe08a'); poly(g, [[-40, -192], [0, -230], [40, -192], [0, -176]], C.green); },
  star(g, t, o) { const pts = []; for (let k = 0; k < 10; k++) { const r = k % 2 ? 46 : 110, a = -Math.PI / 2 + k * Math.PI / 5; pts.push([Math.cos(a) * r, -110 + Math.sin(a) * r]); } poly(g, pts, col(o, C.yellow)); },
  heart(g, t, o) { g.save(); g.translate(0, -100); g.scale(3, 3); g.fillStyle = col(o, '#ff6b8a'); g.beginPath(); g.moveTo(0, 22); g.bezierCurveTo(-40, -6, -22, -40, 0, -18); g.bezierCurveTo(22, -40, 40, -6, 0, 22); g.fill(); g.restore(); },
  circle(g, t, o) { circle(g, 0, -100, 100, col(o, C.blue)); },
  square(g, t, o) { rr(g, -95, -190, 190, 190, 18); g.fillStyle = col(o, C.green); g.fill(); },
  triangle(g, t, o) { poly(g, [[0, -200], [110, 0], [-110, 0]], col(o, C.orange)); },
  number(g, t, o) { text(g, String(o.n ?? 1), 0, -110, { size: 240, color: col(o, C.purple), stroke: 18, strokeColor: '#fff' }); },
  letter(g, t, o) { rr(g, -100, -200, 200, 200, 30); g.fillStyle = col(o, C.blue); g.fill(); text(g, String(o.letter || 'A'), 0, -100, { size: 150, color: '#fff' }); },
  toothbrush(g, t, o) { g.save(); g.rotate(-0.5); rr(g, -18, -260, 36, 260, 18); g.fillStyle = col(o, C.blue); g.fill(); rr(g, -26, -330, 52, 80, 12); g.fillStyle = '#fff'; g.fill();
    for (let i = 0; i < 4; i++) seg(g, [[-30, -320 + i * 20], [-60, -320 + i * 20]], 8, '#bfe8ff'); g.restore(); },
  soap(g, t, o) { rr(g, -100, -90, 200, 90, 30); g.fillStyle = col(o, C.pink); g.fill(); for (let i = 0; i < 6; i++) { const y = -130 - ((t * 60 + i * 50) % 260); ring(g, -60 + i * 24 + Math.sin(t * 2 + i) * 14, y, 14 + (i % 3) * 6, 4, 'rgba(160,220,255,.9)'); } },
  umbrella(g, t, o) { const c = col(o, C.red); g.fillStyle = c; g.beginPath(); g.arc(0, -220, 150, Math.PI, 0); g.fill(); seg(g, [[0, -220], [0, -20]], 10, INK); g.strokeStyle = INK; g.lineWidth = 10; g.beginPath(); g.arc(-20, -20, 20, 0, Math.PI); g.stroke(); },
  flower(g, t, o) { seg(g, [[0, 0], [0, -150]], 12, '#4aa83a'); for (let k = 0; k < 6; k++) { const a = k * Math.PI / 3 + t * 0.5; circle(g, Math.cos(a) * 48, -170 + Math.sin(a) * 48, 36, col(o, C.pink)); } circle(g, 0, -170, 32, C.yellow); },
  cake(g, t, o) { rr(g, -130, -150, 260, 150, 20); g.fillStyle = col(o, C.pink); g.fill(); rr(g, -130, -150, 260, 40, 20); g.fillStyle = '#fff'; g.fill(); seg(g, [[0, -150], [0, -220]], 14, C.blue); circle(g, 0, -236, 14 + Math.sin(t * 12) * 2, C.yellow); },
  moon(g, t, o) { circle(g, 0, -120, 110, '#fff2b0'); circle(g, 50, -150, 96, 'rgba(30,40,90,1)'); },
  sun(g, t, o) { for (let k = 0; k < 10; k++) { const a = k * Math.PI / 5 + t * 0.4; seg(g, [[Math.cos(a) * 120, -120 + Math.sin(a) * 120], [Math.cos(a) * 160, -120 + Math.sin(a) * 160]], 16, C.orange); } circle(g, 0, -120, 100, C.yellow); eye(g, -34, -134, 10); eye(g, 34, -134, 10); },
  snowflake(g, t, o) { g.save(); g.translate(0, -120); g.rotate(t * 0.6); for (let k = 0; k < 6; k++) { g.rotate(Math.PI / 3); seg(g, [[0, 0], [0, -110]], 14, '#bfe8ff'); seg(g, [[0, -60], [30, -90]], 10, '#bfe8ff'); seg(g, [[0, -60], [-30, -90]], 10, '#bfe8ff'); } g.restore(); },
  cloud(g, t, o) { for (const [dx, dy, r] of [[-70, -80, 60], [0, -110, 80], [74, -80, 62], [0, -60, 60]]) circle(g, dx, dy, r, col(o, '#ffffff')); },
  bed(g, t, o) { rr(g, -170, -110, 340, 110, 16); g.fillStyle = col(o, C.purple); g.fill(); rr(g, -190, -200, 30, 200, 10); g.fillStyle = C.brown; g.fill(); rr(g, -150, -150, 90, 50, 20); g.fillStyle = '#fff'; g.fill(); },
};
export const PROP_KINDS = Object.keys(P);

// drawProp(g, kind, x, y, s, t, {color, n, letter, pop}) — pop 0..1 scales in from the ground
export function drawProp(g, kind, x, y, s, t, o = {}) {
  const f = P[kind]; if (!f) return; const k = o.pop ?? 1; if (k <= 0) return;
  g.save(); g.translate(x, y); g.scale(s * k, s * k);
  g.save(); g.globalAlpha *= 0.18; g.fillStyle = '#2a4a1a'; g.beginPath(); g.ellipse(0, 6, 110, 16, 0, 0, Math.PI * 2); g.fill(); g.restore();
  f(g, t, o); g.restore();
}
export const FLYING = new Set(['kite', 'balloon', 'star', 'moon', 'sun', 'cloud', 'snowflake']);
