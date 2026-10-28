"""What a run remembers for the next one: the moment up to which the issues and comments were taken up.

``state.json`` is part of the repository and pushed with the files of the run, so a run that is dropped or fails before
the push leaves it as it was and the next run covers the same ground again.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from .common import iso, read_json, write_json

STATE = "state.json"
#: Clocks of GitHub and of the runner differ a little; the next run reads this much further back.
MARGIN = timedelta(seconds=60)


def load(root: Path) -> dict[str, Any]:
    path = root / STATE
    try:
        data = read_json(path) if path.is_file() else {}
    except ValueError:
        data = {}
    return data if isinstance(data, dict) else {}


def since_of(root: Path) -> str | None:
    """The moment the last complete run began (less the margin), or nothing before the first one."""
    value = load(root).get("since")
    return value if isinstance(value, str) and value else None


def remember(root: Path, began: datetime) -> None:
    write_json(root / STATE, {**load(root), "since": iso(began - MARGIN)})
