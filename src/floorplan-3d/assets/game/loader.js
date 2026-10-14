// Asset loading that never depends on fetch(): an Artifact page may not fetch its own files, but it can
// import() its own scripts and load images through <img>. Models and HDRIs therefore ship as JS modules
// (see scripts/assets.py) and every data: URL a loader asks for is answered in memory.
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { HDRLoader } from 'three/addons/loaders/HDRLoader.js';

const realFetch = window.fetch.bind(window);

function decodeDataUrl(url) {
  const comma = url.indexOf(',');
  const head = url.slice(5, comma);
  const body = url.slice(comma + 1);
  const bytes = head.endsWith(';base64')
    ? Uint8Array.from(atob(body), (c) => c.charCodeAt(0))
    : new TextEncoder().encode(decodeURIComponent(body));
  return new Response(bytes, { headers: { 'Content-Type': head.split(';')[0] || 'application/octet-stream' } });
}

/** Install once: data: URLs never reach the network (or the page's CSP); everything else is untouched. */
export function installDataUrlFetch() {
  window.fetch = (input, init) => {
    const url = typeof input === 'string' ? input : input?.url || '';
    return url.startsWith('data:') ? Promise.resolve(decodeDataUrl(url)) : realFetch(input, init);
  };
}

/** Counts finished jobs so the loading screen shows real progress, not a timer. */
export class Progress {
  constructor(onChange) { Object.assign(this, { total: 0, done: 0, onChange }); }
  track(promise, label) {
    this.total += 1;
    this.onChange(this);
    return promise.then((v) => { this.done += 1; this.last = label; this.onChange(this); return v; });
  }
  get ratio() { return this.total ? this.done / this.total : 0; }
}

const absolute = (rel) => new URL(rel, document.baseURI).href;
const b64ToBuffer = (b64) => Uint8Array.from(atob(b64), (c) => c.charCodeAt(0)).buffer;

export async function loadHdr(entry) {
  const b64 = (await import(/* @vite-ignore */ absolute(entry.js))).default;
  const hdr = new HDRLoader().parse(b64ToBuffer(b64));
  const tex = new THREE.DataTexture(hdr.data, hdr.width, hdr.height, THREE.RGBAFormat, hdr.type);
  Object.assign(tex, { mapping: THREE.EquirectangularReflectionMapping, colorSpace: THREE.LinearSRGBColorSpace,
    minFilter: THREE.LinearFilter, magFilter: THREE.LinearFilter, generateMipmaps: false, flipY: true });
  tex.needsUpdate = true;
  return tex;
}

export async function loadModel(entry) {
  const json = (await import(/* @vite-ignore */ absolute(entry.js))).default;
  const gltf = await new GLTFLoader().parseAsync(JSON.stringify(json), absolute('assets/m/'));
  gltf.scene.traverse((o) => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
  return gltf.scene;
}

const textureLoader = new THREE.TextureLoader();

/** A PBR map set {diff, nor_gl, rough} -> textures (colour space set, tiling enabled). */
export async function loadTextureSet(entry, anisotropy) {
  const load = (rel, srgb) => textureLoader.loadAsync(absolute(rel)).then((t) => {
    t.colorSpace = srgb ? THREE.SRGBColorSpace : THREE.NoColorSpace;
    t.wrapS = t.wrapT = THREE.RepeatWrapping;
    t.anisotropy = anisotropy;
    return t;
  });
  // Relief-only sets (plaster, cloth) ship without a colour map: the palette supplies the colour.
  const [map, normalMap, roughnessMap] = await Promise.all([entry.diff ? load(entry.diff, true) : null, load(entry.nor_gl, false), load(entry.rough, false)]);
  return { map, normalMap, roughnessMap, repeatM: entry.repeat_m, tint: entry.tint };
}
