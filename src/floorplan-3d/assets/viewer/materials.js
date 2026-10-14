// Materials and finish presets. Every texture is drawn on a <canvas>: the Artifact sandbox cannot fetch images.
import * as THREE from 'three';

const TEX_SIZE = 512;

export const FINISHES = {
  floor: [
    { id: 'oak', label: 'פרקט אלון', swatch: '#c9a27a' },
    { id: 'porcelain', label: 'פורצלן בהיר', swatch: '#e4e0da' },
    { id: 'concrete', label: 'בטון מוחלק', swatch: '#a9a7a3' },
  ],
  cabinet: [
    { id: 'oak', label: 'אלון טבעי', swatch: '#d7b98f' },
    { id: 'white', label: 'לבן מט', swatch: '#f1efea' },
    { id: 'walnut', label: 'אגוז', swatch: '#7a553a' },
    { id: 'graphite', label: 'גרפיט', swatch: '#3d4146' },
  ],
  counter: [
    { id: 'quartz', label: 'קוורץ לבן', swatch: '#f3f2ef' },
    { id: 'concrete', label: 'בטון', swatch: '#9c9a96' },
    { id: 'nero', label: 'שיש שחור', swatch: '#26272a' },
  ],
};

function canvas(draw) {
  const c = document.createElement('canvas');
  c.width = c.height = TEX_SIZE;
  draw(c.getContext('2d'), TEX_SIZE);
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
  tex.anisotropy = 8;
  return tex;
}

// Deterministic noise, so the textures look the same on every load.
function rng(seed) {
  let s = seed >>> 0;
  return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296);
}

function woodPlanks(base, seed) {
  return canvas((g, n) => {
    const r = rng(seed);
    const plankH = n / 6;
    for (let row = 0; row < 6; row += 1) {
      const shade = 0.9 + r() * 0.16;
      g.fillStyle = shadeHex(base, shade);
      g.fillRect(0, row * plankH, n, plankH);
      for (let k = 0; k < 26; k += 1) {
        g.strokeStyle = `rgba(60,35,15,${0.04 + r() * 0.06})`;
        g.lineWidth = 1 + r() * 2;
        const y = row * plankH + r() * plankH;
        g.beginPath(); g.moveTo(0, y); g.bezierCurveTo(n * 0.3, y + r() * 6 - 3, n * 0.7, y + r() * 6 - 3, n, y); g.stroke();
      }
      g.fillStyle = 'rgba(40,25,10,0.35)';
      g.fillRect(0, row * plankH, n, 1.5);
      g.fillRect(((row * 0.37 + r() * 0.3) % 1) * n, row * plankH, 1.5, plankH);
    }
  });
}

/** Continuous vertical grain, no plank joints: what a cabinet front actually looks like. */
function veneer(base, seed) {
  return canvas((g, n) => {
    const r = rng(seed);
    g.fillStyle = base; g.fillRect(0, 0, n, n);
    for (let k = 0; k < 70; k += 1) {
      g.strokeStyle = `rgba(70,40,15,${0.03 + r() * 0.07})`;
      g.lineWidth = 0.8 + r() * 2.2;
      const x = r() * n; const sway = 4 + r() * 10;
      g.beginPath(); g.moveTo(x, 0); g.bezierCurveTo(x + sway, n * 0.33, x - sway, n * 0.66, x + r() * 4, n); g.stroke();
    }
  });
}

function tiles(base, grout, count, seed) {
  return canvas((g, n) => {
    const r = rng(seed);
    const s = n / count;
    g.fillStyle = grout; g.fillRect(0, 0, n, n);
    for (let i = 0; i < count; i += 1) {
      for (let j = 0; j < count; j += 1) {
        g.fillStyle = shadeHex(base, 0.97 + r() * 0.05);
        g.fillRect(i * s + 1.5, j * s + 1.5, s - 3, s - 3);
      }
    }
  });
}

function speckle(base, dark, seed) {
  return canvas((g, n) => {
    const r = rng(seed);
    g.fillStyle = base; g.fillRect(0, 0, n, n);
    for (let k = 0; k < 2600; k += 1) {
      g.fillStyle = `rgba(${dark},${0.04 + r() * 0.1})`;
      g.fillRect(r() * n, r() * n, 1 + r() * 2.5, 1 + r() * 2.5);
    }
    g.strokeStyle = `rgba(${dark},0.08)`;
    for (let k = 0; k < 7; k += 1) {
      g.lineWidth = 0.6 + r();
      g.beginPath(); g.moveTo(r() * n, 0); g.bezierCurveTo(r() * n, n * 0.4, r() * n, n * 0.6, r() * n, n); g.stroke();
    }
  });
}

function shadeHex(hex, k) {
  const c = new THREE.Color(hex).multiplyScalar(k);
  return `#${c.getHexString()}`;
}

const std = (opts) => new THREE.MeshStandardMaterial({ roughness: 0.8, metalness: 0, ...opts });

/** One shared material set; finishes swap textures/colours in place so meshes never need rebuilding. */
function createTextures() {
  return {
    oak: woodPlanks('#c39a6b', 7), porcelain: tiles('#e7e3dd', '#cfcac2', 4, 3), concrete: speckle('#a6a49f', '60,60,60', 5),
    bathTile: tiles('#eceff1', '#c9cfd4', 8, 9), cabWood: veneer('#d7b98f', 11), cabWalnut: veneer('#7a553a', 13),
    quartz: speckle('#f2f1ee', '120,120,120', 17), counterConcrete: speckle('#9c9a96', '50,50,50', 19), nero: speckle('#26272a', '255,255,255', 23),
  };
}

export function createMaterials() {
  const textures = createTextures();
  const m = {
    textures,
    floor: std({ map: textures.oak, roughness: 0.62 }),
    floorTile: std({ map: textures.porcelain, roughness: 0.5 }),
    floorWet: std({ map: textures.bathTile, roughness: 0.45 }),
    floorOutdoor: std({ map: textures.concrete, roughness: 0.9 }),
    wall: std({ color: '#f4f2ee', roughness: 0.92 }),
    wallCut: std({ color: '#d8d2c8', roughness: 0.95 }),
    ceiling: std({ color: '#fbfaf8', roughness: 0.95, side: THREE.DoubleSide }),
    cabinet: std({ map: textures.cabWood, roughness: 0.55 }),
    counter: std({ map: textures.quartz, roughness: 0.28 }),
    handle: std({ color: '#2b2d31', roughness: 0.35, metalness: 0.7 }),
    steel: std({ color: '#c9ccd0', roughness: 0.3, metalness: 0.85 }),
    black: std({ color: '#1d1f22', roughness: 0.25, metalness: 0.2 }),
    ceramic: std({ color: '#fbfbfa', roughness: 0.18 }),
    fabric: std({ color: '#8b9198', roughness: 0.95 }),
    fabricWarm: std({ color: '#c8b8a2', roughness: 0.95 }),
    linen: std({ color: '#f1ede6', roughness: 0.95 }),
    wood: std({ map: textures.oak, roughness: 0.6 }),
    frame: std({ color: '#3a3d42', roughness: 0.5, metalness: 0.4 }),
    door: std({ color: '#efece6', roughness: 0.7 }),
    glass: new THREE.MeshPhysicalMaterial({ color: '#dfeef3', roughness: 0.05, transmission: 0.9, thickness: 0.01, transparent: true, opacity: 0.35, side: THREE.DoubleSide, depthWrite: false }),
    plant: std({ color: '#4f7d52', roughness: 0.8 }),
    underlay: new THREE.MeshBasicMaterial({ transparent: true, opacity: 0, depthWrite: false }),
  };
  setFinish(m, 'floor', 'porcelain');
  return m;
}

const FLOOR_MAP = { oak: 'oak', porcelain: 'porcelain', concrete: 'concrete' };
const CAB_MAP = { oak: ['cabWood', '#ffffff'], white: [null, '#f1efea'], walnut: ['cabWalnut', '#ffffff'], graphite: [null, '#3d4146'] };
const COUNTER_MAP = { quartz: 'quartz', concrete: 'counterConcrete', nero: 'nero' };

export function setFinish(m, kind, id) {
  if (kind === 'floor') {
    m.floor.map = m.textures[FLOOR_MAP[id]];
    m.floor.roughness = id === 'oak' ? 0.62 : 0.5;
  } else if (kind === 'cabinet') {
    const [tex, color] = CAB_MAP[id];
    m.cabinet.map = tex ? m.textures[tex] : null;
    m.cabinet.color.set(color);
  } else if (kind === 'counter') {
    m.counter.map = m.textures[COUNTER_MAP[id]];
    m.counter.roughness = id === 'nero' ? 0.18 : 0.3;
  }
  for (const mat of [m.floor, m.cabinet, m.counter]) mat.needsUpdate = true;
}

/** UV-scale a geometry so a texture repeats per metre instead of stretching per face. */
export function worldUV(geometry, metresPerRepeat = 1.2) {
  const pos = geometry.attributes.position;
  const nor = geometry.attributes.normal;
  const uv = new Float32Array(pos.count * 2);
  for (let i = 0; i < pos.count; i += 1) {
    const ax = Math.abs(nor.getX(i)); const ay = Math.abs(nor.getY(i));
    const [u, v] = ay > 0.5 ? [pos.getX(i), pos.getZ(i)] : ax > 0.5 ? [pos.getZ(i), pos.getY(i)] : [pos.getX(i), pos.getY(i)];
    uv[i * 2] = u / metresPerRepeat;
    uv[i * 2 + 1] = v / metresPerRepeat;
  }
  geometry.setAttribute('uv', new THREE.BufferAttribute(uv, 2));
  return geometry;
}
