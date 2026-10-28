"""Stand-ins for GitHub and for the drawing, and the helpers every test of the tools shares."""

from __future__ import annotations

import re
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from tools import issue_form, publish, submit
from tools.common import ROOT

BOT = {"login": "github-actions[bot]", "id": 41898282, "type": "Bot"}
SUBMISSIONS = Path(__file__).parent / "submissions"
NOON = datetime(2026, 10, 28, 12, 0, tzinfo=UTC)

#: Whoever acts in the tests: a maintainer, and two ordinary accounts.
MAINTAINER = {"id": 900, "login": "maintainer"}
ALICE = {"id": 101, "login": "alice"}
BOB = {"id": 202, "login": "bob"}


def sample(folder: str, name: str) -> str:
    # The only text of a secret in the samples is made here, so no scanner takes the repository for a leak.
    return (SUBMISSIONS / folder / name).read_text(encoding="utf-8").replace("@@SECRET@@", "0123456789abcdef" * 2)


class FakeHub:
    """GitHub as far as the tools use it: issues with comments, discussions with thumbs."""

    repo = "DerKezorm/nexdeck-workshop"

    def __init__(self) -> None:
        self.issues: dict[int, dict[str, Any]] = {}
        self.thread: dict[int, list[dict[str, Any]]] = {}
        self.discussions: list[dict[str, str]] = []
        self.reactions: dict[str, int] = {}
        self.discussions_on = True

    def submit(self, number: int, user: dict[str, Any], body: str, state: str = "open") -> None:
        self.issues[number] = {"number": number, "state": state, "body": body, "user": user, "title": f"Submit {number}"}
        self.thread.setdefault(number, [])

    def open_issues(self) -> list[dict[str, Any]]:
        return [one for one in self.issues.values() if one["state"] == "open"]

    def issue(self, number: int) -> dict[str, Any]:
        return self.issues[number]

    def comments(self, number: int) -> list[dict[str, Any]]:
        return self.thread.get(number, [])

    def post_comment(self, number: int, body: str) -> None:
        self.thread.setdefault(number, []).append({"user": BOT, "body": body})

    def close_issue(self, number: int) -> None:
        self.issues[number]["state"] = "closed"

    def create_discussion(self, title: str, body: str) -> dict[str, str] | None:
        if not self.discussions_on:
            return None
        made = {"id": f"D_{len(self.discussions) + 1}", "url": f"https://github.com/{self.repo}/discussions/{len(self.discussions) + 1}"}
        self.discussions.append({**made, "title": title})
        return made

    def thumbs(self, discussion_id: str) -> int | None:
        return self.reactions.get(discussion_id, 0)

    def last_comment(self, number: int) -> str:
        return self.thread[number][-1]["body"]


def fake_draw(checked: dict[str, Any], light: Path, dark: Path) -> None:
    """Writes two small files where the pictures go; the real drawing is tested on its own."""
    light.write_bytes(b"\x89PNG light " + b"0" * 300)
    dark.write_bytes(b"\x89PNG dark " + b"0" * 300)


@pytest.fixture
def hub() -> FakeHub:
    return FakeHub()


@pytest.fixture
def root(tmp_path: Path) -> Path:
    """An empty workshop: the README with its markers, the list of maintainers and an empty catalog."""
    shutil.copyfile(ROOT / "README.md", tmp_path / "README.md")
    (tmp_path / "MAINTAINERS").write_text("900  # maintainer\n", encoding="utf-8")
    (tmp_path / "catalog.json").write_text('{"format": 1, "generated_at": "", "entries": []}\n', encoding="utf-8")
    return tmp_path


@pytest.fixture
def ctx(root: Path, hub: FakeHub) -> submit.Context:
    return submit.Context(root, hub, clock=NOON, kit=ROOT / "kit", draw=fake_draw)


def form_body(text: str, *, type: str | None = None, category: str = "media", description: str = "Shows how many items wait.", **more: Any) -> str:
    kind = type or ("integration" if re.search(r"^nexdeck: integration", text, re.MULTILINE) else "card")
    return issue_form.build_body(type=kind, category=category, definition=text, description=description, **more)


def run(ctx: submit.Context, issue: int | None = None, *, force: bool = False) -> list[dict[str, Any]]:
    """One run of the submit action, with what ``publish`` does afterwards."""
    posts = submit.sweep(ctx, issue, force)
    publish.save_outbox(ctx.root, posts)
    publish.publish(ctx.root, ctx.hub)
    return posts
