/* Camera effects - transforms of the #cam wrapper aimed at the face.
 * punch_zoom (זום חד) · jump_zoom (חיתוך זום) · dolly_zoom (דולי זום) · digital_zoom (זום דיגיטלי)
 */
(function () {
  "use strict";
  const THFX = window.THFX;
  const PUNCH_IN = 0.18, PUNCH_OUT = 0.22, PUNCH_BLUR = 7;
  const DOLLY_OUT = 0.35;
  const SHAKE_FREQ = 1.7, SHAKE_PX = 6;
  const TIMECODE_BASE_SEC = 12 * 60 + 18; // camcorder counter starts at 00:12:18

  function aimAtFace(tl, ctx, t0, dur) {
    const f = ctx.faceAt(t0 + dur / 2);
    tl.set(ctx.cam, { transformOrigin: f.x + "px " + f.y + "px" }, t0);
    return f;
  }

  THFX.fx.punch_zoom = function (tl, t0, dur, p, ctx) {
    const zoom = p.zoom || 1.35;
    aimAtFace(tl, ctx, t0, dur);
    tl.fromTo(ctx.cam, { scale: 1, filter: "blur(" + PUNCH_BLUR + "px)" },
      { scale: zoom, filter: "blur(0px)", duration: PUNCH_IN, ease: "power3.out" }, t0);
    tl.to(ctx.cam, { scale: 1, duration: PUNCH_OUT, ease: "power2.inOut" }, t0 + dur - PUNCH_OUT);
    THFX.resetCam(tl, ctx, t0 + dur);
  };

  THFX.fx.jump_zoom = function (tl, t0, dur, p, ctx) {
    const zoom = p.zoom || 1.6;
    aimAtFace(tl, ctx, t0, dur);
    tl.set(ctx.cam, { scale: zoom, filter: "blur(10px)" }, t0);
    tl.to(ctx.cam, { filter: "blur(0px)", duration: 0.12, ease: "power1.out" }, t0);
    THFX.resetCam(tl, ctx, t0 + dur);
  };

  THFX.fx.dolly_zoom = function (tl, t0, dur, p, ctx) {
    const zoom = p.zoom || 1.18;
    aimAtFace(tl, ctx, t0, dur);
    tl.fromTo(ctx.cam, { scale: 1 }, { scale: zoom, duration: dur - DOLLY_OUT, ease: "none" }, t0);
    tl.to(ctx.cam, { scale: 1, duration: DOLLY_OUT, ease: "power2.inOut" }, t0 + dur - DOLLY_OUT);
    THFX.resetCam(tl, ctx, t0 + dur);
  };

  function viewfinder(tl, ctx, t0, dur) {
    const scene = THFX.scene(tl, ctx, ctx.top, t0, dur, "fx-viewfinder");
    ["tl", "tr", "bl", "br"].forEach((c) => ctx.el("i", "vf-corner vf-" + c, scene));
    const rec = ctx.el("div", "vf-rec", scene, '<b class="vf-dot"></b>REC');
    const tc = ctx.el("div", "vf-tc", scene, "00:00:00");
    const badge = ctx.el("div", "vf-zoom", scene, "1.0x");
    return { scene, rec, tc, badge };
  }

  function timecode(sec) {
    const s = Math.floor(sec), pad = (n) => String(n).padStart(2, "0");
    return pad(Math.floor(s / 3600)) + ":" + pad(Math.floor((s % 3600) / 60)) + ":" + pad(s % 60);
  }

  THFX.fx.digital_zoom = function (tl, t0, dur, p, ctx) {
    const zoom = p.zoom || 2.6;
    const vf = viewfinder(tl, ctx, t0, dur);
    aimAtFace(tl, ctx, t0, dur);
    const st = { z: 1, k: 0 };
    tl.fromTo(st, { z: 1, k: 0 }, {
      z: zoom, k: 1, duration: dur, ease: "power1.inOut",
      onUpdate: () => {
        const shake = Math.sin(st.k * dur * SHAKE_FREQ * Math.PI * 2) * SHAKE_PX;
        gsap.set(ctx.cam, { scale: st.z, x: shake, y: -shake * 0.6 });
        vf.badge.textContent = st.z.toFixed(1) + "x";
        vf.tc.textContent = timecode(TIMECODE_BASE_SEC + st.k * dur);
        vf.rec.classList.toggle("off", Math.floor(st.k * dur * 2) % 2 === 1);
      },
    }, t0);
    tl.fromTo(vf.scene, { scale: 1.08 }, { scale: 1, duration: 0.25, ease: "power2.out" }, t0);
    THFX.resetCam(tl, ctx, t0 + dur);
  };
})();
