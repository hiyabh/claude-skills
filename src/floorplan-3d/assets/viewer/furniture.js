// Furniture meshes. Same local frame as cabinetry: +X width, +Y up, +Z = the side people use (front).
import * as THREE from 'three';
import { box, cyl, rounded } from './parts.js';

function legs(g, mat, w, d, h, inset = 0.05, r = 0.02) {
  for (const [x, z] of [[-1, -1], [1, -1], [-1, 1], [1, 1]]) cyl(g, mat, r, r, h, x * (w / 2 - inset), 0, z * (d / 2 - inset), 8);
}

const MAKERS = {
  bed(g, m, [w, d]) {
    rounded(g, m.wood, w, 0.28, d, 0.03, 0, 0.05, 0);
    rounded(g, m.linen, w - 0.04, 0.2, d - 0.06, 0.06, 0, 0.33, 0.02);
    rounded(g, m.fabricWarm, w - 0.02, 0.05, d * 0.42, 0.04, 0, 0.53, d * 0.27);
    box(g, m.wood, w + 0.04, 0.95, 0.06, 0, 0.05, -d / 2 - 0.02);
    const pillows = w > 1.2 ? [-w / 4, w / 4] : [0];
    for (const x of pillows) rounded(g, m.linen, Math.min(0.6, w / pillows.length - 0.08), 0.12, 0.38, 0.06, x, 0.53, -d / 2 + 0.28);
  },
  nightstand(g, m, [w, d, h]) { box(g, m.wood, w, h, d); box(g, m.handle, 0.12, 0.012, 0.012, 0, h - 0.1, d / 2 + 0.006); },
  wardrobe(g, m, [w, d, h]) {
    box(g, m.door, w, h, d);
    const n = Math.max(2, Math.round(w / 0.5));
    for (let i = 1; i < n; i += 1) box(g, m.black, 0.005, h - 0.04, 0.004, -w / 2 + (w / n) * i, 0.02, d / 2 + 0.002);
  },
  sofa(g, m, [w, d]) {
    rounded(g, m.fabric, w, 0.42, d, 0.06, 0, 0.04, 0);
    rounded(g, m.fabric, w, 0.45, 0.2, 0.06, 0, 0.42, -d / 2 + 0.1);
    for (const x of [-1, 1]) rounded(g, m.fabric, 0.18, 0.22, d, 0.05, x * (w / 2 - 0.09), 0.42, 0);
    const seats = Math.max(2, Math.round((w - 0.36) / 0.7));
    const sw = (w - 0.36) / seats;
    for (let i = 0; i < seats; i += 1) rounded(g, m.fabric, sw - 0.03, 0.1, d - 0.26, 0.05, -w / 2 + 0.18 + sw * (i + 0.5), 0.46, 0.08);
    for (const k of [-1, 1]) {   // throw pillows leaning on the back, one at each end
      const pillow = rounded(g, k < 0 ? m.fabricWarm : m.linen, 0.42, 0.38, 0.14, 0.07, k * (w / 2 - 0.42), 0.5, -d / 2 + 0.26);
      pillow.rotation.x = -0.25;
    }
    legs(g, m.black, w, d, 0.04, 0.08, 0.015);
  },
  armchair(g, m, [w, d]) { MAKERS.sofa(g, m, [w, d]); },
  coffee_table(g, m, [w, d, h]) { rounded(g, m.wood, w, 0.04, d, 0.08, 0, h - 0.04, 0); legs(g, m.black, w, d, h - 0.04, 0.08, 0.012); },
  tv_unit(g, m, [w, d, h]) {
    box(g, m.wood, w, h, d);
    const tv = box(g, m.black, Math.min(1.45, w * 0.8), 0.82, 0.04, 0, h + 0.25, -d / 2 + 0.06);
    tv.material = new THREE.MeshStandardMaterial({ color: '#0d0e10', roughness: 0.15, metalness: 0.3 });
  },
  dining_table(g, m, [w, d, h]) { box(g, m.wood, w, 0.04, d, 0, h - 0.04); legs(g, m.black, w, d, h - 0.04, 0.08, 0.022); },
  chair(g, m) {
    box(g, m.wood, 0.44, 0.03, 0.44, 0, 0.45); box(g, m.wood, 0.44, 0.4, 0.03, 0, 0.48, -0.205);
    legs(g, m.black, 0.44, 0.44, 0.45, 0.03, 0.012);
  },
  desk(g, m, [w, d, h]) { box(g, m.wood, w, 0.03, d, 0, h - 0.03); legs(g, m.black, w, d, h - 0.03, 0.04, 0.015); },
  rug(g, m, [w, d]) {
    const rug = box(g, m.rug || m.fabricWarm, w, 0.008, d);
    rug.castShadow = false;
  },
  plant(g, m) {
    cyl(g, m.ceramic, 0.16, 0.12, 0.34);
    const leaves = new THREE.Mesh(new THREE.IcosahedronGeometry(0.32, 1), m.plant);
    leaves.position.y = 0.72; leaves.scale.set(1, 1.3, 1); leaves.castShadow = true;
    g.add(leaves);
  },
  outdoor_table(g, m, [w, , h]) { cyl(g, m.frame, w / 2, w / 2, 0.03, 0, h - 0.03); cyl(g, m.frame, 0.02, 0.02, h - 0.03, 0, 0); },
  outdoor_chair(g, m) { MAKERS.chair(g, { ...m, wood: m.frame }); },
  bathtub(g, m, [w, d]) { rounded(g, m.ceramic, w, 0.55, d, 0.12); },
};

/** Build any furniture kind; unknown kinds become a neutral box so nothing silently disappears. */
export function buildFurniture(g, m, item) {
  const maker = MAKERS[item.kind];
  if (maker) maker(g, m, item.size);
  else box(g, m.door, item.size[0], item.size[2], item.size[1]);
}

export const FURNITURE_KINDS = Object.keys(MAKERS);
