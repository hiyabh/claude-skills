---
description: "Turn a static mockup / design into a working, clickable prototype, then close the gap with an automated visual-diff loop against the original. TRIGGER when the user pastes or points to a mockup/screenshot/Figma and wants it built (\"here is a mockup, build a working prototype I can click through, matching the layout and states shown\"), or asks to implement a design and self-correct against it (\"implement this design, then take a screenshot of the result, compare it to the original, and fix any differences\"). Hebrew: 'תבנה פרוטוטייפ מהמוקאפ', 'תהפוך את התמונה לפרוטוטייפ קליקבילי', 'תממש את העיצוב ותשווה למקור', 'לולאת השוואה ויזואלית'. NOT for production feature work with a real backend (use your normal feature-development process), NOT for pure design generation in Figma (use the figma skills)."
---

# Prototype — Mockup → Clickable Prototype (+ Visual-Diff Loop)

## Purpose
Take a **static input** (pasted mockup image, screenshot, Figma frame, or a written
design spec) and produce a **working, clickable prototype** that reproduces the
layout and the visible states. Then optionally run a **visual-diff loop**: render
the result, screenshot it, compare against the original, and fix the differences —
repeating until it matches.

This is throwaway-quality-friendly, fast-feedback work. Do not over-engineer:
no real backend, no auth, no DB unless explicitly asked. Mock data is fine.

**Language:** talk to the user in Hebrew; code/comments in English (global rules).

---

## Mode A — Mockup → Clickable Prototype

### 1. Read the mockup
- If an image was pasted, **look at it carefully** and enumerate: screens/views,
  major regions (header, sidebar, content, footer), components, and every **state**
  shown (default, hover, active, empty, loading, error, filled, modal open, etc.).
- If it's a Figma URL, use the `figma:figma-generate-design` / `get_design_context`
  tools to pull layout + tokens instead of guessing.
- Restate to the user, in one short Hebrew paragraph, what you're about to build:
  the list of screens and the interactive states — so mismatches surface early.

### 2. Pick the lightest stack that fits
- Default to a **single self-contained HTML file** (inline CSS + a little JS) for
  simple 1–3 screen flows — fastest to iterate and screenshot.
- Use **React (Vite) + Tailwind** when the project already uses it, or when there's
  real component reuse / many states.
- Match an existing project's stack if building inside one (explore its structure
  and conventions first).
- RTL by default for any Hebrew UI (logical properties, `dir="rtl"`).

### 3. Build it
- Reproduce layout, spacing, colors, and typography as seen — pull exact hex/spacing
  from Figma tokens when available; eyeball from an image otherwise.
- Wire the **interactivity**: navigation between screens, toggles, tabs, modals,
  form states. Every state visible in the mockup must be reachable by clicking.
- Use placeholder/mock data; clearly fake anything that would need a backend.
- Code every state's UI (loading / empty / error / success) — never only happy path.

### 4. Show it
- Serve it (`python -m http.server`, `npm run dev`, or open the file) and tell the
  user exactly what to click to walk each flow. Offer the visual-diff loop (Mode B).

---

## Mode B — Visual-Diff Self-Correction Loop

Use when the user says "implement this, screenshot it, compare to the original, and
fix the differences", or after Mode A to tighten fidelity.

Requires the **Playwright MCP** (`mcp__playwright__*`) for rendering + screenshots.

### Loop
1. **Render** the prototype at the mockup's aspect ratio. `browser_navigate` to the
   local URL/file, `browser_resize` to match the mockup's dimensions.
2. **Capture** with `browser_take_screenshot`. For multi-state designs, drive the UI
   (`browser_click`, `browser_fill_form`) to reach each state and screenshot each.
3. **Compare** each screenshot side-by-side with the original mockup. Look at it and
   list concrete deltas: spacing, alignment, font size/weight, color, radius,
   missing/extra elements, wrong state. Be specific — "CTA is #2563EB but should be
   #1D4ED8, and sits 8px too low".
4. **Fix** only those deltas in the code. One coherent batch per iteration.
5. **Repeat** from step 1. Stop when the diff is visually negligible or after ~3–4
   iterations with diminishing returns — then report the residual gaps honestly
   instead of looping forever.

### Rules
- Compare against the **original**, not your last screenshot — avoid drift.
- Don't invent content the mockup doesn't show; flag ambiguity and pick a sensible
  default, noting it.
- Report each iteration briefly in Hebrew: what differed, what you changed.

---

## Output
- The prototype file(s) + how to run/click through them.
- If Mode B ran: before/after note per iteration and the final fidelity assessment.
- List anything faked (mock data, stubbed nav) and what real work productionizing
  would need.
