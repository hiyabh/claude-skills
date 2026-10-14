import { Sky } from 'three/addons/objects/Sky.js';

const META = { title: 'סימולטור F-16', subtitle: 'המראה, הקפה ונחיתה. גררו לסיבוב המצלמה, גלגלו לזום.' };
const TIMELINE = { duration: 1, loop: true, speeds: [1, 2, 4, 8], speed: 2 }; // duration is computed in buildScene
const CONTROLS = [
  { id: 'throttle', type: 'range', label: 'מצערת', min: 0, max: 100, step: 1, value: 90, unit: '%' },
  { id: 'sun', type: 'range', label: 'גובה השמש', min: -4, max: 45, step: 0.5, value: 8, unit: '°' },
  { id: 'chase', type: 'toggle', label: 'מצלמה צמודה למטוס', value: true },
];
const READOUTS = [
  { id: 'phase', label: 'שלב' },
  { id: 'alt', label: 'גובה', unit: 'ft' },
  { id: 'kt', label: 'מהירות', unit: 'kt' },
  { id: 'bank', label: 'הטיה', unit: '°' },
];
const INFO = [
  '<p>בהדמיה הזו, מצערת מעל 85% מדליקה את המבער האחורי (אפטרברנר): דלק נוסף מרוסס לגזי הפליטה ונשרף בהם, ולכן נראית להבה מאחורי המנוע. המצערת גם מאיצה את המטוס.</p>',
  '<p>זווית ההטיה בפניות מחושבת מהפיזיקה של פנייה מאוזנת: <code>tan φ = v²κ / g</code>, כאשר κ היא עקמומיות המסלול.</p>',
  '<p>הורידו את השמש מתחת ל-5° כדי לראות שקיעה ואת אורות המסלול.</p>',
].join('');
const CAMERA = { position: [-1172, 6.5, -15], target: [-1150, 2.35, 0], fov: 50, near: 0.5, far: 60000 };

// --- Flight model (metres, m/s) ---
const G = 9.81;
const MS_TO_KT = 1.94384;
const M_TO_FT = 3.28084;
const WHEEL_H = 2.35;            // fuselage centre height with the gear on the runway
const AB_THRESHOLD = 85;         // throttle % that lights the afterburner
const THROTTLE_REF = 70;         // throttle % at which the timeline runs in real time
const LIFTOFF_D = 900;           // takeoff roll length
const CLIMB_D = 4000;            // distance by which pattern speed is reached
const APPROACH_D = 6500;         // final approach starts this far before the stop point
const ROLLOUT_D = 1100;          // landing rollout length
const V_LIFTOFF = 85, V_PATTERN = 165, V_TOUCHDOWN = 72, V_MIN = 2;
const GEAR_AGL = 150;
const AOA_APPROACH = THREE.MathUtils.degToRad(13);
const MAX_BANK = THREE.MathUtils.degToRad(75);
const BANK_WINDOW = 150;         // metres either side used to measure curvature
const SAMPLES = 4000;
const SUN_AZIMUTH = 235;
// Left-hand pattern around a runway that lies along +X. [x, height above ground, z]
const ROUTE = [
  [-1150, 0, 0], [-600, 0, 0], [-250, 3, 0], [900, 120, 0], [2600, 380, -500],
  [3200, 500, -2100], [1500, 500, -3300], [-2000, 500, -3300], [-4300, 450, -3000],
  [-5400, 350, -1500], [-4800, 260, 0], [-3000, 160, 0], [-1300, 15, 0], [-600, 0, 0],
  [200, 0, 0], [500, 0, 0],
];

const PAINT = new THREE.MeshStandardMaterial({ color: 0x8e979f, roughness: 0.55, metalness: 0.35, side: THREE.DoubleSide });
const DARK_METAL = new THREE.MeshStandardMaterial({ color: 0x3d3f42, roughness: 0.4, metalness: 0.8 });
const RUBBER = new THREE.MeshStandardMaterial({ color: 0x151515, roughness: 0.9 });
const CANOPY = new THREE.MeshStandardMaterial({ color: 0xb08d3c, roughness: 0.12, metalness: 0.9, transparent: true, opacity: 0.85 });
const MISSILE = new THREE.MeshStandardMaterial({ color: 0xd9d9d6, roughness: 0.5 });
const SKY_NIGHT = new THREE.Color(0x0d1424), SKY_DUSK = new THREE.Color(0x8c6a5c), SKY_DAY = new THREE.Color(0xb9c9d9);
const SUN_LOW = new THREE.Color(0xff9a5a), SUN_HIGH = new THREE.Color(0xfff6ea);
const P = new THREE.Vector3(), T = new THREE.Vector3(), TA = new THREE.Vector3(), TB = new THREE.Vector3();

const lerp = THREE.MathUtils.lerp;
const clamp01 = (x) => THREE.MathUtils.clamp(x, 0, 1);

function rng(seed) {
  return () => {
    seed = (seed + 0x6d2b79f5) | 0;
    let r = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    r = (r + Math.imul(r ^ (r >>> 7), 61 | r)) ^ r;
    return ((r ^ (r >>> 14)) >>> 0) / 4294967296;
  };
}

function part(geo, mat, pos = [0, 0, 0]) {
  const mesh = new THREE.Mesh(geo, mat);
  mesh.position.fromArray(pos);
  return mesh;
}

function flatShape(points, mirror = false) {
  const shape = new THREE.Shape(points.map(([x, y]) => new THREE.Vector2(mirror ? -x : x, y)));
  return new THREE.ExtrudeGeometry(shape, { depth: 0.12, bevelEnabled: false });
}

// --- Jet (nose along +Z, real F-16 proportions: 15 m long, ~10 m span) ---
function buildFuselage() {
  const g = new THREE.Group();
  g.add(part(new THREE.CylinderGeometry(0.72, 0.62, 11, 20).rotateX(Math.PI / 2), PAINT));
  g.add(part(new THREE.ConeGeometry(0.72, 3.4, 20).rotateX(Math.PI / 2), PAINT, [0, 0, 7.2]));
  g.add(part(new THREE.BoxGeometry(1.4, 0.9, 3), PAINT, [0, -0.9, 2.6]));
  g.add(part(new THREE.BoxGeometry(1.2, 0.7, 0.05), RUBBER, [0, -0.9, 4.12]));
  g.add(part(new THREE.CylinderGeometry(0.58, 0.5, 1.1, 20).rotateX(Math.PI / 2), DARK_METAL, [0, 0, -6]));
  g.add(part(new THREE.SphereGeometry(0.6, 20, 14).scale(1, 0.85, 2.7), CANOPY, [0, 0.55, 3.8]));
  return g;
}

function buildLiftingSurfaces() {
  const g = new THREE.Group();
  const wing = [[0.6, 5.0], [1.2, 2.6], [4.9, -1.9], [4.9, -3.0], [0.6, -3.6]];
  const stab = [[0.5, -3.9], [3.0, -5.6], [3.0, -6.3], [0.5, -6.2]];
  const fin = [[-2.0, 0.6], [-4.6, 4.1], [-5.5, 4.1], [-5.8, 0.6]];
  for (const mirror of [false, true]) {
    g.add(part(flatShape(wing, mirror).rotateX(Math.PI / 2), PAINT, [0, 0.05, 0]));
    g.add(part(flatShape(stab, mirror).rotateX(Math.PI / 2), PAINT, [0, -0.15, 0]));
    const side = mirror ? -1 : 1;
    g.add(part(new THREE.CylinderGeometry(0.065, 0.065, 2.9, 8).rotateX(Math.PI / 2), MISSILE, [side * 5.0, -0.05, -1.6]));
  }
  g.add(part(flatShape(fin).rotateY(-Math.PI / 2).translate(0.06, 0, 0), PAINT));
  return g;
}

function buildGear() {
  const g = new THREE.Group();
  for (const [x, z] of [[0, 3.6], [1.1, -0.6], [-1.1, -0.6]]) {
    g.add(part(new THREE.CylinderGeometry(0.08, 0.08, 1.4, 8), DARK_METAL, [x, -1.35, z]));
    g.add(part(new THREE.CylinderGeometry(0.35, 0.35, 0.22, 16).rotateZ(Math.PI / 2), RUBBER, [x, -2.0, z]));
  }
  return g;
}

function flameCone(radius, length, color, opacity) {
  const geo = new THREE.ConeGeometry(radius, length, 20, 1, true).rotateX(-Math.PI / 2).translate(0, 0, -length / 2);
  const mat = new THREE.MeshBasicMaterial({ color, transparent: true, opacity, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide });
  return new THREE.Mesh(geo, mat);
}

function buildExhaust() {
  const flame = new THREE.Group();
  flame.add(flameCone(0.55, 7, 0xff6a1a, 0.55), flameCone(0.35, 4, 0xffe2a8, 0.9));
  const diamondMat = new THREE.MeshBasicMaterial({ color: 0xffc77a, transparent: true, opacity: 0.8, blending: THREE.AdditiveBlending, depthWrite: false });
  for (const z of [-1.2, -2.4, -3.6]) flame.add(part(new THREE.SphereGeometry(0.22, 12, 8), diamondMat, [0, 0, z]));
  const light = new THREE.PointLight(0xff8a3c, 0, 80, 2);
  const exhaust = new THREE.Group();
  exhaust.position.z = -6.55;
  exhaust.add(flame, light);
  return { exhaust, flame, light };
}

function buildJet() {
  const jet = new THREE.Group();
  const gear = buildGear();
  const { exhaust, flame, light } = buildExhaust();
  jet.add(buildFuselage(), buildLiftingSurfaces(), gear, exhaust);
  return { jet, gear, flame, light };
}

// --- Airfield ---
function instanced(geo, mat, positions) {
  const mesh = new THREE.InstancedMesh(geo, mat, positions.length);
  const m = new THREE.Matrix4();
  positions.forEach(([x, y, z, s = 1], i) => mesh.setMatrixAt(i, m.makeScale(s, s, s).setPosition(x, y, z)));
  return mesh;
}

function buildRunway() {
  const g = new THREE.Group();
  const asphalt = new THREE.MeshStandardMaterial({ color: 0x3a3d41, roughness: 0.95 });
  const paint = new THREE.MeshStandardMaterial({ color: 0xe8e8e2, roughness: 0.8 });
  g.add(part(new THREE.PlaneGeometry(2600, 45).rotateX(-Math.PI / 2), asphalt, [0, 0.05, 0]));
  const dashes = [];
  for (let x = -1180; x <= 1180; x += 60) dashes.push([x, 0.08, 0]);
  g.add(instanced(new THREE.PlaneGeometry(30, 0.9).rotateX(-Math.PI / 2), paint, dashes));
  const keys = [];
  for (const x of [-1270, 1270]) for (let z = -18; z <= 18; z += 4.5) keys.push([x, 0.08, z]);
  g.add(instanced(new THREE.PlaneGeometry(30, 1.8).rotateX(-Math.PI / 2), paint, keys));
  const lights = [];
  for (let x = -1300; x <= 1300; x += 60) lights.push([x, 0.4, 24], [x, 0.4, -24]);
  const lamp = new THREE.MeshStandardMaterial({ color: 0xfff1c9, emissive: 0xffe7b0, emissiveIntensity: 2 });
  g.add(instanced(new THREE.SphereGeometry(0.4, 8, 6), lamp, lights));
  return { runway: g, lamp };
}

function buildSurroundings() {
  const g = new THREE.Group();
  const sand = new THREE.MeshStandardMaterial({ color: 0xc9b184, roughness: 1 });
  g.add(part(new THREE.PlaneGeometry(80000, 80000).rotateX(-Math.PI / 2), sand));
  const concrete = new THREE.MeshStandardMaterial({ color: 0x9b9486, roughness: 0.9, side: THREE.DoubleSide });
  const shelter = new THREE.CylinderGeometry(12, 12, 30, 20, 1, true, 0, Math.PI).rotateX(Math.PI / 2).rotateZ(Math.PI / 2);
  for (const x of [-700, -600, -500, -400]) g.add(part(shelter, concrete, [x, 0, 320]));
  const random = rng(7);
  const shrubs = [];
  while (shrubs.length < 1200) {
    const x = (random() - 0.5) * 16000, z = (random() - 0.5) * 16000;
    if (Math.abs(z) > 120 || Math.abs(x) > 1500) shrubs.push([x, 1.5, z, 0.6 + random() * 1.6]);
  }
  g.add(instanced(new THREE.ConeGeometry(1.6, 3, 6), new THREE.MeshStandardMaterial({ color: 0x6b6a3a, roughness: 1 }), shrubs));
  return g;
}

function buildSky(scene) {
  const sky = new Sky();
  sky.scale.setScalar(450000);
  const u = sky.material.uniforms;
  u.turbidity.value = 10;
  u.rayleigh.value = 3;
  u.mieCoefficient.value = 0.005;
  u.mieDirectionalG.value = 0.7;
  scene.add(sky);
  const sun = new THREE.DirectionalLight(0xffffff, 3);
  const hemi = new THREE.HemisphereLight(0xcfe0ff, 0x6d5a3e, 1);
  scene.add(sun, hemi);
  scene.fog = new THREE.Fog(SKY_DAY.clone(), 3000, 25000);
  return { sky, sun, hemi };
}

// --- Speed profile: v(d) along the route, integrated into a time table ---
function speedAt(d, L) {
  const toEnd = L - d;
  if (d < LIFTOFF_D) return Math.max(V_MIN, V_LIFTOFF * Math.sqrt(d / LIFTOFF_D));
  if (toEnd < ROLLOUT_D) return Math.max(V_MIN, V_TOUCHDOWN * Math.sqrt(toEnd / ROLLOUT_D));
  if (d < CLIMB_D) return lerp(V_LIFTOFF, V_PATTERN, (d - LIFTOFF_D) / (CLIMB_D - LIFTOFF_D));
  if (toEnd > APPROACH_D) return V_PATTERN;
  return lerp(V_TOUCHDOWN, V_PATTERN, (toEnd - ROLLOUT_D) / (APPROACH_D - ROLLOUT_D));
}

function buildProfile(curve) {
  const L = curve.getLength();
  const times = new Float64Array(SAMPLES + 1);
  for (let i = 1; i <= SAMPLES; i++) {
    times[i] = times[i - 1] + L / SAMPLES / speedAt(((i - 0.5) / SAMPLES) * L, L);
  }
  return { L, times, duration: times[SAMPLES] };
}

function arcAt({ times }, t) {
  let lo = 0, hi = SAMPLES;
  while (hi - lo > 1) {
    const mid = (lo + hi) >> 1;
    if (times[mid] <= t) lo = mid; else hi = mid;
  }
  const span = times[hi] - times[lo] || 1;
  return clamp01((lo + (t - times[lo]) / span) / SAMPLES);
}

function phaseAt(d, L) {
  const toEnd = L - d;
  if (d < LIFTOFF_D) return 'גלגול המראה';
  if (toEnd < ROLLOUT_D) return toEnd < 40 ? 'עצירה' : 'נגיעה ובלימה';
  if (d < CLIMB_D) return 'טיפוס';
  if (toEnd < APPROACH_D) return 'גישה סופית';
  return 'הקפה';
}

// Coordinated-turn bank: tan(phi) = v^2 * kappa / g, kappa measured over a fixed window.
function bankAt(curve, L, s, v) {
  const w = BANK_WINDOW / L;
  curve.getTangentAt(Math.max(0, s - w), TA);
  curve.getTangentAt(Math.min(1, s + w), TB);
  const cross = TA.z * TB.x - TA.x * TB.z; // > 0 means a left turn
  const kappa = Math.abs(cross) / (2 * BANK_WINDOW);
  return -Math.sign(cross) * Math.min(MAX_BANK, Math.atan((v * v * kappa) / G));
}

function throttleScale(throttle) {
  return 0.4 + (0.6 * throttle) / THROTTLE_REF;
}

function applySun(ctx, state, elevation) {
  const dir = new THREE.Vector3().setFromSphericalCoords(1, THREE.MathUtils.degToRad(90 - elevation), THREE.MathUtils.degToRad(SUN_AZIMUTH));
  state.sky.material.uniforms.sunPosition.value.copy(dir);
  const day = THREE.MathUtils.smoothstep(elevation, -3, 18);
  state.sun.position.copy(dir).multiplyScalar(100);
  state.sun.intensity = 3.2 * THREE.MathUtils.smoothstep(elevation, -2, 10);
  state.sun.color.lerpColors(SUN_LOW, SUN_HIGH, THREE.MathUtils.smoothstep(elevation, 0, 25));
  state.hemi.intensity = 0.4 + day;
  ctx.renderer.toneMappingExposure = 0.45 + 0.3 * day;
  ctx.scene.fog.color.lerpColors(SKY_NIGHT, SKY_DUSK, THREE.MathUtils.smoothstep(elevation, -4, 2));
  ctx.scene.fog.color.lerp(SKY_DAY, THREE.MathUtils.smoothstep(elevation, 4, 20));
  state.lamp.emissiveIntensity = 1 + 5 * (1 - day);
}

function buildScene(ctx) {
  const { scene, params, controls } = ctx;
  controls.maxPolarAngle = Math.PI / 2 - 0.02;
  controls.minDistance = 6;
  controls.maxDistance = 20000;
  const curve = new THREE.CatmullRomCurve3(ROUTE.map(([x, h, z]) => new THREE.Vector3(x, h, z)), false, 'centripetal');
  curve.arcLengthDivisions = 4000;
  const profile = buildProfile(curve);
  TIMELINE.duration = profile.duration;
  const { runway, lamp } = buildRunway();
  scene.add(runway, buildSurroundings());
  const state = { curve, profile, lamp, ...buildJet(), ...buildSky(scene) };
  scene.add(state.jet);
  applySun(ctx, state, params.sun);
  ctx.timeScale = throttleScale(params.throttle);
  return state;
}

function placeJet(state, s, v) {
  const { jet, curve, profile } = state;
  curve.getPointAt(s, P);
  curve.getTangentAt(s, T);
  const agl = Math.max(0, P.y);
  const toEnd = profile.L * (1 - s);
  jet.position.set(P.x, WHEEL_H + agl, P.z);
  T.y = agl > 0.5 ? T.y : 0;
  jet.lookAt(P.set(jet.position.x + T.x, jet.position.y + T.y, jet.position.z + T.z));
  const bank = agl > 3 ? bankAt(curve, profile.L, s, v) : 0;
  jet.rotateZ(bank);
  jet.rotateX(-AOA_APPROACH * clamp01((APPROACH_D - toEnd) / 1000) * clamp01(agl / 2));
  state.gear.visible = agl < GEAR_AGL || toEnd < APPROACH_D;
  return { agl, bank };
}

function updateExhaust(state, throttle) {
  const afterburner = throttle > AB_THRESHOLD;
  const flicker = 1 + 0.07 * Math.sin(performance.now() * 0.05) + 0.05 * Math.random();
  const level = afterburner ? 1 : (throttle / 100) * 0.25;
  state.flame.visible = level > 0.02;
  state.flame.scale.set(1, 1, Math.max(0.01, level * flicker));
  state.light.intensity = afterburner ? 300 * flicker : 0;
}

function update(ctx, state, t) {
  const s = arcAt(state.profile, Math.min(t, state.profile.duration));
  const d = s * state.profile.L;
  const v = speedAt(d, state.profile.L) * ctx.timeScale;
  const { agl, bank } = placeJet(state, s, v);
  updateExhaust(state, ctx.params.throttle);
  if (ctx.params.chase) ctx.follow(state.jet.position); else ctx.unfollow();
  ctx.readout('phase', phaseAt(d, state.profile.L));
  ctx.readout('alt', Math.round(agl * M_TO_FT).toLocaleString('en-US'));
  ctx.readout('kt', Math.round(v * MS_TO_KT));
  ctx.readout('bank', Math.round(Math.abs(THREE.MathUtils.radToDeg(bank))));
}

function onParam(ctx, state, id, value) {
  if (id === 'sun') applySun(ctx, state, value);
  if (id === 'throttle') ctx.timeScale = throttleScale(value);
}
