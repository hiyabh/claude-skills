# Effects catalog

Every effect is one entry in `fx_plan.json` → `effects[]`:

```json
{"type": "growth_chart", "start": 12.4, "dur": 2.6, "params": {"to": 10, "suffix": "x"}, "why": "..."}
```

`start`/`dur` are seconds on the footage clock. Effects must not overlap each other, except
`title`, which may sit on top of any effect. Each effect restores the picture when it ends.
**Matte** = needs a cut-out of the speaker (`matte_segments.py`). Without one, the effect is
skipped, or degrades as noted.

## Camera moves (cheap, safe, use the most)

| type | Hebrew | Looks like | Use when | dur | params |
|---|---|---|---|---|---|
| `punch_zoom` | זום חד | Fast push-in on the face with a blur flash, eases back | A key word, a punchline, or the hook in the first second | 0.9-1.4 | `zoom` (1.35) |
| `jump_zoom` | חיתוך זום | Hard cut to a tight shot, hard cut back | "but / wait / right?", or a rhetorical turn | 0.8-1.2 | `zoom` (1.6) |
| `dolly_zoom` | דולי זום | Slow continuous push-in | A story, a slow build, an emotional sentence | 2-4 | `zoom` (1.18) |
| `digital_zoom` | זום דיגיטלי | Camcorder viewfinder (corners, REC, timecode, zoom factor) with a handheld push | "look / notice / closer", or a reveal | 1.8-2.6 | `zoom` (2.6) |

## Overlays (the footage keeps running underneath)

| type | Hebrew | Looks like | Use when | dur | params |
|---|---|---|---|---|---|
| `checklist_pop` | צ'קליסט קופץ | Pills with green checks pop in beside the face | Enumerations: "three things", "first, second" | 2-3 | `items` [2-4 short strings], `side` |
| `headline_storm` | סערת כותרות | Tilted ribbons of text sweep across | "Everyone is talking about it", a hype moment | 1.8-2.6 | `lines` [3-6 short strings] |
| `orbit_ui` | מסלול | Editor icons (CC, ▶, ✂, Aa…) orbit the face | Tools, features, "all in one place" | 1.6-2.4 | `icons`, `count` |
| `portal_zoom` | פורטל זום | A ringed circle beside the speaker shows their face up close | Reaction, a personal confession, emphasis on emotion | 1.6-2.4 | `radius`, `zoom` |
| `liquid_glass` | זכוכית נוזלית | A glass lens drifts across the frame and magnifies | "secret / magic / behind the scenes" | 1.8-2.6 | `radius`, `zoom` |
| `frame_break` | שבירת פריים | White flash, rays radiate from the speaker, frame jolts | Shock, "crazy", a big reveal | 1.0-1.6 | - |
| `title` | כותרת | Big glowing title with a counter, lower third | Section headers, numbered tips | 1.2-3 | `text`, `counter` ("05 / 20"), `y` |

## Frames (the footage shrinks into a container)

| type | Hebrew | Looks like | Use when | dur | params |
|---|---|---|---|---|---|
| `chat_takeover` | השתלטות צ'אט | Video becomes an attachment in a chat card with a prompt bubble | AI, "I asked Claude/GPT", prompts | 2.2-3 | `prompt`, `assistant` ("Claude") |
| `phone_mockup` | מוקאפ טלפון | Video inside a phone on a dark background | Apps, social networks, "on your phone" | 2.2-3 | - |
| `broll_layers` | שכבות בי-רול | Video in an editor window with timeline tracks, B-roll cards fly in | Editing, process, "behind the project" | 2.5-3.5 | `images` [up to 2 paths in the project] |
| `frame_escape` | בריחה מהפריים | Video framed in a white box, the speaker's head breaks out over the top edge | "Think outside the box", breaking limits | 2-3 | `scale` (0.8). **Matte**: without it, a plain frame |

## Backgrounds (matte: the speaker is cut out)

| type | Hebrew | Looks like | Use when | dur | params |
|---|---|---|---|---|---|
| `green_screen` | מסך ירוק | Background turns chroma-green, then wipes to a dusk city (or your image) | "Imagine", travel, "from anywhere" | 2.4-3.2 | `image`, `swapAt` (0.42) |
| `studio` | סטודיו | Dark studio with softbox lights and an ON-AIR tag | Broadcast, news, interview, podcast | 2.2-3 | `tag` ("בשידור") |
| `paper_cutout` | גזירי נייר | White sticker outline, orange paper with star and dot, stop-motion wobble | Simple, fun, DIY, kids | 2-3 | - |
| `magazine_cover` | שער מגזין | Cream cover, masthead behind the head, cover lines, badge, barcode | Success story, "famous", an achievement | 2.2-3 | `masthead`, `lines`, `badge`, `issue` |
| `growth_chart` | גרף צמיחה | Grid background, a red line climbs and a counter runs 1x→10x | Numbers, growth, percentages | 2.2-3 | `from`, `to`, `suffix` ("x" or "%"), `label`. Without matte, it is drawn over dimmed footage |

All matte effects accept `subjectScale` (0.7-1) to shrink the cut-out from the bottom edge so
the background reads. By default they shrink, except on a tight shot (face taller than 20% of
the canvas): there, shrinking would expose the straight edges where the body is cropped.

## Closing

| type | Hebrew | Looks like | Use when | dur | params |
|---|---|---|---|---|---|
| `recap_checklist` | צ'קליסט סיכום | Dark panel, a two-column list ticks item by item | "In summary", the last 3-5 seconds | 3-5 | `title`, `items` |

## Global options (top level of fx_plan.json)

- `canvas`: `[1080, 1920]` (vertical, default), `[1920, 1080]`, or `[1080, 1080]`.
- `theme`: overrides any `--fx-*` token, for example `{"accent": "#2f80ed", "dark": "#0d1b2a"}`.
  The tokens are `accent ink paper dark navy good alert blue`.
- `captions`: `{}` turns on karaoke captions from `words.json`. Optional keys are `maxWords`
  (4), `maxChars` (24) and `y` (0.6, a share of the height). `false` turns them off.
- `progress`: `{"label": "..."}` adds a pill and a dashed progress track at the top.
- `seed`: changes the "random" layouts (skyline, chart wobble), which stay deterministic.

## Adding an effect

1. Write `THFX.fx.<type> = function (tl, t0, dur, p, ctx) {...}` in the matching
   `assets/runtime/fx-*.js` file. Keep each file under 500 lines; add a new `fx-*.js` if one
   is full and list it in `RUNTIME_SCRIPTS` in `build_project.py`.
2. Use `THFX.scene(tl, ctx, layer, t0, dur)` for a container that exists only in the window,
   `ctx.faceAt(t)` to aim at the face, `THFX.frameCam` to shrink the footage into a rectangle,
   and `THFX.useSubject` for a cut-out. Restore anything shared (`#cam`, subjects, lens) at
   `t0 + dur`.
3. Deterministic only: no `Math.random` (use `ctx.rand`), no clocks, no network.
4. Add a row here and a rule in `scripts/cues.py` (`matte=True` if it needs a cut-out; that
   one flag feeds `MATTE_TYPES` for matting and building).
5. Verify: add the effect to a test plan, build, `npx hyperframes check`, and snapshot its
   midpoint.
