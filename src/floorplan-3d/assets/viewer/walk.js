// First-person walk: drag to look, WASD/arrows to move, a joystick on touch screens.
// Collision is a circle against wall segments and furniture footprints, in plan coordinates.
import { IS_TOUCH, insidePoly } from './util.js';
import { EYE_H } from './camera.js';

const RADIUS = 0.24;
const SPEED = 1.5;             // m/s, a calm indoor walk
const ACCEL = 9;               // how quickly velocity follows input
const LOOK = 0.0042;           // radians per pixel of drag
const PITCH_MAX = 1.2;
const OBSTACLE_MAX_Z = 1.2;    // items whose bottom is above this (upper cabinets) do not block
const MAX_STEP = 0.08;         // metres per collision sub-step: well under RADIUS, so slow frames cannot tunnel
const KEYS = { KeyW: [0, 1], ArrowUp: [0, 1], KeyS: [0, -1], ArrowDown: [0, -1], KeyA: [-1, 0], ArrowLeft: [-1, 0], KeyD: [1, 0], ArrowRight: [1, 0] };

function footprintSegments(item) {
  const [w, d] = item.size; const r = item.rot || 0;
  const fx = Math.cos(r); const fy = Math.sin(r);
  const pts = [[-1, -1], [1, -1], [1, 1], [-1, 1]].map(([a, o]) => [
    item.center[0] - fy * a * w / 2 + fx * o * d / 2, item.center[1] + fx * a * w / 2 + fy * o * d / 2]);
  return pts.map((p, i) => [...p, ...pts[(i + 1) % 4]]);
}

function pushOut(pos, seg) {
  const [ax, ay, bx, by] = seg;
  const dx = bx - ax; const dy = by - ay;
  const len2 = dx * dx + dy * dy || 1e-9;
  const t = Math.max(0, Math.min(1, ((pos[0] - ax) * dx + (pos[1] - ay) * dy) / len2));
  const qx = ax + dx * t; const qy = ay + dy * t;
  const ex = pos[0] - qx; const ey = pos[1] - qy;
  const dist = Math.hypot(ex, ey);
  if (dist >= RADIUS || dist < 1e-9) return;
  pos[0] = qx + (ex / dist) * RADIUS;
  pos[1] = qy + (ey / dist) * RADIUS;
}

export class Walker {
  constructor(camera, dom, ui) {
    Object.assign(this, { camera, dom, ui, active: false, yaw: 0, pitch: 0, vel: [0, 0], input: [0, 0], keys: new Set(), segments: [], rooms: [],
      speedMul: 1, bob: 0, extraSegments: [] });
    this.bind();
  }

  setWorld(collide, items, rooms) {
    const solid = items.filter((i) => (i.z || 0) < OBSTACLE_MAX_Z && i.kind !== 'rug' && i.tier !== 'counter');
    this.segments = [...collide, ...solid.flatMap(footprintSegments)];
    this.rooms = rooms;
  }

  enter(x, y, yaw) {
    Object.assign(this, { active: true, pos: [x, y], yaw, pitch: -0.05, vel: [0, 0] });
    this.ui.joy.hidden = !IS_TOUCH;
    this.ui.hud.hidden = false;
    this.ui.crosshair.hidden = false;
    this.apply();
  }

  exit() {
    this.active = false;
    this.keys.clear();
    this.ui.joy.hidden = this.ui.hud.hidden = this.ui.crosshair.hidden = true;
  }

  bind() {
    addEventListener('keydown', (e) => { if (this.active && KEYS[e.code]) { this.keys.add(e.code); e.preventDefault(); } });
    addEventListener('keyup', (e) => this.keys.delete(e.code));
    let last = null;
    this.dom.addEventListener('pointerdown', (e) => { if (this.active) { last = [e.clientX, e.clientY]; this.dom.setPointerCapture(e.pointerId); } });
    this.dom.addEventListener('pointermove', (e) => {
      if (!this.active || !last) return;
      // Grab-the-world: the scene follows the finger 1:1, as in Street View.
      this.yaw += (e.clientX - last[0]) * LOOK;
      this.pitch = Math.max(-PITCH_MAX, Math.min(PITCH_MAX, this.pitch + (e.clientY - last[1]) * LOOK));
      last = [e.clientX, e.clientY];
    });
    const end = () => { last = null; };
    this.dom.addEventListener('pointerup', end);
    this.dom.addEventListener('pointercancel', end);
    this.bindJoystick();
  }

  bindJoystick() {
    const pad = this.ui.joy; const knob = pad.firstElementChild;
    let origin = null;
    const reset = () => { origin = null; this.input = [0, 0]; knob.style.transform = ''; };
    pad.addEventListener('pointerdown', (e) => { pad.setPointerCapture(e.pointerId); const r = pad.getBoundingClientRect(); origin = [r.left + r.width / 2, r.top + r.height / 2]; });
    pad.addEventListener('pointermove', (e) => {
      if (!origin) return;
      const max = pad.clientWidth / 2 - 10;
      let dx = e.clientX - origin[0]; let dy = e.clientY - origin[1];
      const k = Math.min(1, max / (Math.hypot(dx, dy) || 1));
      dx *= k; dy *= k;
      knob.style.transform = `translate(${dx}px, ${dy}px)`;   // 1:1 with the finger
      this.input = [dx / max, -dy / max];
    });
    pad.addEventListener('pointerup', reset);
    pad.addEventListener('pointercancel', reset);
  }

  wish() {
    let [sx, sy] = this.input;
    for (const k of this.keys) { sx += KEYS[k][0]; sy += KEYS[k][1]; }
    const mag = Math.hypot(sx, sy);
    if (mag > 1) { sx /= mag; sy /= mag; }
    // Forward in plan coordinates for the current yaw (yaw 0 = looking north).
    const fx = -Math.sin(this.yaw); const fy = Math.cos(this.yaw);
    const speed = SPEED * this.speedMul;
    return [(fx * sy + fy * sx) * speed, (fy * sy - fx * sx) * speed];
  }

  update(dt) {
    if (!this.active) return;
    const [wx, wy] = this.wish();
    const k = 1 - Math.exp(-ACCEL * dt);
    this.vel[0] += (wx - this.vel[0]) * k;
    this.vel[1] += (wy - this.vel[1]) * k;
    const dx = this.vel[0] * dt; const dy = this.vel[1] * dt;
    const steps = Math.max(1, Math.ceil(Math.hypot(dx, dy) / MAX_STEP));
    for (let i = 0; i < steps; i += 1) {
      this.pos[0] += dx / steps;
      this.pos[1] += dy / steps;
      for (const s of this.segments) pushOut(this.pos, s);
      for (const s of this.extraSegments) pushOut(this.pos, s);   // e.g. doors closed in game mode
    }
    this.bob += Math.hypot(this.vel[0], this.vel[1]) * dt;
    this.apply();
  }

  /** Head bob, in metres; zero unless a subclass wants it (the viewer's walk stays steady). */
  bobHeight() { return 0; }

  apply() {
    this.camera.position.set(this.pos[0], EYE_H + this.bobHeight(), -this.pos[1]);
    this.camera.rotation.set(this.pitch, this.yaw, 0, 'YXZ');
    const room = this.rooms.find((r) => insidePoly(this.pos, r.polygon));
    if (room && this.ui.room.textContent !== room.label) this.ui.room.textContent = room.label;
  }
}
