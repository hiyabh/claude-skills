// Progressive enhancement: every page works without this file.
// Hub: live search + category filter. Skill pages: copy buttons.
(function () {
  "use strict";

  var COPY_RESET_MS = 1600;

  function initFilter() {
    var search = document.querySelector(".search");
    var chips = document.querySelectorAll(".chip[data-filter]");
    if (!search || !chips.length) return;
    var cards = document.querySelectorAll(".cardwrap");
    var sections = document.querySelectorAll("section.cat");
    var empty = document.querySelector(".empty");
    var active = "all";
    search.hidden = false;

    function apply() {
      var q = search.value.trim().toLowerCase();
      var shown = 0;
      cards.forEach(function (card) {
        var okCat = active === "all" || card.dataset.cat === active;
        var okText = !q || card.dataset.search.indexOf(q) !== -1;
        card.hidden = !(okCat && okText);
        if (!card.hidden) shown++;
      });
      sections.forEach(function (sec) {
        sec.hidden = !sec.querySelector(".cardwrap:not([hidden])");
      });
      empty.hidden = shown !== 0;
    }

    function setActive(filter) {
      active = filter;
      chips.forEach(function (c) {
        c.setAttribute("aria-pressed", String(c.dataset.filter === filter));
      });
      apply();
    }

    document.addEventListener("click", function (e) {
      var el = e.target.closest("[data-filter]");
      if (!el) return;
      e.preventDefault();
      if (el.dataset.filter === "all") search.value = "";
      setActive(el.dataset.filter);
    });
    search.addEventListener("input", apply);
  }

  function copyText(text, done) {
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(text).then(function () { done(true); },
                                               function () { done(legacyCopy(text)); });
    } else {
      done(legacyCopy(text));
    }
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

  function initCopy() {
    document.querySelectorAll(".copybtn[data-copy]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var src = document.getElementById(btn.dataset.copy);
        copyText(src.innerText, function (ok) {
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

  initFilter();
  initCopy();
})();
