---
name: print-ready-logo
description: "Turn any logo or image into a print-ready pack - a clean TRANSPARENT-background PNG plus a high-DPI PDF that preserves the transparency - and boost it to high pixel quality with AI super-resolution (Real-ESRGAN). Handles three cases: background already transparent (keeps + trims it), solid/white background (removes it), or complex photo background (optional rembg AI). TRIGGER on Hebrew: 'רקע שקוף', 'תעשה רקע שקוף', 'תהפוך את הרקע לשקוף', 'תכין לוגו להדפסה', 'הכן לבית דפוס', 'PDF לבית דפוס', 'לוגו PNG שקוף', 'תגדיל את הלוגו באיכות', 'upscale ללוגו'. English: 'transparent background PNG', 'make the background transparent', 'prepare logo for print', 'print-ready PDF', 'upscale this logo', 'pack logo into a PDF'. USE for delivering a logo/graphic to a print shop as a transparent PNG + PDF at high resolution. NOT for vectorizing (stays raster), NOT for photo editing, NOT for generating new art."
---

# Print-Ready Logo Pack

`<SKILL_DIR>` = the folder that contains this SKILL.md (normally
`~/.claude/skills/print-ready-logo`). Resolve it once to an absolute path
before running commands - PowerShell/cmd do not expand `~` inside quotes.

Produce two deliverables a print shop can use from a single source image:

1. **`<name> - רקע שקוף.png`** — clean transparent-background PNG, AI-upscaled, with DPI metadata.
2. **`<name> - להדפסה.pdf`** — a PDF page sized to the artwork at the chosen DPI, with **real transparency preserved** (soft-mask embedded — not flattened onto white).

The pipeline: ensure transparent background → trim transparent margins → **Real-ESRGAN AI upscale** (sharp edges & text, not a blurry resize) → export PNG + transparency-preserving PDF.

## Requirements

- Python with `pillow`, `numpy`, `reportlab`, `opencv-python`
  - check: `python -c "import PIL, numpy, reportlab, cv2"` — if it fails: `pip install pillow numpy reportlab opencv-python`
- **Windows only**, and needs a **Vulkan-capable GPU** (most modern integrated/discrete GPUs qualify). The Real-ESRGAN (ncnn-vulkan) binary is NOT shipped in this package — the script downloads it automatically into `<SKILL_DIR>/bin/` on first run (~45 MB, one-time, requires internet access). `--scale 1` skips upscaling entirely and avoids this dependency if a GPU/Windows isn't available.

## How to Use

Run from the folder with the image (outputs land next to it by default):

```bash
python "<SKILL_DIR>/build_print_pack.py" "INPUT.png" [options]
```

The script auto-detects the background situation and picks a strategy. Then **render the
output PNG and look at it** to confirm the text/edges are sharp and transparency is clean
before reporting done.

### Common options

| Option | Default | Purpose |
|---|---|---|
| `--scale {1,2,3,4}` | `4` | Upscale factor. `1` = pack only, no upscale. |
| `--dpi N` | `300` | DPI metadata + PDF physical size. Higher DPI → smaller sharp print size. |
| `--model NAME` | `realesrgan-x4plus` | `realesrgan-x4plus` keeps gradients/3D shading (medallion-style logos). Use `realesrgan-x4plus-anime` for flat line-art / pure-text logos (crisper edges, flatter fills). |
| `--name NAME` | input stem | Base name for the two output files (use a Hebrew descriptive name). |
| `--output-dir DIR` | input's folder | Where to write the pack. |
| `--remove-bg` | off | Force solid-background removal even if alpha already exists. |
| `--no-remove-bg` | off | Never touch the background (only upscale + pack). |
| `--bg-tolerance N` | `25` | Color tolerance for solid-bg flood fill (raise if bg leftovers remain). |
| `--rembg` | off | Use the rembg AI model for complex / non-solid backgrounds (installs on first use, ~170 MB). |

### Background strategy (auto)

- **Already transparent** → kept and trimmed (don't re-remove). Common for `*-removebg-*` files.
- **Solid / white background** (no alpha) → removed via 4-corner flood fill (no heavy deps).
- **Complex photo background** → pass `--rembg`.

## Print-size guidance (report this to the user)

At the chosen DPI, sharp print width = `output_px / dpi` inches. The script prints this.
A 4× upscale of a ~425 px logo → ~1700 px → **sharp up to ~14 cm @ 300 DPI**. For larger
(signs/banners/roll-ups) run again at higher scale, or recommend a true **vector** source
(AI/EPS/SVG) — this skill stays raster and won't invent detail beyond what AI can restore.

## Notes

- Output filenames follow the user's Hebrew descriptive-naming rule. Always pass `--name`
  with a Hebrew name matching the logo (e.g. `--name "לוגו אורות יצחק"`).
- The PDF embeds a single RGB image with a soft-mask alpha layer; verify with PyMuPDF
  (`get_pixmap(alpha=True).alpha == 1`) if a print shop reports a white box.
- Real-ESRGAN preserves the alpha channel, so transparency survives the upscale.
