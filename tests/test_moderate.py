"""Removing, withdrawing, re-checking, the daily thumbs, the catalog (KARTEN-13 AC-5 to AC-8, EC-4, EC-5)."""

from __future__ import annotations

import json
import re
from datetime import timedelta
from pathlib import Path
from typing import Any

from tests.conftest import ALICE, BOB, MAINTAINER, NOON, FakeHub, form_body, run, run_daily, sample
from tools import entries, moderate, orders
from tools.common import read_json, sha256_of

VALUE = sample("good", "value-card.yaml")
ID = "101/test-queue-size"


def _accepted(ctx: Any, hub: FakeHub, number: int = 1) -> None:
    hub.submit(number, ALICE, form_body(VALUE))
    run(ctx, number)


def _comment(number: int, user: dict[str, Any], body: str, *, issue_user: dict[str, Any] = ALICE) -> dict[str, Any]:
    return {"issue": {"number": number, "user": issue_user}, "comment": {"body": body, "user": user}}


def _go(ctx: Any, event: dict[str, Any]) -> list[dict[str, Any]]:
    """A person writes the comment, and the next run of the action takes it up (nothing says which comment woke it)."""
    number = int(event["issue"]["number"])
    if number not in ctx.hub.issues:
        ctx.hub.submit(number, event["issue"]["user"], "A question, not a submission.")
    ctx.hub.say(number, event["comment"]["user"], event["comment"]["body"])
    return run(ctx)


def _entry(root: Path) -> dict[str, Any]:
    return read_json(root / "entries" / ID / "entry.json")  # type: ignore[no-any-return]


def test_karten13_ac8_a_maintainer_removes_an_entry_with_a_level_and_a_reason(ctx: Any, hub: FakeHub, root: Path) -> None:
    _accepted(ctx, hub)
    _go(ctx, _comment(1, MAINTAINER, "/remove harmful It sends your passwords away."))
    removed = _entry(root)["removed"]
    assert removed == {"level": "harmful", "reason": "It sends your passwords away.", "at": "2026-10-28T12:00:00Z"}
    catalog = read_json(root / "catalog.json")
    assert [one["id"] for one in catalog["entries"]] == [ID], "a removed entry stays in the catalog"
    assert catalog["entries"][0]["removed"] == removed
    assert "Nothing here yet." in (root / "README.md").read_text(encoding="utf-8"), "and leaves the list"
    assert (root / "entries" / ID / "definition.yaml").is_file()
    assert "**Removed.**" in hub.last_comment(1)


def test_karten13_ac8_not_useful_takes_the_reason_in_several_spellings(ctx: Any, hub: FakeHub, root: Path) -> None:
    _accepted(ctx, hub)
    _go(ctx, _comment(1, MAINTAINER, "/remove not useful Shows nothing a plain number card does not."))
    assert _entry(root)["removed"]["level"] == "not_useful"


def test_karten13_ac8_nobody_else_removes_anything(ctx: Any, hub: FakeHub, root: Path) -> None:
    _accepted(ctx, hub)
    # The name of the maintainer is not enough: the id decides.
    liar = {"id": 5, "login": "maintainer"}
    _go(ctx, _comment(1, liar, "/remove harmful I just do not like it."))
    _go(ctx, _comment(1, ALICE, "/remove harmful I do not like my own card."))
    assert _entry(root)["removed"] is None
    assert "Only a maintainer can remove an entry." in hub.last_comment(1)


def test_karten13_ac8_a_removal_needs_a_valid_level_and_a_reason_and_an_entry(ctx: Any, hub: FakeHub, root: Path) -> None:
    _accepted(ctx, hub)
    for text in ("/remove", "/remove harmful", "/remove awful because", "/remove withdrawn because"):
        _go(ctx, _comment(1, MAINTAINER, text))
        assert _entry(root)["removed"] is None, text
        assert "Write `/remove harmful <reason>`" in hub.last_comment(1)
    _go(ctx, _comment(4, MAINTAINER, "/remove harmful Because."))
    assert "belongs to no entry" in hub.last_comment(4)


def test_karten13_ec5_the_author_withdraws_his_own_entry(ctx: Any, hub: FakeHub, root: Path) -> None:
    _accepted(ctx, hub)
    _go(ctx, _comment(1, BOB, "/withdraw", issue_user=ALICE))
    assert _entry(root)["removed"] is None and "Only the author of an entry can withdraw it." in hub.last_comment(1)
    _go(ctx, _comment(1, ALICE, "/withdraw"))
    removed = _entry(root)["removed"]
    assert removed["level"] == "withdrawn" and removed["reason"] == "withdrawn by the author"
    assert read_json(root / "catalog.json")["entries"][0]["removed"]["reason"] == "withdrawn by the author"


def test_karten13_a_removal_comes_from_the_issue_of_any_version_of_the_entry(ctx: Any, hub: FakeHub, root: Path) -> None:
    _accepted(ctx, hub)
    hub.submit(2, ALICE, form_body(VALUE.replace("version: 1.0.0", "version: 1.1.0"), changes="More."))
    run(ctx, 2)
    _go(ctx, _comment(1, MAINTAINER, "/remove not_useful Superseded by nothing."))
    assert _entry(root)["removed"]["level"] == "not_useful"


def test_karten13_ac8_the_manual_run_removes_for_a_maintainer_only(ctx: Any, hub: FakeHub, root: Path) -> None:
    _accepted(ctx, hub)
    assert orders.record(root, run="1-1", entry=ID, level="harmful", reason="Reason.", sender=5) == "Only a maintainer can remove an entry."
    assert not (root / "orders").exists()
    assert orders.record(root, run="1-1", entry=ID, level="awful", reason="Reason.", sender=900) == "The level is harmful or not_useful."
    assert orders.record(root, run="1-1", entry="../../etc", level="harmful", reason="Reason.", sender=900) == "That is not an entry id."
    assert orders.record(root, run="x", entry=ID, level="harmful", reason="Reason.", sender=900) == "That is not a run."
    assert _entry(root)["removed"] is None
    assert orders.record(root, run="1-1", entry=ID, level="harmful", reason="Reason.", sender=900) is None
    assert (root / "orders" / "1-1.json").is_file() and _entry(root)["removed"] is None, "recorded, not yet carried out"
    run(ctx)
    assert _entry(root)["removed"]["reason"] == "Reason." and not (root / "orders" / "1-1.json").exists()


def test_karten13_b3_an_order_nobody_carried_out_is_carried_out_by_the_next_run_of_any_kind(ctx: Any, hub: FakeHub, root: Path) -> None:
    _accepted(ctx, hub)
    orders.record(root, run="7-1", entry=ID, level="not_useful", reason="Superseded.", sender=900)  # its run was dropped
    hub.submit(2, BOB, form_body(sample("bad", "no-demo.yaml")))
    run(ctx, 2)  # a run for something else
    assert _entry(root)["removed"]["level"] == "not_useful"
    assert not list((root / "orders").glob("*.json"))


def test_karten13_b3_an_order_with_a_forged_sender_or_a_missing_entry_is_deleted_and_changes_nothing(ctx: Any, hub: FakeHub, root: Path) -> None:
    _accepted(ctx, hub)
    folder = root / "orders"
    folder.mkdir()
    (folder / "1-1.json").write_text(json.dumps({"entry": ID, "level": "harmful", "reason": "Bad.", "sender": 5}), encoding="utf-8")
    (folder / "2-1.json").write_text(json.dumps({"entry": "101/none", "level": "harmful", "reason": "Bad.", "sender": 900}), encoding="utf-8")
    (folder / "3-1.json").write_text("not json", encoding="utf-8")
    said = orders.apply(ctx)
    assert len(said) == 3 and "refused" in said[0] and "There is no entry" in said[1] and "not an order" in said[2]
    assert _entry(root)["removed"] is None and not list(folder.glob("*.json"))


def test_karten13_b3_a_command_nobody_took_up_is_carried_out_by_the_next_run_once(ctx: Any, hub: FakeHub, root: Path) -> None:
    _accepted(ctx, hub)
    hub.now = NOON + timedelta(hours=1)
    ctx.clock = hub.now
    hub.say(1, MAINTAINER, "/remove harmful It sends your passwords away.")  # the run for this comment was dropped
    hub.submit(2, BOB, form_body(sample("bad", "no-demo.yaml")))
    run(ctx, 2)
    assert _entry(root)["removed"]["level"] == "harmful"
    replies = [one for one in hub.thread[1] if "**Removed.**" in one["body"]]
    assert len(replies) == 1 and re.search(r"<!-- workshop:done:\d+ -->", replies[0]["body"])
    for later in (1, 2):
        hub.now = ctx.clock = NOON + timedelta(hours=1 + later)
        run(ctx)
    run_daily(ctx)
    assert len([one for one in hub.thread[1] if "**Removed.**" in one["body"]]) == 1, "marked done: not carried out again"


def test_karten13_b3_the_daily_run_finds_a_command_that_slipped_through(ctx: Any, hub: FakeHub, root: Path) -> None:
    _accepted(ctx, hub)
    hub.now = ctx.clock = NOON + timedelta(hours=1)
    hub.say(1, MAINTAINER, "/remove not_useful Nothing a plain card does not.")
    (root / "state.json").write_text('{"since": "2026-10-28T20:00:00Z"}\n', encoding="utf-8")  # a run went on without it
    hub.now = ctx.clock = NOON + timedelta(hours=10)
    run(ctx)
    assert _entry(root)["removed"] is None, "an ordinary run looks from the moment of the last run"
    run_daily(ctx)
    assert _entry(root)["removed"]["level"] == "not_useful"


def test_karten13_b3_a_command_older_than_the_last_run_is_not_carried_out_again(ctx: Any, hub: FakeHub, root: Path) -> None:
    _accepted(ctx, hub)
    hub.now = NOON - timedelta(days=5)
    hub.say(1, MAINTAINER, "/remove harmful Long ago.")
    hub.now = ctx.clock = NOON + timedelta(hours=1)
    run(ctx)
    run_daily(ctx)
    assert _entry(root)["removed"] is None


def test_karten13_b3_what_a_stranger_writes_into_a_comment_is_no_mark(ctx: Any, hub: FakeHub, root: Path) -> None:
    _accepted(ctx, hub)
    number = hub.say(1, MAINTAINER, "/remove harmful Bad.")
    hub.say(1, BOB, f"<!-- workshop:done:{number} -->")  # only the marks of the bot count
    run(ctx)
    assert _entry(root)["removed"]["level"] == "harmful"


def test_karten13_recheck_is_marked_done_by_the_verdict_it_asked_for(ctx: Any, hub: FakeHub, root: Path) -> None:
    hub.submit(1, ALICE, form_body(sample("bad", "no-demo.yaml")))
    run(ctx, 1)
    asked = hub.say(1, ALICE, "/recheck")
    run(ctx)
    assert f"<!-- workshop:done:{asked} -->" in hub.last_comment(1) and "cannot be accepted" in hub.last_comment(1)
    before = len(hub.thread[1])
    run(ctx)
    assert len(hub.thread[1]) == before, "asked once, answered once"
    hub.issues[1]["state"] = "closed"
    second = hub.say(1, MAINTAINER, "/recheck")
    run(ctx)
    assert f"<!-- workshop:done:{second} -->" in hub.last_comment(1) and "nothing to check" in hub.last_comment(1)


def test_karten13_a_word_that_only_starts_like_a_command_is_no_command(ctx: Any, hub: FakeHub, root: Path) -> None:
    _accepted(ctx, hub)
    for text in ("/removed it, thanks", "/withdrawal of my vote", "/restored?"):
        assert _go(ctx, _comment(1, MAINTAINER, text)) == []
    assert _entry(root)["removed"] is None


def test_karten13_a_harmful_entry_cannot_be_brought_back_by_an_update_but_a_withdrawn_one_can(ctx: Any, hub: FakeHub, root: Path) -> None:
    _accepted(ctx, hub)
    moderate.remove(ctx, ID, "harmful", "Bad.")
    hub.submit(2, ALICE, form_body(VALUE.replace("version: 1.0.0", "version: 1.1.0"), changes="Again."))
    run(ctx, 2)
    assert hub.issues[2]["state"] == "open" and "removed by a maintainer" in hub.last_comment(2)
    moderate.restore(ctx, ID)
    moderate.remove(ctx, ID, "withdrawn", "withdrawn by the author")
    run(ctx, 2, force=True)
    assert hub.issues[2]["state"] == "closed" and _entry(root)["removed"] is None


def test_karten13_ac8_the_author_cannot_undo_a_removal_by_withdrawing_and_updating(ctx: Any, hub: FakeHub, root: Path) -> None:
    _accepted(ctx, hub)
    _go(ctx, _comment(1, MAINTAINER, "/remove harmful It sends your passwords away."))
    _go(ctx, _comment(1, ALICE, "/withdraw"))
    assert _entry(root)["removed"]["level"] == "harmful" and _entry(root)["removed"]["reason"] == "It sends your passwords away."
    assert "only a maintainer can bring it back" in hub.last_comment(1)
    moderate.remove(ctx, ID, "not_useful", "Still nothing.")
    _go(ctx, _comment(1, ALICE, "/withdraw"))
    assert _entry(root)["removed"]["level"] == "not_useful"
    hub.submit(2, ALICE, form_body(VALUE.replace("version: 1.0.0", "version: 1.0.1"), changes="Nothing really."))
    run(ctx, 2)
    assert hub.issues[2]["state"] == "open" and _entry(root)["removed"]["level"] == "not_useful"


def test_karten13_ac8_a_maintainer_brings_a_removed_entry_back_and_nobody_else(ctx: Any, hub: FakeHub, root: Path) -> None:
    _accepted(ctx, hub)
    _go(ctx, _comment(1, MAINTAINER, "/restore"))
    assert "is not removed" in hub.last_comment(1)
    _go(ctx, _comment(1, MAINTAINER, "/remove harmful Bad."))
    for who in (ALICE, BOB, {"id": 5, "login": "maintainer"}):
        _go(ctx, _comment(1, who, "/restore"))
        assert _entry(root)["removed"]["level"] == "harmful" and "Only a maintainer can bring an entry back." in hub.last_comment(1)
    _go(ctx, _comment(1, MAINTAINER, "/restore"))
    assert _entry(root)["removed"] is None and "**Restored.**" in hub.last_comment(1)
    assert read_json(root / "catalog.json")["entries"][0]["removed"] is None
    assert "Queue size" in (root / "README.md").read_text(encoding="utf-8")
    # A withdrawal by the author is a removal like any other, and a maintainer takes it back as well.
    _go(ctx, _comment(1, ALICE, "/withdraw"))
    assert _entry(root)["removed"]["level"] == "withdrawn"
    _go(ctx, _comment(1, MAINTAINER, "/restore"))
    assert _entry(root)["removed"] is None


def test_karten13_ec4_when_the_account_is_gone_updates_go_through_the_maintainers(ctx: Any, hub: FakeHub, root: Path) -> None:
    _accepted(ctx, hub)
    # The account 101 is deleted: its issues and its name are gone, its entry stays.
    hub.submit(2, MAINTAINER, form_body(VALUE.replace("version: 1.0.0", "version: 1.0.1"), changes="Kept alive.", update_of=ID))
    run(ctx, 2)
    assert (root / "entries" / ID / "definition.yaml").is_file() and _entry(root)["meta"]["version"] == "1.0.1"
    assert _entry(root)["author_id"] == 101


def test_karten13_recheck_judges_the_issue_again_for_its_author_or_a_maintainer(ctx: Any, hub: FakeHub, root: Path) -> None:
    hub.submit(1, ALICE, form_body(sample("bad", "no-demo.yaml")))
    run(ctx, 1)
    assert len(hub.thread[1]) == 1
    _go(ctx, _comment(1, BOB, "/recheck"))
    assert len(hub.thread[1]) == 2, "somebody else cannot make the action repeat itself: only his comment is there"
    _go(ctx, _comment(1, ALICE, "/recheck"))
    assert len(hub.thread[1]) == 4  # the comment, and the new verdict
    assert "cannot be accepted" in hub.last_comment(1)
    _go(ctx, _comment(1, ALICE, "Thanks!"))
    assert len(hub.thread[1]) == 5


# -- the catalog, the daily thumbs --------------------------------------------------------------------


def test_karten13_ac5_the_catalog_says_what_nexdeck_needs_to_know(ctx: Any, hub: FakeHub, root: Path) -> None:
    for number, name in enumerate(("value-card.yaml", "button-card.yaml", "session-connection.yaml"), start=1):
        hub.submit(number, ALICE, form_body(sample("good", name), category="network"))
    run(ctx)
    catalog = read_json(root / "catalog.json")
    assert catalog["format"] == 1 and catalog["generated_at"].endswith("Z")
    keys = {"id", "type", "slug", "name", "description", "author", "version", "min_nexdeck", "category", "requires", "class", "reads", "buttons", "sha256", "files", "thumbs", "discussion", "based_on", "updated_at", "removed"}
    assert len(catalog["entries"]) == 3
    for one in catalog["entries"]:
        assert set(one) == keys
        assert one["sha256"] == sha256_of(root / one["files"]["definition"])
        assert all((root / path).is_file() for path in one["files"].values())
        assert one["author"] == {"id": 101, "login": "alice"} and one["category"] == "network"
        assert one["removed"] is None and one["thumbs"] == 0 and one["based_on"] is None
    by_class = {one["slug"]: one for one in catalog["entries"]}
    assert by_class["test-queue-flush"]["buttons"] == [{"label": "Flush", "method": "POST", "path": "/api/queue/flush"}]
    assert by_class["test-queue-flush"]["class"] == "buttons" and by_class["test-box"]["class"] == "login"
    assert by_class["test-queue-size"]["requires"] == ["jsonapi"] and by_class["test-queue-size"]["min_nexdeck"]
    assert by_class["test-box"]["reads"] == [{"kind": "custom:test-box", "path": "/api/items"}, {"kind": "custom:test-box", "path": "/api/status"}]
    assert by_class["test-box"]["type"] == "integration"
    assert by_class["test-queue-size"]["name"] == {"en": "Queue size", "de": "Warteschlange"}


def test_karten13_ac7_the_readme_lists_the_entries_with_their_pictures_between_the_markers(ctx: Any, hub: FakeHub, root: Path) -> None:
    before = (root / "README.md").read_text(encoding="utf-8")
    hub.submit(1, ALICE, form_body(VALUE))
    hub.submit(2, BOB, form_body(sample("good", "list-card.yaml"), category="downloads"))
    run(ctx)
    text = (root / "README.md").read_text(encoding="utf-8")
    start, end = text.index(entries.START), text.index(entries.END)
    assert text[:start] == before[: before.index(entries.START)] and text[end + len(entries.END) :] == before[before.index(entries.END) + len(entries.END) :]
    listed = text[start:end]
    assert "### Media" in listed and "### Downloads" in listed
    assert "entries/101/test-queue-size/preview-light.png" in listed and "entries/202/test-downloads/preview-dark.png" in listed
    assert listed.index("### Media") < listed.index("### Downloads")


def test_karten13_ac6_the_daily_run_counts_the_thumbs_into_the_catalog(ctx: Any, hub: FakeHub, root: Path) -> None:
    _accepted(ctx, hub)
    hub.reactions["D_1"] = 4
    run_daily(ctx)
    assert _entry(root)["thumbs"] == 4 and read_json(root / "catalog.json")["entries"][0]["thumbs"] == 4
    assert "4 thumbs up" in (root / "README.md").read_text(encoding="utf-8")


def test_karten13_ac6_a_day_without_news_changes_nothing(ctx: Any, hub: FakeHub, root: Path) -> None:
    _accepted(ctx, hub)
    before = (root / "catalog.json").read_text(encoding="utf-8")
    ctx.clock = NOON + timedelta(days=1)
    run_daily(ctx)
    assert (root / "catalog.json").read_text(encoding="utf-8") == before


def test_karten13_ac6_every_new_entry_gets_a_discussion_and_a_removed_one_none(ctx: Any, hub: FakeHub, root: Path) -> None:
    hub.submit(1, ALICE, form_body(VALUE))
    hub.submit(2, BOB, form_body(VALUE))
    run(ctx)
    assert [one["title"] for one in hub.discussions] == ["Queue size (101/test-queue-size)", "Queue size (202/test-queue-size)"]
    assert json.loads((root / "catalog.json").read_text(encoding="utf-8"))["entries"][1]["discussion"].endswith("/discussions/2")
