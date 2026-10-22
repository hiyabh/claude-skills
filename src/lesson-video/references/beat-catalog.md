# Beat catalog

Every beat starts at `at` (a phrase as transcribed) and lasts until the next beat. The first beat of a
chapter is always `T(...)` and has no `at`. Text fields accept `*word*` = highlight bar swept in by K.mark.
`reveal=[phrase, ...]` anchors inner elements in order; missing entries follow the previous one by ~0.5-1s.
Optional on any beat: `tr="zoom|push|slide|iris|flash|blinds|wipe|fade"` to override the rotating transition.

## Text
| Helper | Shows | Motion |
|---|---|---|
| `T(title, eyebrow, sub)` | chapter card | gold wipe, chapter number counts up, words rise, rule draws, chapter map dots pop |
| `Q(at, text, sub, reveal=[sub_at])` | big question | spring pop + shake, giant "?" swings behind |
| `SAY(at, text, sub)` | spoken punchline | quote mark drops, words rise one by one (or highlight sweep) |
| `KIN(at, words)` | 2-5 key words | each word slams in (scale 2.6→1, tilt) at the moment it is said - reveal defaults to the words |
| `KW(at, big, chips, reveal)` | heading + chips | chips spring in on their words |
| `L(at, title, items, reveal)` | list | dot pops, line slides in, per item |
| `V(at, pasuk, cite)` / `SRC(...)` | quote card | card rises, words reveal / highlight sweeps |
| `N(at, n, label, sub)` | counter | ring draws while the number counts up |
| `END(at, title, eyebrow, sub)` | closing card | like T, gold title |

## Picture
| Helper | Shows | Motion |
|---|---|---|
| `S(at, img, cap, sub, shots=[...])` | full-frame illustration | Ken Burns + automatic camera moves every 6s + light motes; caption slides in word by word |
| `IT(at, img, title, lines, reveal)` | picture left half + text | clip-path reveal, Ken Burns, lines rise |
| `SPLIT(at, img, q, cite)` | picture + quote | picture wipes in from the left, quote card builds |
| `C(at, rh, rl, lh, ll, mid, reveal=[left_at])` | two columns | right column, then "מול" pops, left column; right dims then returns |

`shots`: `[{"at": "phrase", "focus": [x%, y%], "zoom": 1.5}]` - zooms toward that point of the picture without
exposing an edge. Explicit shots and automatic moves are merged.

## Diagrams (drawn live; RTL - the sequence starts on the right)
| Helper | Use for | Motion |
|---|---|---|
| `FLOW(at, nodes, title, reveal)` | process / chain (2-5 nodes) | each arrow draws, then its node pops |
| `CYCLE(at, nodes, title, center, reveal)` | something that returns (3-6) | nodes on a circle, arcs draw, closing arc + centre label last |
| `TL(at, items, dates, title, reveal)` | dates / stages (≤6) | axis draws right→left, dots pop, labels alternate above/below |
| `BARS(at, [{"label", "value", "suffix"}], title, reveal)` | quantities (≤6) | bars grow, values count up |
| `SCALE(at, r, l, tilt, title, reveal=[r, l, tilt])` | weighing | pans pop, beam tilts with elastic swing |
| `VENN(at, r, l, mid, title, reveal=[r, l, mid])` | overlap | circles slide in from both sides, middle label pops |
| `STACK(at, items, title, reveal)` | building up (first = base) | blocks drop and bounce into place |
| `LADDER(at, steps, title, reveal)` | levels (≤5) | steps grow right→left, a marker climbs |

Keep node/label text short (1-3 words) - boxes are ~300px wide at 44px type.

## Always on (no spec needed)
- Captions: line slides in, the spoken word pops gold, chapter `keywords` stay gold.
- Background: breathing glow in the chapter colour, drifting motes, grain, giant ghost word per chapter.
- Progress chrome: chapter segments + chapter name at the top.

## Device (optional)
| Helper | Use for | Motion |
|---|---|---|
| `PHONE(at, steps, title, sub, reveal)` | a conversation in a mobile app; `steps=[you("..."), say("..."), ask("...", "detail"), done("...")]`, one `reveal` phrase per step | phone tilts in, each message rises + pops, Allow button pops after an `ask` |
| `LINK(at, title, url, sub, icon, reveal=[sub_at])` | pointing to a link; say where it is ("מתחת לסרטון"), never read the address | card springs in, QR code spins in; needs `pip install qrcode` |

Not ported from the course engine because the lesson pipeline has no such beat: the laptop mockup and 3D tilt of the
app-window/screenshot beats, and the confetti burst on a finished app step.
