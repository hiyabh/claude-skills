// Measure tool: click two surface points, get the distance in centimetres. Measurements stay until cleared.
import * as THREE from 'three';
import { el } from './util.js';

const CLICK_SLOP = 6; // px a press may travel and still count as a click, not an orbit drag

export class Measure {
  constructor({ camera, dom, scene, labels, hint, pickables }) {
    Object.assign(this, { camera, dom, scene, labels, hint, pickables, active: false, first: null, ray: new THREE.Raycaster() });
    this.group = new THREE.Group();
    scene.add(this.group);
    let down = null;
    dom.addEventListener('pointerdown', (e) => { down = [e.clientX, e.clientY]; });
    dom.addEventListener('pointerup', (e) => {
      if (!this.active || !down || Math.hypot(e.clientX - down[0], e.clientY - down[1]) > CLICK_SLOP) return;
      this.pick(e);
    });
    addEventListener('keydown', (e) => { if (e.key === 'Escape' && this.active) this.toggle(false); });
  }

  toggle(on) {
    this.active = on;
    this.hint.hidden = !on;
    this.first = null;
    if (!on) this.clear();
  }

  clear() {
    this.group.clear();
    for (const e of this.labels.entries.filter((x) => x.layer === 'measure')) e.node.remove();
    this.labels.entries = this.labels.entries.filter((x) => x.layer !== 'measure');
  }

  pick(e) {
    const r = this.dom.getBoundingClientRect();
    this.ray.setFromCamera(new THREE.Vector2(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1), this.camera);
    const hit = this.ray.intersectObjects(this.pickables(), true).find((h) => h.object.visible && h.object.type === 'Mesh');
    if (!hit) return;
    const p = hit.point.clone();
    this.group.add(dot(p));
    if (!this.first) { this.first = p; return; }
    const a = this.first; this.first = null;
    const line = new THREE.Line(new THREE.BufferGeometry().setFromPoints([a, p]), new THREE.LineBasicMaterial({ color: '#c2410c', depthTest: false }));
    line.renderOrder = 6;
    this.group.add(line);
    const node = el('div', 'dim');
    node.append(el('span', 'chip drawn', `${Math.round(a.distanceTo(p) * 100)} ס״מ`));
    this.labels.add('measure', node, a.clone().add(p).multiplyScalar(0.5));
    this.labels.layers.measure = true;
  }
}

function dot(p) {
  const m = new THREE.Mesh(new THREE.SphereGeometry(0.025, 12, 8), new THREE.MeshBasicMaterial({ color: '#c2410c', depthTest: false }));
  m.position.copy(p);
  m.renderOrder = 6;
  return m;
}
