// Hub filter: live search + category chips, cards glide to new spots (FLIP),
// and a single gold pill slides between chips (clip-path over an "active" copy).
(function () {
  "use strict";

  var MOVE_MS = 280;
  var ENTER_MS = 220;
  var EASE_MOVE = "cubic-bezier(0.77, 0, 0.175, 1)";  // on-screen movement: ease-in-out
  var EASE_ENTER = "cubic-bezier(0.23, 1, 0.32, 1)";  // entering: ease-out
  var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  var search = document.querySelector(".search");
  var chips = document.querySelectorAll(".chips-row:not(.pill-copy) .chip[data-filter]");
  if (!search || !chips.length) return;
  var nav = document.querySelector(".chips");
  var copy = document.querySelector(".pill-copy");
  var copyChips = copy.querySelectorAll(".chip");
  var cards = Array.prototype.slice.call(document.querySelectorAll(".cardwrap"));
  var sections = document.querySelectorAll("section.cat");
  var empty = document.querySelector(".empty");
  var active = "all";

  function matches(card, q) {
    var okCat = active === "all" || card.dataset.cat === active;
    return okCat && (!q || card.dataset.search.indexOf(q) !== -1);
  }

  // First: remember where visible cards are. Last: apply. Invert + Play: WAAPI.
  function apply() {
    if (window.revealAll) window.revealAll();
    var q = search.value.trim().toLowerCase();
    var before = new Map();
    cards.forEach(function (c) {
      c.getAnimations().forEach(function (a) { a.cancel(); });
      if (!c.hidden) before.set(c, c.getBoundingClientRect());
    });
    var shown = 0;
    cards.forEach(function (c) { c.hidden = !matches(c, q); if (!c.hidden) shown++; });
    sections.forEach(function (s) { s.hidden = !s.querySelector(".cardwrap:not([hidden])"); });
    empty.hidden = shown !== 0;
    if (!reduce) play(before);
  }

  function play(before) {
    cards.forEach(function (c) {
      if (c.hidden) return;
      var first = before.get(c);
      var last = c.getBoundingClientRect();
      if (!first) {
        c.animate([{ opacity: 0, transform: "scale(0.96)" }, { opacity: 1, transform: "none" }],
                  { duration: ENTER_MS, easing: EASE_ENTER });
        return;
      }
      var dx = first.left - last.left, dy = first.top - last.top;
      if (Math.abs(dx) < 1 && Math.abs(dy) < 1) return;
      c.animate([{ transform: "translate(" + dx + "px," + dy + "px)" }, { transform: "none" }],
                { duration: MOVE_MS, easing: EASE_MOVE });
    });
  }

  // Clip the gold copy row down to the active chip's box.
  function movePill(index) {
    var chip = copyChips[index];
    var w = copy.offsetWidth, h = copy.offsetHeight;
    var top = chip.offsetTop, left = chip.offsetLeft;
    var right = w - left - chip.offsetWidth, bottom = h - top - chip.offsetHeight;
    copy.style.clipPath = "inset(" + top + "px " + right + "px " + bottom + "px " + left + "px round 999px)";
  }

  function setActive(filter) {
    active = filter;
    chips.forEach(function (c, i) {
      var on = c.dataset.filter === filter;
      c.setAttribute("aria-pressed", String(on));
      if (on) movePill(i);
    });
    apply();
  }

  function initPill() {
    copy.hidden = false;
    nav.classList.add("has-pill");
    movePill(0);
    copy.getBoundingClientRect();           // place instantly, animate only later moves
    copy.classList.add("ready");
    window.addEventListener("resize", function () {
      chips.forEach(function (c, i) { if (c.dataset.filter === active) movePill(i); });
    });
  }

  search.hidden = false;
  initPill();
  document.addEventListener("click", function (e) {
    var el = e.target.closest("[data-filter]");
    if (!el) return;
    e.preventDefault();
    if (el.dataset.filter === "all") search.value = "";
    setActive(el.dataset.filter);
  });
  // Searching always covers every category; a stale chip would hide matches.
  search.addEventListener("input", function () {
    if (active !== "all") setActive("all"); else apply();
  });
})();
