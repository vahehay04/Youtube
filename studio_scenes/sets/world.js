// sets/world.js — the Bouncy Meadow world in several variants.
// variants: playground | sandbox | picnic | hill | farm | beach | night | rain | snow | home
import { E, layer, linGrad, circle, rr, poly, seg, rng, glow } from '/engine/core.js';

export const GY = () => E.H * 0.8;
const SKY = { day: ['#62b8ff', '#a8dcff', '#e6f6ff'], night: ['#1c2350', '#33407a', '#5a5aa0'], rain: ['#8a9ab8', '#b4c0d4', '#dfe5ee'], snow: ['#9cc8f0', '#cfe4f7', '#f2f8ff'] };

function cloud(g, x, y, s, c = '#ffffff') { for (const [dx, dy, r] of [[-60, 0, 48], [0, -24, 64], [64, 0, 50], [26, 14, 46], [-26, 16, 40]]) circle(g, x + dx * s, y + dy * s, r * s, c); }
function flower(g, x, y, s, c) { seg(g, [[x, y], [x, y - 40 * s]], 4 * s, '#4aa83a'); for (let k = 0; k < 5; k++) { const a = k * 1.2566; circle(g, x + Math.cos(a) * 11 * s, y - 40 * s + Math.sin(a) * 11 * s, 9 * s, c); } circle(g, x, y - 40 * s, 7 * s, '#ffd23a'); }
function bushTree(g, x, y, s, snow = false) { rr(g, x - 12 * s, y - 150 * s, 24 * s, 150 * s, 10 * s); g.fillStyle = '#a0704a'; g.fill(); for (const [dx, dy, r, c] of [[0, -200, 90, '#5cbf4a'], [-70, -150, 66, '#4fae3e'], [70, -150, 66, '#4fae3e'], [0, -140, 70, '#66c954']]) circle(g, x + dx * s, y + dy * s, r * s, snow ? '#ffffff' : c); }
function barn(g, x, y, s) { g.save(); g.translate(x, y); g.scale(s, s); g.fillStyle = '#e04a4a'; g.fillRect(-160, -260, 320, 260); poly(g, [[-190, -250], [0, -400], [190, -250]], '#b83434');
  g.fillStyle = '#fff'; g.fillRect(-60, -170, 120, 170); seg(g, [[-60, -170], [60, 0]], 10, '#fff'); seg(g, [[60, -170], [-60, 0]], 10, '#fff'); g.restore(); }

export function world(g, t, cam, variant = 'playground') {
  const gy = GY(), v = variant;
  const sky = v === 'night' ? SKY.night : v === 'rain' ? SKY.rain : v === 'snow' ? SKY.snow : SKY.day;
  if (v === 'home') return home(g, t, cam);
  layer(g, cam, 0.1, g => { g.fillStyle = linGrad(g, 0, -E.H, 0, gy, sky); g.fillRect(-E.W * 2, -E.H * 2, E.W * 5, E.H * 3);
    if (v === 'night') { const r = rng(5); for (let i = 0; i < 90; i++) { const x = -E.W * 0.5 + r() * E.W * 2, y = -E.H * 0.4 + r() * E.H * 0.9, tw = 0.5 + 0.5 * Math.sin(t * 3 + i); circle(g, x, y, 2 + r() * 3, `rgba(255,250,210,${0.4 + 0.6 * tw})`); } } });
  layer(g, cam, 0.15, g => {
    const sx = E.W * 0.86, sy = E.H * 0.07;
    if (v === 'night') { glow(g, sx, sy + 60, 260, '#fff2b0', 0.35); circle(g, sx, sy + 60, 90, '#fff2b0'); circle(g, sx + 40, sy + 34, 78, sky[0]); return; }
    if (v === 'rain') return;
    g.save(); g.translate(sx, sy); g.rotate(t * 0.15); for (let k = 0; k < 12; k++) { g.rotate(Math.PI / 6); g.fillStyle = 'rgba(255,236,150,.35)'; g.beginPath(); g.moveTo(0, -120); g.lineTo(26, -230); g.lineTo(-26, -230); g.fill(); } g.restore();
    glow(g, sx, sy, 260, '#fff2b0', 0.6); circle(g, sx, sy, 95, '#ffe066'); circle(g, sx, sy, 78, '#ffd23a');
  });
  layer(g, cam, 0.25, g => { const r = rng(4), cc = v === 'rain' ? '#e8ecf3' : v === 'night' ? 'rgba(255,255,255,.15)' : '#ffffff';
    for (let i = 0; i < (v === 'rain' ? 8 : 5); i++) { const x = ((r() * E.W * 1.6 + t * (18 + i * 6)) % (E.W * 1.8)) - E.W * 0.4; cloud(g, x, E.H * (0.06 + r() * 0.22), 0.8 + r() * 0.7, cc); } });
  if (v === 'beach') { // sea + sand
    layer(g, cam, 0.4, g => { g.fillStyle = linGrad(g, 0, gy - 420, 0, gy - 120, ['#3ab0ff', '#2a8ae0']); g.fillRect(-E.W * 2, gy - 420, E.W * 5, 330);
      g.fillStyle = 'rgba(255,255,255,.7)'; for (let i = 0; i < 12; i++) { const x = ((i * 220 + t * 40) % (E.W * 2)) - E.W * 0.5; g.fillRect(x, gy - 330 + (i % 3) * 70, 80, 8); } });
    layer(g, cam, 0.85, g => { g.fillStyle = linGrad(g, 0, gy - 130, 0, E.H * 1.4, ['#ffe7a8', '#f5cf7a']); g.fillRect(-E.W * 2, gy - 130, E.W * 5, E.H);
      g.fillStyle = 'rgba(255,255,255,.85)'; g.beginPath(); g.moveTo(-E.W, gy - 130); for (let x = -E.W; x <= E.W * 2; x += 30) g.lineTo(x, gy - 130 + Math.sin(x * 0.02 + t * 2) * 10); g.lineTo(E.W * 2, gy - 100); g.lineTo(-E.W, gy - 100); g.fill();
      const r = rng(3); for (let i = 0; i < 14; i++) circle(g, -E.W * 0.5 + r() * E.W * 2, gy - 60 + r() * 360, 6 + r() * 8, '#fff3d6'); });
    return { gy };
  }
  const night = v === 'night', snow = v === 'snow';
  const H1 = night ? '#3c5a6a' : snow ? '#eef5ff' : '#9fdc7a', H2 = night ? '#2f4a58' : snow ? '#e3eefb' : '#86cf5f', GR = night ? ['#2f5a48', '#244a3a'] : snow ? ['#ffffff', '#e6f0fb'] : ['#7cc95a', '#5fb345'];
  layer(g, cam, 0.4, g => { g.fillStyle = H1; g.beginPath(); g.moveTo(-E.W, gy); for (let x = -E.W; x <= E.W * 2; x += 40) g.lineTo(x, gy - 330 - Math.sin(x * 0.004) * 90 - Math.sin(x * 0.011) * 30); g.lineTo(E.W * 2, gy); g.fill();
    for (const [x, s] of [[-80, 0.9], [160, 0.7], [E.W - 120, 0.85], [E.W + 120, 0.8]]) bushTree(g, x, gy - 250, s * 0.8, snow); });
  layer(g, cam, 0.6, g => { g.fillStyle = H2; g.beginPath(); g.moveTo(-E.W, gy); for (let x = -E.W; x <= E.W * 2; x += 40) g.lineTo(x, gy - 150 - Math.sin(x * 0.006 + 1) * 60); g.lineTo(E.W * 2, gy); g.fill();
    if (v === 'farm') barn(g, E.W * 0.82, gy - 110, 0.9);
    else if (v !== 'hill') { bushTree(g, 70, gy - 90, 1.1, snow); bushTree(g, E.W - 60, gy - 110, 1.2, snow); } });
  layer(g, cam, 0.85, g => {
    g.fillStyle = linGrad(g, 0, gy - 120, 0, E.H * 1.5, GR); g.fillRect(-E.W * 2, gy - 120, E.W * 5, E.H);
    if (!snow) { const r = rng(9); for (let i = 0; i < 40; i++) flower(g, -E.W * 0.5 + r() * E.W * 2, gy - 90 + r() * 360, 0.7 + r() * 0.6, ['#ff8ad0', '#ffffff', '#ff6b6b', '#b48cff'][i % 4]); }
    if (v === 'sandbox') { rr(g, E.W * 0.06, gy - 70, E.W * 0.88, 210, 40); g.fillStyle = '#c98a4a'; g.fill(); rr(g, E.W * 0.06 + 22, gy - 52, E.W * 0.88 - 44, 170, 30); g.fillStyle = '#f7d98a'; g.fill(); }
    if (v === 'playground') { seg(g, [[E.W * 0.08, gy - 40], [E.W * 0.08, gy - 330]], 16, '#ff6b6b'); seg(g, [[E.W * 0.08, gy - 330], [E.W * 0.26, gy - 60]], 26, '#ffc94a');
      seg(g, [[E.W * 0.82, gy - 40], [E.W * 0.86, gy - 360], [E.W * 0.98, gy - 360], [E.W * 1.02, gy - 40]], 12, '#3a8bff'); }
    if (v === 'picnic') { g.save(); g.translate(E.W / 2, gy + 40); g.scale(1, 0.38); g.rotate(0.06); for (let i = -4; i < 4; i++) for (let j = -3; j < 3; j++) { g.fillStyle = (i + j) % 2 ? '#ff6b6b' : '#ffffff'; g.fillRect(i * 110, j * 110, 110, 110); } g.restore(); }
    if (v === 'farm') { for (let x = -E.W * 0.5; x < E.W * 1.5; x += 90) { rr(g, x, gy - 210, 18, 120, 6); g.fillStyle = '#f2e2c4'; g.fill(); } g.fillStyle = '#f2e2c4'; g.fillRect(-E.W, gy - 190, E.W * 3, 14); g.fillRect(-E.W, gy - 140, E.W * 3, 14); }
    if (v === 'rain') { for (let i = 0; i < 4; i++) { g.fillStyle = 'rgba(120,170,230,.45)'; g.beginPath(); g.ellipse(E.W * (0.15 + i * 0.25), gy + 120 + (i % 2) * 120, 120, 26, 0, 0, Math.PI * 2); g.fill(); } }
  });
  if (v === 'rain') { g.save(); g.strokeStyle = 'rgba(255,255,255,.6)'; g.lineWidth = 4; const r = rng(2); for (let i = 0; i < 120; i++) { const x = r() * E.W * 1.2, y = ((r() * E.H + t * 1400) % (E.H + 200)) - 100; g.beginPath(); g.moveTo(x, y); g.lineTo(x - 12, y + 46); g.stroke(); } g.restore(); }
  if (snow) { const r = rng(6); for (let i = 0; i < 90; i++) { const x = (r() * E.W + Math.sin(t + i) * 30), y = ((r() * E.H + t * (70 + r() * 60)) % (E.H + 40)) - 20; circle(g, x, y, 4 + r() * 6, '#ffffff'); } }
  return { gy };
}

// indoor room (brushing teeth, washing hands, cleaning up, bedtime inside)
function home(g, t, cam) {
  const gy = GY();
  layer(g, cam, 0.5, g => { g.fillStyle = linGrad(g, 0, -E.H, 0, gy, ['#ffe6c9', '#ffd9b0']); g.fillRect(-E.W * 2, -E.H * 2, E.W * 5, E.H * 3);
    for (let x = -E.W; x < E.W * 2; x += 120) { g.fillStyle = 'rgba(255,255,255,.35)'; g.fillRect(x, -E.H, 50, E.H * 2); }
    rr(g, E.W * 0.58, E.H * 0.16, 340, 400, 30); g.fillStyle = '#ffffff'; g.fill(); rr(g, E.W * 0.58 + 22, E.H * 0.16 + 22, 296, 356, 20); g.fillStyle = linGrad(g, 0, E.H * 0.16, 0, E.H * 0.16 + 380, ['#62b8ff', '#d6f0ff']); g.fill();
    cloud(g, E.W * 0.58 + 170, E.H * 0.16 + 140, 0.7); seg(g, [[E.W * 0.58 + 170, E.H * 0.16 + 22], [E.W * 0.58 + 170, E.H * 0.16 + 378]], 14, '#ffffff');
    rr(g, E.W * 0.06, E.H * 0.22, 260, 200, 20); g.fillStyle = '#ffffff'; g.fill(); circle(g, E.W * 0.06 + 130, E.H * 0.22 + 100, 60, '#ffc94a'); });
  layer(g, cam, 0.85, g => { g.fillStyle = linGrad(g, 0, gy - 140, 0, E.H * 1.4, ['#d8a46a', '#c48a50']); g.fillRect(-E.W * 2, gy - 140, E.W * 5, E.H);
    g.strokeStyle = 'rgba(0,0,0,.12)'; g.lineWidth = 4; for (let y = gy - 100; y < E.H * 1.2; y += 70) { g.beginPath(); g.moveTo(-E.W, y); g.lineTo(E.W * 2, y); g.stroke(); }
    g.save(); g.translate(E.W / 2, gy + 60); g.scale(1, 0.36); circle(g, 0, 0, 420, '#b48cff'); circle(g, 0, 0, 330, '#c9aaff'); g.restore(); });
  return { gy };
}
