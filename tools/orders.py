"""The manual removals (``moderate`` run by hand), kept as files until a run has carried them out.

    python -m tools.orders --record    # in the workflow: ENTRY, LEVEL, REASON, SENDER and RUN in the environment

GitHub drops a waiting run when a newer one arrives in the same group. A manual removal is only inputs of such a run, so
it would be lost with it. The first job of the workflow therefore writes the inputs into ``orders/`` (its own group,
never dropped) and pushes; every run of every action begins by carrying out the orders that lie there (KARTEN-13 AC-8).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from . import moderate, submit
from .common import ID, ROOT, maintainers, read_json, write_json

ORDERS = "orders"
#: Who may ask for a removal by hand, and what.
MANUAL = ("harmful", "not_useful")


def record(root: Path, *, run: str, entry: str, level: str, reason: str, sender: int) -> str | None:
    """Writes an order. Returns what is wrong, or nothing when it is written."""
    if not run.replace("-", "").isdigit():
        return "That is not a run."
    if sender not in maintainers(root):
        return "Only a maintainer can remove an entry."
    if level not in MANUAL:
        return "The level is harmful or not_useful."
    if not ID.match(entry):
        return "That is not an entry id."
    write_json(root / ORDERS / f"{run}.json", {"entry": entry, "level": level, "reason": reason, "sender": sender})
    return None


def apply(ctx: submit.Context) -> list[str]:
    """Carries out every order and deletes its file. Returns what was done or refused, one line each."""
    folder = ctx.root / ORDERS
    said: list[str] = []
    for path in sorted(folder.glob("*.json")) if folder.is_dir() else []:
        try:
            order: Any = read_json(path)
            entry, level, reason, sender = str(order["entry"]), str(order["level"]), str(order["reason"]), int(order["sender"])
        except (ValueError, KeyError, TypeError, OSError):
            said.append(f"{path.name}: not an order, deleted.")
            path.unlink(missing_ok=True)
            continue
        if sender not in ctx.maintainers or level not in MANUAL:
            said.append(f"{path.name}: refused.")
        else:
            said.append(f"{path.name}: " + (moderate.remove(ctx, entry, level, reason) or f"removed {entry}."))
        path.unlink(missing_ok=True)
    return said


def main() -> int:
    failure = record(
        ROOT,
        run=f"{os.environ['RUN']}-{os.environ['ATTEMPT']}",
        entry=os.environ["ENTRY"].strip(),
        level=os.environ["LEVEL"].strip(),
        reason=os.environ["REASON"],
        sender=int(os.environ["SENDER"]),
    )
    print(failure or "Order written.")
    return 1 if failure else 0


if __name__ == "__main__":
    sys.exit(main())
