// Camera rig: OrbitControls for direct manipulation, springs for every programmatic move.
// A fly-to always starts from the live camera pose, and any pointer/wheel input cancels it at once.
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { P, SpringVec3, Spring, REDUCED_MOTION, centroid, bounds, shoelace, insidePoly } from './util.js';

const EYE_H = 1.6;
const CUT_H = 1.05;          // dollhouse wall height
const INTERIOR_H = 2.1;      // interior walls in the overview: low enough to see into small rooms
const FLY = { response: 0.85, damping: 1 };
const CUT_SPRING = { response: 0.35, damping: 1 };

export class CameraRig {
  constructor(camera, dom) {
    this.camera = camera;
    this.controls = new OrbitControls(camera, dom);
    Object.assign(this.controls, { enableDamping: true, dampingFactor: 0.09, maxPolarAngle: Math.PI / 2 - 0.03,
      minDistance: 0.6, maxDistance: 40, screenSpacePanning: true, zoomToCursor: true });
    this.eye = new SpringVec3(camera.position, FLY);
    this.target = new SpringVec3(this.controls.target, FLY);
    this.flying = false;
    this.onArrive = null;
    this.controls.addEventListener('start', () => this.cancel());
  }

  /** Fly to a pose. From the presentation value, always - never from the last target. */
  flyTo(eye, target, onArrive = null) {
    this.eye.snap(this.camera.position);
    this.target.snap(this.controls.target);
    this.eye.set(eye);
    this.target.set(target);
    this.onArrive = onArrive;
    this.flying = true;
    if (REDUCED_MOTION) { this.jump(eye, target); }
  }

  jump(eye, target) {
    this.camera.position.copy(eye);
    this.controls.target.copy(target);
    this.eye.snap(eye); this.target.snap(target);
    this.flying = false;
    this.controls.update();
    if (this.onArrive) { const done = this.onArrive; this.onArrive = null; done(); }
  }

  cancel() {
    this.flying = false;
    this.onArrive = null;
  }

  update(dt) {
    if (this.flying) {
      this.camera.position.copy(this.eye.step(dt));
      this.controls.target.copy(this.target.step(dt));
      if (this.eye.settled && this.target.settled) {
        this.flying = false;
        if (this.onArrive) { const done = this.onArrive; this.onArrive = null; done(); }
      }
    }
    if (this.controls.enabled) this.controls.update();
  }
}

/** Named camera poses derived from the plan: overview, eye level, top-down plan, each room, each elevation. */
export function deriveViews(plan, extraViews) {
  const pts = plan.walls.flatMap((w) => [w.a, w.b]);
  const b = bounds(pts);
  const cx = (b.minX + b.maxX) / 2; const cy = (b.minY + b.maxY) / 2;
  const span = Math.max(b.maxX - b.minX, b.maxY - b.minY);
  const center = P(cx, cy, 0);
  const main = [...plan.rooms].sort((p, q) => shoelace(q.polygon) - shoelace(p.polygon))[0];
  const corner = main ? cornerShot(main.polygon) : { eye: [cx, cy], target: [cx + 1, cy + 1] };
  const views = [
    { id: 'overview', label: 'סקירה', eye: P(cx + span * 0.55, cy - span * 0.7, span * 1.15), target: center, cut: 'auto' },
    { id: 'eye', label: 'גובה עיניים', eye: P(...corner.eye, EYE_H), target: P(...corner.target, 1.25), cut: 'none' },
    { id: 'plan', label: 'תוכנית', eye: P(cx, cy - 0.01, span * 1.45), target: center, cut: 'low' },
  ];
  for (const v of extraViews || []) {
    views.push({ id: v.id, label: v.label, eye: P(...v.eye), target: P(...v.target), cut: 'none', elevation: true });
  }
  return { views, center, span, bounds: b };
}

/** Stand in a corner of the room and look across its longest diagonal, like a property photographer. */
function cornerShot(poly) {
  const b = bounds(poly);
  const inset = 0.6;
  const corners = [[b.minX + inset, b.minY + inset], [b.maxX - inset, b.minY + inset], [b.maxX - inset, b.maxY - inset], [b.minX + inset, b.maxY - inset]];
  let best = null;
  corners.forEach((c, i) => {
    const o = corners[(i + 2) % 4];
    const len = Math.hypot(o[0] - c[0], o[1] - c[1]);
    if (insidePoly(c, poly) && insidePoly(o, poly) && (!best || len > best.len)) best = { eye: c, target: o, len };
  });
  const [x, y] = centroid(poly);
  return best || { eye: [x - 0.5, y - 0.5], target: [x + 1, y + 1] };
}

/** A close look at one room: diagonal, high enough to see the floor. */
export function roomView(room) {
  const [x, y] = centroid(room.polygon);
  const b = bounds(room.polygon);
  const r = Math.max(b.maxX - b.minX, b.maxY - b.minY);
  return { eye: P(x + r * 0.55, y - r * 0.85, r * 1.15 + 1.2), target: P(x, y, 0.4) };
}

/**
 * Dollhouse walls. mode 'auto': exterior walls between the camera and the interior drop to CUT_H.
 * 'low': every wall drops. 'none': full height. Springs make the change continuous and interruptible.
 */
export class WallCutter {
  constructor(wallGroup) {
    this.items = wallGroup.children.map((g) => ({ g, s: new Spring(1, CUT_SPRING), ...wallInfo(g) }));
    this.mode = 'auto';
  }

  update(camera, dt) {
    for (const it of this.items) {
      const target = this.targetScale(it, camera);
      it.s.target = target;
      it.g.scale.y = REDUCED_MOTION ? (it.s.snap(target), target) : it.s.step(dt);
    }
  }

  targetScale(it, camera) {
    if (this.mode === 'none' || it.railing) return 1;
    const low = CUT_H / it.height;
    if (this.mode === 'low') return low;
    if (!it.exterior) return Math.min(1, INTERIOR_H / it.height);
    const toCam = new THREE.Vector3().subVectors(camera.position, it.mid).setY(0).normalize();
    return toCam.dot(it.normal) > 0.15 ? low : 1;
  }
}

function wallInfo(g) {
  const { wall, outward, height } = g.userData;
  const [ax, ay] = wall.a; const [bx, by] = wall.b;
  const len = Math.hypot(bx - ax, by - ay) || 1;
  const ux = (bx - ax) / len; const uy = (by - ay) / len;
  const n = outward > 0 ? [-uy, ux] : [uy, -ux];
  return { exterior: !!wall.exterior, railing: wall.kind === 'railing', height,
    mid: P((ax + bx) / 2, (ay + by) / 2, 0), normal: new THREE.Vector3(n[0], 0, -n[1]) };
}

export { EYE_H };
