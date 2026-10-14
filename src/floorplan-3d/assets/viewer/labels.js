// HTML labels pinned to 3D points (crisp Hebrew text, real CSS), plus 3D dimension lines.
// Layers: rooms, items (label + width chip), dims (drawing dimension lines), walls (ids), notes (pins).
import * as THREE from 'three';
import { P, el, cm, fmtArea, shoelace, centroid } from './util.js';

const TICK = 0.07;
const tmp = new THREE.Vector3();
// Progressive disclosure: detail labels only appear once the camera is close enough to read them.
const MAX_DIST = { items: 6.5, dims: 10, walls: 14 };
// When two labels collide on screen, the lower number wins.
const PRIORITY = { notes: 0, measure: 1, rooms: 2, dims: 3, items: 4, walls: 5 };
const PAD = 4;
const OCCLUDE_EVERY = 6;          // frames between wall-occlusion ray tests
const OCCLUDABLE = new Set(['rooms', 'items', 'dims', 'notes']);
const OCCLUDE_BELOW_H = 3;        // from above, every room label should stay readable

function chip(value, src, prefix = '') {
  const node = el('span', `chip ${src === 'drawing' ? 'drawn' : 'estimated'}`);
  node.textContent = `${src === 'drawing' ? '' : '≈'}${prefix}${value}`;
  return node;
}

function cssColor(name, fallback) {
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return v || fallback;
}

export class Labels {
  constructor(container, camera, pop) {
    Object.assign(this, { container, camera, pop, entries: [], group: new THREE.Group(), tick: 0, ray: new THREE.Raycaster(), occluders: [] });
    this.layers = { rooms: true, items: false, dims: false, walls: false, notes: true };
    this.group.name = 'dimension-lines';
    addEventListener('pointerdown', (e) => { if (!e.target.closest('.notepin, .pop')) this.hidePop(); });
  }

  clear() {
    for (const e of this.entries) e.node.remove();
    this.entries = [];
    this.group.clear();
  }

  add(layer, node, anchor, extra = {}) {
    node.classList.add('lbl');
    this.container.append(node);
    this.entries.push({ layer, node, anchor, ...extra });
  }

  build({ plan, items, notes }) {
    this.clear();
    for (const room of plan.rooms) this.addRoom(room);
    for (const item of items) this.addItem(item);
    for (const dim of plan.dimensions || []) this.addDim(dim);
    for (const wall of plan.walls) this.addWallId(wall, plan.defaults.wall_height);
    (notes || []).forEach((n, i) => this.addNote(n, i + 1));
    this.apply();
  }

  addRoom(room) {
    const node = el('div', 'room glass');
    node.append(el('span', null, room.label || room.type));
    node.append(el('small', null, fmtArea(shoelace(room.polygon))));
    const [x, y] = centroid(room.polygon);
    this.add('rooms', node, P(x, y, 0.15), { room: room.id });
  }

  addItem(item) {
    if (!item.label || item.tier === 'counter') return;
    const node = el('div', 'item');
    node.append(chip(cm(item.size[0]), item.src), el('span', null, item.label));
    const r = item.rot || 0;
    const front = (item.size[1] / 2) * (item.tier === 'upper' ? 1 : 0.6);
    const z = (item.z || 0) + (item.tier === 'upper' ? item.size[2] / 2 : item.size[2] + 0.06);
    this.add('items', node, P(item.center[0] + Math.cos(r) * front, item.center[1] + Math.sin(r) * front, z));
  }

  addDim(dim) {
    const a = P(...dim.a); const b = P(...dim.b);
    const drawn = dim.src === 'drawing';
    const colour = drawn ? cssColor('--drawn', '#1f6fb2') : cssColor('--estimated', '#b7791f');
    const up = new THREE.Vector3(0, TICK, 0);
    const pts = [a, b, a.clone().sub(up), a.clone().add(up), b.clone().sub(up), b.clone().add(up)];
    const geo = new THREE.BufferGeometry().setFromPoints(pts);
    const mat = drawn ? new THREE.LineBasicMaterial({ color: colour, depthTest: false })
      : new THREE.LineDashedMaterial({ color: colour, dashSize: 0.06, gapSize: 0.04, depthTest: false });
    const line = new THREE.LineSegments(geo, mat);
    if (!drawn) line.computeLineDistances();
    line.renderOrder = 5;
    this.group.add(line);
    const value = dim.cm ?? cm(a.distanceTo(b));
    const node = el('div', 'dim');
    node.append(chip(value, dim.src));
    this.add('dims', node, a.clone().add(b).multiplyScalar(0.5), { line });
  }

  addWallId(wall, h) {
    const node = el('div', 'wallid', wall.id);
    this.add('walls', node, P((wall.a[0] + wall.b[0]) / 2, (wall.a[1] + wall.b[1]) / 2, h + 0.12));
  }

  addNote(note, n) {
    const node = el('button', `notepin pin ${note.kind === 'question' ? '' : 'assumption'}`, String(n));
    node.setAttribute('aria-label', `הערה ${n}`);
    node.addEventListener('click', (e) => { e.stopPropagation(); this.showPop(node, note, n); });
    const [x, y, z = 1.3] = note.at || [0, 0];
    this.add('notes', node, P(x, y, z), { note });
  }

  showPop(anchorNode, note, n) {
    const r = anchorNode.getBoundingClientRect();
    this.pop.replaceChildren(el('strong', null, `${n}. ${note.kind === 'question' ? 'שאלה פתוחה' : 'הנחה'}`), el('div', null, note.text));
    this.pop.style.left = `${Math.max(12, Math.min(innerWidth - 272, r.left + r.width / 2 - 130))}px`;
    this.pop.style.top = `${Math.max(12, r.top - 12)}px`;
    this.pop.style.transform = 'translateY(-100%)';
    this.pop.classList.remove('closed');
  }

  hidePop() { this.pop.classList.add('closed'); }

  setLayer(layer, on) {
    this.layers[layer] = on;
    this.apply();
  }

  apply() {
    for (const e of this.entries) {
      const on = !!this.layers[e.layer] && !this.suppressed?.(e);
      e.node.hidden = !on;
      if (e.line) e.line.visible = on;
    }
  }

  /** Labels behind an opaque wall are hidden; re-tested every few frames to keep the cost flat. */
  occlusion() {
    if (!this.occluders.length || this.camera.position.y > OCCLUDE_BELOW_H) {
      for (const e of this.entries) e.occluded = false;
      return;
    }
    const solid = this.occluders.filter((m) => m.visible && !m.material.transparent);
    for (const e of this.entries) {
      if (e.node.hidden || !OCCLUDABLE.has(e.layer)) { e.occluded = false; continue; }
      const dir = tmp.copy(e.anchor).sub(this.camera.position);
      const dist = dir.length();
      this.ray.set(this.camera.position, dir.normalize());
      this.ray.far = dist - 0.15;
      e.occluded = this.ray.intersectObjects(solid, false).length > 0;
    }
  }

  update(width, height) {
    if ((this.tick = (this.tick + 1) % OCCLUDE_EVERY) === 0) this.occlusion();
    const placed = [];
    const order = [...this.entries].sort((p, q) => (PRIORITY[p.layer] ?? 9) - (PRIORITY[q.layer] ?? 9));
    for (const e of order) {
      if (e.node.hidden) continue;
      const far = MAX_DIST[e.layer] && this.camera.position.distanceTo(e.anchor) > MAX_DIST[e.layer];
      tmp.copy(e.anchor).project(this.camera);
      const onScreen = !far && !e.occluded && tmp.z < 1 && Math.abs(tmp.x) < 1.1 && Math.abs(tmp.y) < 1.1;
      const x = (tmp.x * 0.5 + 0.5) * width;
      const y = (-tmp.y * 0.5 + 0.5) * height;
      const rect = onScreen && this.rect(e, x, y);
      const show = onScreen && !placed.some((r) => overlap(r, rect));
      if (show) placed.push(rect);
      e.node.style.opacity = show ? '' : '0';
      if (e.line) e.line.visible = !far && !!this.layers[e.layer];
      if (show) e.node.style.transform = `translate(${x.toFixed(1)}px, ${y.toFixed(1)}px) translate(-50%, -50%)`;
    }
  }

  rect(e, x, y) {
    if (!e.w) { e.w = e.node.offsetWidth; e.h = e.node.offsetHeight; }   // measured once, layout reads are costly
    return [x - e.w / 2 - PAD, y - e.h / 2 - PAD, x + e.w / 2 + PAD, y + e.h / 2 + PAD];
  }
}

function overlap(a, b) {
  return a[0] < b[2] && b[0] < a[2] && a[1] < b[3] && b[1] < a[3];
}
