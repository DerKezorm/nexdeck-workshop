"""The kit is the one of nexdeck 1.0.1 with the corrections of the second security review (found in a real run on 1.0.1).

The kit was made before the corrections of the first review, so the check here took cards nexdeck refuses and the shop
offered cards that could not be installed. These tests hold the kit to what nexdeck refuses now.
"""

from __future__ import annotations

import json

import pytest

from tests.conftest import sample
from tools import kitcheck
from tools.common import ROOT

#: The nexdeck the kit has to come from at least: the last release with the corrections of both reviews.
OLDEST_KIT = (1, 0, 1)
LIST = sample("good", "list-card.yaml")


def _version(text: str) -> tuple[int, ...]:
    return tuple(int(part) for part in text.split("+")[0].split("-")[0].split("."))


def test_karten8t_b9_the_kit_comes_from_a_recent_nexdeck() -> None:
    version = json.loads((ROOT / "kit" / "VERSION").read_text(encoding="utf-8"))
    assert _version(version["nexdeck"]) >= OLDEST_KIT, version
    assert version["commit"] and not version["commit"].endswith("+changed"), "the kit is made from a clean nexdeck"


@pytest.mark.parametrize(
    ("change", "code"),
    [
        (("  title: name\n", "  title: name\n  link: {template: 'https://stats.example.com/q?k={name}'}\n"), "card_link_address"),
        (("  title: name\n", "  title: name\n  link: {template: 'https://{name}.example.com/q'}\n"), "card_link_address"),
        (("path: /api/torrents", "path: /api/%c0%ae%c0%ae/config"), "card_bad_path"),
    ],
    ids=["link-to-a-host-of-the-author", "link-with-the-host-from-the-answer", "dots-in-disguise"],
)
def test_karten8t_b9_the_kit_refuses_what_nexdeck_refuses(change: tuple[str, str], code: str) -> None:
    assert change[0] in LIST
    answer = kitcheck.check(LIST.replace(*change), "card")
    assert answer["ok"] is False and code in [problem["code"] for problem in answer["problems"]], answer


def test_karten8t_b9_a_link_underneath_the_connection_or_written_out_whole_passes() -> None:
    for link in ("/torrents/{name}", "https://docs.example.com/torrents"):
        answer = kitcheck.check(LIST.replace("  title: name\n", f"  title: name\n  link: {{template: '{link}'}}\n"), "card")
        assert answer["ok"] is True, answer["problems"]

