"""Posts what a run collected: the comments, and the closing of the issues that were accepted.

    python -m tools.publish

Runs after the files of the run are pushed, so that a link in a comment leads to something. The posts wait in
``.outbox.json`` (not part of the repository).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from .common import ROOT
from .hub import GitHub, Hub

OUTBOX = ".outbox.json"


def save_outbox(root: Path, posts: list[dict[str, Any]]) -> None:
    (root / OUTBOX).write_text(json.dumps(posts, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def load_outbox(root: Path) -> list[dict[str, Any]]:
    path = root / OUTBOX
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else []


def publish(root: Path, hub: Hub) -> int:
    posts = load_outbox(root)
    for post in posts:
        hub.post_comment(int(post["issue"]), post["comment"])
        if post.get("close"):
            hub.close_issue(int(post["issue"]))
    (root / OUTBOX).unlink(missing_ok=True)
    return len(posts)


def main() -> int:
    print(f"{publish(ROOT, GitHub())} post(s) made")
    return 0


if __name__ == "__main__":
    sys.exit(main())
