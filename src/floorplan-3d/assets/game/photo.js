// Stills for marketing. snapshot(): the real-time image re-rendered at ~4K on Ultra - instant and clean.
// takePhoto(): path-traced (three-gpu-pathtracer), physically exact bounce light but slow to converge
// (F1 on an Intel Arc: ~2.5 min for 360 samples, still visibly grainy), so it is offered as experimental.
import * as THREE from 'three';
import { FullScreenQuad } from 'three/addons/postprocessing/Pass.js';

// 65% resolution with more samples: cleaner and faster than full resolution with fewer (measured on F1/Arc).
const SAMPLES = 900;
const SNAPSHOT_WIDTH = 3840;
const RENDER_SCALE = 0.65;
const TILES = 2;
const EXPOSURE = 1.15;
const GLOSSY_FILTER = 0.5;     // trims fireflies on polished surfaces
// Edge-aware smart denoise (ships with three-gpu-pathtracer): smooths sampling grain, keeps edges.
const DENOISE = { sigma: 4.5, kSigma: 1.2, threshold: 0.06 };

const FIREFLY_RATIO = 1.6;     // a pixel this much brighter than every neighbour is a firefly

// Replace isolated over-bright pixels by their neighbours' mean (fireflies survive any amount of blur otherwise).
const FireflyMaterial = (map) => new THREE.ShaderMaterial({
  uniforms: { map: { value: map }, texel: { value: new THREE.Vector2(1 / map.image.width, 1 / map.image.height) }, ratio: { value: FIREFLY_RATIO } },
  vertexShader: 'varying vec2 vUv; void main() { vUv = uv; gl_Position = vec4(position.xy, 0.0, 1.0); }',
  fragmentShader: `uniform sampler2D map; uniform vec2 texel; uniform float ratio; varying vec2 vUv;
    float lum(vec3 c) { return dot(c, vec3(0.2126, 0.7152, 0.0722)); }
    void main() {
      vec4 c = texture2D(map, vUv); vec3 sum = vec3(0.0); float peak = 0.0;
      for (int x = -1; x <= 1; x++) for (int y = -1; y <= 1; y++) {
        if (x == 0 && y == 0) continue;
        vec3 n = texture2D(map, vUv + vec2(float(x), float(y)) * texel).rgb; sum += n; peak = max(peak, lum(n));
      }
      gl_FragColor = lum(c.rgb) > peak * ratio + 1e-4 ? vec4(sum / 8.0, c.a) : c;
    }`,
  depthTest: false, depthWrite: false,
});

/** Remove fireflies, denoise the accumulated (linear, HDR) image, then draw it tone-mapped to the canvas. */
function finish(renderer, target, DenoiseMaterial) {
  const size = renderer.getDrawingBufferSize(new THREE.Vector2());
  const rt = () => new THREE.WebGLRenderTarget(target.width, target.height, { type: THREE.HalfFloatType });
  const calm = rt();
  const clean = new THREE.WebGLRenderTarget(size.x, size.y, { type: THREE.HalfFloatType });
  const fireflies = new FullScreenQuad(FireflyMaterial(target.texture));
  renderer.setRenderTarget(calm);
  fireflies.render(renderer);
  const denoise = new FullScreenQuad(new DenoiseMaterial({ map: calm.texture, ...DENOISE }));
  renderer.setRenderTarget(clean);
  denoise.render(renderer);
  renderer.setRenderTarget(null);
  fireflies.material.dispose(); fireflies.dispose(); calm.dispose();
  const show = new FullScreenQuad(new THREE.MeshBasicMaterial({ map: clean.texture }));   // toneMapped: renderer's Neutral
  show.render(renderer);
  denoise.material.dispose(); denoise.dispose(); show.material.dispose(); show.dispose();
  return clean;
}

/** Pause the game loop, accumulate samples, return a PNG blob of the finished frame. */
export async function takePhoto({ renderer, scene, camera, onProgress, shouldStop }) {
  const { WebGLPathTracer, DenoiseMaterial } = await import('three-gpu-pathtracer');
  // The game tone-maps in post-processing; the tracer draws straight to the canvas, so it maps here instead.
  const keep = { mapping: renderer.toneMapping, exposure: renderer.toneMappingExposure };
  renderer.toneMapping = THREE.NeutralToneMapping;
  renderer.toneMappingExposure = EXPOSURE;
  // Transmissive glass turns direct sun into caustic noise the tracer cannot sample; hide it for the photo.
  const glass = [];
  scene.traverse((o) => { if (o.isMesh && o.visible && o.material?.transmission > 0) { glass.push(o); o.visible = false; } });
  const tracer = new WebGLPathTracer(renderer);
  tracer.filterGlossyFactor = GLOSSY_FILTER;
  tracer.tiles.set(TILES, TILES);
  tracer.renderScale = RENDER_SCALE;
  tracer.minSamples = 1;
  tracer.fadeDuration = 0;
  tracer.renderToCanvas = true;
  onProgress(0, 'בונה את הסצנה לצילום...');
  await new Promise(requestAnimationFrame);
  tracer.setScene(scene, camera);
  while (tracer.samples < SAMPLES && !shouldStop()) {
    tracer.renderSample();
    if (Math.floor(tracer.samples) % 4 === 0) {
      onProgress(tracer.samples / SAMPLES, `מצלם... ${Math.floor(tracer.samples)}/${SAMPLES}`);
      await new Promise(requestAnimationFrame);
    }
  }
  const clean = finish(renderer, tracer.target, DenoiseMaterial);
  const blob = await new Promise((resolve) => renderer.domElement.toBlob(resolve, 'image/png'));
  clean.dispose();
  tracer.dispose();
  for (const o of glass) o.visible = true;
  renderer.toneMapping = keep.mapping;
  renderer.toneMappingExposure = keep.exposure;
  return blob;
}

/** Re-render the current frame at ~4K on the top quality tier and return it as PNG. */
export async function snapshot(view) {
  const keep = { quality: view.quality, ratio: view.renderer.getPixelRatio() };
  view.setQuality('ultra');
  view.renderer.setPixelRatio(Math.max(1, SNAPSHOT_WIDTH / innerWidth));
  view.resize();
  view.composer.render(0);
  const blob = await new Promise((resolve) => view.renderer.domElement.toBlob(resolve, 'image/png'));
  view.setQuality(keep.quality);
  view.renderer.setPixelRatio(keep.ratio);
  view.resize();
  return blob;
}
