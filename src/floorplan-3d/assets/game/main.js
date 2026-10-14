// Game-mode entry: load assets without fetch(), build the photoreal world, light it by the clock, run the loop.
import * as THREE from 'three';
import { P, shoelace, insidePoly } from '../viewer/util.js';
import { walkStart } from '../viewer/start.js';
import { installDataUrlFetch, Progress, loadHdr, loadModel, loadTextureSet } from './loader.js';
import { createPbrMaterials } from './materials-pbr.js';
import { buildWorld } from './world.js';
import { GameRenderer } from './render.js';
import { Lighting } from './lighting.js';
import { buildOutside } from './outside.js';
import { Player } from './player.js';
import { Interactor } from './interact.js';
import { Hud } from './hud.js';
import { takePhoto, snapshot } from './photo.js';
import { save } from '../viewer/export.js';

const ANISOTROPY = 8;

function readData() {
  return JSON.parse(document.getElementById('game-data').textContent);
}

function loadingUI() {
  const bar = document.getElementById('load-bar');
  const label = document.getElementById('load-label');
  return (p) => {
    bar.style.transform = `scaleX(${p.ratio.toFixed(3)})`;
    label.textContent = p.done < p.total ? `טוען ${p.done}/${p.total}` : 'מכין תאורה...';
  };
}

async function loadAll(index) {
  const progress = new Progress(loadingUI());
  const sets = {}; const hdris = {}; const models = {};
  const jobs = [
    ...Object.entries(index.textures).map(([k, e]) => progress.track(loadTextureSet(e, ANISOTROPY).then((s) => { sets[k] = s; }), k)),
    ...Object.entries(index.hdris).map(([k, e]) => progress.track(loadHdr(e).then((t) => { hdris[k] = t; }), k)),
    ...Object.entries(index.models).map(([k, e]) => progress.track(loadModel(e).then((m) => { models[k] = m; }), k)),
  ];
  await Promise.all(jobs);
  return { sets, hdris, models, progress };
}

/** Outward normals (plan x/y) of the glazing in one room: windows and glass sliding doors. */
function glazingNormals(plan, room) {
  const walls = Object.fromEntries(plan.walls.map((w) => [w.id, w]));
  const [cx, cy] = room.centroid;
  return plan.openings
    .filter((o) => (o.kind === 'window' || o.style === 'sliding') && (o.rooms || []).includes(room.id) && walls[o.wall])
    .map((o) => {
      const w = walls[o.wall];
      const len = Math.hypot(w.b[0] - w.a[0], w.b[1] - w.a[1]) || 1;
      let n = [-(w.b[1] - w.a[1]) / len, (w.b[0] - w.a[0]) / len];
      if (n[0] * (o.center[0] - cx) + n[1] * (o.center[1] - cy) < 0) n = [-n[0], -n[1]];
      return n;
    });
}

function lampGlow(world, roomId, on) {
  for (const lamp of world.lamps.children) {
    if (lamp.userData.room !== roomId) continue;
    lamp.traverse((o) => {
      if (!o.isMesh || !o.material.emissive) return;
      o.material.emissive.set(on ? '#ffd9a8' : '#000000');
      o.material.emissiveIntensity = on ? 2.5 : 0;
    });
  }
}

class Game {
  constructor(data, assets) {
    this.data = data;
    const variant = data.variants[0];
    this.plan = variant.plan;
    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(62, innerWidth / innerHeight, 0.05, 500);
    this.mats = createPbrMaterials(assets.sets);
    this.world = buildWorld(variant, this.mats, assets.models);
    this.scene.add(this.world.root);
    // A lite asset build is meant for phones: start the renderer on its lite tier too.
    this.view = new GameRenderer(document.getElementById('stage'), this.scene, this.camera, data.assets.tier === 'lite' ? 'lite' : 'high');
    this.initLighting(assets);
    this.initPlay();
    let last = performance.now();
    this.view.renderer.setAnimationLoop((now) => { this.frame(Math.min(0.1, (now - last) / 1000)); last = now; });
  }

  initLighting(assets) {
    this.lighting = new Lighting({ scene: this.scene, renderer: this.view.renderer, hdris: assets.hdris, plan: this.plan,
      center: this.world.center, span: this.world.span, shadowSize: this.view.shadowSize() });
    this.lighting.addRoomLights(this.plan.rooms, this.plan.defaults.wall_height, this.world.centroids);
    this.lighting.onRoomLamp = (roomId, on) => lampGlow(this.world, roomId, on);
    this.lighting.onGrade = (grade) => this.view.setLook(grade);
    this.mainRoom = [...this.plan.rooms].sort((p, q) => shoelace(q.polygon) - shoelace(p.polygon))[0];
    const normals = glazingNormals(this.plan, { id: this.mainRoom.id, centroid: this.world.centroids[this.mainRoom.id] });
    this.bestHour = this.lighting.bestHour(normals.length ? normals : [[0, -1]]);
    this.lighting.setTime(this.bestHour);
  }

  initPlay() {
    this.hud = new Hud({ plan: this.plan, onTime: (h) => this.lighting.setTime(h), onQuality: (q) => this.view.setQuality(q),
      onStart: () => this.player.lock(), onAction: () => this.interact.act(), onPhoto: () => this.snapshot(), onPhotoTraced: () => this.photo(),
      onPhotoSave: () => this.savePhoto(), onPhotoClose: () => this.closePhoto() });
    this.hud.setTime(this.bestHour);
    this.hud.setQuality(this.view.quality);
    this.view.onQuality = (q) => this.hud.setQuality(q);
    this.player = new Player(this.camera, this.view.renderer.domElement, this.hud.ref);
    this.player.setWorld(this.world.shell.collide, this.world.items, this.plan.rooms);
    this.interact = new Interactor({ camera: this.camera, world: this.world, mats: this.mats, lighting: this.lighting, ui: this.hud });
    this.interact.onDoors = (segments) => this.player.setClosedDoors(segments);
    const start = walkStart(this.plan);
    this.player.enter(start.x, start.y, start.yaw);
  }

  /** Test hook: stand at eye (plan x, y; height ignored) looking at target. */
  setView(eye, target) {
    const p = this.player;
    p.pos = [eye[0], eye[1]];
    p.yaw = Math.atan2(-(target[0] - eye[0]), target[1] - eye[1]);
    p.pitch = Math.atan2((target[2] ?? 1.4) - 1.6, Math.hypot(target[0] - eye[0], target[1] - eye[1]));
    p.vel = [0, 0];
    p.apply();
  }

  setTime(hour) { this.lighting.setTime(hour); this.hud.setTime(hour); }

  /** The generated window views replace the bare ground: they already show the street below. */
  async addOutside(views) {
    const ring = await buildOutside(views, this.world.center, this.plan.meta?.north_deg || 0);
    if (!ring) return;
    this.scene.add(ring);
    this.world.ground.visible = false;
    this.lighting.onPart = (part) => ring.userData.setPart(part);
    ring.userData.setPart(this.lighting.part);
    this.lighting.needsProbe = true;
  }

  async snapshot() {
    if (this.paused) return;
    this.paused = true;
    document.exitPointerLock?.();
    this.hud.photo('busy', 0.5, 'מצלם...');
    this.photoBlob = await snapshot(this.view);
    this.hud.photo('done', 1, 'הצילום מוכן', URL.createObjectURL(this.photoBlob));
  }

  /** Path-trace the current view; the game loop pauses so the tracer owns the canvas. */
  async photo() {
    if (this.paused) return;
    this.paused = true;
    this.photoStop = false;
    document.exitPointerLock?.();
    // The tracer computes bounce light itself and needs the equirect sky, not the PMREM interior probe.
    const keep = { env: this.scene.environment, intensity: this.scene.environmentIntensity };
    this.scene.environment = this.lighting.hdris[this.lighting.part];
    this.scene.environmentIntensity = this.lighting.part === 'night' ? 0.1 : 1;
    try {
      this.photoBlob = await takePhoto({ renderer: this.view.renderer, scene: this.scene, camera: this.camera,
        onProgress: (r, label) => this.hud.photo('busy', r, label), shouldStop: () => this.photoStop });
      this.hud.photo('done', 1, 'הצילום מוכן', URL.createObjectURL(this.photoBlob));
    } catch (err) {
      this.hud.photo('error', 0, `הצילום נכשל: ${err.message}. אפשר לנסות שוב באיכות חסכונית.`);
    } finally {
      this.scene.environment = keep.env;
      this.scene.environmentIntensity = keep.intensity;
    }
  }

  async savePhoto() {
    const name = `${(this.data.meta.title || 'דירה').replace(/[\\/:*?"<>|]+/g, '-')} - צילום.png`;
    this.hud.toast(await save(name, this.photoBlob));
  }

  closePhoto() {
    this.photoStop = true;
    this.hud.photo('closed');
    this.paused = false;
  }

  currentRoom() { return this.plan.rooms.find((r) => insidePoly(this.player.pos, r.polygon)); }

  frame(dt) {
    if (this.paused) return;
    this.player.update(dt);
    this.interact.update(dt);
    const room = this.currentRoom();
    this.hud.room(room);
    this.hud.minimap(this.player.pos, this.player.yaw);
    this.lighting.shadowRoom(room?.id);
    const [x, y] = this.world.centroids[this.mainRoom.id];
    this.lighting.captureProbe(P(x, y, 0));
    this.view.render(dt);
    if (!this.ready) { this.ready = true; document.getElementById('loading').classList.add('done'); }
  }
}

async function boot() {
  try {
    installDataUrlFetch();
    const data = readData();
    const assets = await loadAll(data.assets);
    const game = new Game(data, assets);
    window.__game = game;
    if (data.views) await game.addOutside(data.views);
  } catch (err) {
    document.getElementById('load-label').textContent = `הטעינה נכשלה: ${err.message}. נסה לרענן, ואם זה חוזר - דפדפן אחר.`;
    throw err;
  }
}

boot();
