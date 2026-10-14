// What you see through the windows: one generated view per compass side (scripts/views.py), hung as a ring of
// planes around the apartment far enough away for real parallax, horizon at eye level, swapped by time of day.
import * as THREE from 'three';
import { P } from '../viewer/util.js';

const DISTANCE_M = 32;            // far enough that walking past a window shifts the view believably
const EYE_M = 1.6;
const SIDES = { north: 0, east: 90, south: 180, west: 270 };
// Basic materials read as LDR; outdoors must outshine the room, and a sunset re-tints the day image.
const LOOK = { morning: ['#ffffff', 1.55], afternoon: ['#fff3e2', 1.6], sunset: ['#ffc596', 1.25], night: ['#ffffff', 1.0] };

const loader = new THREE.TextureLoader();
const load = (rel) => loader.loadAsync(new URL(rel, document.baseURI).href).then((t) => { t.colorSpace = THREE.SRGBColorSpace; return t; });

/** views: { north: {day, night}, ... } with page-relative paths. Missing sides borrow the nearest view. */
export async function buildOutside(views, center, northDeg) {
  const have = Object.keys(views).filter((k) => k in SIDES);
  if (!have.length) return null;
  const textures = {};
  await Promise.all(have.map(async (side) => {
    textures[side] = { day: await load(views[side].day), night: await load(views[side].night) };
  }));
  const group = new THREE.Group();
  const panels = [];
  const width = DISTANCE_M * 2;
  for (const [side, bearing] of Object.entries(SIDES)) {
    const source = have.includes(side) ? side : have.reduce((a, b) => (angleGap(SIDES[b], bearing) < angleGap(SIDES[a], bearing) ? b : a));
    const tex = textures[source];
    const height = width * (tex.day.image.height / tex.day.image.width);
    const mat = new THREE.MeshBasicMaterial({ map: tex.day, fog: false });
    const plane = new THREE.Mesh(new THREE.PlaneGeometry(width, height), mat);
    const planAngle = THREE.MathUtils.degToRad(bearing - northDeg);           // compass -> plan frame
    const dir = [Math.sin(planAngle), Math.cos(planAngle)];
    plane.position.copy(center).add(P(dir[0] * DISTANCE_M, dir[1] * DISTANCE_M, EYE_M));
    plane.lookAt(center.x, EYE_M, center.z);
    group.add(plane);
    panels.push({ mat, tex });
  }
  group.userData.setPart = (part) => {
    const [tint, gain] = LOOK[part] || LOOK.afternoon;
    for (const p of panels) {
      p.mat.map = part === 'night' ? p.tex.night : p.tex.day;
      p.mat.color.set(tint).multiplyScalar(gain);
      p.mat.needsUpdate = true;
    }
  };
  return group;
}

function angleGap(a, b) {
  const d = Math.abs(a - b) % 360;
  return d > 180 ? 360 - d : d;
}
