/* הלכות בישול — flipbook controller
 * StPageFlip + RTL double-mirror + zoom/pan + thumbnails + keyboard.
 */
(function () {
  "use strict";

  const ZOOM_MIN = 1;
  const ZOOM_MAX = 3;
  const ZOOM_STEP = 0.4;

  const els = {
    loader: document.getElementById("loader"),
    flipbook: document.getElementById("flipbook"),
    flipScale: document.getElementById("flip-scale"),
    viewport: document.getElementById("viewport"),
    stage: document.getElementById("stage"),
    navPrev: document.getElementById("nav-prev"),
    navNext: document.getElementById("nav-next"),
    pageCurrent: document.getElementById("page-current"),
    pageTotal: document.getElementById("page-total"),
    btnFirst: document.getElementById("btn-first"),
    btnLast: document.getElementById("btn-last"),
    btnZoomIn: document.getElementById("btn-zoom-in"),
    btnZoomOut: document.getElementById("btn-zoom-out"),
    btnFullscreen: document.getElementById("btn-fullscreen"),
    btnThumbs: document.getElementById("btn-thumbs"),
    btnThumbsClose: document.getElementById("btn-thumbs-close"),
    thumbs: document.getElementById("thumbs"),
    thumbsGrid: document.getElementById("thumbs-grid"),
    scrim: document.getElementById("scrim"),
    bookTitle: document.getElementById("book-title"),
    bookSub: document.getElementById("book-sub"),
    btnDownload: document.getElementById("btn-download"),
  };

  const state = {
    manifest: null,
    pageFlip: null,
    zoom: 1,
    panX: 0,
    panY: 0,
  };

  // ---- Boot --------------------------------------------------------------
  async function boot() {
    try {
      const res = await fetch("assets/manifest.json");
      state.manifest = await res.json();
    } catch (e) {
      showError("טעינת רשימת העמודים נכשלה. ודא שהקובץ assets/manifest.json קיים.");
      return;
    }
    els.pageTotal.textContent = String(state.manifest.pageCount);
    applyMeta();
    buildThumbs();
    initFlip();
  }

  // ---- Title / subtitle / download from manifest -------------------------
  function applyMeta() {
    const m = state.manifest;
    if (m.title) {
      els.bookTitle.textContent = m.title;
      document.title = m.title + " — ספר דיגיטלי";
    }
    if (m.subtitle) els.bookSub.textContent = m.subtitle;
    else els.bookSub.remove();
    if (m.pdf) els.btnDownload.setAttribute("href", m.pdf);
    else els.btnDownload.remove();
  }

  // ---- StPageFlip --------------------------------------------------------
  function computeSize() {
    const aspect = state.manifest.aspect || 1.5; // height / width
    const availH = els.stage.clientHeight - 24;
    const availW = els.stage.clientWidth - 120; // leave room for side arrows
    // Single page (usePortrait): make it as large as fits within both dimensions.
    let h = availH;
    let w = h / aspect;
    if (w > availW) {
      w = availW;
      h = w * aspect;
    }
    return { w: Math.floor(w), h: Math.floor(h) };
  }

  function buildPages() {
    const frag = document.createDocumentFragment();
    state.manifest.pages.forEach((p) => {
      const page = document.createElement("div");
      page.className = "page";
      const img = document.createElement("img");
      img.src = p.page;
      img.loading = "lazy";
      img.decoding = "async";
      img.alt = "עמוד " + p.n;
      page.appendChild(img);
      frag.appendChild(page);
    });
    els.flipbook.appendChild(frag);
  }

  function initFlip() {
    const { w, h } = computeSize();
    const PageFlip = window.St.PageFlip;
    const pf = new PageFlip(els.flipbook, {
      width: w,
      height: h,
      size: "fixed",
      minWidth: 200,
      maxWidth: 2000,
      minHeight: 300,
      maxHeight: 3000,
      showCover: true,
      usePortrait: true,
      maxShadowOpacity: 0.5,
      flippingTime: 700,
      mobileScrollSupport: false,
      useMouseEvents: true,
      drawShadow: true,
    });
    state.pageFlip = pf;

    buildPages();
    pf.loadFromHTML(els.flipbook.querySelectorAll(".page"));

    pf.on("flip", (e) => updatePage(e.data));
    pf.on("changeState", () => {}); // reserved
    pf.on("init", () => updatePage(pf.getCurrentPageIndex()));

    hideLoader();
    bindControls();
    bindZoomPan();
    window.addEventListener("resize", debounce(onResize, 200));
    updatePage(0);
  }

  function onResize() {
    if (!state.pageFlip) return;
    const { w, h } = computeSize();
    state.pageFlip.update({ width: w, height: h });
  }

  // ---- Page tracking -----------------------------------------------------
  function updatePage(index) {
    const total = state.manifest.pageCount;
    const human = index + 1;
    els.pageCurrent.textContent = String(human);
    els.navPrev.disabled = index <= 0;
    els.navNext.disabled = index >= total - 1;
    highlightThumb(index);
  }

  // ---- Navigation (RTL: "prev" = lower page number) ----------------------
  function flipPrev() { state.pageFlip && state.pageFlip.flipPrev(); }
  function flipNext() { state.pageFlip && state.pageFlip.flipNext(); }
  function goTo(index) { state.pageFlip && state.pageFlip.flip(index); }

  function bindControls() {
    els.navPrev.addEventListener("click", flipPrev);
    els.navNext.addEventListener("click", flipNext);
    els.btnFirst.addEventListener("click", () => goTo(0));
    els.btnLast.addEventListener("click", () => goTo(state.manifest.pageCount - 1));
    els.btnZoomIn.addEventListener("click", () => setZoom(state.zoom + ZOOM_STEP));
    els.btnZoomOut.addEventListener("click", () => setZoom(state.zoom - ZOOM_STEP));
    els.btnFullscreen.addEventListener("click", toggleFullscreen);
    els.btnThumbs.addEventListener("click", toggleThumbs);
    els.btnThumbsClose.addEventListener("click", closeThumbs);
    els.scrim.addEventListener("click", closeThumbs);
    document.addEventListener("keydown", onKey);
  }

  function onKey(e) {
    if (e.target.tagName === "INPUT") return;
    switch (e.key) {
      // RTL: ArrowRight = previous page, ArrowLeft = next page
      case "ArrowRight": flipPrev(); break;
      case "ArrowLeft": flipNext(); break;
      case "Home": goTo(0); break;
      case "End": goTo(state.manifest.pageCount - 1); break;
      case "+": case "=": setZoom(state.zoom + ZOOM_STEP); break;
      case "-": case "_": setZoom(state.zoom - ZOOM_STEP); break;
      case "f": case "F": toggleFullscreen(); break;
      case "Escape": if (state.zoom > 1) setZoom(1); closeThumbs(); break;
    }
  }

  // ---- Zoom & pan --------------------------------------------------------
  function setZoom(z) {
    z = Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, Math.round(z * 100) / 100));
    state.zoom = z;
    if (z === 1) { state.panX = 0; state.panY = 0; }
    applyTransform();
    els.viewport.classList.toggle("is-zoomed", z > 1);
    els.btnZoomOut.disabled = z <= ZOOM_MIN;
    els.btnZoomIn.disabled = z >= ZOOM_MAX;
  }

  function applyTransform() {
    els.flipScale.style.transform =
      `translate(${state.panX}px, ${state.panY}px) scale(${state.zoom})`;
  }

  function bindZoomPan() {
    // Wheel zoom (ctrl/﹢) and pan via drag when zoomed. Capture phase so we can
    // stop StPageFlip from receiving the drag while panning.
    els.viewport.addEventListener("wheel", (e) => {
      if (!e.ctrlKey) return;
      e.preventDefault();
      setZoom(state.zoom + (e.deltaY < 0 ? ZOOM_STEP : -ZOOM_STEP));
    }, { passive: false });

    let panning = false, startX = 0, startY = 0, baseX = 0, baseY = 0;
    els.viewport.addEventListener("pointerdown", (e) => {
      if (state.zoom <= 1) return; // let StPageFlip handle flips
      panning = true;
      startX = e.clientX; startY = e.clientY;
      baseX = state.panX; baseY = state.panY;
      els.viewport.classList.add("is-panning");
      els.viewport.setPointerCapture(e.pointerId);
      e.stopPropagation();
    }, true);
    els.viewport.addEventListener("pointermove", (e) => {
      if (!panning) return;
      state.panX = baseX + (e.clientX - startX);
      state.panY = baseY + (e.clientY - startY);
      applyTransform();
      e.stopPropagation();
    }, true);
    const endPan = (e) => {
      if (!panning) return;
      panning = false;
      els.viewport.classList.remove("is-panning");
      e && e.stopPropagation();
    };
    els.viewport.addEventListener("pointerup", endPan, true);
    els.viewport.addEventListener("pointercancel", endPan, true);

    // Double-click toggles zoom
    els.viewport.addEventListener("dblclick", (e) => {
      e.preventDefault();
      setZoom(state.zoom > 1 ? 1 : 2);
    });
  }

  // ---- Fullscreen --------------------------------------------------------
  function toggleFullscreen() {
    const el = document.documentElement;
    if (!document.fullscreenElement) {
      (el.requestFullscreen || el.webkitRequestFullscreen).call(el);
    } else {
      (document.exitFullscreen || document.webkitExitFullscreen).call(document);
    }
  }
  document.addEventListener("fullscreenchange", () => {
    els.btnFullscreen.classList.toggle("is-active", !!document.fullscreenElement);
    setTimeout(onResize, 120);
  });

  // ---- Thumbnails --------------------------------------------------------
  function buildThumbs() {
    const frag = document.createDocumentFragment();
    state.manifest.pages.forEach((p) => {
      const div = document.createElement("div");
      div.className = "thumb";
      div.dataset.index = String(p.n - 1);
      div.innerHTML =
        `<img loading="lazy" src="${p.thumb}" alt="עמוד ${p.n}" />` +
        `<span class="thumb__n">${p.n}</span>`;
      div.addEventListener("click", () => {
        goTo(p.n - 1);
        closeThumbs();
      });
      frag.appendChild(div);
    });
    els.thumbsGrid.appendChild(frag);
  }

  function highlightThumb(index) {
    const prev = els.thumbsGrid.querySelector(".thumb.is-current");
    if (prev) prev.classList.remove("is-current");
    const cur = els.thumbsGrid.querySelector(`.thumb[data-index="${index}"]`);
    if (cur) {
      cur.classList.add("is-current");
      cur.scrollIntoView({ block: "nearest" });
    }
  }

  function toggleThumbs() {
    els.thumbs.classList.contains("is-open") ? closeThumbs() : openThumbs();
  }
  function openThumbs() {
    els.thumbs.classList.add("is-open");
    els.thumbs.setAttribute("aria-hidden", "false");
    els.btnThumbs.classList.add("is-active");
    els.scrim.hidden = false;
  }
  function closeThumbs() {
    els.thumbs.classList.remove("is-open");
    els.thumbs.setAttribute("aria-hidden", "true");
    els.btnThumbs.classList.remove("is-active");
    els.scrim.hidden = true;
  }

  // ---- Helpers -----------------------------------------------------------
  function hideLoader() { els.loader.classList.add("is-hidden"); }
  function showError(msg) {
    els.loader.innerHTML = `<p class="loader__text">⚠ ${msg}</p>`;
  }
  function debounce(fn, ms) {
    let t;
    return function () { clearTimeout(t); t = setTimeout(fn, ms); };
  }

  document.addEventListener("DOMContentLoaded", boot);
})();
