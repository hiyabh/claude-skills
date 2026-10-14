// First-person player for game mode: the viewer's Walker (collision, joystick, touch look) plus pointer-lock
// mouse look, Shift to run, a gentle head bob, and closed doors that block like walls.
import { Walker } from '../viewer/walk.js';
import { REDUCED_MOTION } from '../viewer/util.js';

const MOUSE_LOOK = 0.0022;     // radians per mouse count under pointer lock
const RUN_MUL = 1.9;
const BOB_AMPLITUDE_M = 0.022;
const BOB_STRIDE_M = 0.75;     // one up-down per stride
const PITCH_MAX = 1.35;

export class Player extends Walker {
  constructor(camera, dom, ui) {
    super(camera, dom, ui);
    this.locked = false;
    document.addEventListener('pointerlockchange', () => {
      this.locked = document.pointerLockElement === dom;
      ui.onLock?.(this.locked);
    });
    document.addEventListener('mousemove', (e) => {
      if (!this.active || !this.locked) return;
      this.yaw -= e.movementX * MOUSE_LOOK;                       // FPS convention under pointer lock
      this.pitch = Math.max(-PITCH_MAX, Math.min(PITCH_MAX, this.pitch - e.movementY * MOUSE_LOOK));
    });
    addEventListener('keydown', (e) => { if (e.code === 'ShiftLeft' || e.code === 'ShiftRight') this.speedMul = RUN_MUL; });
    addEventListener('keyup', (e) => { if (e.code === 'ShiftLeft' || e.code === 'ShiftRight') this.speedMul = 1; });
  }

  lock() {
    if (this.dom.requestPointerLock && !matchMedia('(pointer: coarse)').matches) this.dom.requestPointerLock();
  }

  bobHeight() {
    if (REDUCED_MOTION) return 0;
    return Math.sin((this.bob / BOB_STRIDE_M) * Math.PI * 2) * BOB_AMPLITUDE_M * Math.min(1, Math.hypot(...this.vel));
  }

  /** Closed doors join the collision set; open ones leave it. */
  setClosedDoors(segments) { this.extraSegments = segments; }
}
