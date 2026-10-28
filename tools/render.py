"""Draws the preview pictures of an entry with the page of the kit: the real renderers of nexdeck, light and dark.

    from tools.render import draw
    draw(checked, light=Path("preview-light.png"), dark=Path("preview-dark.png"))

The page is served from the kit's folder on a port of this machine only; headless Chromium (Playwright) loads it, hands
it the ``WidgetData`` the kit worked out from the demo data and takes a picture of the card. Every request to anywhere
else is cancelled, so nothing a demo answer names (a picture address, say) is fetched while drawing.
"""

from __future__ import annotations

import functools
import http.server
import threading
from pathlib import Path
from typing import Any

from .common import ROOT, plain


class RenderError(Exception):
    """A picture that cannot be drawn: the submission is refused for it (KARTEN-13 EC-6)."""


def stand_in(checked: dict[str, Any]) -> dict[str, Any]:
    """What an own connection is drawn as: a list card of what it can read. A card brings its own demo data."""
    items = [{"title": label, "subtitle": path["path"], "value": ""} for label, path in zip(checked.get("read_labels") or [], checked.get("reads") or [], strict=False)]
    if not items:
        items = [{"title": "Connection test", "subtitle": "", "value": ""}]
    return {
        "status": "ok",
        "primary": None,
        "secondary": [],
        "items": items,
        "actions": [],
        "metrics": {},
        "link": None,
        "meta": {"custom": True, "empty": None},
        "error": None,
    }


def spec_of(checked: dict[str, Any], theme: str) -> dict[str, Any]:
    if checked["type"] == "integration":
        data, form = stand_in(checked), "list"
    else:
        data, form = checked["widget_data"], checked["form"]
    spec: dict[str, Any] = {"data": data, "form": form, "name": plain(checked["name"]), "theme": theme}
    if checked.get("size"):
        spec["size"] = checked["size"]
    return spec


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        pass


def draw(checked: dict[str, Any], light: Path, dark: Path, kit: Path | None = None) -> None:
    """Writes both pictures, or raises :class:`RenderError`."""
    page = (kit or ROOT / "kit") / "page"
    if not (page / "workshop-preview.html").is_file():
        raise RenderError("The drawing page of the kit is missing.")
    try:
        from playwright.sync_api import Error as PlaywrightError
        from playwright.sync_api import sync_playwright
    except ImportError as failure:
        raise RenderError("Playwright is not installed.") from failure
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(_Quiet, directory=str(page)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    origin = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                context = browser.new_context(device_scale_factor=2, viewport={"width": 900, "height": 700})
                context.route("**/*", lambda route: route.continue_() if route.request.url.startswith(origin) else route.abort())
                view = context.new_page()
                problems: list[str] = []
                view.on("pageerror", lambda error: problems.append(str(error)))
                view.goto(f"{origin}/workshop-preview.html", wait_until="load", timeout=30_000)
                view.wait_for_function("window.nexdeckPreview !== undefined", timeout=15_000)
                for theme, target in (("light", light), ("dark", dark)):
                    view.evaluate("spec => window.nexdeckPreview.show(spec)", spec_of(checked, theme))
                    target.parent.mkdir(parents=True, exist_ok=True)
                    try:
                        # A card whose data break the renderer takes the whole tree down: no stage, and an error of the page.
                        view.wait_for_selector("#stage", timeout=4_000)
                    except PlaywrightError:
                        raise RenderError("The card broke the drawing page" + (f": {problems[0][:200]}" if problems else ".")) from None
                    if problems:
                        raise RenderError("The card broke the drawing page: " + problems[0][:200])
                    view.locator("#stage").screenshot(path=str(target), timeout=15_000)
            finally:
                browser.close()
    except PlaywrightError as failure:
        raise RenderError("The picture could not be drawn: " + str(failure).splitlines()[0][:200]) from failure
    finally:
        server.shutdown()
    for target in (light, dark):
        if not target.is_file() or target.stat().st_size < 200:
            raise RenderError("The picture could not be drawn.")
