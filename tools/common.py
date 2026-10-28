"""What every tool of the workshop shares: the lists the form and the catalog agree on, and small helpers."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent

#: The feature list of the form and of the catalog: one category per entry, from this list (KARTEN-13 AC-12).
CATEGORIES = {
    "media": "Media",
    "downloads": "Downloads",
    "network": "Network",
    "server": "Server",
    "smart_home": "Smart home",
    "other": "Other",
}
TYPES = {"card": "Card", "integration": "Connection"}

#: More new entries than this from one account on one day wait for the next day (KARTEN-13 EC-3).
MAX_NEW_PER_DAY = 10
#: The catalog holds at most this many entries.
MAX_ENTRIES = 5_000
#: The level words of a removal, and the reason the author's own withdrawal gets (KARTEN-13 AC-8, EC-5).
LEVELS = ("harmful", "not_useful", "withdrawn")
WITHDRAWN_REASON = "withdrawn by the author"

#: The discussion category the thumbs are counted in; the first one of these that exists is used.
DISCUSSION_CATEGORIES = ("Cards", "Show and tell", "General")

ID = re.compile(r"^(\d{1,12})/([a-z0-9][a-z0-9_-]{0,59})\Z")
CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def iso(moment: datetime) -> str:
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8", newline="\n")


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def clean(text: str) -> str:
    """Text as the repository keeps it: no control characters, line ends as \\n, no space at the edges."""
    return CONTROL.sub("", text.replace("\r\n", "\n").replace("\r", "\n")).strip()


def clean_local(value: Any) -> Any:
    """A text of the author, or one text per language, as plain text."""
    if isinstance(value, dict):
        return {str(key): clean(str(text)) for key, text in value.items()}
    return clean("" if value is None else str(value))


def plain(value: Any) -> str:
    """A text of the author as one string, English first."""
    if isinstance(value, dict):
        return str(value.get("en") or next(iter(value.values()), ""))
    return "" if value is None else str(value)


_MARKDOWN = re.compile(r"([\\`*_{}\[\]()#+!|<>~&])")


#: Zero-width space: breaks a word GitHub would turn into a link or a mention without changing how the text reads.
BREAK = "​"
_WWW = re.compile(r"(www)\.", re.IGNORECASE)
_GH = re.compile(r"(GH-)", re.IGNORECASE)


def md(text: str) -> str:
    """Text of somebody else for a Markdown page: every sign that means something there is written as itself.

    ⚠️ A description is plain text everywhere it is shown (KARTEN-13 EC-8). HTML, a script and a picture from another
    place come out as the characters they are made of; the only pictures on a page are the ones the action drew.
    GitHub also makes links out of plain words (an address, ``www.``, an at sign with a name, ``#12``), which no escape
    sign stops, so those get a zero-width space inside: still readable, no link or mention any more.
    """
    out = _MARKDOWN.sub(r"\\\1", clean(text))
    out = _WWW.sub(r"\1" + BREAK + ".", out)
    out = _GH.sub(r"\1" + BREAK, out)
    out = out.replace("://", ":" + BREAK + "//").replace("@", "@" + BREAK).replace("\\#", "\\#" + BREAK)
    return out.replace("\n", "  \n")


def version_tuple(text: str) -> tuple[int, ...]:
    parts = [int(part) for part in str(text).split(".") if part.isdigit()][:3]
    return (*parts, *([0] * (3 - len(parts))))


def maintainers(root: Path = ROOT) -> set[int]:
    """The GitHub user ids in ``MAINTAINERS`` (one per line, ``#`` starts a comment)."""
    path = root / "MAINTAINERS"
    if not path.exists():
        return set()
    found: set[int] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        word = line.split("#", 1)[0].strip()
        if word.isdigit():
            found.add(int(word))
    return found
