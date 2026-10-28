"""A run works from the state of the repository, not from the event that woke it (KARTEN-13 EC-7, EC-9)."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from typing import Any

import httpx
import pytest

from tests.conftest import ALICE, BOB, NOON, FakeHub, form_body, run, run_daily, sample
from tools import state, submit
from tools.hub import GitHub

BAD = sample("bad", "no-demo.yaml")
VALUE = sample("good", "value-card.yaml")


def _later(ctx: Any, hub: FakeHub, moment: Any) -> None:
    ctx.clock = moment
    hub.now = moment


def test_karten13_b4_a_run_reads_the_comments_of_the_issues_that_changed_and_of_no_other(ctx: Any, hub: FakeHub, root: Path) -> None:
    hub.now = NOON - timedelta(days=1)
    for number in range(1, 51):
        hub.submit(number, BOB, form_body(BAD))
    run(ctx, 1)
    assert hub.reads["comments"] == 50, "the first run has no moment to start from and reads them all"
    assert state.since_of(root) == "2026-10-28T11:59:00Z"
    _later(ctx, hub, NOON + timedelta(hours=1))
    hub.submit(51, BOB, form_body(BAD))
    hub.reads["comments"] = 0
    run(ctx, 51)
    assert hub.reads["comments"] == 1, "only the new issue"
    hub.reads["comments"] = 0
    _later(ctx, hub, NOON + timedelta(hours=2))
    run(ctx, 51)
    assert hub.reads["comments"] == 1, "the issue that woke the run is looked at even if nothing changed in it"
    hub.reads["comments"] = 0
    run(ctx)
    assert hub.reads["comments"] == 0, "nothing changed, nothing is read"


def test_karten13_b4_the_daily_run_looks_at_every_open_issue(ctx: Any, hub: FakeHub, root: Path) -> None:
    hub.now = NOON - timedelta(days=1)
    for number in range(1, 6):
        hub.submit(number, BOB, form_body(BAD))
    run(ctx)
    _later(ctx, hub, NOON + timedelta(days=1))
    hub.reads["comments"] = 0
    run(ctx)
    assert hub.reads["comments"] == 0
    run_daily(ctx)
    assert hub.reads["comments"] == 5


def test_karten13_ec7_the_run_of_one_issue_takes_up_the_issues_whose_runs_were_dropped(ctx: Any, hub: FakeHub, root: Path) -> None:
    run(ctx)
    _later(ctx, hub, NOON + timedelta(hours=1))
    hub.submit(1, ALICE, form_body(VALUE))  # its run was dropped by GitHub: nobody asked for it
    hub.submit(2, BOB, form_body(VALUE))
    run(ctx, 2)
    assert hub.issues[1]["state"] == "closed" and hub.issues[2]["state"] == "closed"
    assert (root / "entries/101/test-queue-size/definition.yaml").is_file()


def test_karten13_ec7_an_issue_that_could_not_be_judged_is_tried_again_by_the_next_run(
    ctx: Any, hub: FakeHub, root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run(ctx)
    _later(ctx, hub, NOON + timedelta(hours=1))
    before = state.since_of(root)
    hub.submit(1, ALICE, form_body(VALUE))
    original = submit.process

    def broken(*args: Any, **kwargs: Any) -> Any:
        raise OSError("disk full")

    monkeypatch.setattr(submit, "process", broken)
    assert run(ctx, 1) == []
    assert state.since_of(root) == before, "the moment is not moved on over an issue that was not judged"
    monkeypatch.setattr(submit, "process", original)
    _later(ctx, hub, NOON + timedelta(hours=2))
    run(ctx)
    assert hub.issues[1]["state"] == "closed"
    assert state.since_of(root) == "2026-10-28T13:59:00Z"


# -- the client: pages and the moment ------------------------------------------------------------------------


class Pages:
    def __init__(self, rows: int) -> None:
        self.rows = rows
        self.asked: list[dict[str, str]] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        query = dict(request.url.params)
        self.asked.append({"path": request.url.path, **query})
        page, size = int(query["page"]), int(query["per_page"])
        rows = [{"number": number, "updated_at": "x"} for number in range(1, self.rows + 1)][(page - 1) * size : page * size]
        return httpx.Response(200, json=rows)


def _hub(handler: Any) -> GitHub:
    hub = GitHub("DerKezorm/nexdeck-workshop", "token-for-tests")
    hub.http = httpx.Client(base_url="https://api.github.com", transport=httpx.MockTransport(handler))
    return hub


@pytest.mark.parametrize("rows,pages", [(0, 1), (99, 1), (100, 2), (250, 3)])
def test_karten13_b4_every_page_of_a_list_is_read_up_to_the_last(rows: int, pages: int) -> None:
    server = Pages(rows)
    assert len(_hub(server).comments(7)) == rows
    assert len(server.asked) == pages


def test_karten13_b4_the_issues_and_comments_are_asked_for_since_a_moment() -> None:
    server = Pages(3)
    hub = _hub(server)
    hub.open_issues("2026-10-28T11:59:00Z")
    hub.comments_since("2026-10-28T11:59:00Z")
    hub.open_issues()
    assert server.asked[0]["path"] == "/repos/DerKezorm/nexdeck-workshop/issues" and server.asked[0]["since"] == "2026-10-28T11:59:00Z"
    assert server.asked[0]["state"] == "open"
    assert server.asked[1]["path"] == "/repos/DerKezorm/nexdeck-workshop/issues/comments" and server.asked[1]["since"] == "2026-10-28T11:59:00Z"
    assert "since" not in server.asked[2]


def test_karten13_b4_a_list_without_an_end_stops_the_run() -> None:
    with pytest.raises(RuntimeError, match="pages"):
        _hub(lambda request: httpx.Response(200, json=[{"number": 1}] * 100)).comments(7)
