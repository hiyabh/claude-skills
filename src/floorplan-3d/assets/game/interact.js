// Look-to-interact: a ray from the screen centre finds what the player looks at and offers one action on E
// (or the on-screen action button on phones): open/close a door, switch a room's light, cycle a finish.
import * as THREE from 'three';
import { Spring, REDUCED_MOTION } from '../viewer/util.js';
import { GAME_FINISHES, setPbrFinish } from './materials-pbr.js';
import { ACCENTS } from './decor.js';

const REACH_M = 3.2;
const RAY_HZ = 10;
const DOOR_SPRING = { response: 0.55, damping: 0.9 };
const ACCENT_CYCLE = [...new Set([...Object.values(ACCENTS), '#e8d9c4', '#c9a99a', '#7f8f86'])];
const SURFACES = { floor: 'ריצוף', wall: 'צבע קיר', cabinet: 'חזיתות', counter: 'משטח' };

export class Interactor {
  constructor({ camera, world, mats, lighting, ui }) {
    Object.assign(this, { camera, world, mats, lighting, ui, ray: new THREE.Raycaster(), clock: 0, target: null });
    this.ray.far = REACH_M;
    this.doors = [];
    world.root.traverse((o) => { if (o.userData.door) this.doors.push({ swing: o, open: true, spring: new Spring(o.rotation.y, DOOR_SPRING) }); });
    this.finishIndex = { floor: 0, wall: 0, cabinet: 1, counter: 0 };   // current defaults: oak, warm white, white oak, quartz
    this.accentIndex = new Map();
    addEventListener('keydown', (e) => { if (e.code === 'KeyE' && !e.repeat) this.act(); });
  }

  closedDoorSegments() { return this.doors.filter((d) => !d.open).map((d) => d.swing.userData.door.segment); }

  /** What is under the reticle, as {kind, label, object}. */
  inspect() {
    this.ray.setFromCamera(new THREE.Vector2(0, 0), this.camera);
    const hit = this.ray.intersectObject(this.world.root, true).find((h) => h.object.visible && !h.object.material?.transparent);
    if (!hit) return null;
    let o = hit.object;
    while (o) {
      if (o.userData.door) return { kind: 'door', object: o, label: this.doorState(o) ? 'סגור דלת' : 'פתח דלת' };
      if (o.userData.lamp) return { kind: 'lamp', object: o, label: this.lighting.roomOn(o.userData.room) ? 'כבה אור' : 'הדלק אור' };
      o = o.parent;
    }
    const mat = hit.object.material;
    if (mat?.userData?.accent) return { kind: 'accent', object: hit.object, label: 'החלף צבע קיר' };
    const kind = Object.keys(SURFACES).find((k) => mat === this.mats[k]);
    return kind ? { kind, object: hit.object, label: `החלף ${SURFACES[kind]}` } : null;
  }

  doorState(swing) { return this.doors.find((d) => d.swing === swing)?.open; }

  act() {
    const t = this.target;
    if (!t) return;
    if (t.kind === 'door') this.toggleDoor(t.object);
    else if (t.kind === 'lamp') this.lighting.toggleRoom(t.object.userData.room);
    else if (t.kind === 'accent') this.cycleAccent(t.object);
    else this.cycleFinish(t.kind);
    this.target = this.inspect();
    this.ui.prompt(this.target?.label);
  }

  toggleDoor(swing) {
    const d = this.doors.find((x) => x.swing === swing);
    d.open = !d.open;
    d.spring.target = d.open ? swing.userData.door.openAngle : 0;
    if (REDUCED_MOTION) d.spring.snap(d.spring.target);
    this.onDoors?.(this.closedDoorSegments());
  }

  cycleFinish(kind) {
    const list = kind === 'wall' ? GAME_FINISHES.wall : GAME_FINISHES[kind];
    this.finishIndex[kind] = (this.finishIndex[kind] + 1) % list.length;
    const f = list[this.finishIndex[kind]];
    setPbrFinish(this.mats, kind, f.id);
    this.ui.toast(`${SURFACES[kind]}: ${f.label}`, `${this.finishIndex[kind] + 1}/${list.length}`);
  }

  cycleAccent(mesh) {
    const i = ((this.accentIndex.get(mesh) ?? -1) + 1) % ACCENT_CYCLE.length;
    this.accentIndex.set(mesh, i);
    mesh.material.color.set(ACCENT_CYCLE[i]);
    this.ui.toast('צבע קיר מודגש', `${i + 1}/${ACCENT_CYCLE.length}`);
  }

  update(dt) {
    for (const d of this.doors) d.swing.rotation.y = d.spring.step(dt);
    this.clock += dt;
    if (this.clock < 1 / RAY_HZ) return;
    this.clock = 0;
    const next = this.inspect();
    if (next?.label !== this.target?.label || next?.object !== this.target?.object) this.ui.prompt(next?.label);
    this.target = next;
  }
}
