"""Check a built game folder in real Chrome on the real GPU: load, light, frame rate, screenshots.

Usage:
    python check_game.py <game-folder> [--shots <folder>] [--views views.json] [--headless]

Views file (optional): [{"name": "living", "eye": [x, y, z], "target": [x, y, z], "hour": 10}, ...] in plan
metres. Without one, a corner view of every room is generated from the plan embedded in the page.
GPU Chrome is a real window parked off-screen (headless Chromium renders in software and would
under-report the frame rate tenfold). Fails on any console error or page exception.
"""

from __future__ import annotations

import argparse
import functools
import http.server
import json
import socket
import sys
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

from common import utf8_stdout

GPU_ARGS = ["--use-angle=d3d11", "--window-position=-2400,-2400", "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding", "--disable-background-timer-throttling", "--ignore-gpu-blocklist"]
READY_JS = "() => window.__game && window.__game.ready"
CLOSE_INTRO_JS = "() => { document.getElementById('intro').classList.add('closed'); document.getElementById('resume').hidden = true; }"
SETTLE_MS = 2500
FPS_SAMPLE_MS = 3000


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args) -> None:
        pass


def serve(folder: Path) -> tuple[http.server.ThreadingHTTPServer, int]:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), functools.partial(QuietHandler, directory=str(folder)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, port


def default_views(page) -> list[dict]:
    """A corner view per room at 10:00, from the plan embedded in the page."""
    return page.evaluate("""() => {
      const plan = JSON.parse(document.getElementById('game-data').textContent).variants[0].plan;
      return plan.rooms.filter(r => r.ceiling !== false || r.type === 'balcony').map(r => {
        const xs = r.polygon.map(p => p[0]), ys = r.polygon.map(p => p[1]);
        const [x0, x1, y0, y1] = [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)];
        return { name: r.id, eye: [x0 + 0.45, y0 + 0.45, 1.6], target: [x1 - 0.3, y1 - 0.3, 1.1], hour: 10 };
      });
    }""")


def measure_fps(page) -> int:
    return page.evaluate(f"""() => new Promise(res => {{
      let n = 0; const t0 = performance.now();
      const tick = () => {{ n++; if (performance.now() - t0 < {FPS_SAMPLE_MS}) requestAnimationFrame(tick); else res(Math.round(n * 1000 / (performance.now() - t0))); }};
      requestAnimationFrame(tick);
    }})""")


PLAY_JS = """async () => {
  const g = window.__game; const wait = (ms) => new Promise(r => setTimeout(r, ms)); const out = {};
  const door = g.interact.doors[0];
  if (door) { g.interact.toggleDoor(door.swing); await wait(1200);
    out.doorClosed = !door.open && g.player.extraSegments.length === 1; g.interact.toggleDoor(door.swing); }
  const room = g.plan.rooms.find(r => r.ceiling !== false);
  g.lighting.toggleRoom(room.id); out.lightOn = g.lighting.roomOn(room.id); g.lighting.toggleRoom(room.id);
  const before = g.mats.floor.map?.image?.src; g.interact.cycleFinish('floor'); out.floorSwapped = g.mats.floor.map?.image?.src !== before;
  const start = [...g.player.pos];
  dispatchEvent(new KeyboardEvent('keydown', { code: 'KeyW' })); await wait(1500); dispatchEvent(new KeyboardEvent('keyup', { code: 'KeyW' }));
  out.walked = Math.hypot(g.player.pos[0] - start[0], g.player.pos[1] - start[1]) > 0.3;
  out.room = document.getElementById('room-name').textContent;
  out.doors = g.interact.doors.length;
  return out;
}"""


PHONE = {"viewport": {"width": 390, "height": 844}, "device_scale_factor": 3, "is_mobile": True, "has_touch": True}


def run(url: str, shots: Path, views: list[dict] | None, headless: bool, play: bool = False, phone: bool = False) -> list[str]:
    errors: list[str] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True) if headless else p.chromium.launch(channel="chrome", headless=False, args=GPU_ARGS)
        page = browser.new_context(**PHONE).new_page() if phone else browser.new_page(viewport={"width": 1920, "height": 1080})
        page.on("console", lambda m: errors.append(f"console: {m.text}") if m.type == "error" and "favicon" not in (m.location or {}).get("url", "") else None)
        page.on("pageerror", lambda e: errors.append(f"exception: {e}"))
        page.goto(url)
        page.wait_for_function(READY_JS, timeout=180000, polling=500)
        page.evaluate(CLOSE_INTRO_JS)              # shots must show the scene, not the blurred start card
        page.wait_for_timeout(SETTLE_MS)
        gpu = page.evaluate("() => { const g = document.createElement('canvas').getContext('webgl2'); const d = g.getExtension('WEBGL_debug_renderer_info'); return d ? g.getParameter(d.UNMASKED_RENDERER_WEBGL) : 'n/a'; }")
        state = page.evaluate("() => ({ quality: window.__game.view.quality, tunedFps: window.__game.view.fps })")
        print(f"gpu      {gpu}\nquality  {state['quality']} (auto-tune measured {state['tunedFps']} fps)")
        if play:
            result = page.evaluate(PLAY_JS)
            print(f"play     {result}")
            failed = [k for k in ("doorClosed", "lightOn", "floorSwapped", "walked") if result.get(k) is False]
            errors += [f"play: {k} failed" for k in failed]
            page.screenshot(path=str(shots / "hud.png"))
        for v in views or default_views(page):
            page.evaluate(f"() => {{ window.__game.setTime({v.get('hour', 10)}); window.__game.setView({json.dumps(v['eye'])}, {json.dumps(v['target'])}); }}")
            page.wait_for_timeout(SETTLE_MS)
            page.screenshot(path=str(shots / f"{v['name']}.png"))
            print(f"view     {v['name']:12} {measure_fps(page)} fps")
        browser.close()
    return errors


def main() -> int:
    utf8_stdout()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("folder", type=Path)
    parser.add_argument("--shots", type=Path, default=None)
    parser.add_argument("--views", type=Path, default=None)
    parser.add_argument("--headless", action="store_true", help="software rendering; for CI, not for frame rates")
    parser.add_argument("--play", action="store_true", help="also exercise doors, lights, finishes and walking")
    parser.add_argument("--phone", action="store_true", help="iPhone emulation (touch, 390x844 @3x)")
    args = parser.parse_args()
    shots = args.shots or args.folder / "checks"
    shots.mkdir(parents=True, exist_ok=True)
    views = json.loads(args.views.read_text(encoding="utf-8")) if args.views else None
    server, port = serve(args.folder)
    try:
        errors = run(f"http://127.0.0.1:{port}/preview.html", shots, views, args.headless, args.play, args.phone)
    finally:
        server.shutdown()
    for e in errors:
        print(f"  ! {e}")
    print(f"screenshots in {shots}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
