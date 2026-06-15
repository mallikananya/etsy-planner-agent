from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright


def render_html_to_png(html_path: Path, png_path: Path, width: int, height: int) -> bool:
    """Screenshot html_path to png_path at exact pixel dimensions.
    Returns True on success, False on failure.
    Uses playwright sync API with headless Chromium.
    Sets viewport to width x height, device_scale_factor=2 for retina sharpness,
    then saves a full-page screenshot cropped to exactly width x height.
    Never raises — catches all exceptions and returns False.
    """
    try:
        png_path.parent.mkdir(parents=True, exist_ok=True)
        with sync_playwright() as playwright:
            if not _ensure_chromium_available(playwright.chromium.executable_path):
                return False
            browser = playwright.chromium.launch(headless=True)
            try:
                page = browser.new_page(
                    viewport={"width": width, "height": height},
                    device_scale_factor=2,
                )
                page.goto(html_path.resolve().as_uri(), wait_until="networkidle")
                page.screenshot(
                    path=str(png_path),
                    full_page=True,
                    clip={"x": 0, "y": 0, "width": width, "height": height},
                    scale="css",
                )
            finally:
                browser.close()
        return png_path.exists()
    except Exception:
        return False


def _ensure_chromium_available(playwright_browser_path: str) -> bool:
    if shutil.which("chromium") is not None:
        return True

    browser_path = Path(playwright_browser_path)
    if browser_path.exists():
        return True

    result = subprocess.run(
        [sys.executable, "-m", "playwright", "install", "chromium"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0 and (browser_path.exists() or shutil.which("chromium") is not None)
