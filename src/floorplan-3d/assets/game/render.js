// Renderer + post-processing: N8AO contact shadows, gentle bloom, SMAA, AgX tone mapping and a touch of vibrance.
// Quality tiers trade resolution, shadow-map size and AO cost; auto() picks one from the measured frame rate.
import * as THREE from 'three';
import { EffectComposer, RenderPass, EffectPass, BloomEffect, SMAAEffect, ToneMappingEffect, ToneMappingMode,
  HueSaturationEffect, BrightnessContrastEffect } from 'postprocessing';
import { N8AOPostPass } from 'n8ao';

export const QUALITY = {
  ultra: { label: 'אולטרה', pixelRatio: 2, shadow: 4096, ao: 'High', aoHalf: false, bloom: true },
  high: { label: 'גבוהה', pixelRatio: 1.5, shadow: 2048, ao: 'Medium', aoHalf: false, bloom: true },
  lite: { label: 'חסכונית', pixelRatio: 1, shadow: 1024, ao: 'Low', aoHalf: true, bloom: false },
};
// Colour grade: tone-mapping curve plus a little saturation and contrast, so interiors read warm and alive.
const LOOK = { mode: 'NEUTRAL', saturation: 0.22, contrast: 0.1, brightness: 0.02 };   // chosen over AgX/ACES by eye on F1
const AUTO_SAMPLE_MS = 2000;
const AUTO_DOWN_FPS = 40;

export class GameRenderer {
  constructor(container, scene, camera, startQuality = 'high') {
    Object.assign(this, { scene, camera, quality: startQuality, look: { ...LOOK } });
    this.renderer = new THREE.WebGLRenderer({ antialias: false, powerPreference: 'high-performance', stencil: false, preserveDrawingBuffer: true });
    this.renderer.toneMapping = THREE.NoToneMapping;           // the ToneMappingEffect owns tone mapping
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFShadowMap;
    container.append(this.renderer.domElement);
    this.build();
    this.resize();
    addEventListener('resize', () => this.resize());
  }

  build() {
    const q = QUALITY[this.quality];
    this.renderer.setPixelRatio(Math.min(devicePixelRatio, q.pixelRatio));
    this.composer = new EffectComposer(this.renderer, { frameBufferType: THREE.HalfFloatType });
    this.composer.addPass(new RenderPass(this.scene, this.camera));
    this.ao = new N8AOPostPass(this.scene, this.camera, innerWidth, innerHeight);
    Object.assign(this.ao.configuration, { aoRadius: 0.55, distanceFalloff: 0.8, intensity: 2.2, halfRes: q.aoHalf, gammaCorrection: false });
    this.ao.setQualityMode(q.ao);
    this.composer.addPass(this.ao);
    const effects = [];
    if (q.bloom) effects.push(new BloomEffect({ intensity: 0.35, luminanceThreshold: 0.92, mipmapBlur: true }));
    this.toneMap = new ToneMappingEffect({ mode: ToneMappingMode[this.look.mode] });
    this.saturation = new HueSaturationEffect({ saturation: this.look.saturation });
    this.contrast = new BrightnessContrastEffect({ contrast: this.look.contrast, brightness: this.look.brightness });
    effects.push(this.saturation, this.contrast, this.toneMap, new SMAAEffect());
    this.composer.addPass(new EffectPass(this.camera, ...effects));
  }

  setQuality(name) {
    if (!QUALITY[name] || name === this.quality) return;
    this.quality = name;
    this.composer.dispose();
    this.build();
    this.resize();
    this.onQuality?.(name);
  }

  shadowSize() { return QUALITY[this.quality].shadow; }

  /** Live colour grade (used to compare looks; the chosen one becomes LOOK). */
  setLook(look) {
    Object.assign(this.look, look);
    this.toneMap.mode = ToneMappingMode[this.look.mode];
    this.saturation.saturation = this.look.saturation;
    this.contrast.contrast = this.look.contrast;
    this.contrast.brightness = this.look.brightness;
  }

  resize() {
    const w = innerWidth; const h = innerHeight;
    this.renderer.setSize(w, h);
    this.composer.setSize(w, h);
    this.camera.aspect = w / h;
    this.camera.fov = w < h ? 72 : 62;
    this.camera.updateProjectionMatrix();
  }

  render(dt) {
    this.composer.render(dt);
    this.sample(dt);
  }

  /** Measure for a couple of seconds after load, then step quality down once if the device struggles. */
  sample(dt) {
    if (this.tuned) return;
    this.frames = (this.frames || 0) + 1;
    this.elapsed = (this.elapsed || 0) + dt * 1000;
    if (this.elapsed < AUTO_SAMPLE_MS) return;
    this.fps = Math.round((this.frames * 1000) / this.elapsed);
    this.tuned = true;
    // Only step down: the loading frames are cheaper than real views, so a high reading here is not a promise.
    if (this.fps < AUTO_DOWN_FPS) this.setQuality(this.quality === 'ultra' ? 'high' : 'lite');
  }
}
