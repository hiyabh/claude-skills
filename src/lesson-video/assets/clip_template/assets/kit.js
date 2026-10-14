/* Shared, seek-safe GSAP helpers for every chapter composition.
   All times are chapter-local seconds on the chapter's own paused timeline.
   Every helper uses fromTo with explicit endpoints (or `to` after a fromTo) so any frame
   is a pure function of timeline time. */
(function () {
  const BEAT_FADE_IN = 0.45;
  const BEAT_FADE_OUT = 0.4;
  const BREATH_PERIOD = 4;

  function q(root, sel) {
    return typeof sel === "string" ? root.querySelectorAll(sel) : sel;
  }

  const K = {
    // Fade a beat's inner wrapper in at its start and out just before its end.
    beat(tl, root, id, start, dur) {
      const inner = root.querySelector(`#${id} > .in`);
      tl.fromTo(inner, { opacity: 0 }, { opacity: 1, duration: BEAT_FADE_IN, ease: "power1.out" }, start);
      tl.to(inner, { opacity: 0, duration: BEAT_FADE_OUT, ease: "power1.in" }, start + dur - BEAT_FADE_OUT);
    },

    // Entrance: rise/slide + fade. opts: x, y, dur, ease, stagger, scale
    in(tl, root, sel, t, opts = {}) {
      const { x = 0, y = 40, dur = 0.6, ease = "power3.out", stagger = 0, scale = 1 } = opts;
      tl.fromTo(q(root, sel), { opacity: 0, x, y, scale },
        { opacity: 1, x: 0, y: 0, scale: 1, duration: dur, ease, stagger }, t);
    },

    // Spring pop entrance (back.out overshoot).
    pop(tl, root, sel, t, opts = {}) {
      const { dur = 0.55, stagger = 0, overshoot = 1.8 } = opts;
      tl.fromTo(q(root, sel), { opacity: 0, scale: 0.4 },
        { opacity: 1, scale: 1, duration: dur, ease: `back.out(${overshoot})`, stagger }, t);
    },

    // Exit fade (after an entrance on the same target).
    out(tl, root, sel, t, opts = {}) {
      const { dur = 0.4, y = 0, scale = 1 } = opts;
      tl.to(q(root, sel), { opacity: 0, y, scale, duration: dur, ease: "power1.in" }, t);
    },

    // Re-show something that was faded out by K.out.
    back(tl, root, sel, t, opts = {}) {
      const { dur = 0.45 } = opts;
      tl.to(q(root, sel), { opacity: 1, y: 0, scale: 1, duration: dur, ease: "power2.out" }, t);
    },

    // Dim to a resting opacity (de-emphasize without removing).
    dim(tl, root, sel, t, opts = {}) {
      const { to = 0.3, dur = 0.5 } = opts;
      tl.to(q(root, sel), { opacity: to, duration: dur, ease: "power1.inOut" }, t);
    },

    // Highlight sweep under a .hl word (marker bar).
    mark(tl, root, sel, t, opts = {}) {
      const { dur = 0.5 } = opts;
      q(root, sel).forEach((el) => {
        const bar = el.querySelector(".bar");
        tl.fromTo(bar, { scaleX: 0 }, { scaleX: 1, duration: dur, ease: "power2.out" }, t);
      });
    },

    // Number count from `from` to `to`; writes text only (seek-safe via proxy).
    // Repeated calls on the same element chain onto ONE proxy so seeking stays consistent.
    count(tl, root, sel, from, to, t, dur, opts = {}) {
      const { decimals = 0, prefix = "", suffix = "" } = opts;
      const el = q(root, sel)[0];
      const fresh = !el.__kproxy;
      const proxy = el.__kproxy || (el.__kproxy = { v: from });
      const write = () => { el.textContent = prefix + proxy.v.toFixed(decimals) + suffix; };
      if (fresh) {
        write();
        tl.fromTo(proxy, { v: from }, { v: to, duration: dur, ease: "power2.out", onUpdate: write }, t);
      } else {
        tl.to(proxy, { v: to, duration: dur, ease: "power2.out", onUpdate: write }, t);
      }
    },

    // Finite breathing loop (scale) over [t0, t0+total).
    breathe(tl, root, sel, t0, total, opts = {}) {
      const { scale = 1.04, period = BREATH_PERIOD } = opts;
      const half = period / 2;
      const repeat = Math.max(0, Math.floor(total / half) - 1);
      tl.fromTo(q(root, sel), { scale: 1 },
        { scale, duration: half, ease: "sine.inOut", yoyo: true, repeat, immediateRender: false }, t0);
    },

    // Slow Ken Burns on an image wrapper.
    ken(tl, root, sel, t0, dur, opts = {}) {
      const { from = 1.0, to = 1.12, x = 0, y = 0 } = opts;
      tl.fromTo(q(root, sel), { scale: from, x: 0, y: 0 },
        { scale: to, x, y, duration: dur, ease: "none" }, t0);
    },

    // Linear horizontal drift (ghost words).
    drift(tl, root, sel, t0, dur, opts = {}) {
      const { x = 160 } = opts;
      tl.fromTo(q(root, sel), { x: 0 }, { x, duration: dur, ease: "none" }, t0);
    },

    // SVG stroke draw. Path length is measured once at build time.
    draw(tl, root, sel, t, dur, opts = {}) {
      const { ease = "power2.inOut", stagger = 0 } = opts;
      q(root, sel).forEach((p, i) => {
        const len = p.getTotalLength();
        p.style.strokeDasharray = `${len}`;
        tl.fromTo(p, { strokeDashoffset: len }, { strokeDashoffset: 0, duration: dur, ease }, t + i * stagger);
      });
    },

    // Word-by-word reveal of a text element: splits on spaces into inline-block spans.
    words(tl, root, sel, t, opts = {}) {
      const { stagger = 0.08, dur = 0.45, y = 24 } = opts;
      q(root, sel).forEach((el) => {
        const parts = el.textContent.trim().split(/\s+/);
        el.textContent = "";
        parts.forEach((w, i) => {
          const s = document.createElement("span");
          s.className = "w";
          s.style.display = "inline-block";
          s.textContent = w;
          el.appendChild(s);
          if (i < parts.length - 1) el.appendChild(document.createTextNode(" "));
        });
        tl.fromTo(el.querySelectorAll(".w"), { opacity: 0, y },
          { opacity: 1, y: 0, duration: dur, ease: "power2.out", stagger }, t);
      });
    },

    // Color change (e.g. a cell lighting up).
    tint(tl, root, sel, t, color, opts = {}) {
      const { dur = 0.4, prop = "color" } = opts;
      tl.to(q(root, sel), { [prop]: color, duration: dur, ease: "power1.inOut" }, t);
    },
  };

  window.K = K;
})();
