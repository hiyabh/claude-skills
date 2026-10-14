// Kitchen and bathroom items built from expanded boxes (see scripts/runs.py).
// A box: {kind, center:[x,y], size:[w,d,h], z, rot (plan radians, facing), tier, label, src}.
import * as THREE from 'three';
import { P, planAngleToY } from './util.js';
import { box, cyl, rounded, seam, handle } from './parts.js';
import { buildFurniture } from './furniture.js';

const PLINTH = 0.1;
const GAP = 0.003;

function carcass(g, m, w, h, d, plinth = PLINTH) {
  box(g, m.black, w - 0.04, plinth, d - 0.08, 0, 0, -0.04);
  box(g, m.cabinet, w - GAP * 2, h - plinth, d, 0, plinth, 0);
  return d / 2;
}

function doors(g, m, w, y0, y1, zf, count = w > 0.55 ? 2 : 1, pullTop = true) {
  for (let i = 1; i < count; i += 1) seam(g, m.black, 0.006, y1 - y0, -w / 2 + (w / count) * i, y0, zf);
  for (let i = 0; i < count; i += 1) {
    const x = -w / 2 + (w / count) * (i + 0.5) + (count === 2 ? (i === 0 ? 1 : -1) * (w / count / 2 - 0.05) : w / 2 - 0.06);
    handle(g, m.handle, 0.16, true, x, pullTop ? y1 - 0.06 : y0 + 0.22, zf);
  }
}

function drawers(g, m, w, y0, y1, zf, count = 3) {
  const step = (y1 - y0) / count;
  for (let i = 1; i < count; i += 1) seam(g, m.black, w - 0.01, 0.006, 0, y0 + step * i, zf);
  for (let i = 0; i < count; i += 1) handle(g, m.handle, Math.min(0.32, w * 0.55), false, 0, y0 + step * (i + 1) - 0.05, zf);
}

const BASE = {
  cabinet(g, m, [w, d, h]) { doors(g, m, w, PLINTH, h, carcass(g, m, w, h, d)); },
  drawers(g, m, [w, d, h]) { drawers(g, m, w, PLINTH, h, carcass(g, m, w, h, d)); },
  dishwasher(g, m, [w, d, h]) { handle(g, m.handle, w * 0.6, false, 0, h - 0.06, carcass(g, m, w, h, d)); },
  oven(g, m, [w, d, h]) {
    const zf = carcass(g, m, w, h, d);
    box(g, m.black, w - 0.06, 0.48, 0.01, 0, 0.3, zf);
    handle(g, m.steel, w * 0.7, false, 0, 0.74, zf);
  },
  sink(g, m, [w, d, h]) {
    doors(g, m, w, PLINTH, h, carcass(g, m, w, h, d));
    box(g, m.steel, w * 0.72, 0.006, d * 0.62, 0, h + 0.031, 0.02);
    const spout = cyl(g, m.steel, 0.014, 0.018, 0.3, 0, h + 0.03, -d / 2 + 0.07);
    const arm = box(g, m.steel, 0.025, 0.025, 0.2, 0, h + 0.31, -d / 2 + 0.16);
    spout.castShadow = arm.castShadow = true;
  },
  cooktop(g, m, [w, d, h]) {
    drawers(g, m, w, PLINTH, h, carcass(g, m, w, h, d), 2);
    box(g, m.black, w * 0.9, 0.006, d * 0.82, 0, h + 0.031, 0);
    const rings = [[-0.17, -0.12], [0.17, -0.12], [-0.17, 0.13], [0.17, 0.13]];
    for (const [x, z] of rings) {
      const ring = new THREE.Mesh(new THREE.TorusGeometry(0.075, 0.004, 6, 32), m.steel);
      ring.rotation.x = Math.PI / 2;
      ring.position.set(x * (w / 0.62), h + 0.038, z);
      g.add(ring);
    }
  },
};

const TALL = {
  tall(g, m, [w, d, h]) { doors(g, m, w, PLINTH, h, carcass(g, m, w, h, d), w > 0.55 ? 2 : 1, false); seam(g, m.black, w, 0.006, 0, h * 0.62, d / 2); },
  pantry(g, m, s) { TALL.tall(g, m, s); },
  fridge(g, m, [w, d, h]) {
    const zf = carcass(g, m, w, h, d);
    seam(g, m.black, w, 0.006, 0, h * 0.62, zf);
    handle(g, m.handle, 0.5, true, w / 2 - 0.06, h * 0.62 - 0.08, zf);
    handle(g, m.handle, 0.5, true, w / 2 - 0.06, h * 0.62 + 0.6, zf);
  },
  oven_tower(g, m, [w, d, h]) {
    const zf = carcass(g, m, w, h, d);
    for (const y of [0.78, 1.38]) { box(g, m.black, w - 0.08, 0.5, 0.012, 0, y, zf); handle(g, m.steel, w * 0.7, false, 0, y + 0.44, zf + 0.01); }
    doors(g, m, w, 1.95, h, zf, 1, false);
  },
};

const UPPER = {
  cabinet(g, m, [w, d, h]) { box(g, m.cabinet, w - GAP * 2, h, d); doors(g, m, w, 0, h, d / 2, w > 0.55 ? 2 : 1, false); },
  open(g, m, [w, d, h]) { box(g, m.cabinet, w, 0.025, d); box(g, m.cabinet, w, 0.025, d, 0, h / 2); },
  hood(g, m, [w, d, h], ceiling) {
    box(g, m.steel, w * 0.95, 0.08, d + 0.1, 0, 0, 0.05);
    box(g, m.steel, w * 0.42, Math.max(0.2, ceiling), 0.26, 0, 0.08, -d / 2 + 0.13);
  },
};

const FIXTURE = {
  counter(g, m, [w, d, h]) { box(g, m.counter, w, h, d); },
  island(g, m, [w, d, h]) { doors(g, m, w, PLINTH, h, carcass(g, m, w, h, d), Math.max(1, Math.round(w / 0.6)), true); },
  stool(g, m) {
    cyl(g, m.steel, 0.2, 0.22, 0.02, 0, 0, 0); cyl(g, m.steel, 0.025, 0.025, 0.66, 0, 0.02, 0);
    cyl(g, m.fabric, 0.19, 0.17, 0.07, 0, 0.68, 0);
    const ring = new THREE.Mesh(new THREE.TorusGeometry(0.16, 0.01, 6, 28), m.steel);
    ring.rotation.x = Math.PI / 2; ring.position.y = 0.3; g.add(ring);
  },
  shower(g, m, [w, d, h]) {
    box(g, m.ceramic, w, 0.05, d);
    for (const [pw, x, z, rot] of [[w, 0, d / 2, 0], [d, -w / 2, 0, Math.PI / 2]]) {
      const pane = new THREE.Mesh(new THREE.PlaneGeometry(pw, h - 0.1), m.glass);
      pane.position.set(x, 0.05 + (h - 0.1) / 2, z); pane.rotation.y = rot; g.add(pane);
    }
    cyl(g, m.steel, 0.012, 0.012, 1.0, w / 2 - 0.1, 1.0, -d / 2 + 0.05);
    cyl(g, m.steel, 0.1, 0.1, 0.012, w / 2 - 0.1, 2.0, -d / 2 + 0.15);
  },
  toilet(g, m, [w, d]) {
    rounded(g, m.ceramic, w, 0.4, d * 0.72, 0.17, 0, 0, d * 0.12);
    box(g, m.ceramic, w * 0.95, 0.38, 0.16, 0, 0.42, -d / 2 + 0.08);
  },
  vanity(g, m, [w, d, h]) {
    drawers(g, m, w, 0.25, h, carcass(g, m, w, h, d, 0.25), 2);
    rounded(g, m.ceramic, w, 0.06, d, 0.03, 0, h, 0);
    const mirror = box(g, m.glass, w * 0.9, 0.7, 0.01, 0, h + 0.3, -d / 2 + 0.01);
    mirror.material = new THREE.MeshStandardMaterial({ color: '#cfd8dc', roughness: 0.05, metalness: 0.9 });
  },
  washer(g, m, [w, d, h]) {
    const unit = Math.min(0.85, h / 2);
    for (const y of [0, unit]) {
      rounded(g, m.ceramic, w - 0.02, unit - 0.02, d - 0.02, 0.03, 0, y, 0);
      const door = new THREE.Mesh(new THREE.TorusGeometry(0.17, 0.025, 10, 32), m.frame);
      door.position.set(0, y + unit / 2, d / 2); g.add(door);
    }
  },
};

/** Build a box into a positioned group. `ceiling` lets hoods reach the ceiling. */
export function buildItem(item, m, ceilingH = 2.7) {
  const g = new THREE.Group();
  const size = item.size;
  if (item.tier === 'upper') (UPPER[item.kind] || UPPER.cabinet)(g, m, size, ceilingH - item.z - 0.08);
  else if (item.tier === 'tall') (TALL[item.kind] || TALL.tall)(g, m, size);
  else if (item.tier === 'base') (BASE[item.kind] || BASE.cabinet)(g, m, size);
  else if (FIXTURE[item.kind]) FIXTURE[item.kind](g, m, size);
  else if (TALL[item.kind]) TALL[item.kind](g, m, size);
  else buildFurniture(g, m, item);
  g.position.copy(P(item.center[0], item.center[1], item.z || 0));
  g.rotation.y = planAngleToY(item.rot || 0);
  g.userData = { item };
  return g;
}
