"""Skins in the workshop: handed in as JSON, checked and compiled by the kit as nexdeck does, kept as ``skin.json``.

A skin reads and presses nothing, so the entry, the README and the comment say nothing about a reach; its pictures are
the stage of nexdeck's skin editor wearing the style sheet the kit compiled.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from tests.conftest import ALICE, FakeHub, form_body, run, sample
from tools import entries, issue_form, render, work
from tools.common import read_json

SKIN = sample("skins", "pixel-desk.json")
FOLDER = "entries/101/test-pixel-desk"


def changed(**more: Any) -> str:
    return json.dumps({**json.loads(SKIN), **more}, indent=2) + "\n"


def test_a_skin_becomes_an_entry_with_its_file_as_json(ctx: Any, hub: FakeHub, root: Path) -> None:
    hub.submit(7, ALICE, form_body(SKIN, type="skin", category="other", description="Bricks behind the cards and red title bars."))
    run(ctx, 7)
    assert hub.issues[7]["state"] == "closed", hub.last_comment(7)
    folder = root / FOLDER
    assert sorted(path.name for path in folder.iterdir()) == ["CHANGELOG.md", "README.md", "entry.json", "preview-dark.png", "preview-light.png", "skin.json"]
    assert (folder / "skin.json").read_text(encoding="utf-8") == SKIN
    data = read_json(folder / "entry.json")
    assert data["type"] == "skin" and data["meta"]["version"] == "1.0.0" and data["meta"]["reads"] == [] and data["meta"]["buttons"] == []
    listed = read_json(root / "catalog.json")["entries"][0]
    assert listed["type"] == "skin" and listed["files"]["definition"] == f"{FOLDER}/skin.json"
    assert listed["sha256"] == hashlib.sha256(SKIN.encode("utf-8")).hexdigest()
    readme = (folder / "README.md").read_text(encoding="utf-8")
    assert "| Type | Skin |" in readme and "| Reach |" not in readme
    comment = hub.last_comment(7)
    assert "**Accepted.**" in comment and "Reach" not in comment
    assert "Skin, version 1.0.0, by" in (root / "README.md").read_text(encoding="utf-8")


def test_the_pictures_of_a_skin_wear_what_the_kit_compiled(ctx: Any, hub: FakeHub, root: Path) -> None:
    seen: list[dict[str, Any]] = []

    def draw(checked: dict[str, Any], light: Path, dark: Path) -> None:
        seen.append(render.spec_of(checked, "dark"))
        light.write_bytes(b"\x89PNG light " + b"0" * 300)
        dark.write_bytes(b"\x89PNG dark " + b"0" * 300)

    ctx.draw = draw
    hub.submit(7, ALICE, form_body(SKIN, type="skin", category="other", description="Bricks behind the cards and red title bars."))
    run(ctx, 7)
    assert seen and set(seen[0]) == {"skin", "name", "theme"} and seen[0]["name"] == "Pixel desk"
    assert seen[0]["skin"]["key"] == "test-pixel-desk" and "[data-skin='test-pixel-desk']" in seen[0]["skin"]["css"]


def test_a_skin_nexdeck_would_not_wear_stays_open_with_the_reason(ctx: Any, hub: FakeHub, root: Path) -> None:
    hub.submit(3, ALICE, form_body(changed(css="[data-part=chip] { color: red !important }"), type="skin", category="other", description="Bricks behind the cards and red title bars."))
    run(ctx, 3)
    assert hub.issues[3]["state"] == "open" and "important" in hub.last_comment(3)
    assert not (root / FOLDER).exists()


def test_a_skin_handed_in_as_a_card_is_refused(ctx: Any, hub: FakeHub) -> None:
    hub.submit(3, ALICE, form_body(SKIN, type="card", category="other", description="Bricks behind the cards and red title bars."))
    run(ctx, 3)
    assert hub.issues[3]["state"] == "open" and "the text is a skin" in hub.last_comment(3)


def test_an_update_of_a_skin_needs_a_higher_version(ctx: Any, hub: FakeHub, root: Path) -> None:
    words = {"type": "skin", "category": "other", "description": "Bricks behind the cards and red title bars."}
    hub.submit(1, ALICE, form_body(SKIN, **words))
    run(ctx, 1)
    hub.submit(2, ALICE, form_body(SKIN, changes="Nothing.", **words))
    hub.submit(3, ALICE, form_body(changed(version="1.1.0"), changes="Brighter bricks.", **words))
    run(ctx)
    assert "version must be higher than the current 1.0.0" in hub.last_comment(2)
    assert hub.issues[3]["state"] == "closed" and read_json(root / FOLDER / "entry.json")["meta"]["version"] == "1.1.0"
    assert (root / FOLDER / "skin.json").read_text(encoding="utf-8") == changed(version="1.1.0")


def test_the_form_hands_a_skin_in_as_json_and_reads_it_back() -> None:
    body = issue_form.build_body(type="skin", category="other", definition=SKIN, description="Bricks behind the cards.")
    assert "```json\n" in body
    form = issue_form.parse(body)
    assert form.type == "skin" and form.definition == SKIN and not form.problems


def test_a_catalog_entry_of_a_card_keeps_its_yaml_file(root: Path) -> None:
    assert entries.definition_file("card") == entries.definition_file("integration") == "definition.yaml"
    assert entries.definition_file("skin") == "skin.json"


def test_a_skin_taken_by_a_run_whose_comment_never_came_out_is_said_to_be_accepted_once_more(ctx: Any, hub: FakeHub, root: Path) -> None:
    hub.submit(7, ALICE, form_body(SKIN, type="skin", category="other", description="Bricks behind the cards and red title bars."))
    work.run(ctx, issue=7)  # the files are made and pushed, the comment never posted
    assert (root / FOLDER / "skin.json").is_file() and hub.issues[7]["state"] == "open"
    run(ctx, 7)
    assert hub.issues[7]["state"] == "closed" and "**Accepted.**" in hub.last_comment(7)
    assert read_json(root / FOLDER / "entry.json")["issues"] == [7], "the same submission is not taken as its own update"
