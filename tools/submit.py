"""Checks the submissions that wait, and puts the good ones into the repository (KARTEN-13).

    python -m tools.work [--issue N] [--daily]

One run (``work.py``) looks at the open issues that are submissions and changed since the last run, oldest first
(KARTEN-13 EC-9: one after the other, the last one wins); the daily run looks at all of them. A run that GitHub skipped
or delayed costs nothing: the next one takes up what is left (EC-7). A good submission becomes files in ``entries/``; a
bad one gets a comment with every reason, and stays open. Nothing is posted here: the comments to write and the issues
to close are collected in ``.outbox.json`` and posted by ``publish.py`` once the files are pushed.
"""

from __future__ import annotations

import hashlib
import re
import sys
import tempfile
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from . import entries, issue_form, kitcheck
from . import render as renderer
from .common import (
    CATEGORIES,
    DESCRIPTION_SENTENCE,
    SECRET_IN_DEMO,
    ID,
    TYPES,
    MAX_ENTRIES,
    MAX_NEW_PER_DAY,
    MIN_CHANGES_CHARS,
    ROOT,
    demo_secrets,
    describes,
    iso,
    maintainers,
    md,
    now,
    plain,
    definition_file,
    version_tuple,
)
from .hub import GitHub, Hub

BOT = "github-actions[bot]"
MARKER = re.compile(r"<!-- workshop:(accepted|rejected|deferred):([0-9a-f]{64}) -->")
LOGIN = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$")

Draw = Callable[[dict[str, Any], Path, Path], None]


@dataclass
class Context:
    root: Path
    hub: Hub
    clock: datetime = field(default_factory=now)
    kit: Path | None = None
    draw: Draw | None = None
    staff: set[int] | None = None
    #: The issues a run could not judge (an error); while there are some, the run does not move ``since`` on.
    failed: list[int] = field(default_factory=list)

    def pictures(self, checked: dict[str, Any], light: Path, dark: Path) -> None:
        (self.draw or (lambda data, one, two: renderer.draw(data, one, two, self.kit)))(checked, light, dark)

    @property
    def maintainers(self) -> set[int]:
        return self.staff if self.staff is not None else maintainers(self.root)


def marker(status: str, digest: str) -> str:
    return f"<!-- workshop:{status}:{digest} -->"


def last_marker(comments: list[dict[str, Any]]) -> tuple[str, str] | None:
    for comment in reversed(comments):
        if (comment.get("user") or {}).get("login") != BOT:
            continue
        found = MARKER.search(comment.get("body") or "")
        if found:
            return found.group(1), found.group(2)
    return None


def _demo_of(text: str) -> Any:
    """The demo data of a definition, or nothing when it is no YAML (the check of the kit says why)."""
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError:
        return None
    return data.get("demo") if isinstance(data, dict) else None


def _reason(problem: dict[str, Any]) -> str:
    where = ""
    if problem.get("line"):
        where = f" (line {problem['line']})"
    elif problem.get("path"):
        where = f" ({problem['path']})"
    message = " ".join(str(problem["message"]).split())
    # ⚠️ The message may quote the text of the submitter: it is written as plain text, never as Markdown of the bot.
    return md(f"{message}{where}")


def _post(number: int, status: str, digest: str, text: str, *, close: bool = False) -> dict[str, Any]:
    return {"issue": number, "comment": f"{text}\n\n{marker(status, digest)}", "close": close}


def _rejected(number: int, digest: str, reasons: list[str]) -> dict[str, Any]:
    lines = "\n".join(f"- {reason}" for reason in reasons)
    text = (
        "**This submission cannot be accepted yet.**\n\n"
        f"{lines}\n\n"
        "Edit the issue to fix this, or comment `/recheck` to have it checked again."
    )
    return _post(number, "rejected", digest, text)


def process(ctx: Context, issue: dict[str, Any], *, force: bool = False, announce: bool = False) -> dict[str, Any] | None:
    """Judges one issue. Returns the post to make (a comment, perhaps closing the issue), or nothing to do."""
    if issue.get("state") != "open":
        return None
    number = int(issue["number"])
    body = issue.get("body") or ""
    form = issue_form.parse(body)
    if not form.structured and not announce:
        return None
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    last = last_marker(ctx.hub.comments(number))
    if last and last[1] == digest and not force and (last[0] != "deferred"):
        return None
    if not form.structured:
        return _rejected(number, digest, ["This issue is not a submission. Use the form of the New issue page to submit a card, a connection or a skin."])

    if form.problems:
        # The shape is not the form's: what was read from it cannot be trusted to say what its author meant.
        return _rejected(number, digest, form.problems)

    user = issue.get("user") or {}
    author_id = int(user.get("id") or 0)
    login = str(user.get("login") or "")
    if not LOGIN.match(login):
        login = "ghost"
    reasons: list[str] = []

    if form.type not in TYPES:
        reasons.append("The type must be Card, Connection or Skin.")
    if form.category not in CATEGORIES:
        reasons.append(f"The category must be one of {', '.join(CATEGORIES.values())}.")
    if not form.licensed:
        reasons.append("Tick the box that says the submission is under the MIT License.")
    if not form.definition.strip():
        reasons.append("The definition is empty.")
    if not describes(form.description):
        reasons.append(DESCRIPTION_SENTENCE)
    based_on = form.based_on.strip()
    if based_on and not (ID.match(based_on) and entries.load_entry(ctx.root, based_on)):
        reasons.append("Based on must be the id of an entry in this workshop, such as 123456/queue-size.")
    update_of = form.update_of.strip()
    if update_of and not ID.match(update_of):
        reasons.append("Update of must be the id of an entry, such as 123456/queue-size.")

    checked: dict[str, Any] = {}
    if form.type in TYPES and form.definition.strip():
        checked = kitcheck.check(
            form.definition,
            form.type,
            {"description": form.description, "changes": form.changes},
            ctx.kit,
        )
        reasons += [_reason(problem) for problem in checked.get("problems", [])]
        reasons += [md(SECRET_IN_DEMO.format(place=place, key=key)) for place, key in demo_secrets(_demo_of(form.definition))]
    if reasons or not checked.get("ok"):
        return _rejected(number, digest, reasons or ["The definition did not pass the check."])

    slug = checked["slug"]
    target_id = update_of or entries.entry_id_of(author_id, slug)
    previous = entries.load_entry(ctx.root, target_id)
    if update_of and previous is None:
        reasons.append(f"There is no entry {update_of} to update.")
    stored = entries.entry_dir(ctx.root, target_id) / definition_file(checked["type"])
    if previous is not None and number in previous.get("issues", []) and stored.is_file() and stored.read_text(encoding="utf-8") == form.definition:
        # Taken in an earlier run whose comment never came out (the files were pushed, the post failed): say it again.
        return _accepted(ctx, number, digest, target_id, previous, updated=len(previous["issues"]) > 1)
    if previous is not None:
        owner = int(previous["author_id"])
        if author_id != owner and author_id not in ctx.maintainers:
            reasons.append("Only the author of an entry or a maintainer can update it.")
        if target_id.split("/", 1)[1] != slug:
            reasons.append(f"The short name of an update stays {target_id.split('/', 1)[1]}.")
        if previous["type"] != checked["type"]:
            reasons.append(f"This entry is a {TYPES[previous['type']].lower()}; an update cannot change that.")
        removed = previous.get("removed")
        if removed and removed.get("level") != "withdrawn":
            reasons.append("This entry was removed by a maintainer. Ask a maintainer to bring it back.")
        if len(form.changes.strip()) < MIN_CHANGES_CHARS:
            reasons.append("An update needs a list of changes.")
        old_version = previous["meta"].get("version") or ""
        if checked.get("version") and old_version and version_tuple(checked["version"]) <= version_tuple(old_version):
            reasons.append(f"The version must be higher than the current {old_version}.")
    if previous is None and len(entries.all_entries(ctx.root)) >= MAX_ENTRIES:
        reasons.append("The workshop is full.")
    if reasons:
        return _rejected(number, digest, reasons)

    if previous is None:
        today = iso(ctx.clock)[:10]
        made = sum(1 for one in entries.all_entries(ctx.root) if int(one["author_id"]) == author_id and str(one["created_at"])[:10] == today)
        if made >= MAX_NEW_PER_DAY:
            if last and last[0] == "deferred" and last[1] == digest:
                return None
            return _post(
                number,
                "deferred",
                digest,
                f"**This submission waits.** An account may add {MAX_NEW_PER_DAY} new entries a day, and today's are used up. "
                "It is checked again in the next daily run; nothing needs to be done.",
            )

    with tempfile.TemporaryDirectory() as folder:
        light, dark = Path(folder) / entries.PREVIEW_LIGHT, Path(folder) / entries.PREVIEW_DARK
        try:
            ctx.pictures(checked, light, dark)
        except renderer.RenderError as failure:
            return _rejected(number, digest, [f"The preview picture could not be drawn from the demo data: {failure}"])
        discussion = None
        if previous is None or not previous.get("discussion"):
            discussion = ctx.hub.create_discussion(
                f"{plain(checked['name'])} ({target_id})",
                f"Discussion of `{target_id}` in the workshop. Add a thumbs up to this post if it works for you.",
            )
        data = entries.write_entry(
            ctx.root,
            entry_id=target_id,
            checked=checked,
            definition=form.definition,
            description=form.description,
            changes=form.changes,
            category=form.category,
            author_id=int(previous["author_id"]) if previous else author_id,
            author_login=login if not previous or author_id == int(previous["author_id"]) else previous["author_login"],
            issue=number,
            based_on=based_on or None,
            now=ctx.clock,
            pictures=(light, dark),
            previous=previous,
            discussion=discussion,
        )
    return _accepted(ctx, number, digest, target_id, data, updated=previous is not None)


def _accepted(ctx: Context, number: int, digest: str, target_id: str, data: dict[str, Any], *, updated: bool) -> dict[str, Any]:
    link = f"https://github.com/{ctx.hub.repo}/tree/main/entries/{target_id}"
    meta = data["meta"]
    lines = [
        f"**Accepted.** `{target_id}` is {'updated' if updated else 'in the workshop now'}.",
        "",
        f"- Version: {meta['version'] or '-'}",
        *([] if data["type"] == "skin" else [f"- Reach: {meta['class']} (read: only reads; buttons: presses buttons; login: signs in)"]),
        f"- Category: {CATEGORIES[data['category']]}",
        f"- Entry: {link}",
    ]
    if data.get("discussion"):
        lines.append(f"- Discussion: {data['discussion']['url']}")
    return _post(number, "accepted", digest, "\n".join(lines), close=True)


def sweep(
    ctx: Context,
    event_issue: int | None = None,
    force: bool = False,
    *,
    since: str | None = None,
    forced: Iterable[int] = (),
) -> list[dict[str, Any]]:
    """Judges the open issues that wait, oldest first, and makes the catalog and the README list again.

    ``since`` limits the run to the issues changed after that moment (and the issue that woke it, and ``forced``);
    without it every open issue is looked at. ``forced`` issues are judged again even if their wording was judged.
    """
    redo = {int(number) for number in forced} | ({event_issue} if force and event_issue is not None else set())
    found = {int(one["number"]): one for one in ctx.hub.open_issues(since)}
    for number in sorted(({event_issue} if event_issue is not None else set()) | redo):
        if number not in found:
            try:
                found[number] = ctx.hub.issue(number)
            except Exception as failure:  # noqa: BLE001 - an issue that cannot be read now is read by the next run
                print(f"issue {number}: {type(failure).__name__}: {failure}", file=sys.stderr)
                ctx.failed.append(number)
    posts = []
    for number in sorted(found):
        speaks = number == event_issue or number in redo
        try:
            post = process(ctx, found[number], force=number in redo, announce=speaks)
        except Exception as failure:  # noqa: BLE001 - one issue that breaks a run must not hold up the others
            print(f"issue {number}: {type(failure).__name__}: {failure}", file=sys.stderr)
            ctx.failed.append(number)
            continue
        if post:
            posts.append(post)
    entries.refresh(ctx.root, ctx.clock)
    return posts
