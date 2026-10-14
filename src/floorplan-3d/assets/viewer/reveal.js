// The opening moment: the drawing lies flat, walls rise out of it, furniture follows, the camera lifts into 3D.
// Seen once per load, so it may take its time; it never blocks input and reduced motion skips straight to the end.
import { Spring, REDUCED_MOTION } from './util.js';

const WALL_WAVE = 0.9;         // seconds for the rise to travel across the plan
const FURNITURE_DELAY = 0.9;
const UNDERLAY_HOLD = 0.7;     // how long the bare drawing is shown first
const RISE = { response: 0.7, damping: 0.82 };   // a little give, like something settling into place
const FADE = { response: 0.6, damping: 1 };

export class Reveal {
  constructor() {
    this.items = [];
    this.fades = [];
    this.running = false;
  }

  /** walls: WallCutter items; furniture: Object3D[]; underlayMat: material whose opacity fades. */
  start({ cutter, furniture, underlayMat, center, span, onLift }) {
    if (REDUCED_MOTION) {
      if (underlayMat) underlayMat.opacity = 0;
      onLift(true);
      return;
    }
    this.running = true;
    this.clock = 0;
    this.onLift = onLift;
    for (const it of cutter.items) {
      const d = it.mid.distanceTo(center);
      it.s.snap(0.002);
      it.s.setParams(RISE.response, RISE.damping);
      it.hold = UNDERLAY_HOLD + (d / Math.max(span / 2, 1)) * WALL_WAVE;
    }
    this.cutter = cutter;
    furniture.forEach((obj, i) => {
      obj.scale.y = 0.002;
      this.items.push({ obj, s: new Spring(0.002, RISE), hold: UNDERLAY_HOLD + FURNITURE_DELAY + i * 0.025 });
    });
    if (underlayMat) {
      underlayMat.opacity = 1;
      this.fades.push({ mat: underlayMat, s: new Spring(1, FADE), hold: UNDERLAY_HOLD + WALL_WAVE + 0.4, to: 0 });
    }
  }

  /** Called every frame before the wall cutter. Returns true while walls are still held flat. */
  update(dt) {
    if (!this.running) return false;
    this.clock += dt;
    if (this.onLift && this.clock > UNDERLAY_HOLD * 0.6) { this.onLift(false); this.onLift = null; }
    let busy = false;
    for (const it of this.cutter.items) {
      if (it.hold != null && this.clock < it.hold) { it.s.snap(0.002); busy = true; }
      else if (it.hold != null) it.hold = null;   // released: the cutter's spring (RISE params) carries it up
    }
    for (const it of this.items) {
      if (this.clock < it.hold) { busy = true; continue; }
      it.obj.scale.y = it.s.step(dt);
      if (Math.abs(1 - it.obj.scale.y) > 1e-3 || Math.abs(it.s.velocity) > 1e-3) busy = true;
      it.s.target = 1;
    }
    for (const f of this.fades) {
      if (this.clock < f.hold) { busy = true; continue; }
      f.s.target = f.to;
      f.mat.opacity = f.s.step(dt);
      if (!f.s.settled) busy = true;
    }
    if (!busy) this.finish();
    return busy;
  }

  finish() {
    this.running = false;
    for (const it of this.items) it.obj.scale.y = 1;
    for (const f of this.fades) f.mat.opacity = f.to;
    for (const it of this.cutter.items) it.s.setParams(0.35, 1);
  }
}
