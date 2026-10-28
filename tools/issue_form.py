"""The shape of a submission issue, read and written.

The form ``.github/ISSUE_TEMPLATE/submit.yml`` makes GitHub write the issue as Markdown: one ``### Label`` heading per
field, the value under it, ``_No response_`` for an empty optional field, a fenced block for a field with ``render``,
``- [x]`` for a ticked box. nexdeck makes issues of exactly this shape through the API (:func:`build_body`), so a
submission from nexdeck and one from the form are read by the same code.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .common import CATEGORIES, TYPES

LABELS = {
    "type": "Type",
    "category": "Category",
    "definition": "Definition",
    "description": "Description",
    "changes": "Changes",
    "based_on": "Based on",
    "update_of": "Update of",
    "license": "License",
}
LICENSE_SENTENCE = "I submit this under the MIT License and I have the right to do so."
NO_RESPONSE = "_No response_"
_HEADING = re.compile(r"^### (.+?)[ \t]*$")
_FENCE = re.compile(r"\A```[A-Za-z]*[ \t]*\n(.*?)\n?```[ \t]*\Z", re.DOTALL)
_TICKED = re.compile(r"^\s*- \[[xX]\]", re.MULTILINE)


@dataclass
class Form:
    type: str = ""
    category: str = ""
    definition: str = ""
    description: str = ""
    changes: str = ""
    based_on: str = ""
    update_of: str = ""
    licensed: bool = False
    #: The fields the body had, to tell a form from any other text.
    seen: set[str] = field(default_factory=set)

    @property
    def structured(self) -> bool:
        return bool({"type", "definition"} & self.seen)


def _value(text: str) -> str:
    text = text.strip()
    return "" if text == NO_RESPONSE else text


def _sections(text: str) -> list[tuple[str, str]]:
    """``(label, text)`` for every ``### heading``; a heading inside a fenced block is part of the block."""
    found: list[tuple[str, list[str]]] = []
    fenced = False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            fenced = not fenced
        heading = None if fenced else _HEADING.match(line)
        if heading:
            found.append((heading.group(1).strip(), []))
        elif found:
            found[-1][1].append(line)
    return [(label, "\n".join(lines)) for label, lines in found]


def _named(value: str, names: dict[str, str]) -> str:
    """The key of a dropdown entry, from its key or its label; anything else stays as it was written."""
    lowered = value.strip().lower()
    return next((key for key, label in names.items() if lowered in (key, label.lower())), lowered)


def parse(body: str) -> Form:
    """The fields of an issue body. What is missing is empty; nothing is checked here."""
    by_label = {label: key for key, label in LABELS.items()}
    form = Form()
    for label, raw in _sections((body or "").replace("\r\n", "\n")):
        key = by_label.get(label)
        if key is None or key in form.seen:
            continue
        value = _value(raw)
        form.seen.add(key)
        if key == "license":
            form.licensed = bool(_TICKED.search(value))
        elif key == "definition":
            fenced = _FENCE.match(value)
            form.definition = (fenced.group(1) if fenced else value).strip("\n") + ("\n" if value else "")
        elif key == "type":
            form.type = _named(value, TYPES)
        elif key == "category":
            form.category = _named(value, CATEGORIES)
        else:
            setattr(form, key, value)
    return form


def build_body(
    *,
    type: str,
    category: str,
    definition: str,
    description: str,
    changes: str = "",
    based_on: str = "",
    update_of: str = "",
    licensed: bool = True,
) -> str:
    """The body of an issue the way the form writes it, for a client that makes the issue itself."""
    fenced = "```yaml\n" + definition.rstrip("\n") + "\n```"
    box = f"- [{'x' if licensed else ' '}] {LICENSE_SENTENCE}"
    parts = [
        (LABELS["type"], TYPES[type]),
        (LABELS["category"], CATEGORIES[category]),
        (LABELS["definition"], fenced),
        (LABELS["description"], description or NO_RESPONSE),
        (LABELS["changes"], changes or NO_RESPONSE),
        (LABELS["based_on"], based_on or NO_RESPONSE),
        (LABELS["update_of"], update_of or NO_RESPONSE),
        (LABELS["license"], box),
    ]
    return "\n\n".join(f"### {label}\n\n{value}" for label, value in parts) + "\n"
