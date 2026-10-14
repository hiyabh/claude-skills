// Tiny geometry builders shared by cabinetry and furniture. Local frame: +X along the width,
// +Y up from the floor, +Z out of the front face. Every helper adds to `g` and returns the mesh.
import * as THREE from 'three';

export function box(g, mat, w, h, d, x = 0, y = 0, z = 0) {
  const mesh = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat);
  mesh.position.set(x, y + h / 2, z);
  mesh.castShadow = mesh.receiveShadow = true;
  g.add(mesh);
  return mesh;
}

export function cyl(g, mat, rTop, rBottom, h, x = 0, y = 0, z = 0, segments = 24) {
  const mesh = new THREE.Mesh(new THREE.CylinderGeometry(rTop, rBottom, h, segments), mat);
  mesh.position.set(x, y + h / 2, z);
  mesh.castShadow = mesh.receiveShadow = true;
  g.add(mesh);
  return mesh;
}

export function rounded(g, mat, w, h, d, radius, x = 0, y = 0, z = 0) {
  const shape = new THREE.Shape();
  const r = Math.min(radius, w / 2, d / 2);
  shape.moveTo(-w / 2 + r, -d / 2);
  shape.lineTo(w / 2 - r, -d / 2); shape.quadraticCurveTo(w / 2, -d / 2, w / 2, -d / 2 + r);
  shape.lineTo(w / 2, d / 2 - r); shape.quadraticCurveTo(w / 2, d / 2, w / 2 - r, d / 2);
  shape.lineTo(-w / 2 + r, d / 2); shape.quadraticCurveTo(-w / 2, d / 2, -w / 2, d / 2 - r);
  shape.lineTo(-w / 2, -d / 2 + r); shape.quadraticCurveTo(-w / 2, -d / 2, -w / 2 + r, -d / 2);
  const geo = new THREE.ExtrudeGeometry(shape, { depth: h, bevelEnabled: true, bevelSize: 0.008, bevelThickness: 0.008, bevelSegments: 2, curveSegments: 6 });
  geo.rotateX(-Math.PI / 2);
  const mesh = new THREE.Mesh(geo, mat);
  mesh.position.set(x, y, z);
  mesh.castShadow = mesh.receiveShadow = true;
  g.add(mesh);
  return mesh;
}

/** A dark groove line on a front face, used for door/drawer seams. */
export function seam(g, mat, w, h, x, y, zFront) {
  return box(g, mat, w, h, 0.004, x, y, zFront + 0.002);
}

/** Bar handle: horizontal for drawers, vertical for doors. */
export function handle(g, mat, length, vertical, x, y, zFront) {
  const mesh = vertical ? box(g, mat, 0.014, length, 0.022, x, y - length / 2, zFront + 0.011)
    : box(g, mat, length, 0.014, 0.022, x, y, zFront + 0.011);
  return mesh;
}
