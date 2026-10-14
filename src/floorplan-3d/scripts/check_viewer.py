"""Stage 5: smoke-test a built viewer page in real browsers before anyone sees the link.

Usage:
    python check_viewer.py <out.preview.html> [--shots <folder>] [--timeout 120]

Serves the page's folder on a free localhost port, opens it in headless Chromium
as a desktop (1440x900) and as a phone (iPhone emulation: 390x844, touch, DPR 3),
waits for the reveal to settle, then walks every view, work mode, walk mode and
the measure tool. Saves a screenshot per step and fails on any console error or
page exception (the favicon 404 from the local server is ignored).
Needs Python Playwright (`pip install playwright && playwright install chromium`).
"""

from __future__ import annotations

import argparse
import functools
import http.server
import socket
import sys
import threading
from pathlib import Path
from urllib.parse import quote

from playwright.sync_api import sync_playwright

from common import utf8_stdout

SETTLE_JS = "() => !!window.__viewer && !window.__viewer.reveal.running && !window.__viewer.rig.flying"
STEPS = [
    ("overview", "a => a.goView('overview')"),
    ("plan", "a => a.goView('plan')"),
    ("work-mode", "a => { a.ui.setMode('work'); a.goView('overview'); }"),
    ("first-elevation", "a => { const v = a.views.find(v => v.id.startsWith('run-') || v.id.startsWith('isl-')); a.goView(v ? v.id : 'eye'); }"),
    ("eye-level", "a => a.goView('eye')"),
    ("walk", "a => a.enterWalk()"),
    ("walk-exit", "a => a.exitWalk()"),
    ("measure-on", "a => { a.ui.state.measure = true; a.setLayer('measure', true); }"),
    ("present-mode", "a => { a.setLayer('measure', false); a.ui.setMode('present'); }"),
    ("sheet-rooms", "a => a.ui.openSheet('rooms')"),
]
DEVICES = {
    "desktop": {"viewport": {"width": 1440, "height": 900}, "device_scale_factor": 1},
    "phone": {"viewport": {"width": 390, "height": 844}, "device_scale_factor": 3, "is_mobile": True, "has_touch": True},
}


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args) -> None:  # keep the test output to the results
        pass


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _serve(folder: Path) -> tuple[http.server.ThreadingHTTPServer, int]:
    port = _free_port()
    handler = functools.partial(QuietHandler, directory=str(folder))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, port


def _settle(page, timeout_ms: int) -> None:
    page.wait_for_function(SETTLE_JS, timeout=timeout_ms, polling=500)


def run_device(browser, name: str, url: str, shots: Path, timeout_ms: int) -> list[str]:
    context = browser.new_context(**DEVICES[name])
    page = context.new_page()
    errors: list[str] = []
    page.on("console", lambda m: errors.append(f"console: {m.text}") if m.type == "error" and "favicon" not in m.text else None)
    page.on("pageerror", lambda e: errors.append(f"exception: {e}"))
    page.goto(url)
    _settle(page, timeout_ms)
    page.screenshot(path=str(shots / f"{name}-00-intro.png"), timeout=60000)
    for i, (label, action) in enumerate(STEPS, start=1):
        print(f"  {name} {i}/{len(STEPS)} {label}", flush=True)
        page.evaluate(f"({action})(window.__viewer)")
        if label != "walk":
            _settle(page, timeout_ms)
        page.wait_for_timeout(600)
        page.screenshot(path=str(shots / f"{name}-{i:02d}-{label}.png"), timeout=60000)
    state = page.evaluate("() => ({ views: window.__viewer.views.length, labels: window.__viewer.labels.entries.length })")
    print(f"{name:8} ok - {state['views']} views, {state['labels']} labels, {len(errors)} console errors")
    context.close()
    return errors


def main() -> int:
    utf8_stdout()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("page", type=Path)
    parser.add_argument("--shots", type=Path, default=None)
    parser.add_argument("--timeout", type=int, default=120, help="seconds to wait for each step to settle")
    args = parser.parse_args()
    shots = args.shots or args.page.parent / "checks"
    shots.mkdir(parents=True, exist_ok=True)
    server, port = _serve(args.page.parent)
    url = f"http://127.0.0.1:{port}/{quote(args.page.name)}"
    errors: list[str] = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(args=["--enable-unsafe-swiftshader"])
            for device in DEVICES:
                errors += run_device(browser, device, url, shots, args.timeout * 1000)
            browser.close()
    finally:
        server.shutdown()
    for e in errors:
        print(f"  ! {e}")
    print(f"screenshots in {shots}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
