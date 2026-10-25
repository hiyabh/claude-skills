/* Frame effects - the footage shrinks into a designed container.
 * chat_takeover (השתלטות צ'אט) · phone_mockup (מוקאפ טלפון) · broll_layers (שכבות בי-רול) ·
 * frame_escape (בריחה מהפריים, needs a matted subject)
 */
(function () {
  "use strict";
  const THFX = window.THFX;
  const MOVE = 0.38;            // seconds for the shrink / grow transition
  const EASE_IN = "power3.inOut";

  /* Crop of the full-canvas footage (local px) that lands on `rect` (canvas px). */
  function cropFor(ctx, rect, scale, t, topBias) {
    const f = ctx.faceAt(t);
    const cw = rect.w / scale, ch = rect.h / scale;
    const left = ctx.clamp(f.x - cw / 2, 0, Math.max(0, ctx.W - cw));
    const top = ctx.clamp(topBias !== undefined ? topBias : f.y - ch * 0.35, 0, Math.max(0, ctx.H - ch));
    return { left, top, cw, ch };
  }

  function insetOf(ctx, c, radius) {
    const r = ctx.W - (c.left + c.cw), b = ctx.H - (c.top + c.ch);
    return "inset(" + c.top + "px " + r + "px " + b + "px " + c.left + "px round " + radius + "px)";
  }

  /* Animate #cam (and optional extra layers) into `rect`, hold, then back out. */
  THFX.frameCam = function (tl, ctx, t0, dur, rect, opts) {
    const o = opts || {};
    const scale = o.scale || Math.max(rect.w / ctx.W, rect.h / ctx.H);
    const crop = o.crop || cropFor(ctx, rect, scale, t0 + dur / 2);
    const target = {
      scale, x: rect.x - crop.left * scale, y: rect.y - crop.top * scale,
      clipPath: insetOf(ctx, crop, (o.radius || 0) / scale),
    };
    const layers = [ctx.cam].concat(o.with || []);
    tl.set(layers, { transformOrigin: "0px 0px" }, t0);
    tl.fromTo(layers, { scale: 1, x: 0, y: 0, clipPath: insetOf(ctx, { left: 0, top: 0, cw: ctx.W, ch: ctx.H }, 0) },
      Object.assign({ duration: MOVE, ease: EASE_IN }, target), t0);
    tl.to(layers, { scale: 1, x: 0, y: 0, clipPath: "inset(0px 0px 0px 0px round 0px)",
      duration: MOVE, ease: EASE_IN }, t0 + dur - MOVE);
    THFX.resetCam(tl, ctx, t0 + dur);
    return { crop, scale, target };
  };

  function popIn(tl, node, t, from) {
    tl.fromTo(node, Object.assign({ opacity: 0, scale: 0.9 }, from || {}),
      { opacity: 1, scale: 1, x: 0, y: 0, duration: 0.32, ease: "back.out(1.6)" }, t);
  }

  THFX.fx.chat_takeover = function (tl, t0, dur, p, ctx) {
    const W = ctx.W, H = ctx.H;
    const scene = THFX.scene(tl, ctx, ctx.bg, t0, dur, "fx-dark");
    const card = ctx.el("div", "chat-card", scene);
    const cx = 0.07 * W, cy = 0.2 * H, cw = 0.86 * W, ch = 0.56 * H;
    Object.assign(card.style, { left: cx + "px", top: cy + "px", width: cw + "px", height: ch + "px" });
    ctx.el("div", "chat-head", card, '<span class="chat-logo">✺</span>' + (p.assistant || "Claude"));
    const bubble = ctx.el("div", "chat-bubble", card, p.prompt || "תערוך את הסרטון ותוסיף אפקטים");
    const dots = ctx.el("div", "chat-dots", card, "<i></i><i></i><i></i>");
    popIn(tl, card, t0, { y: 60 });
    popIn(tl, bubble, t0 + 0.18, { x: 40 });
    popIn(tl, dots, t0 + 0.3);
    const rect = { x: cx + cw * 0.45, y: cy + ch * 0.3, w: cw * 0.5, h: ch * 0.64 };
    THFX.frameCam(tl, ctx, t0, dur, rect, { radius: 26 });
  };

  THFX.fx.phone_mockup = function (tl, t0, dur, p, ctx) {
    const W = ctx.W, H = ctx.H;
    THFX.scene(tl, ctx, ctx.bg, t0, dur, "fx-navy");
    const pw = 0.56 * W, ph = Math.min(pw * 2.05, 0.8 * H);
    const rect = { x: (W - pw) / 2, y: (H - ph) / 2 - 0.02 * H, w: pw, h: ph };
    const frameScene = THFX.scene(tl, ctx, ctx.top, t0, dur, "");
    const phone = ctx.el("div", "phone-frame", frameScene, '<i class="phone-island"></i>');
    const bez = 16;
    Object.assign(phone.style, { left: rect.x - bez + "px", top: rect.y - bez + "px",
      width: pw + 2 * bez + "px", height: ph + 2 * bez + "px" });
    tl.fromTo(phone, { opacity: 0, scale: 1.12 }, { opacity: 1, scale: 1, duration: MOVE, ease: EASE_IN }, t0);
    tl.to(phone, { opacity: 0, scale: 1.12, duration: MOVE * 0.8, ease: EASE_IN }, t0 + dur - MOVE);
    THFX.frameCam(tl, ctx, t0, dur, rect, { radius: 58 });
  };

  function editorChrome(ctx, scene, rect) {
    const win = ctx.el("div", "ed-window", scene, '<div class="ed-bar"><i></i><i></i><i></i></div>');
    const frame = ctx.el("div", "ed-preview", scene);
    Object.assign(frame.style, { left: rect.x - 6 + "px", top: rect.y - 6 + "px",
      width: rect.w + 12 + "px", height: rect.h + 12 + "px" });
    const tracks = ctx.el("div", "ed-tracks", scene);
    const lanes = [[0.05, 0.3, 0.5, 0.2], [0.15, 0.25, 0.62, 0.2], [0.0, 0.42, 0.55, 0.3]];
    lanes.forEach((lane) => {
      const row = ctx.el("div", "ed-lane", tracks);
      for (let i = 0; i < lane.length; i += 2) {
        const clip = ctx.el("b", "ed-clip", row);
        Object.assign(clip.style, { left: lane[i] * 100 + "%", width: lane[i + 1] * 100 + "%" });
      }
    });
    const head = ctx.el("i", "ed-playhead", tracks);
    return { win, tracks, head };
  }

  function brollCard(ctx, parent, p, i) {
    const card = ctx.el("div", "broll-card broll-" + i, parent);
    if (p.images && p.images[i]) ctx.el("img", "", card).src = p.images[i];
    else card.innerHTML = "<i></i><i></i><i></i><i class='short'></i>";
    return card;
  }

  THFX.fx.broll_layers = function (tl, t0, dur, p, ctx) {
    const W = ctx.W, H = ctx.H;
    const scene = THFX.scene(tl, ctx, ctx.bg, t0, dur, "fx-editor");
    const rect = { x: 0.2 * W, y: 0.13 * H, w: 0.6 * W, h: 0.5 * H };
    const ed = editorChrome(ctx, scene, rect);
    tl.fromTo(ed.head, { left: "8%" }, { left: "86%", duration: dur, ease: "none" }, t0);
    const over = THFX.scene(tl, ctx, ctx.top, t0, dur, "");
    const n = Math.min(2, (p.images || []).length || 2);
    for (let i = 0; i < n; i++) popIn(tl, brollCard(ctx, over, p, i), t0 + MOVE + 0.25 + i * 0.35, { y: -40 });
    THFX.frameCam(tl, ctx, t0, dur, rect, { radius: 18 });
  };

  THFX.fx.frame_escape = function (tl, t0, dur, p, ctx) {
    const subj = ctx.subject(ctx.index);
    const W = ctx.W, H = ctx.H, f = ctx.faceAt(t0 + dur / 2);
    THFX.scene(tl, ctx, ctx.bg, t0, dur, "fx-dark");
    const scale = p.scale || 0.8;
    const rect = { x: 0.1 * W, w: 0.8 * W, y: 0, h: 0 };
    const cropTop = Math.max(0, f.y - f.h * 0.15);
    const ch = Math.min(H - cropTop, (0.5 * H) / scale);
    rect.h = ch * scale;
    rect.y = 0.36 * H;
    const crop = cropFor(ctx, rect, scale, t0 + dur / 2, cropTop);
    const border = THFX.scene(tl, ctx, ctx.mid, t0 + MOVE, dur - 2 * MOVE, "");
    const box = ctx.el("div", "escape-border", border);
    Object.assign(box.style, { left: rect.x + "px", top: rect.y + "px", width: rect.w + "px", height: rect.h + "px" });
    const fc = THFX.frameCam(tl, ctx, t0, dur, rect, { scale, crop });
    if (!subj) return console.warn("[thfx] frame_escape without a matted subject - showing a plain frame.");
    // The subject sits exactly on the framed footage but is clipped only below/beside the
    // box, so the head breaks out over the top border.
    const r = ctx.W - (crop.left + crop.cw), b = ctx.H - (crop.top + crop.ch);
    tl.set(subj, { transformOrigin: "0px 0px", scale, x: fc.target.x, y: fc.target.y, opacity: 1,
      clipPath: "inset(0px " + r + "px " + b + "px " + crop.left + "px)" }, t0 + MOVE);
    tl.set(subj, { opacity: 0, scale: 1, x: 0, y: 0, clipPath: "none" }, t0 + dur - MOVE);
  };
})();
