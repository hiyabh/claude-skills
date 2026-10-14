"""Game-mode assets: download from Poly Haven once, export in formats an Artifact serves.

Usage:
    python assets.py sync                     # download everything in assets/game/manifest.json (cached)
    python assets.py export <out> --tier high # write served files + <out>/assets.json for the page

Poly Haven is CC0 (polyhaven.com/license); credits.json still lists every source.
An Artifact serves .js/.jpg/.webp but not .glb/.hdr/.bin, and its fetch() is unreliable
(the spike, 09.10.2026: a fetch-based load failed, an import()-based one passed). So nothing
here needs fetch():
  models   -> <key>.gltf.js: `export default <glTF JSON>`, buffer AND webp textures embedded as
              data URIs (the engine answers data: URLs in memory, see game/loader.js)
  HDRIs    -> <key>.hdr.js: `export default "<base64 Radiance>"`
  textures -> resized JPG per map, loaded through <img> (TextureLoader)
"""

from __future__ import annotations

import argparse
import base64
import json
import shutil
import subprocess
import time
import urllib.request
from pathlib import Path

from PIL import Image

from common import utf8_stdout, write_json

SKILL = Path(__file__).resolve().parent.parent
MANIFEST = SKILL / "assets" / "game" / "manifest.json"
CACHE = Path.home() / ".cache" / "floorplan-3d" / "polyhaven"
API = "https://api.polyhaven.com"
UA = {"User-Agent": "floorplan-3d (claude skill)"}
TEXTURE_MAPS = {"diff": "Diffuse", "nor_gl": "nor_gl", "rough": "Rough"}
SOURCE_RES = "2k"
TIMEOUT_S = 60
RETRIES = 4
GLTF_TRANSFORM = "@gltf-transform/cli@4"
Image.MAX_IMAGE_PIXELS = None


def manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def _get_json(url: str) -> dict:
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=TIMEOUT_S) as r:
        return json.loads(r.read())


def _download(url: str, dest: Path) -> Path:
    """Cached download; retries with backoff because the CDN occasionally stalls mid-file."""
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    for attempt in range(RETRIES):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=TIMEOUT_S) as r, open(tmp, "wb") as f:
                shutil.copyfileobj(r, f)
            tmp.replace(dest)
            return dest
        except (TimeoutError, OSError) as error:
            if attempt == RETRIES - 1:
                raise SystemExit(f"download failed after {RETRIES} tries: {url} ({error})")
            time.sleep(2 ** attempt)
    return dest


# ---------------------------------------------------------------- sync

def sync_texture(slug: str) -> dict[str, Path]:
    files = _get_json(f"{API}/files/{slug}")
    out = {}
    for short, key in TEXTURE_MAPS.items():
        entry = files[key][SOURCE_RES]["jpg"]
        out[short] = _download(entry["url"], CACHE / "textures" / slug / f"{short}.jpg")
    return out


def sync_hdri(slug: str, res: str = "1k") -> Path:
    entry = _get_json(f"{API}/files/{slug}")["hdri"][res]["hdr"]
    return _download(entry["url"], CACHE / "hdris" / f"{slug}_{res}.hdr")


def sync_model(slug: str) -> Path:
    """Download the 1k glTF and every file it includes; returns the .gltf path."""
    files = _get_json(f"{API}/files/{slug}")
    if "gltf" not in files:
        raise SystemExit(f"{slug} has no glTF download on Poly Haven (only {', '.join(k for k in files if k in ('fbx', 'blend', 'usd'))}) - pick another model in manifest.json")
    entry = files["gltf"]["1k"]["gltf"]
    root = CACHE / "models" / slug
    for rel, inc in entry.get("include", {}).items():
        _download(inc["url"], root / rel)
    return _download(entry["url"], root / f"{slug}.gltf")


def info(slug: str) -> dict:
    data = _get_json(f"{API}/info/{slug}")
    return {"name": data.get("name", slug), "authors": sorted(data.get("authors", {})), "url": f"https://polyhaven.com/a/{slug}"}


def sync_all() -> None:
    m = manifest()
    for key, spec in m["textures"].items():
        sync_texture(spec["id"]); print(f"texture  {key:18} {spec['id']}")
    for key, slug in m["hdris"].items():
        sync_hdri(slug); print(f"hdri     {key:18} {slug}")
    for key, spec in m["models"].items():
        sync_model(spec["id"]); print(f"model    {key:18} {spec['id']}")


# ---------------------------------------------------------------- export

def _resize_jpg(src: Path, dest: Path, px: int, quality: int) -> str:
    im = Image.open(src)
    im = im.convert("RGB") if im.mode not in ("RGB", "L") else im
    if max(im.size) > px:
        im = im.resize((px, px), Image.LANCZOS)
    dest.parent.mkdir(parents=True, exist_ok=True)
    im.save(dest, "JPEG", quality=quality, optimize=True)
    return dest.name


def export_texture(key: str, spec: dict, tier: dict, out: Path) -> dict:
    maps = sync_texture(spec["id"])
    entry = {"repeat_m": spec.get("repeat_m", 1.0), "tint": spec.get("tint", False)}
    wanted = spec.get("maps", list(TEXTURE_MAPS))
    for short, src in maps.items():
        if short not in wanted:
            continue
        px = tier["texture_px"] if short == "diff" else tier["detail_px"]
        name = _resize_jpg(src, out / "t" / f"{key}_{short}.jpg", px, 86 if short == "diff" else 90)
        entry[short] = f"assets/t/{name}"
    return entry


def _js_module(payload: str, dest: Path) -> None:
    dest.write_text("export default " + payload + ";\n", encoding="utf-8")


def export_hdri(key: str, slug: str, tier: dict, out: Path) -> dict:
    raw = sync_hdri(slug, tier["hdri"]).read_bytes()
    (out / "h").mkdir(parents=True, exist_ok=True)
    _js_module(json.dumps(base64.b64encode(raw).decode("ascii")), out / "h" / f"{key}.hdr.js")
    return {"js": f"assets/h/{key}.hdr.js"}


def _gltf_transform(*args: str) -> None:
    npx = shutil.which("npx") or shutil.which("npx.cmd")
    done = subprocess.run([npx, "--yes", GLTF_TRANSFORM, *args], capture_output=True, text=True, encoding="utf-8")
    if done.returncode != 0:
        raise SystemExit(f"gltf-transform {args[0]} failed:\n{done.stderr.strip()[-600:]}")


def _data_uri(path: Path, mime: str) -> str:
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def export_model(key: str, spec: dict, tier: dict, out: Path, work: Path) -> dict:
    """Resize + webp the textures, then write one JS module holding the whole glTF (buffer and images inline)."""
    src = sync_model(spec["id"])
    stage = work / key
    shutil.rmtree(stage, ignore_errors=True)
    stage.mkdir(parents=True)
    px = str(tier["model_px"])
    _gltf_transform("resize", str(src), str(stage / "r.glb"), "--width", px, "--height", px)
    _gltf_transform("webp", str(stage / "r.glb"), str(stage / "w.glb"))
    _gltf_transform("copy", str(stage / "w.glb"), str(stage / "m.gltf"))
    g = json.loads((stage / "m.gltf").read_text(encoding="utf-8"))
    for b in g["buffers"]:
        b["uri"] = _data_uri(stage / b["uri"], "application/octet-stream")
    for im in g.get("images", []):
        im["uri"] = _data_uri(stage / im["uri"], "image/webp")
    (out / "m").mkdir(parents=True, exist_ok=True)
    _js_module(json.dumps(g, separators=(",", ":")), out / "m" / f"{key}.gltf.js")
    return {"js": f"assets/m/{key}.gltf.js"}


def export(out: Path, tier_name: str, keys: dict[str, list[str]] | None = None) -> dict:
    """Export the manifest (or the subset in keys) into out/; returns the index the page reads."""
    m = manifest()
    tier = m["tiers"][tier_name]
    want = keys or {k: list(m[k]) for k in ("textures", "hdris", "models")}
    out.mkdir(parents=True, exist_ok=True)
    work = CACHE.parent / "stage"
    index = {"tier": tier_name, "textures": {}, "hdris": {}, "models": {}}
    credits = []
    for key in want.get("textures", []):
        index["textures"][key] = export_texture(key, m["textures"][key], tier, out)
        credits.append({"key": key, **info(m["textures"][key]["id"])})
    for key in want.get("hdris", []):
        index["hdris"][key] = export_hdri(key, m["hdris"][key], tier, out)
        credits.append({"key": key, **info(m["hdris"][key])})
    for key in want.get("models", []):
        index["models"][key] = export_model(key, m["models"][key], tier, out, work)
        credits.append({"key": key, **info(m["models"][key]["id"])})
    write_json(out / "credits.json", {"license": "CC0 1.0 - https://polyhaven.com/license", "assets": credits})
    return index


def main() -> int:
    utf8_stdout()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("sync")
    ex = sub.add_parser("export")
    ex.add_argument("out", type=Path)
    ex.add_argument("--tier", choices=("high", "lite"), default="high")
    args = parser.parse_args()
    if args.cmd == "sync":
        sync_all()
        return 0
    index = export(args.out, args.tier)
    write_json(args.out / "assets.json", index)
    size = sum(p.stat().st_size for p in args.out.rglob("*") if p.is_file())
    print(f"exported {sum(len(v) for k, v in index.items() if k != 'tier')} assets to {args.out} ({size / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
