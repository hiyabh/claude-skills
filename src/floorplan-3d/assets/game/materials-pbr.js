// Photoreal materials with the same keys as viewer/materials.js, so the existing geometry builders work unchanged.
// Texture sets come from Poly Haven scans (scripts/assets.py); repeats are set so one tile covers its real size.
import * as THREE from 'three';

// worldUV() in viewer/shell.js maps UVs as metres / these values; a texture covering repeat_m metres needs m / repeat_m.
const UV_METRES = { floor: 1.6, wall: 1.5 };

export const GAME_FINISHES = {
  floor: [
    { id: 'floor_oak', label: 'פרקט אלון', swatch: '#a8774a' },
    { id: 'floor_porcelain', label: 'פורצלן בהיר', swatch: '#d9cdb8' },
    { id: 'floor_light_oak', label: 'פרקט בהיר', swatch: '#c9b08e' },
    { id: 'floor_herringbone', label: 'פרקט אדרה', swatch: '#b48958' },
  ],
  cabinet: [
    { id: 'veneer_oak', label: 'אלון', swatch: '#c49a62' },
    { id: 'veneer_white_oak', label: 'אלון לבן', swatch: '#d8c7ad' },
    { id: 'veneer_walnut', label: 'אגוז', swatch: '#6f4c33' },
    { id: 'matte_white', label: 'לבן מט', swatch: '#f0eee9' },
    { id: 'graphite', label: 'גרפיט', swatch: '#3a3d41' },
  ],
  counter: [
    { id: 'quartz', label: 'קוורץ לבן', swatch: '#f1efea' },
    { id: 'concrete', label: 'בטון', swatch: '#9a9893' },
    { id: 'nero', label: 'שחור', swatch: '#232427' },
  ],
  wall: [
    { id: '#f3ede3', label: 'לבן חם', swatch: '#f3ede3' },
    { id: '#e6dfd3', label: 'שמנת', swatch: '#e6dfd3' },
    { id: '#d4d8d2', label: 'מרווה', swatch: '#d4d8d2' },
    { id: '#cfd6de', label: 'תכלת אפרפר', swatch: '#cfd6de' },
    { id: '#8e9a8a', label: 'ירוק זית', swatch: '#8e9a8a' },
  ],
};

function tiled(set, uvMetres) {
  const r = uvMetres / set.repeatM;
  const t = (tex) => { if (!tex) return null; const c = tex.clone(); c.repeat.set(r, r); c.needsUpdate = true; return c; };
  return { map: t(set.map), normalMap: t(set.normalMap), roughnessMap: t(set.roughnessMap) };
}

/** Surface relief only (normal + roughness): scanned plaster and cloth carry stains and dye we do not want;
 *  the colour comes from the palette instead, so walls read as fresh paint and fabrics take any colour. */
function relief(set, uvMetres) {
  const { normalMap, roughnessMap } = tiled(set, uvMetres);
  return { normalMap, roughnessMap, normalScale: new THREE.Vector2(0.6, 0.6) };
}

const std = (o) => new THREE.MeshStandardMaterial({ roughness: 0.85, metalness: 0, ...o });
const phys = (o) => new THREE.MeshPhysicalMaterial({ roughness: 0.5, metalness: 0, ...o });

/** sets: { key: textureSet from loader.loadTextureSet } */
export function createPbrMaterials(sets) {
  const has = (k) => !!sets[k];
  const m = {
    sets,
    floor: std({ ...tiled(sets.floor_oak || sets.floor_porcelain, UV_METRES.floor), roughness: 1 }),
    floorTile: std({ ...tiled(sets.floor_porcelain, UV_METRES.floor), roughness: 1 }),
    floorWet: std({ ...tiled(sets.floor_concrete || sets.floor_porcelain, UV_METRES.floor), roughness: 1 }),
    floorOutdoor: std({ ...tiled(sets.floor_concrete || sets.floor_porcelain, UV_METRES.floor), color: '#b9b2a6', roughness: 1 }),
    wall: std({ ...relief(sets.wall_plaster, UV_METRES.wall), color: '#f3ede3', roughness: 1 }),
    wallCut: std({ color: '#d8d2c8', roughness: 0.95 }),
    ceiling: std({ color: '#f7f5f1', roughness: 0.95, side: THREE.DoubleSide }),
    cabinet: std({ ...tiled(sets.veneer_white_oak || sets.veneer_oak, 1), roughness: 1 }),
    counter: phys({ color: '#f1efea', roughness: 0.22, clearcoat: 0.35, clearcoatRoughness: 0.25 }),
    handle: std({ color: '#2a2b2e', roughness: 0.3, metalness: 0.85 }),
    steel: std({ color: '#c8ccd0', roughness: 0.22, metalness: 1 }),
    black: phys({ color: '#141518', roughness: 0.12, clearcoat: 0.8 }),
    ceramic: phys({ color: '#fbfbfa', roughness: 0.08, clearcoat: 1, clearcoatRoughness: 0.05 }),
    fabric: std({ ...(has('fabric_velvet') ? relief(sets.fabric_velvet, 1) : {}), color: '#b06a50', roughness: 1 }),
    fabricWarm: std({ ...(has('fabric_linen') ? relief(sets.fabric_linen, 1) : {}), color: '#d6a74e', roughness: 1 }),
    rug: std({ ...(has('fabric_linen') ? relief(sets.fabric_linen, 0.5) : {}), color: '#d8c2a2', roughness: 1 }),
    linen: std({ ...(has('fabric_cotton') ? relief(sets.fabric_cotton, 1) : {}), color: '#f2eee7', roughness: 1 }),
    wood: std({ ...tiled(sets.veneer_walnut || sets.veneer_oak, 1), roughness: 1 }),
    frame: std({ color: '#2f3134', roughness: 0.45, metalness: 0.6 }),
    door: phys({ color: '#f1efea', roughness: 0.35, clearcoat: 0.2 }),
    glass: new THREE.MeshPhysicalMaterial({ color: '#ffffff', roughness: 0.02, transmission: 1, thickness: 0.006, ior: 1.5,
      transparent: true, opacity: 0.18, side: THREE.DoubleSide, depthWrite: false }),
    plant: std({ color: '#4c7a4f', roughness: 0.8 }),
    underlay: new THREE.MeshBasicMaterial({ transparent: true, opacity: 0, depthWrite: false }),
  };
  return m;
}

function swapMaps(mat, set, uvMetres) {
  Object.assign(mat, tiled(set, uvMetres));
  mat.color.set('#ffffff');
  mat.needsUpdate = true;
}

/** Change a finish in place; every mesh sharing the material updates at once. */
export function setPbrFinish(m, kind, id) {
  if (kind === 'floor' && m.sets[id]) swapMaps(m.floor, m.sets[id], UV_METRES.floor);
  else if (kind === 'wall') { m.wall.color.set(id); }
  else if (kind === 'cabinet' && m.sets[id]) { swapMaps(m.cabinet, m.sets[id], 1); m.cabinet.roughness = 1; }
  else if (kind === 'cabinet') {
    Object.assign(m.cabinet, { map: null, normalMap: null, roughnessMap: null, roughness: id === 'graphite' ? 0.55 : 0.75 });
    m.cabinet.color.set(id === 'graphite' ? '#3a3d41' : '#efede8');
    m.cabinet.needsUpdate = true;
  } else if (kind === 'counter') {
    const look = { quartz: ['#f1efea', 0.22], concrete: ['#9a9893', 0.7], nero: ['#1f2023', 0.15] }[id];
    if (look) { m.counter.color.set(look[0]); m.counter.roughness = look[1]; }
  }
}
