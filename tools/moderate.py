"""The commands of the comments, and the removal itself (KARTEN-13 AC-8, EC-5, EC-7).

``/remove harmful|not_useful <reason>``: a maintainer takes an entry out of the shop; it stays in the catalog, marked
removed, with the reason. ``/restore``: a maintainer brings a removed entry back. ``/withdraw``: the author takes his own
entry back (not one a maintainer removed). ``/recheck``: the submission in this issue is judged again. The id of the
person is the one of the comment, never a name written in a comment.

A command is carried out when a run finds it without the mark of the bot, ``<!-- workshop:done:<comment id> -->``, in a
comment of the same issue. The reply of the bot carries that mark. So it does not matter which run was started for a
comment, or that a run was dropped: the next run finds the command still undone and carries it out.
"""

from __future__ import annotations

import re
from typing import Any

from . import entries, submit
from .common import ID, LEVELS, WITHDRAWN_REASON, clean, iso

REMOVE = re.compile(r"^/remove[ \t]+(harmful|not[_ -]useful)[ \t]+(\S.*)$", re.DOTALL)
COMMAND = re.compile(r"^/(remove|withdraw|restore|recheck)(?![A-Za-z0-9_])")
DONE = re.compile(r"<!-- workshop:done:(\d+) -->")


def done_mark(comment_id: int) -> str:
    return f"<!-- workshop:done:{comment_id} -->"


def command_of(comment: dict[str, Any]) -> str | None:
    """The command a comment of a person begins with (``remove``, ``withdraw``, ``restore`` or ``recheck``)."""
    user = comment.get("user") or {}
    if user.get("type") == "Bot" or user.get("login") == submit.BOT:
        return None
    found = COMMAND.match(str(comment.get("body") or "").strip())
    return found.group(1) if found else None


def remove(ctx: submit.Context, entry_id: str, level: str, reason: str) -> str | None:
    """Marks an entry removed. Returns what is wrong, or nothing when it is done."""
    if level not in LEVELS:
        return "The level is harmful or not_useful."
    if not ID.match(entry_id):
        return "That is not an entry id."
    data = entries.load_entry(ctx.root, entry_id)
    if data is None:
        return f"There is no entry {entry_id}."
    reason = clean(reason)[:300]
    if not reason:
        return "A removal needs a reason."
    taken = data.get("removed")
    if level == "withdrawn" and taken and taken.get("level") != "withdrawn":
        # The author cannot undo what a maintainer decided, neither by withdrawing nor by an update afterwards (AC-8).
        return f"A maintainer removed `{entry_id}`; only a maintainer can bring it back."
    data["removed"] = {"level": level, "reason": reason, "at": iso(ctx.clock)}
    entries.save_entry(ctx.root, entry_id, data)
    entries.refresh(ctx.root, ctx.clock)
    return None


def restore(ctx: submit.Context, entry_id: str) -> str | None:
    """Takes a removal back, whatever its level. Returns what is wrong, or nothing when it is done."""
    if not ID.match(entry_id):
        return "That is not an entry id."
    data = entries.load_entry(ctx.root, entry_id)
    if data is None:
        return f"There is no entry {entry_id}."
    if not data.get("removed"):
        return f"`{entry_id}` is not removed."
    data["removed"] = None
    entries.save_entry(ctx.root, entry_id, data)
    entries.refresh(ctx.root, ctx.clock)
    return None


def answer(ctx: submit.Context, issue: dict[str, Any], comment: dict[str, Any]) -> tuple[str | None, bool]:
    """What the bot says to a command: ``(reply, recheck)``. A recheck has no reply of its own: the new verdict is it."""
    body = str(comment.get("body") or "").strip()
    command = command_of(comment)
    number = int(issue["number"])
    sender = int((comment.get("user") or {}).get("id") or 0)
    if command == "recheck":
        allowed = sender == int((issue.get("user") or {}).get("id") or 0) or sender in ctx.maintainers
        return None, allowed
    entry = entries.entry_for_issue(ctx.root, number)
    if command == "remove":
        if sender not in ctx.maintainers:
            return "Only a maintainer can remove an entry.", False
        found = REMOVE.match(body)
        if not found:
            return "Write `/remove harmful <reason>` or `/remove not_useful <reason>`.", False
        if entry is None:
            return "This issue belongs to no entry.", False
        level = found.group(1).replace("-", "_").replace(" ", "_")
        failure = remove(ctx, entry["id"], level, found.group(2))
        return failure or f"**Removed.** `{entry['id']}` stays in the catalog, marked as removed, and cannot be installed any more.", False
    if command == "withdraw":
        if entry is None:
            return "This issue belongs to no entry.", False
        if sender != int(entry["author_id"]):
            return "Only the author of an entry can withdraw it.", False
        failure = remove(ctx, entry["id"], "withdrawn", WITHDRAWN_REASON)
        return failure or f"**Withdrawn.** `{entry['id']}` stays in the catalog, marked as withdrawn by the author.", False
    if command == "restore":
        if sender not in ctx.maintainers:
            return "Only a maintainer can bring an entry back.", False
        if entry is None:
            return "This issue belongs to no entry.", False
        failure = restore(ctx, entry["id"])
        return failure or f"**Restored.** `{entry['id']}` can be installed again.", False
    return None, False


def _number_of(comment: dict[str, Any]) -> int:
    return int(str(comment["issue_url"]).rstrip("/").rsplit("/", 1)[1])


def catch_up(ctx: submit.Context, since: str) -> tuple[list[dict[str, Any]], dict[int, list[int]]]:
    """Carries out the commands written since the moment given that the bot has not marked done, oldest first.

    Returns the replies to post and, for ``/recheck``, ``{issue: [comment ids]}``: the run judges those issues again and
    puts the mark on the verdict.
    """
    asked = [one for one in ctx.hub.comments_since(since) if command_of(one)]
    posts: list[dict[str, Any]] = []
    rechecks: dict[int, list[int]] = {}
    for number in sorted({_number_of(one) for one in asked}):
        try:
            issue = ctx.hub.issue(number)
            if "pull_request" in issue:
                continue
            thread = ctx.hub.comments(number)
            marked = {
                int(found)
                for one in thread
                if (one.get("user") or {}).get("login") == submit.BOT
                for found in DONE.findall(str(one.get("body") or ""))
            }
            candidates = {int(one["id"]) for one in asked if _number_of(one) == number}
            for comment in sorted(thread, key=lambda one: int(one["id"])):
                comment_id = int(comment["id"])
                if comment_id not in candidates or comment_id in marked:
                    continue
                reply, recheck = answer(ctx, issue, comment)
                if recheck:
                    rechecks.setdefault(number, []).append(comment_id)
                elif reply:
                    posts.append({"issue": number, "comment": f"{reply}\n\n{done_mark(comment_id)}", "close": False})
        except Exception as failure:  # noqa: BLE001 - one issue that breaks a run must not hold up the others
            print(f"issue {number}: {type(failure).__name__}: {failure}")
            ctx.failed.append(number)
    return posts, rechecks


def mark_rechecks(posts: list[dict[str, Any]], rechecks: dict[int, list[int]]) -> None:
    """Puts the mark of the commands on the verdicts they asked for; a command that got no verdict gets a reply."""
    for number, ids in rechecks.items():
        marks = "\n".join(done_mark(one) for one in ids)
        verdict = next((post for post in posts if post["issue"] == number), None)
        if verdict:
            verdict["comment"] += f"\n{marks}"
        else:
            posts.append({"issue": number, "comment": f"There is nothing to check in this issue: it is not an open submission.\n\n{marks}", "close": False})
