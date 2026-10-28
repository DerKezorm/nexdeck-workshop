"""Runs the kit of nexdeck (``kit/check.py``) on a submission, in a Python of its own.

The text of a stranger is read by the kit's modules in a separate process with no access to this repository's
modules, and with a time limit: a definition that makes the reader slow or break is a reason, not a crash here.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from .common import ROOT

TIMEOUT_SECONDS = 120


def kit_version(kit: Path | None = None) -> dict[str, str]:
    return json.loads(((kit or ROOT / "kit") / "VERSION").read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def check(text: str, kind: str, texts: dict[str, str] | None = None, kit: Path | None = None) -> dict[str, Any]:
    """What ``check.py`` says: ``ok``, ``problems`` and, when the text is good, everything the catalog needs."""
    kit = kit or ROOT / "kit"
    with tempfile.TemporaryDirectory() as folder:
        work = Path(folder)
        source = work / "submission.yaml"
        source.write_text(text, encoding="utf-8", newline="\n")
        command = [sys.executable, "-I", str(kit / "check.py"), str(source), "--type", kind]
        for label, body in (texts or {}).items():
            file = work / f"{label}.txt"
            file.write_text(body, encoding="utf-8", newline="\n")
            command += ["--scan", f"{label}={file}"]
        try:
            done = subprocess.run(command, cwd=work, capture_output=True, text=True, timeout=TIMEOUT_SECONDS, check=False)
        except subprocess.TimeoutExpired:
            return _failed("The check took too long. Make the definition smaller.")
    try:
        found = json.loads(done.stdout)
    except ValueError:
        return _failed("The check could not read this submission.")
    return found  # type: ignore[no-any-return]


def _failed(reason: str) -> dict[str, Any]:
    return {"ok": False, "problems": [{"code": "check_failed", "message": reason, "path": "", "line": None}]}
