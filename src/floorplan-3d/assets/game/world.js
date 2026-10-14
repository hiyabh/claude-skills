// The apartment as a game world: the viewer's shell and cabinetry builders with PBR materials,
// Poly Haven models standing in for procedural furniture where one fits, ceiling lamps, and the ground below.
import * as THREE from 'three';
import { P, planAngleToY, centroid, bounds } from '../viewer/util.js';
import { buildShell } from '../viewer/shell.js';
import { buildItem } from '../viewer/cabinetry.js';
import { autoFurnish } from '../viewer/autofurnish.js';
import { buildDecor } from './decor.js';

// furniture kind -> model key (null = hide: the set model already includes it)
const MODEL_FOR = { coffee_table: 'coffee_table', plant: 'plant', armchair: 'armchair', outdoor_table: 'outdoor_set', outdoor_chair: null };
const STOREY_M = 3.0;
const GROUND_SIZE = 400;
const OVERSIZE = 1.35;   // a model may exceed its slot by this much before it is scaled down

function modelInstance(models, key) {
  const src = models[key];
  return src ? src.clone(true) : null;
}

/** Place a model on the floor at the item's slot, facing like the item; shrink it only if it would not fit. */
function placeModel(obj, item) {
  const box = new THREE.Box3().setFromObject(obj);
  const size = box.getSize(new THREE.Vector3());
  const fit = Math.min(1, (item.size[0] * OVERSIZE) / Math.max(size.x, 1e-3), (item.size[1] * OVERSIZE) / Math.max(size.z, 1e-3));
  obj.scale.setScalar(fit);
  const centre = box.getCenter(new THREE.Vector3()).multiplyScalar(fit);
  const holder = new THREE.Group();
  obj.position.set(-centre.x, -box.min.y * fit, -centre.z);
  holder.add(obj);
  holder.position.copy(P(item.center[0], item.center[1], item.z || 0));
  holder.rotation.y = planAngleToY(item.rot || 0);
  holder.userData = { item, model: true };
  return holder;
}

function buildFurnishing(item, mats, models, ceilingH) {
  if (item.kind in MODEL_FOR) {
    const key = MODEL_FOR[item.kind];
    if (key === null) return models.outdoor_set ? null : buildItem(item, mats, ceilingH);
    const inst = modelInstance(models, key);
    if (inst) return placeModel(inst, item);
  }
  if (item.kind === 'tv_unit' && models.tv_console) return tvUnit(item, mats, models);
  return buildItem(item, mats, ceilingH);
}

/** The console model plus a slim screen: Poly Haven only has CRT televisions. */
function tvUnit(item, mats, models) {
  const holder = placeModel(modelInstance(models, 'tv_console'), item);
  const consoleTop = new THREE.Box3().setFromObject(holder).max.y;
  const screen = new THREE.Mesh(new THREE.BoxGeometry(Math.min(1.4, item.size[0] * 0.8), 0.8, 0.03), mats.black);
  screen.position.set(0, consoleTop - (item.z || 0) + 0.5, -item.size[1] / 2 + 0.08);
  screen.castShadow = true;
  holder.add(screen);
  return holder;
}

function ceilingLamps(plan, models, ceilingH) {
  const group = new THREE.Group();
  if (!models.ceiling_lamp) return group;
  for (const room of plan.rooms) {
    if (room.ceiling === false) continue;
    const [x, y] = centroid(room.polygon);
    const lamp = models.ceiling_lamp.clone(true);
    const box = new THREE.Box3().setFromObject(lamp);
    lamp.position.copy(P(x, y, (room.ceiling_height || ceilingH) - box.max.y));
    lamp.userData = { lamp: true, room: room.id };
    lamp.traverse((o) => { if (o.isMesh) { o.castShadow = false; o.material = o.material.clone(); } });
    group.add(lamp);
  }
  return group;
}

function ground(plan, mats) {
  const floor = Number(plan.meta?.floor ?? 2);
  const geo = new THREE.PlaneGeometry(GROUND_SIZE, GROUND_SIZE);
  geo.rotateX(-Math.PI / 2);
  const mesh = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({ color: '#7d8268', roughness: 1 }));
  mesh.position.y = -floor * STOREY_M - 0.05;
  mesh.receiveShadow = true;
  return mesh;
}

export function buildWorld(variant, mats, models) {
  const { plan, items } = variant;
  const ceilingH = plan.defaults.wall_height;
  const shell = buildShell(plan, mats);
  shell.ceilings.visible = true;
  shell.ceilings.traverse((o) => { if (o.isMesh) o.castShadow = true; });   // indoors is lit through windows, not the roof
  const auto = autoFurnish(plan, items);
  const furnishings = new THREE.Group();
  for (const item of [...items, ...auto]) {
    const obj = buildFurnishing(item, mats, models, ceilingH);
    if (obj) furnishings.add(obj);
  }
  const lamps = ceilingLamps(plan, models, ceilingH);
  const root = new THREE.Group();
  const groundMesh = ground(plan, mats);
  root.add(shell.floors, shell.walls, shell.ceilings, furnishings, lamps, buildDecor(plan, [...items, ...auto], mats), groundMesh);
  const pts = plan.walls.flatMap((w) => [w.a, w.b]);
  const b = bounds(pts);
  const centroids = Object.fromEntries(plan.rooms.map((r) => [r.id, centroid(r.polygon)]));
  return { root, shell, lamps, ground: groundMesh, items: [...items, ...auto], centroids,
    center: P((b.minX + b.maxX) / 2, (b.minY + b.maxY) / 2, 0), span: Math.max(b.maxX - b.minX, b.maxY - b.minY) };
}
