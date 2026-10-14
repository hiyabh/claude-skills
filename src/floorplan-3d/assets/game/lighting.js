// Light by the clock: a sun placed by hour and the plan's north, an HDRI sky per part of day, an interior probe
// captured inside the main room (a cheap second bounce), and warm ceiling lights after dark.
import * as THREE from 'three';
import { P } from '../viewer/util.js';

const LAT_RAD = THREE.MathUtils.degToRad(31.8);    // Israel
const DECLINATION_RAD = THREE.MathUtils.degToRad(5); // early autumn; enough for believable sun angles
const SUN_DISTANCE = 30;
const PROBE_HEIGHT = 1.4;
const NIGHT_LIGHT = { color: '#ffe3c4', intensity: 6.5, distance: 7, decay: 2 };
// Per part of day: sky, how strongly the sky lights the interior, and whether ceiling lights are on.
const LOOK = {
  // grade: the colour boost suits daylight; warm lamps already saturate, so night is graded almost neutral
  morning: { env: 1.0, probe: 1.35, lamps: false, grade: { saturation: 0.22, contrast: 0.1 } },
  afternoon: { env: 1.0, probe: 1.35, lamps: false, grade: { saturation: 0.22, contrast: 0.1 } },
  sunset: { env: 0.8, probe: 1.0, lamps: false, grade: { saturation: 0.12, contrast: 0.08 } },
  night: { env: 0.1, probe: 0.75, lamps: true, grade: { saturation: -0.05, contrast: 0.06 } },
};
const BEST_LIGHT_HOURS = [8, 9, 10, 11, 12, 13, 14, 15, 16, 17];
const PARTS = [
  { until: 6, hdri: 'night' }, { until: 11, hdri: 'morning' }, { until: 16.5, hdri: 'afternoon' },
  { until: 19, hdri: 'sunset' }, { until: 24.1, hdri: 'night' },
];

/** Solar elevation/azimuth (radians, azimuth from north clockwise) for a local solar hour. */
export function sunAngles(hour) {
  const h = THREE.MathUtils.degToRad((hour - 12) * 15);
  const sinEl = Math.sin(LAT_RAD) * Math.sin(DECLINATION_RAD) + Math.cos(LAT_RAD) * Math.cos(DECLINATION_RAD) * Math.cos(h);
  const el = Math.asin(sinEl);
  const az = Math.atan2(Math.sin(h), Math.cos(h) * Math.sin(LAT_RAD) - Math.tan(DECLINATION_RAD) * Math.cos(LAT_RAD)) + Math.PI;
  return { el, az };
}

export class Lighting {
  constructor({ scene, renderer, hdris, plan, center, span, shadowSize }) {
    Object.assign(this, { scene, renderer, hdris, plan, center, span, envCache: {}, hour: 10 });
    this.pmrem = new THREE.PMREMGenerator(renderer);
    this.northRad = THREE.MathUtils.degToRad(plan.meta?.north_deg || 0);
    this.sun = new THREE.DirectionalLight('#fff1dc', 4.2);
    this.sun.castShadow = true;
    this.sun.shadow.mapSize.set(shadowSize, shadowSize);
    this.sun.shadow.bias = -0.0002;
    this.sun.shadow.normalBias = 0.025;
    const r = span * 0.75 + 2;
    Object.assign(this.sun.shadow.camera, { left: -r, right: r, top: r, bottom: -r, near: 1, far: SUN_DISTANCE * 2.5 });
    scene.add(this.sun, this.sun.target);
    this.sun.target.position.copy(center);
    this.roomLights = [];
  }

  envFor(name) {
    if (!this.envCache[name]) this.envCache[name] = this.pmrem.fromEquirectangular(this.hdris[name]).texture;
    return this.envCache[name];
  }

  partOfDay(hour) { return PARTS.find((p) => hour < p.until).hdri; }

  /** Ceiling lights per room (shadows only where the player is, to stay within budget). */
  addRoomLights(rooms, ceilingH, centroids) {
    for (const room of rooms) {
      if (room.ceiling === false) continue;
      const [x, y] = centroids[room.id];
      const light = new THREE.PointLight(NIGHT_LIGHT.color, 0, NIGHT_LIGHT.distance, NIGHT_LIGHT.decay);
      light.position.copy(P(x, y, (room.ceiling_height || ceilingH) - 0.35));
      light.shadow.mapSize.set(512, 512);
      light.shadow.bias = -0.001;
      light.userData.room = room.id;
      this.scene.add(light);
      this.roomLights.push(light);
    }
  }

  setTime(hour) {
    this.hour = hour;
    const { el, az } = sunAngles(hour);
    const day = el > 0.02;
    const worldAz = az - this.northRad;                       // plan north may be rotated on the sheet
    const dir = new THREE.Vector3(Math.sin(worldAz) * Math.cos(el), Math.sin(el), -Math.cos(worldAz) * Math.cos(el));
    this.sun.position.copy(this.center).addScaledVector(dir, SUN_DISTANCE);
    this.sun.visible = day;
    const warm = THREE.MathUtils.clamp(el / 0.6, 0, 1);       // low sun = warmer, dimmer
    this.sun.color.setHSL(0.085, 0.9 - warm * 0.45, 0.64 + warm * 0.14);   // warm even at noon: the look is Mediterranean
    this.sun.intensity = day ? 3 + warm * 5 : 0;
    const part = this.partOfDay(hour);
    this.part = part;
    this.scene.background = this.hdris[part];
    this.scene.backgroundIntensity = part === 'night' ? 0.35 : 1;
    this.scene.environment = this.envFor(part);
    this.scene.environmentIntensity = LOOK[part].env;
    this.setLamps(LOOK[part].lamps);
    this.onGrade?.(LOOK[part].grade);
    this.onPart?.(part);
    this.needsProbe = true;
  }

  setLamps(on) {
    this.lampsOn = on;
    for (const l of this.roomLights) this.setRoomLight(l, on);
  }

  setRoomLight(light, on) {
    light.intensity = on ? NIGHT_LIGHT.intensity : 0;
    light.userData.on = on;
    this.onRoomLamp?.(light.userData.room, on);
  }

  roomOn(roomId) { return !!this.roomLights.find((l) => l.userData.room === roomId)?.userData.on; }

  toggleRoom(roomId) {
    const light = this.roomLights.find((l) => l.userData.room === roomId);
    if (light) this.setRoomLight(light, !light.userData.on);
  }

  /** Only the light in the player's room casts shadows: point-light shadows are six renders each. */
  shadowRoom(roomId) {
    for (const l of this.roomLights) l.castShadow = l.userData.on && l.userData.room === roomId;
  }

  /** Re-light from inside: render a cube at the main room and use it as the environment (second bounce). */
  captureProbe(at) {
    if (!this.needsProbe) return;
    this.needsProbe = false;
    const cubeRT = new THREE.WebGLCubeRenderTarget(256, { type: THREE.HalfFloatType });
    const cam = new THREE.CubeCamera(0.05, 60, cubeRT);
    cam.position.copy(at).setY(PROBE_HEIGHT);
    cam.update(this.renderer, this.scene);
    const env = this.pmrem.fromCubemap(cubeRT.texture).texture;
    cubeRT.dispose();
    this.probeEnv?.dispose();
    this.probeEnv = env;
    this.scene.environment = env;
    this.scene.environmentIntensity = LOOK[this.part].probe;
  }

  /** The hour whose sun shines most directly through these windows (outward normals, plan x/y). */
  bestHour(windowNormals) {
    let best = { hour: 10, score: -Infinity };
    for (const hour of BEST_LIGHT_HOURS) {
      const { el, az } = sunAngles(hour);
      const worldAz = az - this.northRad;
      const sun = [Math.sin(worldAz) * Math.cos(el), Math.cos(worldAz) * Math.cos(el)];   // plan x east, y north
      const into = Math.max(0, ...windowNormals.map(([nx, ny]) => nx * sun[0] + ny * sun[1]));
      const score = into * Math.sin(Math.min(el, 0.7));                                  // low but not grazing sun
      if (score > best.score) best = { hour, score };
    }
    return best.hour;
  }
}
