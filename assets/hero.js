// Hub hero: rotating "say to Claude" ticker, count-up stats, icon constellation.
(function () {
  "use strict";

  var TICKER_INTERVAL_MS = 3400;
  var TICKER_OUT_MS = 200;
  var COUNT_MS = 900;
  var COUNT_DELAY_MS = 450;
  var PARALLAX_PX = 22;
  var SPRING = 0.09;          // fraction of the remaining distance closed per frame
  var SETTLE_PX = 0.05;
  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var fine = window.matchMedia("(hover: hover) and (pointer: fine)").matches;

  function initTicker() {
    var box = document.querySelector(".ticker");
    if (!box || reduce) return;
    var phrases = JSON.parse(box.dataset.phrases);
    var link = box.querySelector(".ticker-link");
    var say = box.querySelector(".ticker-say");
    var skill = box.querySelector(".ticker-skill");
    var index = 0;
    var paused = false;

    function show(p) {
      say.textContent = "\"" + p.say + "\"";
      skill.textContent = "← " + p.title;
      link.href = p.url;
    }

    function next() {
      if (paused || document.hidden) return;
      index = (index + 1) % phrases.length;
      link.classList.add("swap-out");
      setTimeout(function () {
        show(phrases[index]);
        link.classList.remove("swap-out");
        link.classList.add("swap-in");
        link.getBoundingClientRect();          // commit the start state before transitioning
        link.classList.remove("swap-in");
      }, TICKER_OUT_MS);
    }

    show(phrases[0]);
    link.addEventListener("pointerenter", function () { paused = true; });
    link.addEventListener("pointerleave", function () { paused = false; });
    link.addEventListener("focus", function () { paused = true; });
    link.addEventListener("blur", function () { paused = false; });
    setInterval(next, TICKER_INTERVAL_MS);
  }

  function countUp(el) {
    var target = parseInt(el.dataset.count, 10);
    var start = null;
    function frame(t) {
      if (start === null) start = t;
      var p = Math.min((t - start) / COUNT_MS, 1);
      var eased = 1 - Math.pow(1 - p, 3);    // ease-out cubic: fast start, soft landing
      el.textContent = String(Math.round(target * eased));
      if (p < 1) requestAnimationFrame(frame);
    }
    el.textContent = "0";
    setTimeout(function () { requestAnimationFrame(frame); }, COUNT_DELAY_MS);
  }

  function initCounts() {
    if (reduce) return;
    document.querySelectorAll("[data-count]").forEach(countUp);
  }

  // Each star eases toward a pointer-driven offset scaled by its depth, so
  // near icons move more than far ones. The loop sleeps once everything settles.
  function initConstellation() {
    var field = document.querySelector(".constellation");
    if (!field || reduce || !fine) return;
    var stars = Array.prototype.map.call(field.querySelectorAll(".star"), function (el) {
      return { el: el, depth: parseFloat(el.dataset.depth), x: 0, y: 0 };
    });
    var target = { x: 0, y: 0 };
    var running = false;

    function tick() {
      var moving = false;
      stars.forEach(function (s) {
        var tx = target.x * s.depth, ty = target.y * s.depth;
        s.x += (tx - s.x) * SPRING;
        s.y += (ty - s.y) * SPRING;
        if (Math.abs(tx - s.x) > SETTLE_PX || Math.abs(ty - s.y) > SETTLE_PX) moving = true;
        s.el.style.transform = "translate3d(" + s.x.toFixed(2) + "px," + s.y.toFixed(2) + "px,0)";
      });
      running = moving;
      if (moving) requestAnimationFrame(tick);
    }

    window.addEventListener("pointermove", function (e) {
      target.x = (e.clientX / window.innerWidth - 0.5) * -PARALLAX_PX * 2;
      target.y = (e.clientY / window.innerHeight - 0.5) * -PARALLAX_PX * 2;
      if (!running) { running = true; requestAnimationFrame(tick); }
    }, { passive: true });
  }

  initTicker();
  initCounts();
  initConstellation();
})();
