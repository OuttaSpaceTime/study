"""Smoke-test an explorable page in headless Chromium before it is published.

Loads the page from disk at a desktop and a phone width, screenshots both and
reports what the page wrote to the console. An uncaught exception or a failed
load is an error (exit 1): it is what a blank or frozen scene looks like from
the outside. Opened from disk the page has no `window.claude`, which is also
how it must cope when a capability is missing, so a page that only works with
its capabilities fails here, as it should.

Chromium logs every console message at INFO, whatever its level, so errors are
told apart by their text, not their level.
"""

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

VIEWPORTS = {"desktop": (1280, 900), "phone": (390, 844)}

CONSOLE_RE = re.compile(r':CONSOLE(?:\(\d+\)|:\d+)\] "(?P<msg>.*)", source: \S* \((?P<line>\d+)\)')
ERROR_RE = re.compile(r"^(Uncaught|Failed to load|Refused to)|Error\b")


def parse_console(stderr: str) -> tuple[list[str], list[str]]:
    """Chromium's stderr -> (errors, other messages), each as `msg (line N)`."""
    errors: list[str] = []
    other: list[str] = []
    for m in CONSOLE_RE.finditer(stderr):
        entry = f"{m['msg']} (line {m['line']})"
        (errors if ERROR_RE.search(m["msg"]) else other).append(entry)
    return errors, other


def find_chromium() -> str | None:
    for name in ("chromium", "chromium-browser", "google-chrome-stable", "google-chrome"):
        if path := shutil.which(name):
            return path
    return None


def run_viewport(browser: str, page: Path, shot: Path, size: tuple[int, int]) -> str:
    """Screenshot `page` at `size` into `shot`; return Chromium's stderr.

    A screenshot left by an earlier run is removed first, so `shot` existing
    afterwards means this run took it."""
    shot.unlink(missing_ok=True)
    with tempfile.TemporaryDirectory() as profile:
        proc = subprocess.run(
            [
                browser, "--headless=new", "--disable-gpu", "--no-first-run",
                f"--user-data-dir={profile}", f"--window-size={size[0]},{size[1]}",
                # Lets the page's load-time animations and timers run before the shot.
                "--virtual-time-budget=3000",
                "--enable-logging=stderr", "--v=0",
                f"--screenshot={shot}", page.resolve().as_uri(),
            ],
            capture_output=True, text=True, timeout=60,
        )
    return proc.stderr


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("page", type=Path, help="the explorable's HTML file")
    parser.add_argument("--out", type=Path, help="where the screenshots go (default: a temp dir)")
    args = parser.parse_args()

    if not args.page.is_file():
        sys.exit(f"explore-check: no such file: {args.page}")
    browser = find_chromium()
    if not browser:
        sys.exit("explore-check: no Chromium or Chrome on PATH")
    out = args.out or Path(tempfile.mkdtemp(prefix="explore-check-"))
    out.mkdir(parents=True, exist_ok=True)

    failed = False
    for name, size in VIEWPORTS.items():
        shot = out / f"{args.page.stem}-{name}.png"
        try:
            errors, other = parse_console(run_viewport(browser, args.page, shot, size))
        except subprocess.TimeoutExpired:
            errors, other = ["Chromium timed out after 60s"], []
        print(f"{name}: {shot}" if shot.exists() else f"{name}: no screenshot taken")
        failed |= bool(errors) or not shot.exists()
        for e in errors:
            print(f"  error: {e}")
        for o in other:
            print(f"  console: {o}")
    sys.exit(1 if failed else 0)
