/* Overlay effects - graphics drawn over the running footage.
 * orbit_ui (מסלול) · checklist_pop (צ'קליסט קופץ) · headline_storm (סערת כותרות) ·
 * portal_zoom (פורטל זום) · liquid_glass (זכוכית נוזלית) · frame_break (שבירת פריים) ·
 * recap_checklist (צ'קליסט סיכום)
 */
(function () {
  "use strict";
  const THFX = window.THFX;
  const ICONS = ["CC", "▶", "✂", "Aa", "+", "♫", "✕", "◐"];
  const ICON_CLASS = ["", "ic-white", "ic-orange", "ic-white", "ic-red", "ic-blue", "", "ic-orange"];
  const RIBBON_STYLES = ["rb-dark", "rb-accent", "rb-light", "rb-dark", "rb-accent", "rb-dark"];
  const BREAK_RAYS = 18;
  const ICON_MARGIN = 80;       // keep orbiting icons fully on canvas
  const ICON_TOP = 230;         // ...and below the progress bar
  const PORTAL_FACE_FILL = 1.7; // face height as a share of the portal diameter

  THFX.fx.orbit_ui = function (tl, t0, dur, p, ctx) {
    const scene = THFX.scene(tl, ctx, ctx.top, t0, dur, "");
    const f = ctx.faceAt(t0 + dur / 2);
    const n = Math.min(p.count || 6, ICONS.length);
    const rx = Math.min(ctx.W * 0.42, f.h * 1.45), ry = f.h * 0.95;
    for (let i = 0; i < n; i++) {
      const icon = ctx.el("div", "orbit-icon " + ICON_CLASS[i], scene, (p.icons || ICONS)[i]);
      const a0 = (i / n) * Math.PI * 2, st = { a: a0 };
      const place = () => gsap.set(icon, { xPercent: -50, yPercent: -50,
        x: ctx.clamp(f.x + Math.cos(st.a) * rx, ICON_MARGIN, ctx.W - ICON_MARGIN),
        y: ctx.clamp(f.y + 0.15 * f.h + Math.sin(st.a) * ry, ICON_TOP, ctx.H - ICON_MARGIN) });
      tl.fromTo(st, { a: a0 }, { a: a0 + 0.9, duration: dur, ease: "none", onUpdate: place }, t0);
      tl.fromTo(icon, { scale: 0 }, { scale: 1, duration: 0.3, ease: "back.out(2.4)" }, t0 + i * 0.07);
      tl.to(icon, { scale: 0, duration: 0.2, ease: "power2.in" }, t0 + dur - 0.25);
    }
  };

  THFX.fx.checklist_pop = function (tl, t0, dur, p, ctx) {
    const scene = THFX.scene(tl, ctx, ctx.top, t0, dur, "");
    const f = ctx.faceAt(t0 + dur / 2);
    const list = ctx.el("div", "pop-list", scene);
    const side = p.side || (f.x < ctx.W / 2 ? "right" : "left");
    list.classList.add("pop-" + side);
    list.style.top = Math.max(60, f.y - f.h * 0.4) + "px";
    const items = p.items || ["עריכה", "כתוביות", "אפקטים"];
    const gap = Math.min(0.45, (dur - 0.6) / items.length);
    items.forEach((txt, i) => {
      const pill = ctx.el("div", "pop-pill", list, '<span class="pop-check">✓</span><span>' + txt + "</span>");
      tl.fromTo(pill, { scale: 0, opacity: 0 }, { scale: 1, opacity: 1, duration: 0.28, ease: "back.out(2.2)" }, t0 + 0.1 + i * gap);
      tl.fromTo(pill.firstChild, { scale: 0 }, { scale: 1, duration: 0.2, ease: "back.out(3)" }, t0 + 0.25 + i * gap);
    });
  };

  THFX.fx.headline_storm = function (tl, t0, dur, p, ctx) {
    const scene = THFX.scene(tl, ctx, ctx.top, t0, dur, "");
    const lines = p.lines || ["עריכה עם AI", "כתוביות לכל מילה", "20 אפקטים. פרומפט אחד."];
    const n = Math.min(6, Math.max(4, lines.length));
    for (let i = 0; i < n; i++) {
      const txt = lines[i % lines.length];
      const rb = ctx.el("div", "ribbon " + RIBBON_STYLES[i], scene, ("<span>" + txt + "</span>").repeat(4));
      rb.setAttribute("data-layout-allow-overflow", ""); // ribbons run edge to edge on purpose
      const rot = (i % 2 ? 1 : -1) * (6 + ctx.rand() * 6);
      rb.style.top = 22 + i * (52 / n) + "%";
      const dir = i % 2 ? 1 : -1;
      tl.fromTo(rb, { xPercent: dir * 110, rotation: rot }, { xPercent: 0, duration: 0.35, ease: "power3.out" }, t0 + i * 0.08);
      tl.to(rb, { xPercent: -dir * 6, duration: dur - 0.6, ease: "none" }, t0 + 0.35 + i * 0.08);
      tl.to(rb, { xPercent: -dir * 110, duration: 0.25, ease: "power2.in" }, t0 + dur - 0.25);
    }
  };

  /* Show the magnifying lens video inside a circle of radius r centred on (cx, cy). */
  function lensFrame(ctx, cx, cy, r, z, focus) {
    gsap.set(ctx.lensWrap, { clipPath: "circle(" + r + "px at " + cx + "px " + cy + "px)" });
    gsap.set(ctx.lensInner, { transformOrigin: "0px 0px", scale: z, x: cx - focus.x * z, y: cy - focus.y * z });
  }

  function lensOn(tl, ctx, t0, dur) {
    tl.set(ctx.lensWrap, { opacity: 1 }, t0);
    tl.set(ctx.lensWrap, { opacity: 0 }, t0 + dur);
  }

  THFX.fx.portal_zoom = function (tl, t0, dur, p, ctx) {
    const f = ctx.faceAt(t0 + dur / 2);
    const r = p.radius || ctx.W * 0.12;
    const cx = f.x < ctx.W / 2 ? ctx.W - r * 1.35 : r * 1.35, cy = Math.max(r * 1.4, f.y);
    const ring = ctx.el("i", "lens-ring ring-accent", THFX.scene(tl, ctx, ctx.top, t0, dur, ""));
    Object.assign(ring.style, { left: cx - r + "px", top: cy - r + "px", width: 2 * r + "px", height: 2 * r + "px" });
    lensOn(tl, ctx, t0, dur);
    // Fit the whole face in the circle, whatever its size in the frame.
    const zoom = p.zoom || ctx.clamp((2 * r) / (f.h * PORTAL_FACE_FILL), 0.3, 2.5);
    const st = { k: 0 };
    tl.fromTo(st, { k: 0 }, { k: 1, duration: 0.3, ease: "back.out(1.8)",
      onUpdate: () => lensFrame(ctx, cx, cy, Math.max(0.1, r * st.k), zoom, f) }, t0);
    tl.fromTo(ring, { scale: 0 }, { scale: 1, duration: 0.3, ease: "back.out(1.8)" }, t0);
  };

  THFX.fx.liquid_glass = function (tl, t0, dur, p, ctx) {
    const f = ctx.faceAt(t0 + dur / 2);
    const r = p.radius || ctx.W * 0.16;
    const ring = ctx.el("i", "lens-ring ring-glass", THFX.scene(tl, ctx, ctx.top, t0, dur, ""));
    Object.assign(ring.style, { width: 2 * r + "px", height: 2 * r + "px" });
    lensOn(tl, ctx, t0, dur);
    const x0 = ctx.W + r, x1 = -r, st = { k: 0 };
    tl.fromTo(st, { k: 0 }, { k: 1, duration: dur, ease: "sine.inOut", onUpdate: () => {
      const cx = x0 + (x1 - x0) * st.k, cy = f.y + Math.sin(st.k * Math.PI) * -f.h * 0.15;
      lensFrame(ctx, cx, cy, r, p.zoom || 1.35, { x: cx, y: cy });
      gsap.set(ring, { x: cx - r, y: cy - r });
    } }, t0);
  };

  THFX.fx.frame_break = function (tl, t0, dur, p, ctx) {
    const scene = THFX.scene(tl, ctx, ctx.top, t0, dur, "");
    const f = ctx.faceAt(t0 + dur / 2);
    const s = ctx.svg("svg", { class: "break-svg", viewBox: "0 0 " + ctx.W + " " + ctx.H }, scene);
    const L = Math.hypot(ctx.W, ctx.H);
    const rays = [];
    for (let i = 0; i < BREAK_RAYS; i++) {
      const a = (i / BREAK_RAYS) * Math.PI * 2 + ctx.rand() * 0.15;
      rays.push(ctx.svg("line", { x1: f.x, y1: f.y + f.h * 0.6, x2: f.x + Math.cos(a) * L, y2: f.y + f.h * 0.6 + Math.sin(a) * L,
        class: "break-ray", "stroke-dasharray": L, "stroke-dashoffset": L }, s));
    }
    const ring = ctx.svg("circle", { cx: f.x, cy: f.y + f.h * 0.6, r: f.h * 0.9, class: "break-ray" }, s);
    const flash = ctx.el("i", "fx-flash", scene);
    tl.fromTo(flash, { opacity: 0.85 }, { opacity: 0, duration: 0.25, ease: "power2.out" }, t0);
    tl.to(rays, { attr: { "stroke-dashoffset": 0 }, duration: 0.3, stagger: 0.012, ease: "power3.out" }, t0);
    tl.fromTo(ring, { attr: { r: 10 } }, { attr: { r: f.h * 0.9 }, duration: 0.35, ease: "power3.out" }, t0);
    tl.fromTo(ctx.cam, { x: -14 }, { x: 0, duration: 0.3, ease: "elastic.out(1.2,0.3)" }, t0);
    tl.to(s, { opacity: 0, duration: 0.3 }, t0 + dur - 0.3);
  };

  THFX.fx.recap_checklist = function (tl, t0, dur, p, ctx) {
    const scene = THFX.scene(tl, ctx, ctx.top, t0, dur, "fx-recap");
    ctx.el("div", "recap-title", scene, p.title || "סיכום");
    const grid = ctx.el("div", "recap-grid", scene);
    const items = p.items || [];
    const gap = Math.min(0.18, (dur - 0.8) / Math.max(1, items.length));
    items.forEach((txt, i) => {
      const row = ctx.el("div", "recap-row", grid, '<span class="pop-check">✓</span><span>' + txt + "</span>");
      tl.fromTo(row, { opacity: 0, x: 30 }, { opacity: 1, x: 0, duration: 0.2, ease: "power2.out" }, t0 + 0.3 + i * gap);
    });
    tl.fromTo(scene, { opacity: 0 }, { opacity: 1, duration: 0.25 }, t0);
  };
})();
