# Recipes

Short building blocks. The F-16 example (`examples/f16-pattern.scene.js`) uses most of them in context.

## Models from primitives

- Build in real units (metres), with the object's **forward axis on +Z**. Then `obj.lookAt(pos + direction)` points it
  along a path. After `lookAt`, `rotateZ(+a)` banks right and `rotateX(-a)` pitches the nose up.
- `CylinderGeometry(...).rotateX(Math.PI / 2)` lays a cylinder along Z, with `radiusTop` at the front (+Z).
- Flat surfaces (wings, fins, plates): `new THREE.Shape(points)`, then `ExtrudeGeometry(shape, { depth, bevelEnabled: false })`.
  `rotateX(Math.PI / 2)` lays it flat with shape-y mapped to world Z. `rotateY(-Math.PI / 2)` stands it up with shape-x mapped to world Z.
- Mirror a part by negating the x of its points instead of using `scale(-1, 1, 1)`, which flips normals.
- One helper, `part(geo, mat, [x, y, z])`, keeps builders short. Group parts per subsystem (fuselage, gear, exhaust)
  so they can be toggled with `.visible`.
- Many identical items (trees, lamps, markings): `InstancedMesh` with a seeded RNG (`rng(seed)` in the example), so the layout is the same on every load.

## Fire, glow, exhaust

- Open cones (`ConeGeometry(r, len, 20, 1, true)`) with `MeshBasicMaterial({ blending: AdditiveBlending, transparent: true, depthWrite: false, side: DoubleSide })`.
  Use an orange outer cone and a pale inner core. Small additive spheres along the axis make shock diamonds.
- Scale the group along its length for intensity, plus a small `sin(time) + random` flicker. The flicker can use
  `performance.now()`: it is visual only and does not need to follow `t`.
- Add a `PointLight` at the source (intensity in the hundreds, decay 2), so the flame lights the ground at dusk.

## Sky, sun, time of day

- `import { Sky } from 'three/addons/objects/Sky.js'`, `sky.scale.setScalar(450000)`. Sky renders at the far plane,
  so `camera.far` does not need to cover it.
- Get the sun direction from elevation and azimuth with `Vector3.setFromSphericalCoords(1, rad(90 - elev), rad(az))`.
  Apply it to `sky.material.uniforms.sunPosition` and to a `DirectionalLight`.
- Drive these from one `day = smoothstep(elev, -3, 18)` value: light intensity and colour (orange near the horizon),
  `HemisphereLight` (keep a floor of about 0.4 or the ground goes black), `renderer.toneMappingExposure`,
  `scene.fog.color`, and emissive lamps (brighter at night).

## Motion along a path

- `CatmullRomCurve3(points, false, 'centripetal')` (centripetal avoids overshoot loops). Raise `curve.arcLengthDivisions` for long curves.
- `getPointAt(u)` and `getTangentAt(u)` are arc-length based. For a realistic speed profile (accelerate, cruise,
  decelerate), integrate a time table `t(d) = Σ Δd / v(d)` once, then binary-search it each frame (`buildProfile` and `arcAt` in the example).
  Use √ ramps for constant-acceleration segments.
- Coordinated-turn bank: `tan φ = v²κ / g`. Measure κ from tangents a fixed distance apart (no frame smoothing, so scrubbing stays correct).
- Chase camera: `ctx.follow(object.position)` each frame. It keeps the viewer's orbit offset. `ctx.unfollow()` releases it.

## Labels in the scene

- `import { CSS2DRenderer, CSS2DObject } from 'three/addons/renderers/CSS2DRenderer.js'`. Create the renderer in
  `buildScene`, append its `domElement` to `#stage` with `position:absolute; inset:0; pointer-events:none`, call
  `labelRenderer.setSize` on resize, and render it in `update`. Labels are DOM elements: write Hebrew with `dir="rtl"`
  and style them with the page tokens.

## Explainer / learning mode

- Put the explanation in `INFO` as short paragraphs. Use `<code>` for formulas, since it is bidi-isolated in the template.
- Make the timeline the lesson: `TIMELINE = { duration, loop: false }`, and let readouts show the quantity being
  taught (t, position, velocity). Scrubbing then becomes the lesson itself.
- Show the internals: a toggle for wireframe, helpers (`AxesHelper`, `ArrowHelper` for vectors), or a trail line built from past positions.

## Performance

- Pixel ratio is capped at 2 in the engine. Keep draw calls low: merge static parts into one `Group`, and use instancing for repeats.
- When rebuilding geometry in `onParam`, `dispose()` the old geometry.
- Shadows are off by default. If needed: `renderer.shadowMap.enabled = true`, one shadow-casting light, and a tight `shadow.camera` box.
