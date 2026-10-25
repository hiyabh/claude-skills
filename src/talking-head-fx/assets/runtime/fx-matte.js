/* Matte effects - the speaker is cut out (subject_<i>.webm from matte_segments.py) and
 * placed on a designed background.
 * green_screen (מסך ירוק) · studio (סטודיו) · paper_cutout (גזירי נייר) ·
 * magazine_cover (שער מגזין) · growth_chart (גרף צמיחה)
 */
(function () {
  "use strict";
  const THFX = window.THFX;
  const SKYLINE_BUILDINGS = 14;
  // How far each effect shrinks the cut-out so its background shows (plan params.subjectScale overrides).
  const SUBJECT_SCALE = { green_screen: 0.9, studio: 0.82, paper_cutout: 0.78, magazine_cover: 0.8, growth_chart: 0.74 };
  const MASTHEAD_MAX_PX = 230;
  const TAG_MIN_TOP = 210;      // keep the ON AIR tag clear of the top progress bar

  // A tight shot crops the body at the frame edges; shrinking it would expose those straight
  // cuts in mid-canvas, so tight framings keep the cut-out full size.
  const TIGHT_FACE = 0.2;       // face height / canvas height above which the shot counts as tight
  const subjScale = (type, p, ctx, t) => {
    if (p.subjectScale) return p.subjectScale;
    if (ctx.faceAt(t).h / ctx.H > TIGHT_FACE) return 1;
    return SUBJECT_SCALE[type];
  };
  const WINDOW_LIT_CHANCE = 0.45;
  const STAR_POINTS = "50,4 61,38 97,38 68,59 79,93 50,72 21,93 32,59 3,38 39,38";
  // Four hard white shadows = a sticker outline around the cut-out speaker.
  const PAPER_OUTLINE = "drop-shadow(7px 0 0 #fff) drop-shadow(-7px 0 0 #fff) drop-shadow(0 7px 0 #fff) " +
    "drop-shadow(0 -7px 0 #fff) drop-shadow(0 18px 22px rgba(0,0,0,.35))";

  function enter(tl, node, t0) {
    tl.fromTo(node, { opacity: 0 }, { opacity: 1, duration: 0.18, ease: "none" }, t0);
  }

  function skyline(ctx, parent) {
    const s = ctx.svg("svg", { class: "skyline", viewBox: "0 0 1000 600", preserveAspectRatio: "none" }, parent);
    const bw = 1000 / SKYLINE_BUILDINGS;
    for (let i = 0; i < SKYLINE_BUILDINGS; i++) {
      const h = 160 + ctx.rand() * 340, x = i * bw;
      ctx.svg("rect", { x, y: 600 - h, width: bw - 4, height: h, fill: "#0b0d1c" }, s);
      for (let wy = 600 - h + 14; wy < 590; wy += 22) {
        for (let wx = x + 8; wx < x + bw - 14; wx += 16) {
          if (ctx.rand() < WINDOW_LIT_CHANCE)
            ctx.svg("rect", { x: wx, y: wy, width: 6, height: 9, fill: "#ffcf6e" }, s);
        }
      }
    }
    return s;
  }

  THFX.fx.green_screen = function (tl, t0, dur, p, ctx) {
    if (!THFX.useSubject(tl, ctx, ctx.index, t0, dur, subjScale("green_screen", p, ctx, t0 + dur / 2))) return;
    const scene = THFX.scene(tl, ctx, ctx.bg, t0, dur, "fx-chroma");
    const swap = ctx.el("div", "fx-scene fx-dusk", scene);
    if (p.image) {
      const img = ctx.el("img", "fx-cover", swap);
      img.src = p.image;
    } else skyline(ctx, swap);
    const at = t0 + dur * (p.swapAt || 0.42);
    tl.fromTo(swap, { clipPath: "inset(0% 0% 0% 100%)", opacity: 1 },
      { clipPath: "inset(0% 0% 0% 0%)", duration: 0.35, ease: "power2.inOut" }, at);
  };

  THFX.fx.studio = function (tl, t0, dur, p, ctx) {
    const s = subjScale("studio", p, ctx, t0 + dur / 2);
    if (!THFX.useSubject(tl, ctx, ctx.index, t0, dur, s)) return;
    const scene = THFX.scene(tl, ctx, ctx.bg, t0, dur, "fx-studio");
    const lights = [0.04, 0.4, 0.76].map((x) => {
      const l = ctx.el("i", "softbox", scene);
      l.style.left = x * 100 + "%";
      return l;
    });
    enter(tl, scene, t0);
    tl.fromTo(lights, { opacity: 0 }, { opacity: 1, duration: 0.12, stagger: 0.09, ease: "none" }, t0 + 0.1);
    const f = THFX.faceInSubject(ctx, t0 + dur / 2, s);
    const tagScene = THFX.scene(tl, ctx, ctx.top, t0, dur, "");
    const tag = ctx.el("div", "onair", tagScene, p.tag || "בשידור");
    Object.assign(tag.style, { left: f.x + "px", top: Math.max(TAG_MIN_TOP, f.y - f.h * 0.95) + "px" });
    tl.fromTo(tag, { opacity: 0, scale: 0.6 }, { opacity: 1, scale: 1, duration: 0.25, ease: "back.out(2)" }, t0 + 0.3);
  };

  THFX.fx.paper_cutout = function (tl, t0, dur, p, ctx) {
    const subj = THFX.useSubject(tl, ctx, ctx.index, t0, dur, subjScale("paper_cutout", p, ctx, t0 + dur / 2));
    if (!subj) return;
    const scene = THFX.scene(tl, ctx, ctx.bg, t0, dur, "fx-paper");
    const star = ctx.svg("svg", { class: "paper-star", viewBox: "0 0 100 100" }, scene);
    ctx.svg("polygon", { points: STAR_POINTS }, star);
    const dot = ctx.el("i", "paper-dot", scene);
    ctx.el("i", "paper-torn", scene);
    tl.set(subj, { filter: PAPER_OUTLINE }, t0);
    tl.set(subj, { filter: "none" }, t0 + dur);
    tl.fromTo([star, dot], { scale: 0, rotation: -40 }, { scale: 1, rotation: 0, duration: 0.3,
      stagger: 0.08, ease: "back.out(2.2)" }, t0 + 0.05);
    // Stop-motion wobble: stepped rotation reads as hand-cut paper.
    tl.fromTo(subj, { rotation: -1.2 }, { rotation: 1.2, duration: dur, ease: "steps(" + Math.max(2, Math.round(dur * 4)) + ")" }, t0);
    tl.set(subj, { rotation: 0 }, t0 + dur);
  };

  THFX.fx.magazine_cover = function (tl, t0, dur, p, ctx) {
    if (!THFX.useSubject(tl, ctx, ctx.index, t0, dur, subjScale("magazine_cover", p, ctx, t0 + dur / 2))) return;
    THFX.scene(tl, ctx, ctx.bg, t0, dur, "fx-cream");
    const mastScene = THFX.scene(tl, ctx, ctx.mid, t0, dur, "");
    const title = p.masthead || "STRATEGIX";
    const mast = ctx.el("div", "mag-masthead", mastScene, title);
    mast.style.fontSize = Math.min(MASTHEAD_MAX_PX, (ctx.W * 1.5) / title.length) + "px";
    const over = THFX.scene(tl, ctx, ctx.top, t0, dur, "");
    ctx.el("div", "mag-issue", over, p.issue || "גיליון מיוחד");
    const lines = ctx.el("div", "mag-lines", over, (p.lines || ["קלוד", "עורך", "וידאו"]).map((l) => "<b>" + l + "</b>").join(""));
    const badge = ctx.el("div", "mag-badge", over, p.badge || "20<small>אפקטים</small>");
    ctx.el("div", "mag-barcode", over);
    // Cover lines go on the side away from the face.
    const side = ctx.faceAt(t0 + dur / 2).x > ctx.W / 2 ? "left" : "right";
    [lines, badge].forEach((n) => Object.assign(n.style, { insetInlineStart: "auto", [side]: "6%" }));
    tl.fromTo(mast, { y: -60, opacity: 0 }, { y: 0, opacity: 1, duration: 0.35, ease: "power3.out" }, t0);
    tl.fromTo(lines, { x: 50, opacity: 0 }, { x: 0, opacity: 1, duration: 0.3, ease: "power2.out" }, t0 + 0.15);
    tl.fromTo(badge, { scale: 0, rotation: -30 }, { scale: 1, rotation: 0, duration: 0.35, ease: "back.out(2)" }, t0 + 0.3);
  };

  function chartPath(n, rand) {
    const pts = [];
    for (let i = 0; i <= n; i++) {
      const x = 20 + (i / n) * 460;
      const y = 380 - Math.pow(i / n, 1.8) * 330 + (i > 0 && i < n ? (rand() - 0.5) * 40 : 0);
      pts.push(x.toFixed(1) + "," + y.toFixed(1));
    }
    return pts.join(" ");
  }

  THFX.fx.growth_chart = function (tl, t0, dur, p, ctx) {
    const hasSubject = !!THFX.useSubject(tl, ctx, ctx.index, t0, dur, subjScale("growth_chart", p, ctx, t0 + dur / 2));
    THFX.scene(tl, ctx, ctx.bg, t0, dur, "fx-grid");
    if (!hasSubject) tl.fromTo(ctx.cam, { filter: "brightness(1)" }, { filter: "brightness(0.55)", duration: 0.2 }, t0);
    // With a cut-out the chart sits behind the speaker; over plain footage it has to go on top.
    const over = THFX.scene(tl, ctx, hasSubject ? ctx.mid : ctx.top, t0, dur, "fx-chart");
    const chart = ctx.svg("svg", { class: "chart-svg", viewBox: "0 0 500 400" }, over);
    const line = ctx.svg("polyline", { points: chartPath(9, ctx.rand), class: "chart-line" }, chart);
    const badge = ctx.el("div", "chart-badge", over, "1x");
    ctx.el("div", "chart-label", over, p.label || "צמיחה");
    const len = 1400;
    tl.fromTo(line, { attr: { "stroke-dasharray": len, "stroke-dashoffset": len } },
      { attr: { "stroke-dashoffset": 0 }, duration: dur * 0.8, ease: "power1.in" }, t0 + 0.1);
    const st = { v: p.from || 1 };
    tl.fromTo(st, { v: p.from || 1 }, { v: p.to || 10, duration: dur * 0.8, ease: "power1.in",
      onUpdate: () => { badge.textContent = Math.round(st.v) + (p.suffix || "x"); } }, t0 + 0.1);
    if (!hasSubject) tl.set(ctx.cam, { filter: "none" }, t0 + dur);
  };
})();
