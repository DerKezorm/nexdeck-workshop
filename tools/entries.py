"""The entries on disk, the catalog and the README list made from them.

``entries/<author id>/<short name>/`` holds ``definition.yaml``, ``README.md``, ``CHANGELOG.md``, ``entry.json`` and the
two pictures. Ownership hangs on the numeric id of the GitHub account, never on the name (KARTEN-13 EC-10). The catalog
and the list in the README are made from these files alone, so they can be made again at any time.
"""

from __future__ import annotations

import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from .common import (
    CATEGORIES,
    ID,
    MAX_ENTRIES,
    clean,
    clean_local,
    iso,
    md,
    plain,
    read_json,
    sha256_of,
    write_json,
    write_text,
)

CATALOG_FORMAT = 1
#: The list of the entries that are examples to start from; only maintainers change it, by a push.
STARTERS = "starters.json"
START = "<!-- entries:start -->"
END = "<!-- entries:end -->"
PREVIEW_LIGHT = "preview-light.png"
PREVIEW_DARK = "preview-dark.png"


def entry_dir(root: Path, entry_id: str) -> Path:
    if not ID.match(entry_id):
        raise ValueError(f"Not an entry id: {entry_id!r}")
    return root / "entries" / entry_id


def entry_id_of(author_id: int, slug: str) -> str:
    return f"{author_id}/{slug}"


def load_entry(root: Path, entry_id: str) -> dict[str, Any] | None:
    path = entry_dir(root, entry_id) / "entry.json"
    return read_json(path) if path.is_file() else None  # type: ignore[no-any-return]


def all_entries(root: Path) -> list[dict[str, Any]]:
    """Every entry.json, with its ``id``, in the order of the ids."""
    found = []
    for path in sorted((root / "entries").glob("*/*/entry.json")):
        data = read_json(path)
        data["id"] = f"{path.parent.parent.name}/{path.parent.name}"
        found.append(data)
    return found


def save_entry(root: Path, entry_id: str, data: dict[str, Any]) -> None:
    write_json(entry_dir(root, entry_id) / "entry.json", {key: value for key, value in data.items() if key != "id"})


def entry_for_issue(root: Path, number: int) -> dict[str, Any] | None:
    """The entry an issue belongs to: the one it was submitted for, an update of it included."""
    return next((one for one in all_entries(root) if number in one.get("issues", [one.get("issue")])), None)


# -- one entry -------------------------------------------------------------------------------------


def _readme(checked: dict[str, Any], data: dict[str, Any], description: str) -> str:
    meta = data["meta"]
    lines = [
        f"# {md(plain(meta['name']))}",
        "",
        md(description),
        "",
        "| | |",
        "|---|---|",
        f"| Type | {'Card' if data['type'] == 'card' else 'Connection'} |",
        f"| Category | {CATEGORIES[data['category']]} |",
        f"| Version | {md(meta['version']) if meta['version'] else '-'} |",
        f"| Author | [{md(data['author_login'])}](https://github.com/{data['author_login']}) |",
        f"| Reach | {meta['class']} |",
        "",
        f"![light]({PREVIEW_LIGHT}) ![dark]({PREVIEW_DARK})",
        "",
        "Submitted under the [MIT License](../../../LICENSE).",
    ]
    return "\n".join(lines)


def _changelog(previous: str, version: str, day: str, changes: str) -> str:
    title = "# Changelog\n"
    body = previous.split("\n", 1)[1].lstrip("\n") if previous.startswith(title) else ""
    heading = f"## {md(version)} ({day})" if version else f"## {day}"
    return f"{title}\n{heading}\n\n{md(changes or 'Initial release.')}\n" + (f"\n{body}" if body else "")


def write_entry(
    root: Path,
    *,
    entry_id: str,
    checked: dict[str, Any],
    definition: str,
    description: str,
    changes: str,
    category: str,
    author_id: int,
    author_login: str,
    issue: int,
    based_on: str | None,
    now: datetime,
    pictures: tuple[Path, Path],
    previous: dict[str, Any] | None,
    discussion: dict[str, str] | None,
) -> dict[str, Any]:
    """Writes the files of an entry, new or updated, and returns its entry.json."""
    target = entry_dir(root, entry_id)
    target.mkdir(parents=True, exist_ok=True)
    stamp = iso(now)
    slug = checked["slug"]
    data: dict[str, Any] = {
        "type": checked["type"],
        "author_id": author_id,
        "author_login": author_login,
        "category": category,
        "based_on": based_on or (previous or {}).get("based_on"),
        "issue": issue,
        "issues": [*((previous or {}).get("issues") or []), issue],
        "created_at": (previous or {}).get("created_at") or stamp,
        "updated_at": stamp,
        "removed": None,
        "thumbs": (previous or {}).get("thumbs", 0),
        "discussion": (previous or {}).get("discussion") or discussion,
        "test": slug.startswith("test-"),
        "meta": {
            "slug": slug,
            "name": clean_local(checked["name"]),
            "description": clean(description) or clean(plain(checked.get("description"))),
            "version": checked.get("version") or "",
            "min_nexdeck": checked["min_nexdeck"],
            "requires": checked.get("requires") or [],
            "class": checked["class"],
            "reads": checked.get("reads") or [],
            "buttons": checked.get("buttons") or [],
        },
    }
    write_text(target / "definition.yaml", definition)
    old_log = (target / "CHANGELOG.md").read_text(encoding="utf-8") if (target / "CHANGELOG.md").is_file() else ""
    write_text(target / "CHANGELOG.md", _changelog(old_log, data["meta"]["version"], stamp[:10], clean(changes)))
    write_text(target / "README.md", _readme(checked, data, data["meta"]["description"]))
    shutil.copyfile(pictures[0], target / PREVIEW_LIGHT)
    shutil.copyfile(pictures[1], target / PREVIEW_DARK)
    save_entry(root, entry_id, data)
    return data


# -- the catalog ------------------------------------------------------------------------------------


def starters(root: Path) -> set[str]:
    """The ids in ``starters.json``: the entries the maintainers hold up as examples to start from (KARTEN-19 AC-4)."""
    path = root / STARTERS
    try:
        found = read_json(path) if path.is_file() else []
    except ValueError:
        return set()
    return {one for one in found if isinstance(one, str) and ID.match(one)} if isinstance(found, list) else set()


def _entry_in_catalog(root: Path, one: dict[str, Any], examples: set[str]) -> dict[str, Any]:
    folder = f"entries/{one['id']}"
    meta = one["meta"]
    return {
        "id": one["id"],
        "type": one["type"],
        "slug": meta["slug"],
        "name": meta["name"],
        "description": meta["description"],
        "author": {"id": one["author_id"], "login": one["author_login"]},
        "version": meta["version"],
        "min_nexdeck": meta["min_nexdeck"],
        "category": one["category"],
        "requires": meta["requires"],
        "class": meta["class"],
        "reads": meta["reads"],
        "buttons": meta["buttons"],
        "sha256": sha256_of(root / folder / "definition.yaml"),
        "files": {
            "definition": f"{folder}/definition.yaml",
            "readme": f"{folder}/README.md",
            "changelog": f"{folder}/CHANGELOG.md",
            "light": f"{folder}/{PREVIEW_LIGHT}",
            "dark": f"{folder}/{PREVIEW_DARK}",
        },
        "thumbs": int(one.get("thumbs") or 0),
        "discussion": (one.get("discussion") or {}).get("url"),
        "based_on": one.get("based_on"),
        "updated_at": one["updated_at"],
        "removed": one.get("removed"),
        "starter": one["id"] in examples,
    }


def build_catalog(root: Path, now: datetime) -> dict[str, Any]:
    examples = starters(root)
    entries = [_entry_in_catalog(root, one, examples) for one in all_entries(root)][:MAX_ENTRIES]
    return {"format": CATALOG_FORMAT, "generated_at": iso(now), "entries": entries}


def write_catalog(root: Path, now: datetime) -> bool:
    """Writes ``catalog.json`` and says whether anything but the time of making changed."""
    path = root / "catalog.json"
    fresh = build_catalog(root, now)
    if path.is_file():
        old = read_json(path)
        if {**old, "generated_at": ""} == {**fresh, "generated_at": ""}:
            return False
    write_json(path, fresh)
    return True


# -- the list in the README --------------------------------------------------------------------------


def _line(one: dict[str, Any]) -> str:
    name = md(plain(one["name"]))
    text = md(one["description"]).replace("  \n", " ")
    first = one["files"]
    kind = "Card" if one["type"] == "card" else "Connection"
    mark = " (test)" if one["id"].split("/")[1].startswith("test-") else ""
    return (
        f"#### [{name}](entries/{one['id']}){mark}\n\n"
        f"{kind}, version {md(one['version']) if one['version'] else '-'}, reach: {one['class']}, "
        f"by [{md(one['author']['login'])}](https://github.com/{one['author']['login']}), {one['thumbs']} thumbs up\n\n"
        f"{text}\n\n"
        f"![Preview, light]({first['light']}#gh-light-mode-only)![Preview, dark]({first['dark']}#gh-dark-mode-only)\n"
    )


def build_list(catalog: dict[str, Any]) -> str:
    live = [one for one in catalog["entries"] if not one["removed"]]
    if not live:
        return "Nothing here yet."
    out: list[str] = []
    for key, label in CATEGORIES.items():
        group = sorted((one for one in live if one["category"] == key), key=lambda one: plain(one["name"]).lower())
        if group:
            out.append(f"### {label}\n\n" + "\n".join(_line(one) for one in group))
    return "\n".join(out)


def write_readme(root: Path, catalog: dict[str, Any]) -> bool:
    path = root / "README.md"
    text = path.read_text(encoding="utf-8")
    found = re.search(re.escape(START) + r".*?" + re.escape(END), text, re.DOTALL)
    if not found:
        raise ValueError("README.md has no list markers.")
    new = text[: found.start()] + f"{START}\n\n{build_list(catalog)}\n\n{END}" + text[found.end() :]
    if new == text:
        return False
    path.write_text(new, encoding="utf-8", newline="\n")
    return True


def refresh(root: Path, now: datetime) -> dict[str, Any]:
    """The catalog and the README list, made again from the entries."""
    write_catalog(root, now)
    catalog = read_json(root / "catalog.json")
    write_readme(root, catalog)
    return catalog  # type: ignore[no-any-return]
