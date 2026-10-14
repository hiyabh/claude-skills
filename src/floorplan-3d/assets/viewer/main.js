// Entry point: read the embedded plan data, build the scene, wire camera, walk, labels, UI and the frame loop.
import * as THREE from 'three';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { P, IS_TOUCH, centroid, shoelace } from './util.js';
import { createMaterials, setFinish } from './materials.js';
import { buildShell, buildUnderlay } from './shell.js';
import { buildItem } from './cabinetry.js';
import { autoFurnish } from './autofurnish.js';
import { CameraRig, WallCutter, deriveViews, roomView } from './camera.js';
import { Walker } from './walk.js';
import { Labels } from './labels.js';
import { Measure } from './measure.js';
import { Reveal } from './reveal.js';
import { UI } from './ui.js';
import { exportModel, exportImage, exportPlan } from './export.js';
import { walkStart } from './start.js';

const TOUR_HOLD_MS = 3200;
const CLICK_SLOP = 6;

class App {
  constructor(data) {
    this.data = data;
    this.variant = 0;
    this.finishes = { floor: 'porcelain', cabinet: 'oak', counter: 'quartz' };
    this.walking = false;
    this.stage = document.getElementById('stage');
    this.initRenderer();
    this.mats = createMaterials();
    this.ui = new UI(this);
    this.rig = new CameraRig(this.camera, this.renderer.domElement);
    this.labels = new Labels(this.ui.ref.labels, this.camera, this.ui.ref.pop);
    this.labels.suppressed = (e) => this.walking && e.layer === 'rooms';
    this.scene.add(this.labels.group);
    this.walker = new Walker(this.camera, this.renderer.domElement, this.ui.ref);
    this.measure = new Measure({ camera: this.camera, dom: this.renderer.domElement, scene: this.scene, labels: this.labels,
      hint: this.ui.ref.measureHint, pickables: () => [this.model] });
    this.reveal = new Reveal();
    this.rig.controls.addEventListener('start', () => this.stopTour());
    this.bindRoomClicks();
    this.load(0, true);
    addEventListener('resize', () => this.resize());
    this.resize();
    let last = performance.now();
    this.renderer.setAnimationLoop((now) => { this.frame(Math.min(0.25, (now - last) / 1000)); last = now; });
  }

  initRenderer() {
    this.renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
    this.renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    this.renderer.toneMapping = THREE.NeutralToneMapping;
    this.renderer.shadowMap.enabled = !IS_TOUCH;
    this.renderer.shadowMap.type = THREE.PCFShadowMap;   // PCFSoftShadowMap was removed in r186
    this.renderer.localClippingEnabled = true;
    this.stage.append(this.renderer.domElement);
    this.scene = new THREE.Scene();
    const bg = getComputedStyle(document.documentElement).getPropertyValue('--stage').trim() || '#e9ecef';
    this.scene.background = new THREE.Color(bg);
    const pmrem = new THREE.PMREMGenerator(this.renderer);
    this.scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
    this.scene.environmentIntensity = 0.55;
    this.camera = new THREE.PerspectiveCamera(45, 1, 0.05, 200);
    this.scene.add(new THREE.HemisphereLight('#ffffff', '#d9cbb8', 0.9));
    this.sun = new THREE.DirectionalLight('#fff4e6', 1.6);
    this.sun.castShadow = true;
    this.sun.shadow.mapSize.set(2048, 2048);
    this.sun.shadow.bias = -0.0004;
    this.sun.shadow.normalBias = 0.02;
    this.scene.add(this.sun, this.sun.target);
  }

  get current() { return this.data.variants[this.variant]; }

  /** (Re)build the model for one variant. */
  load(index, first = false) {
    this.variant = index;
    if (this.model) { this.scene.remove(this.model); disposeTree(this.model); }
    const { plan, items, views } = this.current;
    this.model = new THREE.Group();
    const shell = buildShell(plan, this.mats);
    this.shell = shell;
    const ceilingH = plan.defaults.wall_height;
    this.itemsGroup = new THREE.Group();
    for (const item of items) this.itemsGroup.add(buildItem(item, this.mats, ceilingH));
    this.autoItems = autoFurnish(plan, items);
    this.furniture = new THREE.Group();
    for (const item of this.autoItems) this.furniture.add(buildItem(item, this.mats, ceilingH));
    this.underlay = buildUnderlay(this.data.underlay, this.mats);
    this.model.add(shell.floors, shell.walls, shell.ceilings, this.itemsGroup, this.furniture);
    if (this.underlay) this.scene.add(this.underlay);
    this.scene.add(this.model);
    this.cutter = new WallCutter(shell.walls);
    this.labels.occluders = [];
    shell.walls.traverse((o) => { if (o.isMesh) this.labels.occluders.push(o); });
    const derived = deriveViews(plan, views);
    Object.assign(this, { views: derived.views, center: derived.center, span: derived.span });
    this.fitSun(derived.bounds);
    this.walker.setWorld(shell.collide, [...items, ...this.autoItems], plan.rooms);
    this.labels.build({ plan, items: [...items, ...this.autoItems.filter((i) => i.label)], notes: plan.notes || [] });
    this.ui.render({ meta: this.data.meta, plan, notes: plan.notes || [], variants: this.data.variants, underlay: !!this.data.underlay });
    this.applyLayers();
    if (first) this.intro();
    else this.goView(this.currentView || 'overview');
  }

  intro() {
    const plan = this.views.find((v) => v.id === 'plan');
    this.rig.jump(plan.eye, plan.target);
    this.currentView = 'overview';
    this.ui.markView('overview');
    this.reveal.start({ cutter: this.cutter, furniture: [...this.itemsGroup.children, ...this.furniture.children],
      underlayMat: this.underlay ? this.mats.underlay : null, center: this.center, span: this.span,
      onLift: () => this.goView('overview') });
    this.ui.ready();
  }

  fitSun(b) {
    const cx = (b.minX + b.maxX) / 2; const cy = (b.minY + b.maxY) / 2;
    const r = Math.max(b.maxX - b.minX, b.maxY - b.minY) * 0.75 + 1;
    this.sun.position.copy(P(cx - r * 0.6, cy - r * 0.9, r * 1.6));
    this.sun.target.position.copy(P(cx, cy, 0));
    Object.assign(this.sun.shadow.camera, { left: -r, right: r, top: r, bottom: -r, near: 0.5, far: r * 5 });
    this.sun.shadow.camera.updateProjectionMatrix();
  }

  goView(id) {
    const v = this.views.find((x) => x.id === id);
    if (!v) return;
    if (this.walking) this.exitWalk(false);
    this.currentView = id;
    this.cutter.mode = v.cut;
    this.ui.markView(id);
    this.rig.flyTo(v.eye, v.target);
  }

  flyToRoom(roomId) {
    const room = this.current.plan.rooms.find((r) => r.id === roomId);
    if (!room) return;
    if (this.walking) this.exitWalk(false);
    const v = roomView(room);
    this.cutter.mode = 'auto';
    this.currentView = null;
    this.ui.markView(null);
    this.rig.flyTo(v.eye, v.target);
    this.ui.caption(room.label, `${shoelace(room.polygon).toFixed(1)} מ״ר`);
    clearTimeout(this.captionTimer);
    this.captionTimer = setTimeout(() => this.ui.caption(null), 2600);
  }

  flyToNote(note) {
    const [x, y] = note.at || centroid(this.current.plan.rooms[0].polygon);
    this.rig.flyTo(P(x + 1.6, y - 2.4, 3.2), P(x, y, 0.8));
    this.cutter.mode = 'auto';
    if (!this.ui.state.notes) { this.ui.state.notes = true; this.setLayer('notes', true); this.ui.renderToggles(); }
  }

  startTour() {
    this.stopTour();
    const rooms = [...this.current.plan.rooms].sort((p, q) => shoelace(q.polygon) - shoelace(p.polygon));
    let i = 0;
    const next = () => {
      if (i >= rooms.length) { this.stopTour(); this.goView('overview'); return; }
      const room = rooms[i++];
      const v = roomView(room);
      this.cutter.mode = 'auto';
      this.ui.caption(room.label, `${shoelace(room.polygon).toFixed(1)} מ״ר · ${i}/${rooms.length}`);
      this.rig.flyTo(v.eye, v.target, () => { this.tourTimer = setTimeout(next, TOUR_HOLD_MS); });
    };
    this.touring = true;
    next();
  }

  stopTour() {
    if (!this.touring) return;
    this.touring = false;
    clearTimeout(this.tourTimer);
    this.ui.caption(null);
  }

  enterWalk() {
    this.stopTour();
    const { plan } = this.current;
    const start = walkStart(plan);
    this.walking = true;
    this.rig.cancel();
    this.rig.controls.enabled = false;
    this.cutter.mode = 'none';
    this.shell.ceilings.visible = true;
    this.labels.apply();
    this.ui.markView(null);
    document.body.classList.add('walking');
    this.walker.enter(start.x, start.y, start.yaw);
  }

  exitWalk(toOverview = true) {
    if (!this.walking) return;
    this.walking = false;
    document.body.classList.remove('walking');
    this.walker.exit();
    const dir = new THREE.Vector3();
    this.camera.getWorldDirection(dir);
    this.rig.controls.target.copy(this.camera.position).addScaledVector(dir, 2);
    this.rig.controls.enabled = true;
    this.shell.ceilings.visible = this.ui.state.ceiling;
    this.labels.apply();
    if (toOverview) this.goView('overview');
  }

  setLayer(id, on) {
    if (['items', 'dims', 'notes', 'walls'].includes(id)) this.labels.setLayer(id, on);
    else if (id === 'ceiling') this.shell.ceilings.visible = on || this.walking;
    else if (id === 'furniture') this.furniture.visible = on;
    else if (id === 'measure') this.measure.toggle(on);
    else if (id === 'underlay' && this.underlay) this.mats.underlay.opacity = on ? 0.85 : 0;
  }

  applyLayers() {
    for (const [id, on] of Object.entries(this.ui.state)) if (id !== 'measure') this.setLayer(id, on);
  }

  setFinish(kind, id) {
    this.finishes[kind] = id;
    setFinish(this.mats, kind, id);
  }

  setVariant(i) { if (i !== this.variant) this.load(i); }

  get fileName() { return (this.data.meta.file || 'floorplan-3d').replace(/[\\/:*?"<>|]+/g, '-'); }
  exportModel() { return exportModel(this.model, this.fileName); }
  exportImage() { return exportImage(this.renderer, () => this.renderer.render(this.scene, this.camera), this.fileName); }
  exportPlan() { return exportPlan(this.current.plan, this.fileName); }

  bindRoomClicks() {
    const dom = this.renderer.domElement;
    const ray = new THREE.Raycaster();
    let down = null;
    dom.addEventListener('pointerdown', (e) => { down = [e.clientX, e.clientY]; });
    dom.addEventListener('pointerup', (e) => {
      if (this.walking || this.measure.active || !down || Math.hypot(e.clientX - down[0], e.clientY - down[1]) > CLICK_SLOP) return;
      const r = dom.getBoundingClientRect();
      ray.setFromCamera(new THREE.Vector2(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1), this.camera);
      const hit = ray.intersectObjects(this.model.children, true)[0];
      const room = hit?.object.userData.room;
      if (room) this.flyToRoom(room);
    });
  }

  resize() {
    const w = innerWidth; const h = innerHeight;
    this.renderer.setSize(w, h);
    this.camera.aspect = w / h;
    this.camera.fov = w < h ? Math.min(75, 45 * (h / w) * 0.75) : 45;   // keep the plan in frame on portrait phones
    this.camera.updateProjectionMatrix();
    this.size = [w, h];
  }

  frame(dt) {
    this.reveal.update(dt);
    this.cutter.update(this.camera, dt);
    if (this.walking) this.walker.update(dt); else this.rig.update(dt);
    this.labels.update(this.size[0], this.size[1]);
    this.renderer.render(this.scene, this.camera);
  }
}

function disposeTree(root) {
  root.traverse((o) => { if (o.geometry) o.geometry.dispose(); });
}

function boot() {
  let data;
  try {
    data = JSON.parse(document.getElementById('plan-data').textContent);
  } catch (err) {
    return new UI({}).fail(`נתוני התוכנית בדף פגומים (${err.message}). יש לבנות את הדף מחדש עם build_viewer.py.`);
  }
  if (!data.variants?.length || !data.variants[0].plan.rooms?.length) {
    return new UI({}).fail('בתוכנית אין חדרים להצגה. יש לבדוק את plan.json ולהריץ שוב את reconcile.py.');
  }
  try {
    window.__viewer = new App(data);
  } catch (err) {
    const gl = /WebGL/i.test(String(err)) ? 'הדפדפן לא הצליח לפתוח WebGL. נסה דפדפן אחר או הפעל האצת חומרה.' : err.message;
    new UI({}).fail(gl);
    throw err;
  }
}

boot();
