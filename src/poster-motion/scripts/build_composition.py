"""shots.json + layers.json + beats.json -> index.html (HyperFrames).

    python build_composition.py <project> --draft       # write shots.json, stop
    python build_composition.py <project>               # build index.html
    python build_composition.py <project> --making-of   # force part (a) on

Without shots.json it drafts one first (every archetype picked by rule from
the layers) and builds from that, so a first pass always runs end to end -
but step 4 of the skill is Claude reading the sheet and rewriting the draft.

Also: cuts the music bed to the film's exact length, fetches the fonts, draws
the textures, and writes package.json pinning the CLI.
"""

import os
import sys
from string import Template

import compose_makingof as MO
import compose_posters as CP
from beat_grid import cut_bed
from pm_common import FPS, TEMPLATES, download, flag, project_arg, read_json, write_json
from pm_textures import write_all as write_textures

HF_CLI = "hyperframes@0.8.81"
GSAP_URL = "https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"
FONTSOURCE = "https://cdn.jsdelivr.net/npm/@fontsource/{pkg}@5.3.0/files/{file}"
FONTS = {  # local name -> (package, file)
    "heebo-hebrew-400.woff2": ("heebo", "heebo-hebrew-400-normal.woff2"),
    "heebo-latin-400.woff2": ("heebo", "heebo-latin-400-normal.woff2"),
    "heebo-hebrew-800.woff2": ("heebo", "heebo-hebrew-800-normal.woff2"),
    "heebo-latin-800.woff2": ("heebo", "heebo-latin-800-normal.woff2"),
    "karantina-hebrew-700.woff2": ("karantina", "karantina-hebrew-700-normal.woff2"),
    "karantina-latin-700.woff2": ("karantina", "karantina-latin-700-normal.woff2"),
    "jetbrains-mono-latin-400.woff2": ("jetbrains-mono", "jetbrains-mono-latin-400-normal.woff2"),
}
TOOLS_AI = "<b>HyperFrames</b> · GSAP · OpenCV · BiRefNet · LaMa · librosa"
TOOLS_LITE = "<b>HyperFrames</b> · GSAP · OpenCV · librosa"
FINALE_BEATS = 8
END_BEATS = 5


def draft(project, layers):
    posters = [CP.draft_poster(p, layers["canvas"]) for p in layers["posters"]]
    spec = {"title": "", "posters": posters,
            "finale": {"beats": FINALE_BEATS}, "end": {"beats": END_BEATS},
            "making_of": {"enabled": False, "prompt": MO.DEFAULT_PROMPT,
                          "scenes": MO.DEFAULT_SCENES}}
    write_json(os.path.join(project, "shots.json"), spec)
    return spec


def fetch_fonts(project):
    folder = os.path.join(project, "assets", "fonts")
    for local, (pkg, file) in FONTS.items():
        download(FONTSOURCE.format(pkg=pkg, file=file), os.path.join(folder, local))


class Grid:
    """Beat index -> seconds. Beat 0 is clamped to 0.0: the grid's phase would
    otherwise open the film on a sliver of nothing (references/traps.md)."""

    def __init__(self, beats):
        self.period = beats["period"]
        self.phase = beats["phase"]

    def t(self, b):
        return 0.0 if b == 0 else self.phase + b * self.period


def facts_for(layers, shots, beats, total):
    n_layers = sum(2 + (1 if p.get("object") else 0) + len(p["accents"])
                   for p in layers["posters"])
    return {"N": len(shots["posters"]), "L": n_layers, "BPM": round(60 / beats["period"]),
            "F": int(total * FPS), "FPS": FPS}


def _poster_part(layers, shots, grid, b0):
    by_id = {p["id"]: p for p in layers["posters"]}
    canvas = layers["canvas"]
    html, js, b = [], [], b0
    for k, spec in enumerate(shots["posters"]):
        p = by_id[spec["id"]]
        t, end = grid.t(b), grid.t(b + spec["beats"])
        html.append(CP.shot_html(k, p, spec, canvas, t, end - t))
        js.append(CP.shot_js(k, p, spec, canvas, t, end - t, grid.period))
        b += spec["beats"]
    return html, js, b


def _closing(layers, shots, beats, grid, b):
    canvas = layers["canvas"]
    posters = [next(p for p in layers["posters"] if p["id"] == s["id"]) for s in shots["posters"]]
    fb, eb = shots["finale"]["beats"], shots["end"]["beats"]
    t1, t2, t3 = grid.t(b), grid.t(b + fb), grid.t(b + fb + eb)
    fin_html, fin_js = CP.finale(posters, canvas, t1, t2 - t1, grid.period, posters[0]["paper"])
    ai = all(p["mode"] == "ai" for p in layers["posters"])
    end_html, end_js = CP.end_card(posters[0]["id"], canvas, t2, t3 - t2, shots.get("title", ""),
                                   TOOLS_AI if ai else TOOLS_LITE, beats.get("credit", ""))
    return [fin_html, end_html], [fin_js, end_js], t3


def _making_of(layers, shots, beats, grid, facts, first_js):
    mo = shots["making_of"]
    if not (mo.get("enabled") or flag("making-of")):
        return "", "", 0
    ids = [s["id"] for s in shots["posters"]]
    demo = next((p["id"] for p in layers["posters"] if p.get("object")), ids[0])
    ctx = {"canvas": layers["canvas"], "ids": ids, "demo": demo, "facts": facts,
           "prompt": mo.get("prompt", MO.DEFAULT_PROMPT), "envelope": beats["envelope"],
           "code": [ln.strip() for ln in first_js.splitlines() if ln.strip()]}
    scenes = mo.get("scenes") or MO.DEFAULT_SCENES
    html, js, _ = MO.build(ctx, scenes, 0.0, grid.period)
    return html, js, sum(s["beats"] for s in scenes)


def assemble(layers, shots, beats):
    grid = Grid(beats)
    total_beats = (sum(s["beats"] for s in shots["posters"]) + shots["finale"]["beats"]
                   + shots["end"]["beats"])
    mo_beats = 0
    if shots["making_of"].get("enabled") or flag("making-of"):
        mo_beats = sum(s["beats"] for s in (shots["making_of"].get("scenes") or MO.DEFAULT_SCENES))
    total = grid.t(total_beats + mo_beats)
    facts = facts_for(layers, shots, beats, total)
    # Part (a) prints the real JS of the first shot, so build (b) once to get it.
    _, probe_js, _ = _poster_part(layers, shots, grid, mo_beats)
    mo_html, mo_js, _ = _making_of(layers, shots, beats, grid, facts, probe_js[0])
    html, js, b = _poster_part(layers, shots, grid, mo_beats)
    c_html, c_js, end_t = _closing(layers, shots, beats, grid, b)
    return mo_html, mo_js, html + c_html, js + c_js, end_t


def _template(name):
    with open(os.path.join(TEMPLATES, name), encoding="utf-8") as fh:
        return fh.read()


def page(layers, shots, beats):
    w, h = layers["canvas"]
    mo_html, mo_js, html, js, total = assemble(layers, shots, beats)
    doc = Template(_template("page.html")).substitute(
        w=w, h=h, total=f"{total:.4f}", gsap=GSAP_URL,
        title=CP.esc(shots.get("title") or "poster-motion"),
        css=_template("style.css"), runtime=_template("runtime.js"),
        body="\n".join(x for x in [mo_html] + html if x),
        code="\n      ".join(x for x in [mo_js] + js if x))
    return total, doc


def main():
    project = project_arg()
    layers = read_json(os.path.join(project, "layers.json"))
    shots_path = os.path.join(project, "shots.json")
    if flag("draft") or not os.path.exists(shots_path):
        draft(project, layers)
        print(f"drafted {shots_path} - review it against layers_sheet.png")
        if flag("draft"):
            return
    shots = read_json(shots_path)
    beats_path = os.path.join(project, "assets", "music", "beats.json")
    if not os.path.exists(beats_path):
        sys.exit("missing beats.json - run beat_grid.py first")
    beats = read_json(beats_path)
    fetch_fonts(project)
    write_textures(os.path.join(project, "assets", "tex"), *layers["canvas"])
    total, doc = page(layers, shots, beats)
    cut_bed(beats["source"], beats["start"], total, os.path.join(project, "assets", "music", "bed.m4a"))
    with open(os.path.join(project, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(doc)
    write_json(os.path.join(project, "package.json"),
               {"name": "poster-motion-film", "private": True, "type": "module",
                "scripts": {"check": f"npx --yes {HF_CLI} check",
                            "preview": f"npx --yes {HF_CLI} preview",
                            "render": f"npx --yes {HF_CLI} render"}})
    print(f"index.html - {len(shots['posters'])} posters, {total:.2f}s, "
          f"{int(total * FPS)} frames at {60 / beats['period']:.1f} BPM")


if __name__ == "__main__":
    main()
