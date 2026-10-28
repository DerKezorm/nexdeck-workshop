"""The daily run: counts the thumbs up, gives an entry without a discussion one, and takes up what waits.

    python -m tools.daily

The thumbs are counted once a day and written into the catalog; nexdeck never asks GitHub for them (KARTEN-13 AC-6).
Submissions that waited for the next day (EC-3) or that no run took up (EC-7) are judged by the same sweep every
submission goes through.
"""

from __future__ import annotations

import sys

from . import entries, submit
from .common import ROOT, plain
from .hub import GitHub


def count_thumbs(ctx: submit.Context) -> int:
    """Updates ``thumbs`` of every entry that has a discussion; makes one for an entry that has none. Returns the entries changed."""
    changed = 0
    for one in entries.all_entries(ctx.root):
        entry_id = one["id"]
        if not one.get("discussion"):
            if one.get("removed"):
                continue
            made = ctx.hub.create_discussion(
                f"{plain(one['meta']['name'])} ({entry_id})",
                f"Discussion of `{entry_id}` in the workshop. Add a thumbs up to this post if it works for you.",
            )
            if made:
                one["discussion"], changed = made, changed + 1
                entries.save_entry(ctx.root, entry_id, one)
            continue
        count = ctx.hub.thumbs(one["discussion"]["id"])
        if count is not None and count != one.get("thumbs"):
            one["thumbs"], changed = count, changed + 1
            entries.save_entry(ctx.root, entry_id, one)
    return changed


def run(ctx: submit.Context) -> list[dict]:  # type: ignore[type-arg]
    count_thumbs(ctx)
    return submit.sweep(ctx)


def main() -> int:
    from .publish import save_outbox

    posts = run(submit.Context(ROOT, GitHub()))
    save_outbox(ROOT, posts)
    print(f"{len(posts)} comment(s) to post")
    return 0


if __name__ == "__main__":
    sys.exit(main())
