"""The thumbs up of the daily run, and the discussion of an entry that has none.

    python -m tools.daily      # the same as python -m tools.work --daily

The thumbs are counted once a day and written into the catalog; nexdeck never asks GitHub for them (KARTEN-13 AC-6).
The rest of the daily run (the submissions that waited for the next day, EC-3, or that no run took up, EC-7) is
``work.py``.
"""

from __future__ import annotations

import sys

from . import entries, submit
from .common import plain


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


def main() -> int:
    from . import work

    return work.main(["--daily"])


if __name__ == "__main__":
    sys.exit(main())
