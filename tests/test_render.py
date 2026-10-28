"""The drawing with the real page of the kit and a real browser (KARTEN-13 AC-3, EC-6).

Needs Playwright and its Chromium, so it runs only when ``WORKSHOP_RENDER=1`` is set (the submit action draws for real
on every run anyway, and the other tests put a stand-in in the place of the drawing).
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from tests.conftest import sample
from tools import kitcheck, render

needs_browser = pytest.mark.skipif(os.environ.get("WORKSHOP_RENDER") != "1", reason="set WORKSHOP_RENDER=1 to draw with a real browser")


def _png(path: Path) -> bytes:
    data = path.read_bytes()
    assert data.startswith(b"\x89PNG\r\n\x1a\n")
    return data


@needs_browser
def test_karten13_ac3_a_card_is_drawn_light_and_dark(tmp_path: Path) -> None:
    checked = kitcheck.check(sample("good", "list-card.yaml"), "card")
    assert checked["ok"], checked["problems"]
    render.draw(checked, tmp_path / "light.png", tmp_path / "dark.png")
    light, dark = _png(tmp_path / "light.png"), _png(tmp_path / "dark.png")
    assert len(light) > 2000 and light != dark


@needs_browser
def test_karten13_ac3_a_connection_is_drawn(tmp_path: Path) -> None:
    checked = kitcheck.check(sample("good", "session-connection.yaml"), "integration")
    assert checked["ok"], checked["problems"]
    render.draw(checked, tmp_path / "light.png", tmp_path / "dark.png")
    assert len(_png(tmp_path / "light.png")) > 2000


@needs_browser
def test_karten13_ec6_a_card_that_breaks_the_page_is_an_error_not_a_picture(tmp_path: Path) -> None:
    checked = kitcheck.check(sample("good", "value-card.yaml"), "card")
    checked["form"], checked["widget_data"] = "list", {"status": "ok", "items": "not a list"}
    with pytest.raises(render.RenderError):
        render.draw(checked, tmp_path / "light.png", tmp_path / "dark.png")


def test_karten13_ec6_without_the_page_of_the_kit_nothing_is_drawn(tmp_path: Path) -> None:
    with pytest.raises(render.RenderError, match="missing"):
        render.draw({"type": "card", "name": "x", "form": "value", "widget_data": {}}, tmp_path / "a.png", tmp_path / "b.png", kit=tmp_path)


def test_karten13_b9_only_the_page_itself_may_be_asked_for_while_drawing() -> None:
    origin = "http://127.0.0.1:5000"
    assert render.is_local(origin, origin) and render.is_local(origin + "/workshop-preview.html", origin)
    assert not render.is_local("http://127.0.0.1:50001/x", origin)
    assert not render.is_local("http://127.0.0.1:5000.evil.example/x", origin)
    assert not render.is_local("https://evil.example/", origin) and not render.is_local("http://127.0.0.1:5000@evil.example/", origin)


@needs_browser
def test_karten13_b9_a_card_that_makes_the_page_hang_is_refused_in_time(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    kit = tmp_path / "kit"
    (kit / "page").mkdir(parents=True)
    (kit / "page" / "workshop-preview.html").write_text(
        "<!doctype html><title>x</title><script>window.nexdeckPreview = {show() { for (;;) {} }}</script>", encoding="utf-8"
    )
    monkeypatch.setattr(render, "SHOW_TIMEOUT_MS", 1_500)
    with pytest.raises(render.RenderError):
        render.draw({"type": "card", "name": "x", "form": "value", "widget_data": {"status": "ok"}}, tmp_path / "a.png", tmp_path / "b.png", kit=kit)
