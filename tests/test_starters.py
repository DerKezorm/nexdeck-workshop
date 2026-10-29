"""The entries marked as examples to start from (KARTEN-19 AC-4): ``starters.json`` and the flag in the catalog."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tests.conftest import ALICE, BOB, NOON, FakeHub, form_body, run, run_daily, sample
from tools import entries
from tools.common import read_json

VALUE = sample("good", "value-card.yaml")
LIST = sample("good", "list-card.yaml")


def _two(ctx: Any, hub: FakeHub) -> None:
    hub.submit(1, ALICE, form_body(VALUE))
    hub.submit(2, BOB, form_body(LIST, category="downloads"))
    run(ctx)


def _flags(root: Path) -> dict[str, bool]:
    return {one["id"]: one["starter"] for one in read_json(root / "catalog.json")["entries"]}


def test_karten19_ac4_without_a_list_no_entry_is_an_example(ctx: Any, hub: FakeHub, root: Path) -> None:
    _two(ctx, hub)
    assert _flags(root) == {"101/test-queue-size": False, "202/test-downloads": False}


def test_karten19_ac4_the_entries_of_the_list_are_marked_in_the_catalog(ctx: Any, hub: FakeHub, root: Path) -> None:
    (root / "starters.json").write_text('["202/test-downloads"]\n', encoding="utf-8")
    _two(ctx, hub)
    assert _flags(root) == {"101/test-queue-size": False, "202/test-downloads": True}


def test_karten19_ac4_the_daily_run_takes_up_a_changed_list(ctx: Any, hub: FakeHub, root: Path) -> None:
    _two(ctx, hub)
    (root / "starters.json").write_text('["101/test-queue-size", "202/test-downloads"]\n', encoding="utf-8")
    run_daily(ctx)
    assert _flags(root) == {"101/test-queue-size": True, "202/test-downloads": True}
    (root / "starters.json").write_text("[]\n", encoding="utf-8")
    run_daily(ctx)
    assert _flags(root) == {"101/test-queue-size": False, "202/test-downloads": False}


def test_karten19_ac4_a_list_that_makes_no_sense_marks_nothing(ctx: Any, hub: FakeHub, root: Path) -> None:
    _two(ctx, hub)
    for text in ("not json", '{"101/test-queue-size": true}', '[7, null, "../x", "nobody/none", "101"]', ""):
        (root / "starters.json").write_text(text, encoding="utf-8")
        assert entries.starters(root) == set(), text
        entries.refresh(root, NOON)
        assert not any(_flags(root).values()), text


def test_karten19_ac4_the_list_of_the_repository_names_entries_that_exist() -> None:
    from tools.common import ROOT

    listed = entries.starters(ROOT)
    assert listed, "the repository names its examples"
    catalog = {one["id"]: one for one in read_json(ROOT / "catalog.json")["entries"]}
    assert listed <= set(catalog)
    assert {key for key, one in catalog.items() if one["starter"]} == listed
