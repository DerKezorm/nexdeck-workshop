"""The commands of the comments, and the manual removal (KARTEN-13 AC-8, EC-5).

    python -m tools.moderate            # from a comment (GITHUB_EVENT_PATH holds the event)
    python -m tools.moderate --dispatch # from the manual run: ENTRY, LEVEL and REASON in the environment

``/remove harmful|not_useful <reason>``: a maintainer takes an entry out of the shop; it stays in the catalog, marked
removed, with the reason. ``/withdraw``: the author takes his own entry back (not one a maintainer removed). ``/restore``: a maintainer brings a removed entry back. ``/recheck``: the submission in this issue
is judged again. The id of the person is the one of the event, never a name written in a comment.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

from . import entries, submit
from .common import ID, LEVELS, ROOT, WITHDRAWN_REASON, clean, iso

REMOVE = re.compile(r"^/remove[ \t]+(harmful|not[_ -]useful)[ \t]+(\S.*)$", re.DOTALL)


def _reply(number: int, text: str) -> dict[str, Any]:
    return {"issue": number, "comment": text, "close": False}


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


def handle_comment(ctx: submit.Context, event: dict[str, Any]) -> list[dict[str, Any]]:
    body = str((event.get("comment") or {}).get("body") or "").strip()
    number = int(event["issue"]["number"])
    sender = int(event["comment"]["user"]["id"])
    first = body.split("\n", 1)[0].strip()
    if first.startswith("/recheck"):
        issue = event["issue"]
        allowed = sender == int((issue.get("user") or {}).get("id") or 0) or sender in ctx.maintainers
        return submit.sweep(ctx, number, force=allowed)
    entry = entries.entry_for_issue(ctx.root, number)
    if first.startswith("/remove"):
        if sender not in ctx.maintainers:
            return [_reply(number, "Only a maintainer can remove an entry.")]
        found = REMOVE.match(body)
        if not found:
            return [_reply(number, "Write `/remove harmful <reason>` or `/remove not_useful <reason>`.")]
        if entry is None:
            return [_reply(number, "This issue belongs to no entry.")]
        failure = remove(ctx, entry["id"], found.group(1).replace("-", "_").replace(" ", "_"), found.group(2))
        return [_reply(number, failure or f"**Removed.** `{entry['id']}` stays in the catalog, marked as removed, and cannot be installed any more.")]
    if first.startswith("/withdraw"):
        if entry is None:
            return [_reply(number, "This issue belongs to no entry.")]
        if sender != int(entry["author_id"]):
            return [_reply(number, "Only the author of an entry can withdraw it.")]
        failure = remove(ctx, entry["id"], "withdrawn", WITHDRAWN_REASON)
        return [_reply(number, failure or f"**Withdrawn.** `{entry['id']}` stays in the catalog, marked as withdrawn by the author.")]
    if first.startswith("/restore"):
        if sender not in ctx.maintainers:
            return [_reply(number, "Only a maintainer can bring an entry back.")]
        if entry is None:
            return [_reply(number, "This issue belongs to no entry.")]
        failure = restore(ctx, entry["id"])
        return [_reply(number, failure or f"**Restored.** `{entry['id']}` can be installed again.")]
    return []


def handle_dispatch(ctx: submit.Context, event: dict[str, Any], entry_id: str, level: str, reason: str) -> str:
    sender = int((event.get("sender") or {}).get("id") or 0)
    if sender not in ctx.maintainers:
        return "Only a maintainer can remove an entry."
    return remove(ctx, entry_id, level, reason) or f"Removed {entry_id}."


def main(argv: list[str] | None = None) -> int:
    from .hub import GitHub
    from .publish import save_outbox

    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8"))
    ctx = submit.Context(ROOT, GitHub())
    if "--dispatch" in (argv if argv is not None else sys.argv[1:]):
        message = handle_dispatch(ctx, event, os.environ["ENTRY"], os.environ["LEVEL"], os.environ["REASON"])
        print(message)
        return 0 if message.startswith("Removed") else 1
    posts = handle_comment(ctx, event)
    save_outbox(ROOT, posts)
    print(f"{len(posts)} comment(s) to post")
    return 0


if __name__ == "__main__":
    sys.exit(main())
