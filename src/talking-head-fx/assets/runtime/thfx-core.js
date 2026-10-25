/* talking-head-fx runtime core.
 * Reads window.THFX_PLAN (written by build_project.py), wires layers, and hands each
 * planned effect to its registered builder: THFX.fx[type](tl, t0, dur, params, ctx).
 * Every builder must leave the shared layers (#cam, subjects, lens) as it found them.
 * Deterministic only: no Date, no Math.random (use ctx.rand), no network.
 */
(function () {
  "use strict";
  const SVG_NS = "http://www.w3.org/2000/svg";
  const FACE_FALLBACK = { x: 0.5, y: 0.38, size: 0.22 };

  const THFX = (window.THFX = window.THFX || { fx: {} });

  /* ---------- DOM helpers ---------- */
  function el(tag, cls, parent, html) {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    if (html !== undefined) node.innerHTML = html;
    if (parent) parent.appendChild(node);
    return node;
  }

  function svg(tag, attrs, parent) {
    const node = document.createElementNS(SVG_NS, tag);
    Object.keys(attrs || {}).forEach((k) => node.setAttribute(k, attrs[k]));
    if (parent) parent.appendChild(node);
    return node;
  }

  /* Mulberry32 - seeded so every render draws the same "random" layout. */
  function makeRand(seed) {
    let a = seed >>> 0;
    return function () {
      a = (a + 0x6d2b79f5) >>> 0;
      let t = a;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  /* ---------- face track -> canvas coordinates ---------- */
  function faceSampler(face) {
    const s = (face && face.samples) || [];
    return function (t) {
      if (!s.length) return FACE_FALLBACK;
      if (t <= s[0][0]) return { x: s[0][1], y: s[0][2], size: s[0][3] };
      for (let i = 1; i < s.length; i++) {
        if (s[i][0] >= t) {
          const a = s[i - 1], b = s[i];
          const k = (t - a[0]) / Math.max(1e-6, b[0] - a[0]);
          return { x: a[1] + (b[1] - a[1]) * k, y: a[2] + (b[2] - a[2]) * k, size: a[3] + (b[3] - a[3]) * k };
        }
      }
      const z = s[s.length - 1];
      return { x: z[1], y: z[2], size: z[3] };
    };
  }

  /* Mirrors CSS object-fit:cover + object-position on #footage. */
  function coverMapper(W, H, srcW, srcH, posX, posY) {
    const scale = Math.max(W / srcW, H / srcH);
    const dw = srcW * scale, dh = srcH * scale;
    const offX = (W - dw) * posX, offY = (H - dh) * posY;
    return function (nx, ny) {
      return { x: offX + nx * dw, y: offY + ny * dh, scale: dh };
    };
  }

  /* Face point in canvas px at time t, plus face height in px. */
  function makeFaceAt(plan, sampler, map) {
    return function (t) {
      const f = sampler(t);
      const p = map(f.x, f.y);
      return { x: p.x, y: p.y, h: f.size * p.scale };
    };
  }

  /* ---------- context shared by all effects ---------- */
  function buildContext(plan) {
    const W = plan.canvas.w, H = plan.canvas.h;
    const fit = plan.footage.fit || { x: 0.5, y: 0.5 };
    const map = coverMapper(W, H, plan.footage.w, plan.footage.h, fit.x, fit.y);
    const ctx = {
      W, H, plan,
      theme: plan.theme || {},
      faceAt: makeFaceAt(plan, faceSampler(plan.face), map),
      root: document.getElementById("root"),
      cam: document.getElementById("cam"),
      bg: document.getElementById("fx-bg"),
      mid: document.getElementById("fx-mid"),
      top: document.getElementById("fx-top"),
      lensWrap: document.getElementById("lens-wrap"),
      lensInner: document.getElementById("lens-inner"),
      el, svg, rand: makeRand(plan.seed || 7),
    };
    ctx.subject = (i) => document.getElementById("subj-" + i);
    ctx.clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
    return ctx;
  }

  /* A full-canvas scene container that exists only inside [t0, t0+dur]. */
  THFX.scene = function (tl, ctx, layer, t0, dur, cls) {
    const node = el("div", "fx-scene " + (cls || ""), layer);
    tl.set(node, { opacity: 1 }, t0);
    tl.set(node, { opacity: 0 }, t0 + dur);
    return node;
  };

  /* Swap the footage for a matted subject for the whole effect window. The cut-out is scaled
   * down from the bottom edge (`scale`) so the designed background reads around the speaker. */
  THFX.useSubject = function (tl, ctx, fxIndex, t0, dur, scale) {
    const subj = ctx.subject(fxIndex);
    if (!subj) {
      console.warn("[thfx] effect #" + fxIndex + " needs a matted subject (run matte_segments.py).");
      return null;
    }
    const s = scale || 1;
    tl.set(subj, { opacity: 1, transformOrigin: "50% 100%", scale: s }, t0);
    tl.set(ctx.cam, { opacity: 0 }, t0);
    tl.set(subj, { opacity: 0, scale: 1 }, t0 + dur);
    tl.set(ctx.cam, { opacity: 1 }, t0 + dur);
    return subj;
  };

  /* Face position after the subject was scaled by `s` around the bottom-centre. */
  THFX.faceInSubject = function (ctx, t, s) {
    const f = ctx.faceAt(t);
    return { x: ctx.W / 2 + (f.x - ctx.W / 2) * s, y: ctx.H - (ctx.H - f.y) * s, h: f.h * s };
  };

  /* Restore the camera wrapper to identity at time t. */
  THFX.resetCam = function (tl, ctx, t) {
    tl.set(ctx.cam, { scale: 1, x: 0, y: 0, rotation: 0, filter: "none", clipPath: "inset(0px 0px 0px 0px round 0px)" }, t);
  };

  function runEffects(tl, ctx) {
    (ctx.plan.effects || []).forEach((e, i) => {
      const build = THFX.fx[e.type];
      if (!build) {
        console.warn("[thfx] unknown effect type '" + e.type + "' - see references/effects.md for the catalog.");
        return;
      }
      build(tl, e.start, e.dur, e.params || {}, Object.assign({}, ctx, { index: i }));
    });
  }

  THFX.run = function (plan) {
    // immediateRender:false - otherwise every fromTo paints its start state at build time and
    // (e.g.) a punch-zoom blur leaks onto the footage before the effect begins.
    const tl = gsap.timeline({ paused: true, defaults: { immediateRender: false } });
    const ctx = buildContext(plan);
    THFX.resetCam(tl, ctx, 0);
    tl.set(ctx.lensWrap, { opacity: 0 }, 0);
    runEffects(tl, ctx);
    if (THFX.captions && plan.captions) THFX.captions(tl, plan.captions, ctx);
    if (THFX.progress && plan.progress) THFX.progress(tl, plan.progress, ctx);
    tl.set({}, {}, plan.footage.duration);
    return tl; // index.html registers it on window.__timelines (lint looks for that line there)
  };
})();
