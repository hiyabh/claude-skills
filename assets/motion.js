// Shared by every page: scroll reveal, card spotlight, copy buttons.
// Progressive enhancement - without this file everything is visible and static.
(function () {
  "use strict";

  var STAGGER_MS = 45;
  var STAGGER_CAP = 8;
  var COPY_RESET_MS = 1600;
  var fine = window.matchMedia("(hover: hover) and (pointer: fine)");

  // Reveal once, staggering the elements that enter in the same frame.
  function initReveal() {
    var items = document.querySelectorAll(".reveal");
    if (!("IntersectionObserver" in window)) {
      items.forEach(function (el) { el.setAttribute("data-visible", ""); });
      return;
    }
    var io = new IntersectionObserver(function (entries) {
      var batch = entries.filter(function (e) { return e.isIntersecting; });
      batch.forEach(function (entry, i) {
        var el = entry.target;
        el.style.transitionDelay = Math.min(i, STAGGER_CAP) * STAGGER_MS + "ms";
        el.setAttribute("data-visible", "");
        io.unobserve(el);
        // Drop the delay afterwards so later hover/filter transitions are not late.
        el.addEventListener("transitionend", function () { el.style.transitionDelay = ""; },
                            { once: true });
      });
    }, { rootMargin: "0px 0px -6% 0px", threshold: 0.12 });
    items.forEach(function (el) { io.observe(el); });
    window.revealAll = function () {
      io.disconnect();
      items.forEach(function (el) { el.style.transitionDelay = ""; el.setAttribute("data-visible", ""); });
    };
  }

  // Gold light that follows the pointer inside each card (mouse only).
  function initSpotlight() {
    if (!fine.matches) return;
    document.querySelectorAll(".skill-card").forEach(function (card) {
      card.addEventListener("pointermove", function (e) {
        var r = card.getBoundingClientRect();
        card.style.setProperty("--mx", (e.clientX - r.left) + "px");
        card.style.setProperty("--my", (e.clientY - r.top) + "px");
      });
    });
  }

  function legacyCopy(text) {
    try {
      var ta = document.createElement("textarea");
      ta.value = text;
      ta.setAttribute("readonly", "");
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      var ok = document.execCommand("copy");
      document.body.removeChild(ta);
      return ok;
    } catch (err) { return false; }
  }

  function copyText(text, done) {
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(text).then(function () { done(true); },
                                               function () { done(legacyCopy(text)); });
    } else {
      done(legacyCopy(text));
    }
  }

  function initCopy() {
    document.querySelectorAll(".copybtn[data-copy]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        copyText(document.getElementById(btn.dataset.copy).innerText, function (ok) {
          btn.textContent = ok ? "הועתק ✓" : "בחר והעתק";
          if (ok) btn.setAttribute("data-done", "");
          setTimeout(function () {
            btn.textContent = "העתק";
            btn.removeAttribute("data-done");
          }, COPY_RESET_MS);
        });
      });
    });
  }

  window.motionReady = true;
  initReveal();
  initSpotlight();
  initCopy();
})();
