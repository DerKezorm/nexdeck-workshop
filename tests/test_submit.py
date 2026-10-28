"""The submit action against good and bad submissions (KARTEN-13 AC-1 to AC-5, AC-9, AC-10, AC-12, EC-1 to EC-3, EC-6 to EC-10)."""

from __future__ import annotations

import json
import re
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest

from tests.conftest import ALICE, BOB, MAINTAINER, NOON, SUBMISSIONS, FakeHub, form_body, run, sample
from tools import entries, render
from tools.common import read_json

GOOD = sorted(path.name for path in (SUBMISSIONS / "good").glob("*.yaml"))
BAD = sorted(path.name for path in (SUBMISSIONS / "bad").glob("*.yaml"))
CLASSES = {"value-card.yaml": "read", "list-card.yaml": "read", "button-card.yaml": "buttons", "session-connection.yaml": "login"}

VALUE = sample("good", "value-card.yaml")


def _files(root: Path) -> list[str]:
    return sorted(path.relative_to(root).as_posix() for path in (root / "entries").rglob("*") if path.is_file()) if (root / "entries").exists() else []


def _expect(name: str) -> str:
    return sample("bad", name).splitlines()[0].removeprefix("# expect:").strip()


def _with_category(body: str, category: str) -> str:
    """The body with whatever is written under Category, as a person can write it in the form's dropdown or a client by mistake."""
    return body.replace("### Category\n\nMedia", f"### Category\n\n{category}")


def _update(text: str, version: str, slug: str | None = None) -> str:
    text = text.replace("version: 1.0.0", f"version: {version}")
    return text.replace("slug: test-queue-size", f"slug: {slug}") if slug else text


@pytest.mark.parametrize("name", GOOD)
def test_karten13_ac1_ac3_a_good_submission_becomes_an_entry(ctx: Any, hub: FakeHub, root: Path, name: str) -> None:
    hub.submit(7, ALICE, form_body(sample("good", name), category="downloads"))
    run(ctx, 7)
    assert hub.issues[7]["state"] == "closed"
    slug = {"value-card.yaml": "test-queue-size", "list-card.yaml": "test-downloads", "button-card.yaml": "test-queue-flush", "session-connection.yaml": "test-box"}[name]
    folder = f"entries/101/{slug}"
    assert _files(root) == sorted(f"{folder}/{one}" for one in ("CHANGELOG.md", "README.md", "definition.yaml", "entry.json", "preview-dark.png", "preview-light.png"))
    assert (root / folder / "definition.yaml").read_text(encoding="utf-8") == sample("good", name)
    data = read_json(root / folder / "entry.json")
    assert data["author_id"] == 101 and data["author_login"] == "alice" and data["category"] == "downloads"
    assert data["issue"] == 7 and data["removed"] is None and data["test"] is True
    assert data["meta"]["class"] == CLASSES[name]
    comment = hub.last_comment(7)
    assert "**Accepted.**" in comment and f"/tree/main/{folder}" in comment and CLASSES[name] in comment


@pytest.mark.parametrize("name", BAD)
def test_karten13_ac2_ac4_a_bad_submission_stays_open_with_the_reason(ctx: Any, hub: FakeHub, root: Path, name: str) -> None:
    hub.submit(3, ALICE, form_body(sample("bad", name)))
    run(ctx, 3)
    assert hub.issues[3]["state"] == "open"
    assert _files(root) == []
    comment = hub.last_comment(3)
    assert "cannot be accepted yet" in comment and _expect(name) in comment
    assert "/recheck" in comment


def test_karten13_ac4_every_reason_is_listed(ctx: Any, hub: FakeHub) -> None:
    hub.submit(3, ALICE, _with_category(form_body(sample("bad", "secret.yaml"), description="", licensed=False), "nonsense"))
    run(ctx, 3)
    reasons = [line for line in hub.last_comment(3).splitlines() if line.startswith("- ")]
    assert len(reasons) == 4
    text = " ".join(reasons)
    for part in ("category must be one of", "MIT License", "description", "holds no secrets"):
        assert part in text


def test_karten13_ac4_a_corrected_submission_in_the_same_issue_is_checked_again(ctx: Any, hub: FakeHub, root: Path) -> None:
    hub.submit(3, ALICE, form_body(sample("bad", "no-demo.yaml")))
    run(ctx, 3)
    assert hub.issues[3]["state"] == "open"
    hub.issues[3]["body"] = form_body(sample("good", "value-card.yaml"))
    run(ctx, 3)
    assert hub.issues[3]["state"] == "closed" and "**Accepted.**" in hub.last_comment(3)
    assert len(_files(root)) == 6


def test_karten13_a_judged_wording_is_not_judged_twice(ctx: Any, hub: FakeHub) -> None:
    hub.submit(3, ALICE, form_body(sample("bad", "no-demo.yaml")))
    run(ctx, 3)
    run(ctx, 3)
    run(ctx)
    assert len(hub.thread[3]) == 1
    run(ctx, 3, force=True)
    assert len(hub.thread[3]) == 2


@pytest.mark.parametrize("category", ["", "media-ish", "Server stuff"])
def test_karten13_ac12_without_a_category_from_the_list_the_check_is_red(ctx: Any, hub: FakeHub, category: str) -> None:
    hub.submit(3, ALICE, _with_category(form_body(VALUE), category or "_No response_"))
    run(ctx, 3)
    assert hub.issues[3]["state"] == "open" and "category must be one of Media, Downloads, Network, Server, Smart home, Other" in hub.last_comment(3)


def test_karten13_ac10_without_the_mit_box_ticked_nothing_is_taken(ctx: Any, hub: FakeHub, root: Path) -> None:
    hub.submit(3, ALICE, form_body(VALUE, licensed=False))
    run(ctx, 3)
    assert hub.issues[3]["state"] == "open" and "MIT License" in hub.last_comment(3)
    assert _files(root) == []


def test_karten13_a_key_in_the_description_or_the_changes_is_refused(ctx: Any, hub: FakeHub, root: Path) -> None:
    token = "ghp" + "_" + "a1b2c3d4e5" * 4
    hub.submit(3, ALICE, form_body(VALUE, description=f"Log in with {token}."))
    run(ctx, 3)
    assert hub.issues[3]["state"] == "open" and "description looks like it holds" in hub.last_comment(3)
    assert token not in hub.last_comment(3)
    assert _files(root) == []


def test_karten13_ac3_the_pictures_come_from_the_action(ctx: Any, hub: FakeHub, root: Path) -> None:
    hub.submit(3, ALICE, form_body(VALUE))
    run(ctx, 3)
    folder = root / "entries/101/test-queue-size"
    assert (folder / "preview-light.png").read_bytes().startswith(b"\x89PNG light")
    assert (folder / "preview-dark.png").read_bytes().startswith(b"\x89PNG dark")


def test_karten13_ec6_a_picture_that_cannot_be_drawn_is_red(ctx: Any, hub: FakeHub, root: Path) -> None:
    def broken(checked: dict[str, Any], light: Path, dark: Path) -> None:
        raise render.RenderError("The picture could not be drawn.")

    ctx.draw = broken
    hub.submit(3, ALICE, form_body(VALUE))
    run(ctx, 3)
    assert hub.issues[3]["state"] == "open" and "preview picture could not be drawn" in hub.last_comment(3)
    assert _files(root) == []


def test_karten13_ec1_the_same_short_name_from_the_same_account_is_an_update(ctx: Any, hub: FakeHub, root: Path) -> None:
    hub.submit(1, ALICE, form_body(VALUE))
    run(ctx, 1)
    hub.submit(2, ALICE, form_body(_update(VALUE, "1.1.0"), changes="Added a unit."))
    run(ctx, 2)
    assert hub.issues[2]["state"] == "closed" and "is updated" in hub.last_comment(2)
    data = read_json(root / "entries/101/test-queue-size/entry.json")
    assert data["meta"]["version"] == "1.1.0" and data["issues"] == [1, 2] and data["issue"] == 2
    assert data["created_at"] == data["updated_at"] == "2026-10-28T12:00:00Z"
    log = (root / "entries/101/test-queue-size/CHANGELOG.md").read_text(encoding="utf-8")
    assert log.index("1.1.0") < log.index("1.0.0") and "Added a unit." in log
    assert len(read_json(root / "catalog.json")["entries"]) == 1


def test_karten13_an_update_needs_a_higher_version_and_a_list_of_changes(ctx: Any, hub: FakeHub, root: Path) -> None:
    hub.submit(1, ALICE, form_body(VALUE))
    run(ctx, 1)
    hub.submit(2, ALICE, form_body(VALUE, changes="Nothing."))
    hub.submit(3, ALICE, form_body(_update(VALUE, "1.2.0")))
    run(ctx)
    assert "version must be higher than the current 1.0.0" in hub.last_comment(2)
    assert "update needs a list of changes" in hub.last_comment(3)
    assert read_json(root / "entries/101/test-queue-size/entry.json")["meta"]["version"] == "1.0.0"


def test_karten13_ec2_two_authors_may_choose_the_same_short_name(ctx: Any, hub: FakeHub, root: Path) -> None:
    hub.submit(1, ALICE, form_body(VALUE))
    hub.submit(2, BOB, form_body(VALUE))
    run(ctx)
    assert _files(root)[0].startswith("entries/101/") and any(one.startswith("entries/202/test-queue-size/") for one in _files(root))
    catalog = read_json(root / "catalog.json")
    assert [(one["id"], one["author"]["login"]) for one in catalog["entries"]] == [("101/test-queue-size", "alice"), ("202/test-queue-size", "bob")]


def test_karten13_ac9_only_the_author_or_a_maintainer_updates_an_entry(ctx: Any, hub: FakeHub, root: Path) -> None:
    hub.submit(1, ALICE, form_body(VALUE))
    run(ctx, 1)
    hub.submit(2, BOB, form_body(_update(VALUE, "2.0.0"), changes="Mine now.", update_of="101/test-queue-size"))
    run(ctx, 2)
    assert hub.issues[2]["state"] == "open" and "Only the author of an entry or a maintainer can update it" in hub.last_comment(2)
    assert read_json(root / "entries/101/test-queue-size/entry.json")["meta"]["version"] == "1.0.0"
    hub.submit(3, MAINTAINER, form_body(_update(VALUE, "1.0.1"), changes="Fixed a typo.", update_of="101/test-queue-size"))
    run(ctx, 3)
    data = read_json(root / "entries/101/test-queue-size/entry.json")
    assert hub.issues[3]["state"] == "closed"
    assert data["meta"]["version"] == "1.0.1" and data["author_id"] == 101 and data["author_login"] == "alice"
    assert not (root / "entries/900").exists()


def test_karten13_ac9_an_update_of_nothing_is_refused(ctx: Any, hub: FakeHub) -> None:
    hub.submit(1, ALICE, form_body(VALUE, update_of="101/none"))
    run(ctx, 1)
    assert "There is no entry 101/none to update" in hub.last_comment(1)


def test_karten13_ec10_the_entry_belongs_to_the_id_not_to_the_name(ctx: Any, hub: FakeHub, root: Path) -> None:
    hub.submit(1, ALICE, form_body(VALUE))
    run(ctx, 1)
    renamed = {"id": 101, "login": "alice-new-name"}
    hub.submit(2, renamed, form_body(_update(VALUE, "1.1.0"), changes="Same person."))
    run(ctx, 2)
    assert hub.issues[2]["state"] == "closed"
    data = read_json(root / "entries/101/test-queue-size/entry.json")
    assert data["author_id"] == 101 and data["author_login"] == "alice-new-name"
    # Somebody who takes the old name does not get the entry.
    hub.submit(3, {"id": 303, "login": "alice"}, form_body(_update(VALUE, "9.0.0"), changes="Hijack.", update_of="101/test-queue-size"))
    run(ctx, 3)
    assert hub.issues[3]["state"] == "open"
    assert read_json(root / "entries/101/test-queue-size/entry.json")["meta"]["version"] == "1.1.0"


def test_karten13_ec9_two_updates_one_after_the_other_the_last_one_wins(ctx: Any, hub: FakeHub, root: Path) -> None:
    hub.submit(1, ALICE, form_body(VALUE))
    run(ctx, 1)
    # Listed the wrong way round on purpose: the run takes them by number.
    hub.submit(6, ALICE, form_body(_update(VALUE, "1.2.0"), changes="Second."))
    hub.submit(5, ALICE, form_body(_update(VALUE, "1.1.0"), changes="First."))
    run(ctx)
    data = read_json(root / "entries/101/test-queue-size/entry.json")
    assert data["meta"]["version"] == "1.2.0" and data["issues"] == [1, 5, 6]
    assert hub.issues[5]["state"] == hub.issues[6]["state"] == "closed"
    log = (root / "entries/101/test-queue-size/CHANGELOG.md").read_text(encoding="utf-8")
    assert log.index("1.2.0") < log.index("1.1.0") < log.index("1.0.0")


def test_karten13_ec3_the_eleventh_new_entry_of_a_day_waits_for_the_next_day(ctx: Any, hub: FakeHub, root: Path) -> None:
    for number in range(1, 12):
        hub.submit(number, ALICE, form_body(VALUE.replace("slug: test-queue-size", f"slug: test-card-{number}")))
    run(ctx)
    assert [hub.issues[number]["state"] for number in range(1, 12)] == ["closed"] * 10 + ["open"]
    assert "waits" in hub.last_comment(11) and "daily run" in hub.last_comment(11)
    run(ctx)
    assert len(hub.thread[11]) == 1, "the notice is given once"
    # An update is no new entry, and another account has its own ten.
    hub.submit(12, ALICE, form_body(_update(VALUE.replace("slug: test-queue-size", "slug: test-card-1"), "1.1.0"), changes="More."))
    hub.submit(13, BOB, form_body(VALUE))
    run(ctx)
    assert hub.issues[12]["state"] == hub.issues[13]["state"] == "closed" and hub.issues[11]["state"] == "open"
    ctx.clock = NOON + timedelta(days=1)
    run(ctx)
    assert hub.issues[11]["state"] == "closed" and "**Accepted.**" in hub.last_comment(11)
    assert len(hub.thread[11]) == 2


def test_karten13_ec7_a_submission_no_run_took_up_is_taken_by_the_next_one(ctx: Any, hub: FakeHub, root: Path) -> None:
    hub.submit(1, ALICE, form_body(VALUE))
    hub.submit(2, BOB, form_body(VALUE.replace("test-queue-size", "test-other")))
    run(ctx, 2)
    assert hub.issues[1]["state"] == hub.issues[2]["state"] == "closed"


def test_karten13_ec8_a_description_with_html_and_pictures_is_plain_text_everywhere(ctx: Any, hub: FakeHub, root: Path) -> None:
    nasty = 'Hello <script>alert(1)</script> <img src="https://evil.example.com/x.png"> ![pixel](https://evil.example.com/p.png) [click](javascript:alert(1))'
    hub.submit(1, ALICE, form_body(VALUE, description=nasty))
    run(ctx, 1)
    assert hub.issues[1]["state"] == "closed"
    for text in ((root / "entries/101/test-queue-size/README.md").read_text(encoding="utf-8"), (root / "README.md").read_text(encoding="utf-8")):
        assert not re.search(r"(?<!\\)<(script|img)", text), "no tag of the author gets through unescaped"
        assert not re.search(r"(?<!\\)!\[pixel\]", text) and not re.search(r"(?<!\\)\[click\]\(", text)
    assert r"\<script\>" in (root / "entries/101/test-queue-size/README.md").read_text(encoding="utf-8")
    catalog = json.loads((root / "catalog.json").read_text(encoding="utf-8"))
    assert catalog["entries"][0]["description"] == nasty, "the catalog keeps the text; whoever draws it draws text"
    images = [line for line in (root / "README.md").read_text(encoding="utf-8").splitlines() if "![" in line]
    assert images and all("evil" not in line for line in images)


def test_karten13_ac3_a_connection_is_drawn_as_a_list_of_what_it_reads() -> None:
    checked = {"type": "integration", "name": "Example box", "reads": [{"kind": "custom:x", "path": "/api/items"}], "read_labels": ["Items"]}
    spec = render.spec_of(checked, "dark")
    assert spec["form"] == "list" and spec["theme"] == "dark" and spec["name"] == "Example box"
    assert spec["data"]["items"][0]["title"] == "Items" and spec["data"]["items"][0]["subtitle"] == "/api/items"


def test_karten13_a_card_is_drawn_from_its_demo_data_in_its_own_size() -> None:
    checked = {"type": "card", "name": {"en": "Queue", "de": "Warteschlange"}, "form": "stats", "widget_data": {"status": "ok"}, "size": [4, 2]}
    spec = render.spec_of(checked, "light")
    assert spec == {"data": {"status": "ok"}, "form": "stats", "name": "Queue", "theme": "light", "size": [4, 2]}


def test_karten13_without_discussions_a_submission_is_still_taken_and_the_daily_run_makes_the_discussion(ctx: Any, hub: FakeHub, root: Path) -> None:
    from tools import daily

    hub.discussions_on = False
    hub.submit(1, ALICE, form_body(VALUE))
    run(ctx, 1)
    assert hub.issues[1]["state"] == "closed" and "Discussion:" not in hub.last_comment(1)
    assert read_json(root / "entries/101/test-queue-size/entry.json")["discussion"] is None
    hub.discussions_on = True
    daily.run(ctx)
    assert read_json(root / "entries/101/test-queue-size/entry.json")["discussion"]["id"] == "D_1"
    assert read_json(root / "catalog.json")["entries"][0]["discussion"].endswith("/discussions/1")


def test_karten13_an_issue_that_is_no_submission_is_told_once_and_only_when_it_woke_the_run(ctx: Any, hub: FakeHub) -> None:
    hub.submit(1, ALICE, "My card does not work, help!")
    hub.submit(2, BOB, "A question about the form.")
    run(ctx, 1)
    assert "not a submission" in hub.last_comment(1) and hub.thread[2] == []
    run(ctx, 1)
    assert len(hub.thread[1]) == 1


def test_karten13_a_closed_issue_is_left_alone(ctx: Any, hub: FakeHub, root: Path) -> None:
    hub.submit(1, ALICE, form_body(VALUE), state="closed")
    run(ctx, 1)
    assert _files(root) == [] and hub.thread[1] == []


def test_karten13_one_issue_that_breaks_the_run_does_not_hold_up_the_others(ctx: Any, hub: FakeHub, root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from tools import kitcheck

    real = kitcheck.check

    def flaky(text: str, kind: str, texts: dict[str, str] | None = None, kit: Path | None = None) -> dict[str, Any]:
        if "test-other" in text:
            raise RuntimeError("boom")
        return real(text, kind, texts, kit)

    monkeypatch.setattr(kitcheck, "check", flaky)
    hub.submit(1, ALICE, form_body(VALUE.replace("test-queue-size", "test-other")))
    hub.submit(2, BOB, form_body(VALUE))
    run(ctx)
    assert hub.issues[1]["state"] == "open" and hub.issues[2]["state"] == "closed"


def test_karten13_based_on_names_an_entry_that_exists(ctx: Any, hub: FakeHub, root: Path) -> None:
    hub.submit(1, ALICE, form_body(VALUE))
    run(ctx, 1)
    hub.submit(2, BOB, form_body(VALUE.replace("test-queue-size", "test-better"), based_on="101/test-queue-size"))
    hub.submit(3, BOB, form_body(VALUE.replace("test-queue-size", "test-worse"), based_on="101/nothing"))
    run(ctx)
    assert read_json(root / "entries/202/test-better/entry.json")["based_on"] == "101/test-queue-size"
    assert hub.issues[3]["state"] == "open" and "Based on must be the id of an entry" in hub.last_comment(3)
    assert entries.load_entry(root, "202/test-worse") is None
