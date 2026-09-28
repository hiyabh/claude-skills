# Layering - how posters split, and how to fix a bad split

Code: `scripts/split_layers.py` (orchestration), `scripts/pm_masks.py` (all thresholds),
`scripts/pm_models.py` (BiRefNet + LaMa via onnxruntime).

## What each layer is

| Layer | Definition | File |
|---|---|---|
| paper | the poster with everything off-paper painted out at 1/8 scale (TELEA), blurred | (internal) |
| ink | darker than paper by `INK_DL` and colourless (`INK_CHROMA`), in shapes whose surrounding ring is mostly paper (`RING_OBJECT_MAX`). Alpha from darkness, colour un-mixed from the paper, so no paper halo | `ink.png` |
| accents | small shapes more colourful than the paper by `ACCENT_CHROMA`, surrounded by paper | `aK.png` crops |
| object | AI: BiRefNet matte. Lite: everything off paper that is not ink or accent, closed, holes filled, components ≥ 1.2% of the canvas. Ink is always cut out of it | `object.png` |
| plate | the poster with ink + object + accents + a band under the object (contact shadow) removed. AI: LaMa. Lite: paper estimate + grain matched to the real paper | `plate.png` |

All layers are full-canvas PNGs (accents are crops), so the composition stacks them with
`inset: 0` and no offsets.

## The ring test (why a cat is object and a title is ink)

A dark shape is ink only if the ring of pixels around it (1.2% of the frame height wide)
is mostly paper. Lettering floats on paper → ink. A black cat inside a bag, or "מהקופסה"
printed on a box, is ringed by bag/box → object. Only *strongly* off-paper pixels count
as object in the ring (`RING_STRONG` x `FG_DE`), so a soft shadow or a paper gradient next
to lettering does not steal it.

With BiRefNet present there is a second way in: a dark shape mostly **outside** the matte
(`AI_OVERLAP_MAX`) is ink even when it touches the object - lettering sitting right on a
fork's tines.

## Symptom → fix

| On the layer sheet | Cause | Fix |
|---|---|---|
| Part of the lettering is in the object column | touches the object; ring test says object | AI mode fixes most of these. Lite: raise `RING_OBJECT_MAX` (0.35 → 0.5) - but check the cat/box posters still keep their inner shapes in the object |
| Object column has a black cat missing / a hole | the dark part passed as ink | lower `RING_OBJECT_MAX`, or it will be filled anyway by `_fill_holes` if enclosed |
| Dozens of tiny ink groups, dots all over the page | paper grain or a watermark read as ink | raise `INK_MIN_AREA`; specks survive only beside real strokes |
| Grey handwriting missing from the ink | stroke not dark enough | lower `INK_DL` (18 → 14) |
| Coloured shapes still on the plate | accent too pale or its box too tight | lower `ACCENT_CHROMA`, raise `ACCENT_GROW_PX` / `ACCENT_MARGIN_PX` |
| Box edges / cardboard fragments listed as accents | saturated fragments touching the object | they should fail the ring test; if not, lower `ACCENT_MAX_AREA` |
| Brown ghost on the plate where the object stood | soft shadow outside the hole | raise `SHADOW_FRAC` / `PLATE_GROW_FRAC` in split_layers.py; in lite also `PAPER_SEED_DE` lower |
| Object includes a big floor area | lite mode: floor texture differs from paper | expected on photographic floors; use AI mode, or accept - the floor moves with the object |
| Object "no object" but there is one | object under 1.2% of the canvas, or pale | lower `OBJECT_MIN_AREA`, or lower `FG_DE` |

Change a constant, re-run `split_layers.py`, re-read the sheet. Never patch layer PNGs
by hand - the next run overwrites them.

## Lite vs AI

| | Lite (OpenCV) | AI (BiRefNet + LaMa) |
|---|---|---|
| Install | nothing | `python setup_models.py` once, ≈430 MB, CPU |
| Speed (7 posters, 720x900) | ~4 s | ~1-2 min |
| Object edges | follows the paper difference - includes floor shadows | a real matte - soft, hair-accurate |
| Plate under a big object | smooth paper + grain: fine on plain paper, visible on textured floors | LaMa reconstructs texture |
| Lettering touching the object | often lost to the object | kept (matte test) |

Posters on plain paper split well in lite mode. Use AI for photographic objects on
textured floors, or lettering that touches the object.

## Why not rembg

On some Windows machines `pip show rembg` lists it but `import rembg` fails: Windows
Application Control blocks the numba DLLs it imports. `pm_models.py` talks to onnxruntime directly
(the same `.onnx` files rembg would download), which needs only numpy.
