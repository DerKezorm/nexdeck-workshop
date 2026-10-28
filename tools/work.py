"""One run of the workshop: takes up what is there, whatever woke it.

    python -m tools.work [--issue N] [--force] [--daily]

A run works from the state of the repository, never from the one event that started it (KARTEN-13 EC-7, EC-9): GitHub
keeps only one waiting run per group and drops the others, so what a dropped run was for must be found by the next one.
The issue that woke the run (``--issue``) is looked at in any case. The daily run (``--daily``) looks at everything.
"""

from __future__ import annotations

import argparse
import sys
from datetime import timedelta
from typing import Any

from . import daily, moderate, orders, state, submit
from .common import ROOT, iso

#: The daily run looks this far back for commands nobody carried out.
COMMAND_LOOKBACK = timedelta(days=2)
#: ... and the first run, which has no moment to start from, looks this far back.
FIRST_LOOKBACK = timedelta(hours=1)


def run(ctx: submit.Context, *, issue: int | None = None, force: bool = False, daily_run: bool = False) -> list[dict[str, Any]]:
    """Does what is to do. Returns the comments to post (and issues to close) once the files are pushed."""
    ctx.failed.clear()
    for line in orders.apply(ctx):
        print(line)
    began = state.since_of(ctx.root)
    since = None if daily_run else began
    # Commands are looked for from the last moment that was complete (an hour back when there is none yet, two days back in the daily run).
    asked_since = began or iso(ctx.clock - FIRST_LOOKBACK)
    if daily_run:
        asked_since = min(asked_since, iso(ctx.clock - COMMAND_LOOKBACK))
    replies, rechecks = moderate.catch_up(ctx, asked_since)
    if daily_run:
        daily.count_thumbs(ctx)
    posts = submit.sweep(ctx, issue, force, since=since, forced=rechecks)
    moderate.mark_rechecks(posts, rechecks)
    if not ctx.failed:
        state.remember(ctx.root, ctx.clock)
    return replies + posts


def main(argv: list[str] | None = None) -> int:
    from .hub import GitHub
    from .publish import save_outbox

    parser = argparse.ArgumentParser()
    parser.add_argument("--issue", type=int, help="The issue that woke this run.")
    parser.add_argument("--force", action="store_true", help="Judge that issue again even if its wording was judged.")
    parser.add_argument("--daily", action="store_true", help="The daily run: look at everything, count the thumbs up.")
    arguments = parser.parse_args(argv)
    posts = run(submit.Context(ROOT, GitHub()), issue=arguments.issue, force=arguments.force, daily_run=arguments.daily)
    save_outbox(ROOT, posts)
    print(f"{len(posts)} comment(s) to post")
    return 0


if __name__ == "__main__":
    sys.exit(main())
