// The building shell: walls split around openings, windows, doors, railings, floors, ceilings.
// Also returns collision segments (plan coordinates) for walk mode and per-wall data for the dollhouse cut.
import * as THREE from 'three';
import { P, insidePoly } from './util.js';
import { worldUV } from './materials.js';

const RAILING_H = 1.05;
const FRAME = 0.045;
const LEAF_T = 0.04;
const DOOR_OPEN_DEG = 72;
const FLOOR_T = 0.03;

function axis(wall) {
  const [ax, ay] = wall.a; const [bx, by] = wall.b;
  const len = Math.hypot(bx - ax, by - ay) || 1e-6;
  return { ax, ay, ux: (bx - ax) / len, uy: (by - ay) / len, len };
}

/** A box spanning [t0,t1] along the wall, [z0,z1] in height, centred on the wall axis. */
function wallPiece(w, t0, t1, z0, z1, depth, mat) {
  const a = axis(w);
  const geo = worldUV(new THREE.BoxGeometry(t1 - t0, z1 - z0, depth), 1.5);
  const mesh = new THREE.Mesh(geo, mat);
  const mid = (t0 + t1) / 2;
  mesh.position.copy(P(a.ax + a.ux * mid, a.ay + a.uy * mid, (z0 + z1) / 2));
  mesh.rotation.y = Math.atan2(a.uy, a.ux);
  mesh.castShadow = mesh.receiveShadow = true;
  return mesh;
}

function openingsOn(wall, openings) {
  const a = axis(wall);
  return openings
    .filter((o) => o.wall === wall.id)
    .map((o) => {
      const t = (o.center[0] - a.ax) * a.ux + (o.center[1] - a.ay) * a.uy;
      return { ...o, t0: Math.max(0, t - o.width / 2), t1: Math.min(a.len, t + o.width / 2) };
    })
    .sort((p, q) => p.t0 - q.t0);
}

function outwardSign(wall, rooms) {
  const a = axis(wall);
  const mx = a.ax + a.ux * a.len / 2; const my = a.ay + a.uy * a.len / 2;
  const left = [mx - a.uy * 0.4, my + a.ux * 0.4];
  return rooms.some((r) => insidePoly(left, r.polygon)) ? -1 : 1; // +1: outward is the left normal
}

function windowFill(group, w, o, mats) {
  const a = axis(w);
  const width = o.t1 - o.t0; const mid = (o.t0 + o.t1) / 2;
  const z0 = o.sill; const z1 = o.sill + o.height;
  const at = (dt, z) => P(a.ax + a.ux * (mid + dt), a.ay + a.uy * (mid + dt), z);
  const glass = new THREE.Mesh(new THREE.PlaneGeometry(width, z1 - z0), mats.glass);
  glass.position.copy(at(0, (z0 + z1) / 2));
  glass.rotation.y = Math.atan2(a.uy, a.ux);
  group.add(glass);
  const bars = [[0, z0 + FRAME / 2, width, FRAME], [0, z1 - FRAME / 2, width, FRAME],
    [-width / 2 + FRAME / 2, (z0 + z1) / 2, FRAME, z1 - z0], [width / 2 - FRAME / 2, (z0 + z1) / 2, FRAME, z1 - z0],
    [0, (z0 + z1) / 2, FRAME * 0.7, z1 - z0]];
  for (const [dt, z, bw, bh] of bars) {
    const bar = new THREE.Mesh(new THREE.BoxGeometry(bw, bh, FRAME * 1.4), mats.frame);
    bar.position.copy(at(dt, z));
    bar.rotation.y = Math.atan2(a.uy, a.ux);
    group.add(bar);
  }
}

function slidingDoor(group, w, o, mats) {
  const a = axis(w);
  const width = o.t1 - o.t0; const h = o.height;
  for (const [k, off] of [[-1, -0.02], [1, 0.02]]) {
    const t = (o.t0 + o.t1) / 2 + k * width / 4;
    const panel = new THREE.Group();
    const glass = new THREE.Mesh(new THREE.PlaneGeometry(width / 2 - 0.04, h - 0.08), mats.glass);
    glass.position.y = h / 2;
    panel.add(glass);
    const outline = new THREE.EdgesGeometry(new THREE.BoxGeometry(width / 2, h, 0.035));
    const edges = new THREE.LineSegments(outline, new THREE.LineBasicMaterial({ color: '#3a3d42' }));
    edges.position.y = h / 2;
    panel.add(edges);
    panel.position.copy(P(a.ax + a.ux * t - a.uy * off, a.ay + a.uy * t + a.ux * off, 0));
    panel.rotation.y = Math.atan2(a.uy, a.ux);
    group.add(panel);
  }
}

/** +1 if the door leaf swings to the wall's left-normal side. `swing` is relative to rooms[0]. */
function swingSide(w, o, rooms) {
  const a = axis(w);
  const probe = [o.center[0] - a.uy * 0.3, o.center[1] + a.ux * 0.3];
  const first = rooms.find((r) => r.id === (o.rooms || [])[0]);
  const firstOnLeft = first ? insidePoly(probe, first.polygon) : true;
  const toFirst = firstOnLeft ? 1 : -1;
  return o.swing === 'outward' ? -toFirst : toFirst;
}

function hingedDoor(group, w, o, mats, side) {
  const a = axis(w);
  const width = o.t1 - o.t0;
  const hingeT = o.hinge === 'b' ? o.t1 : o.t0;
  const dir = o.hinge === 'b' ? -1 : 1;                // leaf extends from the hinge along the wall
  const pivot = new THREE.Group();
  pivot.position.copy(P(a.ax + a.ux * hingeT, a.ay + a.uy * hingeT, 0));
  pivot.rotation.y = Math.atan2(a.uy, a.ux);
  const leaf = new THREE.Mesh(new THREE.BoxGeometry(width - 0.02, o.height - 0.01, LEAF_T), mats.door);
  leaf.position.set(dir * (width / 2), o.height / 2, 0);
  leaf.castShadow = true;
  const knob = new THREE.Mesh(new THREE.SphereGeometry(0.03, 12, 8), mats.handle);
  knob.position.set(dir * (width - 0.09), 1.0, LEAF_T);
  const swing = new THREE.Group();
  swing.add(leaf, knob);
  // Local -Z is the wall's left normal; rotating by +phi moves a +X leaf tip toward -Z.
  swing.rotation.y = dir * side * THREE.MathUtils.degToRad(DOOR_OPEN_DEG);
  // Game mode opens and closes doors: it needs the open angle and the leaf's closed footprint.
  swing.userData.door = { openAngle: swing.rotation.y, id: o.id, segment: [a.ax + a.ux * o.t0, a.ay + a.uy * o.t0, a.ax + a.ux * o.t1, a.ay + a.uy * o.t1] };
  pivot.add(swing);
  group.add(pivot);
}

function railing(group, w, mats) {
  const a = axis(w);
  const glass = new THREE.Mesh(new THREE.PlaneGeometry(a.len, RAILING_H - 0.08), mats.glass);
  glass.position.copy(P(a.ax + a.ux * a.len / 2, a.ay + a.uy * a.len / 2, (RAILING_H - 0.08) / 2));
  glass.rotation.y = Math.atan2(a.uy, a.ux);
  group.add(glass, wallPiece(w, 0, a.len, RAILING_H - 0.05, RAILING_H, 0.06, mats.frame));
}

function buildWall(w, plan, mats, collide) {
  const group = new THREE.Group();
  const H = plan.defaults.wall_height;
  group.userData = { wall: w, outward: outwardSign(w, plan.rooms), height: H };
  const a = axis(w);
  if (w.kind === 'railing') {
    railing(group, w, mats);
    collide.push([w.a[0], w.a[1], w.b[0], w.b[1]]);
    return group;
  }
  const ext = w.thickness / 2;   // stretch past the ends so corners close
  let cursor = -ext;
  const pieces = (t0, t1, z0, z1) => { if (t1 - t0 > 0.005 && z1 - z0 > 0.005) group.add(wallPiece(w, t0, t1, z0, z1, w.thickness, mats.wall)); };
  const segment = (t0, t1) => collide.push([a.ax + a.ux * t0, a.ay + a.uy * t0, a.ax + a.ux * t1, a.ay + a.uy * t1]);
  for (const o of openingsOn(w, plan.openings)) {
    pieces(cursor, o.t0, 0, H);
    segment(Math.max(cursor, 0), o.t0);
    pieces(o.t0, o.t1, 0, o.sill);
    pieces(o.t0, o.t1, Math.min(o.sill + o.height, H), H);
    if (o.kind === 'window') { windowFill(group, w, o, mats); segment(o.t0, o.t1); }
    else if (o.kind === 'door' && o.style === 'sliding') slidingDoor(group, w, o, mats);
    else if (o.kind === 'door') hingedDoor(group, w, o, mats, swingSide(w, o, plan.rooms));
    cursor = o.t1;
  }
  pieces(cursor, a.len + ext, 0, H);
  segment(Math.max(cursor, 0), a.len);
  return group;
}

function floorMaterial(room, mats) {
  if (room.type === 'bathroom' || room.type === 'toilet') return mats.floorWet;
  if (room.type === 'balcony' || room.type === 'garden') return mats.floorOutdoor;
  return mats.floor;
}

function roomShape(poly) {
  const shape = new THREE.Shape();
  poly.forEach(([x, y], i) => (i ? shape.lineTo(x, y) : shape.moveTo(x, y)));
  return shape;
}

function buildFloor(room, mats) {
  const geo = new THREE.ExtrudeGeometry(roomShape(room.polygon), { depth: FLOOR_T, bevelEnabled: false });
  geo.rotateX(-Math.PI / 2);   // shape XY -> plan: (x, y) -> (x, 0, -y); extrusion goes up
  geo.translate(0, -FLOOR_T, 0);
  worldUV(geo, 1.6);
  const mesh = new THREE.Mesh(geo, floorMaterial(room, mats));
  mesh.receiveShadow = true;
  mesh.userData = { room: room.id };
  return mesh;
}

function buildCeiling(room, mats, defaultH) {
  const geo = new THREE.ShapeGeometry(roomShape(room.polygon));
  geo.rotateX(-Math.PI / 2);
  const mesh = new THREE.Mesh(geo, mats.ceiling);
  mesh.position.y = room.ceiling_height || defaultH;
  return mesh;
}

/** Build everything structural for one plan. */
export function buildShell(plan, mats) {
  const collide = [];
  const walls = new THREE.Group();
  const floors = new THREE.Group();
  const ceilings = new THREE.Group();
  for (const w of plan.walls) walls.add(buildWall(w, plan, mats, collide));
  for (const r of plan.rooms) {
    floors.add(buildFloor(r, mats));
    if (r.ceiling !== false) ceilings.add(buildCeiling(r, mats, plan.defaults.wall_height));
  }
  return { walls, floors, ceilings, collide };
}

/** The original drawing laid on the ground, for the 2D -> 3D reveal and the plan overlay. */
export function buildUnderlay(underlay, mats) {
  if (!underlay) return null;
  const [x0, y0, x1, y1] = underlay.bounds;
  const tex = new THREE.TextureLoader().load(underlay.src);
  tex.colorSpace = THREE.SRGBColorSpace;
  mats.underlay.map = tex;
  const mesh = new THREE.Mesh(new THREE.PlaneGeometry(x1 - x0, y1 - y0), mats.underlay);
  mesh.rotation.x = -Math.PI / 2;
  mesh.position.copy(P((x0 + x1) / 2, (y0 + y1) / 2, 0.006));
  mesh.renderOrder = 2;
  return mesh;
}
