/* Text layers - word-by-word karaoke captions, the section title, and the top progress bar.
 * captions: plan.captions = {words:[[text,start,end],...], maxWords, maxChars, y}
 * title (כותרת אפקט): an effect like any other - {type:"title", params:{text, counter}}
 * progress: plan.progress = {label}
 */
(function () {
  "use strict";
  const THFX = window.THFX;
  const MAX_GAP = 0.6;          // a pause longer than this starts a new caption line
  const DEFAULT_WORDS = 4;
  const DEFAULT_CHARS = 24;

  function chunkWords(words, maxWords, maxChars) {
    const chunks = [];
    let cur = [];
    words.forEach((w, i) => {
      const prev = words[i - 1];
      const chars = cur.reduce((n, x) => n + x[0].length + 1, 0) + w[0].length;
      const pause = prev && w[1] - prev[2] > MAX_GAP;
      if (cur.length && (cur.length >= maxWords || chars > maxChars || pause)) {
        chunks.push(cur);
        cur = [];
      }
      cur.push(w);
    });
    if (cur.length) chunks.push(cur);
    return chunks;
  }

  THFX.captions = function (tl, cfg, ctx) {
    const layer = document.getElementById("captions");
    if (!layer || !cfg.words || !cfg.words.length) return;
    layer.style.top = (cfg.y || 0.6) * 100 + "%";
    const chunks = chunkWords(cfg.words, cfg.maxWords || DEFAULT_WORDS, cfg.maxChars || DEFAULT_CHARS);
    chunks.forEach((chunk, ci) => {
      const line = ctx.el("div", "cap-line", layer);
      line.setAttribute("dir", "auto");
      const start = chunk[0][1];
      const end = ci + 1 < chunks.length ? Math.min(chunks[ci + 1][0][1], chunk[chunk.length - 1][2] + MAX_GAP) : chunk[chunk.length - 1][2] + 0.4;
      tl.set(line, { opacity: 1 }, start);
      tl.fromTo(line, { scale: 0.86 }, { scale: 1, duration: 0.14, ease: "back.out(2)" }, start);
      tl.set(line, { opacity: 0 }, end);
      chunk.forEach((w) => {
        const span = ctx.el("span", "cap-word", line, w[0]);
        tl.set(span, { attr: { class: "cap-word on" } }, w[1]);
        tl.set(span, { attr: { class: "cap-word" } }, Math.max(w[1] + 0.05, w[2]));
      });
    });
  };

  THFX.fx.title = function (tl, t0, dur, p, ctx) {
    const scene = THFX.scene(tl, ctx, ctx.top, t0, dur, "");
    const box = ctx.el("div", "fx-title", scene);
    box.style.top = (p.y || 0.74) * 100 + "%";
    if (p.counter) ctx.el("div", "fx-counter", box, p.counter);
    const text = ctx.el("div", "fx-title-text", box, p.text || "");
    const rule = ctx.el("i", "fx-title-rule", box);
    tl.fromTo(text, { y: 40, opacity: 0 }, { y: 0, opacity: 1, duration: 0.3, ease: "power3.out" }, t0);
    tl.fromTo(rule, { scaleX: 0 }, { scaleX: 1, duration: 0.35, ease: "power2.out" }, t0 + 0.1);
    tl.to(box, { opacity: 0, duration: 0.2 }, t0 + dur - 0.2);
  };

  THFX.progress = function (tl, cfg, ctx) {
    const bar = ctx.el("div", "fx-progress", ctx.top);
    ctx.el("div", "fx-progress-label", bar, cfg.label || "");
    const track = ctx.el("div", "fx-progress-track", bar);
    const fill = ctx.el("i", "fx-progress-fill", track);
    tl.fromTo(fill, { scaleX: 0 }, { scaleX: 1, duration: ctx.plan.footage.duration, ease: "none" }, 0);
  };
})();
