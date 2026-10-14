// Shared helpers: plan <-> three.js coordinates, a critically damped spring, formatting.
import * as THREE from 'three';

// Plan frame: x east, y north, metres. Three.js: x east, y up, z south (so -y).
export const P = (x, y, z = 0) => new THREE.Vector3(x, z, -y);
// Facing direction in plan radians -> rotation.y for an object modelled facing local +Z.
// Check: east (0) -> +Z maps to +X; north (pi/2) -> +Z maps to -Z (north).
export const planAngleToY = (rad) => rad + Math.PI / 2;

export const REDUCED_MOTION = typeof matchMedia === 'function' && matchMedia('(prefers-reduced-motion: reduce)').matches;
export const IS_TOUCH = typeof matchMedia === 'function' && matchMedia('(pointer: coarse)').matches;

const TAU = Math.PI * 2;
const SUB_STEP = 1 / 240;
const MAX_DT = 0.25;

/**
 * Apple-style spring: `response` (seconds, how fast) and `damping` (1 = no overshoot).
 * Always integrates from the current value and velocity, so a new target mid-flight blends smoothly.
 */
export class Spring {
  constructor(value, { response = 0.45, damping = 1 } = {}) {
    this.value = value;
    this.target = value;
    this.velocity = 0;
    this.setParams(response, damping);
  }

  setParams(response, damping) {
    this.omega = TAU / Math.max(response, 0.05);
    this.zeta = damping;
  }

  step(dt) {
    // Fixed small sub-steps: stable at any frame rate, and real-time even when frames are slow.
    let left = Math.min(dt, MAX_DT);
    while (left > 1e-6) {
      const h = Math.min(left, SUB_STEP);
      const accel = this.omega * this.omega * (this.target - this.value) - 2 * this.zeta * this.omega * this.velocity;
      this.velocity += accel * h;
      this.value += this.velocity * h;
      left -= h;
    }
    return this.value;
  }

  snap(value) {
    this.value = this.target = value;
    this.velocity = 0;
  }

  get settled() {
    return Math.abs(this.target - this.value) < 1e-4 && Math.abs(this.velocity) < 1e-3;
  }
}

/** Three independent springs: decomposing per axis keeps 3D motion in sync with each axis's own velocity. */
export class SpringVec3 {
  constructor(v, opts) {
    this.x = new Spring(v.x, opts);
    this.y = new Spring(v.y, opts);
    this.z = new Spring(v.z, opts);
    this.out = v.clone();
  }

  set(v) { this.x.target = v.x; this.y.target = v.y; this.z.target = v.z; }
  snap(v) { this.x.snap(v.x); this.y.snap(v.y); this.z.snap(v.z); }
  setParams(response, damping) { [this.x, this.y, this.z].forEach((s) => s.setParams(response, damping)); }
  step(dt) { return this.out.set(this.x.step(dt), this.y.step(dt), this.z.step(dt)); }
  get settled() { return this.x.settled && this.y.settled && this.z.settled; }
}

export const cm = (metres) => Math.round(metres * 100);
export const fmtArea = (m2) => `${m2.toFixed(1)} מ״ר`;

export function shoelace(poly) {
  let total = 0;
  for (let i = 0; i < poly.length; i += 1) {
    const [x1, y1] = poly[i];
    const [x2, y2] = poly[(i + 1) % poly.length];
    total += x1 * y2 - x2 * y1;
  }
  return Math.abs(total) / 2;
}

export function centroid(poly) {
  // Area centroid, so L-shaped rooms put their label inside the room.
  let a = 0; let cx = 0; let cy = 0;
  for (let i = 0; i < poly.length; i += 1) {
    const [x1, y1] = poly[i];
    const [x2, y2] = poly[(i + 1) % poly.length];
    const f = x1 * y2 - x2 * y1;
    a += f; cx += (x1 + x2) * f; cy += (y1 + y2) * f;
  }
  if (Math.abs(a) < 1e-9) return poly[0];
  return [cx / (3 * a), cy / (3 * a)];
}

export function bounds(points) {
  const xs = points.map((p) => p[0]);
  const ys = points.map((p) => p[1]);
  return { minX: Math.min(...xs), maxX: Math.max(...xs), minY: Math.min(...ys), maxY: Math.max(...ys) };
}

export function insidePoly([x, y], poly) {
  let hit = false;
  for (let i = 0, j = poly.length - 1; i < poly.length; j = i, i += 1) {
    const [xi, yi] = poly[i];
    const [xj, yj] = poly[j];
    if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) hit = !hit;
  }
  return hit;
}

export const el = (tag, cls, text) => {
  const node = document.createElement(tag);
  if (cls) node.className = cls;
  if (text != null) node.textContent = text;
  return node;
};
