// What makes a room feel lived-in: an accent wall behind the sofa or bed, original abstract art above it,
// and sheer linen curtains at the windows. Everything is placed from the plan, so it follows any apartment.
import * as THREE from 'three';
import { P, planAngleToY, insidePoly } from '../viewer/util.js';

// Warm Mediterranean palette: accents per room type, and the colours art is painted with.
export const ACCENTS = { living: '#a7b29a', bedroom: '#d3a58f', safe_room: '#a9bccb' };
const ART_PALETTE = ['#c4704f', '#e2b25c', '#8f9d7a', '#2f4858', '#efe6d8', '#a65e46', '#d9c3a5'];
const ACCENT_OFFSET = 0.004;   // proud of the wall face, so it never z-fights
const CURTAIN = { inset: 0.12, gap: 0.05, folds: 9, depth: 0.035, color: '#efe6d8' };
const ART_SIZE = { sofa: [1.1, 0.75], bed: [0.95, 0.65] };
const ART_HEIGHT = { sofa: 1.55, bed: 1.45 };
const CANVAS_PX = 512;

function rng(seed) {
  let s = seed >>> 0;
  return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296);
}

/** An original abstract composition: overlapping arcs and blocks in the palette (seeded, so stable per room). */
function paintArt(seed, aspect) {
  const c = document.createElement('canvas');
  c.width = CANVAS_PX; c.height = Math.round(CANVAS_PX / aspect);
  const g = c.getContext('2d'); const r = rng(seed); const pick = () => ART_PALETTE[Math.floor(r() * ART_PALETTE.length)];
  g.fillStyle = '#f3ece0'; g.fillRect(0, 0, c.width, c.height);
  for (let i = 0; i < 7; i += 1) {
    g.fillStyle = pick(); g.globalAlpha = 0.85 + r() * 0.15;
    if (r() < 0.5) { g.beginPath(); g.arc(r() * c.width, r() * c.height, 40 + r() * 140, 0, Math.PI * (1 + r())); g.fill(); }
    else g.fillRect(r() * c.width * 0.8, r() * c.height * 0.8, 60 + r() * 200, 40 + r() * 160);
  }
  g.globalAlpha = 1; g.strokeStyle = '#2b2b2b'; g.lineWidth = 3;
  g.beginPath(); g.moveTo(r() * c.width, 0); g.bezierCurveTo(r() * c.width, c.height * 0.4, r() * c.width, c.height * 0.6, r() * c.width, c.height); g.stroke();
  const tex = new THREE.CanvasTexture(c); tex.colorSpace = THREE.SRGBColorSpace;
  return tex;
}

function framedArt(seed, [w, h], mats) {
  const group = new THREE.Group();
  const frame = new THREE.Mesh(new THREE.BoxGeometry(w + 0.06, h + 0.06, 0.03), mats.wood);
  const canvas = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshStandardMaterial({ map: paintArt(seed, w / h), roughness: 0.9 }));
  canvas.position.z = 0.016;
  frame.castShadow = true;
  group.add(frame, canvas);
  return group;
}

/** The wall behind an item (sofa/bed): a painted panel the width of the room on that side, plus art above. */
function backWall(item, room, mats, seed) {
  const r = item.rot; const fx = Math.cos(r); const fy = Math.sin(r);
  // Walk backwards from the item until we leave the room: that is the wall face behind it.
  let back = item.size[1] / 2;
  while (back < 3 && insidePoly([item.center[0] - fx * back, item.center[1] - fy * back], room.polygon)) back += 0.02;
  const face = [item.center[0] - fx * (back - 0.02), item.center[1] - fy * (back - 0.02)];
  const along = [-fy, fx];
  let left = 0; let right = 0;
  while (left < 6 && insidePoly([face[0] + fx * 0.05 - along[0] * left, face[1] + fy * 0.05 - along[1] * left], room.polygon)) left += 0.02;
  while (right < 6 && insidePoly([face[0] + fx * 0.05 + along[0] * right, face[1] + fy * 0.05 + along[1] * right], room.polygon)) right += 0.02;
  const width = left + right; const mid = (right - left) / 2;
  const height = room.ceiling_height || 2.7;
  const colour = ACCENTS[room.type];
  const group = new THREE.Group();
  if (colour) {
    const paint = mats.wall.clone(); paint.color.set(colour); paint.userData.accent = true;
    const panel = new THREE.Mesh(new THREE.PlaneGeometry(width, height), paint);
    panel.position.set(mid, height / 2, 0); panel.receiveShadow = true;
    group.add(panel);
  }
  const kind = item.kind === 'bed' ? 'bed' : 'sofa';
  const art = framedArt(seed, ART_SIZE[kind], mats);
  art.position.set(0, ART_HEIGHT[kind], 0.02);
  group.add(art);
  group.position.copy(P(face[0] + fx * ACCENT_OFFSET, face[1] + fy * ACCENT_OFFSET, 0));
  group.rotation.y = planAngleToY(r);
  return group;
}

function curtainPanel(width, height, mat) {
  const geo = new THREE.PlaneGeometry(width, height, CURTAIN.folds * 4, 1);
  const pos = geo.attributes.position;
  for (let i = 0; i < pos.count; i += 1) pos.setZ(i, Math.sin((pos.getX(i) / width) * Math.PI * 2 * CURTAIN.folds) * CURTAIN.depth);
  geo.computeVertexNormals();
  const mesh = new THREE.Mesh(geo, mat);
  mesh.castShadow = true;
  return mesh;
}

/** Sheer curtains drawn to both sides of every window in living rooms and bedrooms. */
function curtains(plan, mats) {
  const group = new THREE.Group();
  const walls = Object.fromEntries(plan.walls.map((w) => [w.id, w]));
  const rooms = Object.fromEntries(plan.rooms.map((r) => [r.id, r]));
  const sheer = new THREE.MeshStandardMaterial({ color: CURTAIN.color, roughness: 1, side: THREE.DoubleSide,
    transparent: true, opacity: 0.88, normalMap: mats.linen.normalMap || null });
  for (const o of plan.openings) {
    const room = (o.rooms || []).map((id) => rooms[id]).find((r) => r && ACCENTS[r.type]);
    if (!room || !(o.kind === 'window' || o.style === 'sliding') || !walls[o.wall]) continue;
    const w = walls[o.wall];
    const len = Math.hypot(w.b[0] - w.a[0], w.b[1] - w.a[1]); const ux = (w.b[0] - w.a[0]) / len; const uy = (w.b[1] - w.a[1]) / len;
    let n = [-uy, ux];
    if (!insidePoly([o.center[0] + n[0] * 0.4, o.center[1] + n[1] * 0.4], room.polygon)) n = [uy, -ux];
    const off = w.thickness / 2 + CURTAIN.inset; const h = (room.ceiling_height || 2.7) - 0.08; const pw = Math.max(0.35, o.width * 0.28);
    for (const side of [-1, 1]) {
      const t = side * (o.width / 2 + pw / 2 - 0.1);
      const panel = curtainPanel(pw, h, sheer);
      panel.position.copy(P(o.center[0] + ux * t + n[0] * off, o.center[1] + uy * t + n[1] * off, h / 2 + 0.02));
      panel.rotation.y = planAngleToY(Math.atan2(n[1], n[0]));
      group.add(panel);
    }
  }
  return group;
}

export function buildDecor(plan, items, mats) {
  const group = new THREE.Group();
  const rooms = Object.fromEntries(plan.rooms.map((r) => [r.id, r]));
  let seed = 7;
  for (const item of items) {
    if ((item.kind === 'sofa' || item.kind === 'bed') && rooms[item.room]) group.add(backWall(item, rooms[item.room], mats, (seed += 31)));
  }
  group.add(curtains(plan, mats));
  return group;
}
