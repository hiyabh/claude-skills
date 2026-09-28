// poster-motion runtime - the motion vocabulary every generated shot calls.
// Inlined into index.html by build_composition.py, before the timeline code.
//
// Rules this file keeps (hyperframes determinism):
//  * everything is a pure function of timeline position - no Math.random,
//    no Date.now, no requestAnimationFrame, no repeat:-1
//  * cyclic motion runs off ONE phase proxy per group, tweened ease:"none",
//    mapped in onUpdate - it seeks deterministically
//  * elements are positioned with left/top/inset, never a CSS transform, so
//    GSAP owns every transform (gsap_css_transform_conflict)
var PM = (function () {
  var TAU = Math.PI * 2;

  function lcg(seed) {
    var s = seed >>> 0;
    return function () {
      s = (s * 1664525 + 1013904223) >>> 0;
      return s / 4294967296;
    };
  }

  // Word windows grow from their right edge: Hebrew is written right to left.
  function write(tl, sel, t, each, gap) {
    var els = gsap.utils.toArray(sel);
    els.forEach(function (el, i) {
      var w = el.getAttribute("data-w");
      tl.fromTo(el, { width: 0 }, { width: w + "px", duration: each,
        ease: "power2.inOut" }, t + i * (each + gap));
    });
    return t + els.length * (each + gap);
  }

  // Words slam in, one per beat, and the camera takes the hit.
  function stamp(tl, sel, t, beat, cam) {
    var els = gsap.utils.toArray(sel);
    els.forEach(function (el, i) {
      var at = t + i * beat;
      tl.fromTo(el, { scale: 1.9, opacity: 0 }, { scale: 1, opacity: 1,
        duration: 0.16, ease: "power4.in" }, at);
      if (cam) shake(tl, cam, at + 0.16, 7);
    });
    return t + els.length * beat;
  }

  function shake(tl, el, t, px) {
    tl.to(el, { x: px, y: -px * 0.5, duration: 0.04, ease: "none" }, t)
      .to(el, { x: -px * 0.6, y: px * 0.4, duration: 0.05, ease: "none" }, t + 0.04)
      .to(el, { x: px * 0.3, y: 0, duration: 0.05, ease: "none" }, t + 0.09)
      .to(el, { x: 0, y: 0, duration: 0.06, ease: "power2.out" }, t + 0.14);
  }

  function fade(tl, sel, t, dur) {
    tl.fromTo(sel, { opacity: 0, y: 14 }, { opacity: 1, y: 0, duration: dur,
      ease: "power2.out", stagger: dur * 0.35 }, t);
  }

  // Object entrances. `from` is set by build_composition from the bbox.
  var ENTER = {
    rise: function (el, d) { return [{ y: d.h * 0.18, opacity: 0 },
      { y: 0, opacity: 1, ease: "back.out(1.6)" }]; },
    drop: function (el, d) { return [{ y: -d.H * 0.7 }, { y: 0, ease: "bounce.out" }]; },
    pop: function (el, d) { return [{ scale: 0.55, opacity: 0 },
      { scale: 1, opacity: 1, ease: "back.out(2.2)" }]; },
    edge: function (el, d) {
      var o = { left: { x: -d.W }, right: { x: d.W }, top: { y: -d.H }, bottom: { y: d.H } };
      return [o[d.side], { x: 0, y: 0, ease: "power3.out" }];
    },
    peek: function (el, d) { return [{ y: d.h * 0.9 }, { y: 0, ease: "power2.out" }]; },
    fade: function () { return [{ opacity: 0 }, { opacity: 1, ease: "power1.out" }]; }
  };

  function enter(tl, el, kind, t, dur, d) {
    var pair = (ENTER[kind] || ENTER.fade)(el, d);
    pair[1].duration = dur;
    tl.fromTo(el, pair[0], pair[1], t);
  }

  // Accents fly in from seeded offsets and settle, spinning.
  function scatter(tl, sel, t, each, seed) {
    var rnd = lcg(seed);
    gsap.utils.toArray(sel).forEach(function (el, i) {
      var dx = (rnd() - 0.5) * 260, dy = (rnd() - 0.2) * 220, r = (rnd() - 0.5) * 90;
      tl.fromTo(el, { x: dx, y: dy, rotation: r, opacity: 0, scale: 0.4 },
        { x: 0, y: 0, rotation: 0, opacity: 1, scale: 1, duration: each * 2,
          ease: "power3.out" }, t + i * each);
    });
  }

  // Gentle bob / flutter for the rest of the shot. One proxy drives them all.
  function drift(tl, sel, t, span, amp, seed) {
    var els = gsap.utils.toArray(sel), rnd = lcg(seed), ph = [];
    els.forEach(function () { ph.push(rnd() * TAU); });
    var proxy = { p: 0 };
    tl.to(proxy, { p: TAU * Math.max(1, Math.round(span / 2.4)), duration: span,
      ease: "none", onUpdate: function () {
        for (var i = 0; i < els.length; i++) {
          var p = proxy.p + ph[i];
          gsap.set(els[i], { y: amp * Math.sin(p), x: amp * 0.5 * Math.sin(2 * p),
            rotation: amp * 0.35 * Math.cos(p) });
        }
      } }, t);
  }

  // Ink cut into vertical strips: drawn in right to left, then a travelling wave.
  function rope(tl, sel, t, drawDur, span, amp) {
    var els = gsap.utils.toArray(sel), n = els.length;
    els.forEach(function (el, i) {
      tl.fromTo(el, { opacity: 0 }, { opacity: 1, duration: 0.05, ease: "none" },
        t + drawDur * (n - 1 - i) / n);
    });
    var proxy = { p: 0 };
    tl.to(proxy, { p: TAU * Math.max(1, Math.round(span / 1.6)), duration: span,
      ease: "none", onUpdate: function () {
        for (var i = 0; i < n; i++) {
          gsap.set(els[i], { y: amp * Math.sin(proxy.p - i * 0.42) });
        }
      } }, t);
  }

  function push(tl, el, t, span, to) {
    tl.fromTo(el, { scale: 1 }, { scale: to, duration: span, ease: "none" }, t);
  }

  function punch(tl, el, t) {
    tl.fromTo(el, { scale: 1.045 }, { scale: 1, duration: 0.3, ease: "power2.out" }, t);
  }

  // Deterministic typing: text length is a function of the playhead.
  function type(tl, el, text, t, dur) {
    var node = typeof el === "string" ? document.querySelector(el) : el;
    var proxy = { n: 0 };
    tl.to(proxy, { n: text.length, duration: dur, ease: "none", onUpdate: function () {
      node.textContent = text.slice(0, Math.round(proxy.n));
    } }, t);
  }

  function count(tl, el, to, t, dur) {
    var node = typeof el === "string" ? document.querySelector(el) : el;
    var proxy = { n: 0 };
    tl.to(proxy, { n: to, duration: dur, ease: "power2.out", onUpdate: function () {
      node.firstChild.nodeValue = String(Math.round(proxy.n));
    } }, t);
  }

  function caption(tl, el, t, dur) {
    tl.fromTo(el, { opacity: 0, y: 40 }, { opacity: 1, y: 0, duration: 0.28,
      ease: "power3.out" }, t);
    tl.to(el, { opacity: 0, duration: 0.12, ease: "none" }, t + dur - 0.12);
  }

  return { lcg: lcg, write: write, stamp: stamp, shake: shake, fade: fade,
    enter: enter, scatter: scatter, drift: drift, rope: rope, push: push,
    punch: punch, type: type, count: count, caption: caption };
})();
