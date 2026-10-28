"""The shape of a submission issue, read and written.

The form ``.github/ISSUE_TEMPLATE/submit.yml`` makes GitHub write the issue as Markdown: one ``### Label`` heading per
field, the value under it, ``_No response_`` for an empty optional field, a fenced block for a field with ``render``,
``- [x]`` for a ticked box. nexdeck makes issues of exactly this shape through the API (:func:`build_body`), so a
submission from nexdeck and one from the form are read by the same code.

⚠️ The reader is strict about the shape (:func:`parse`, ``Form.problems``): the known headings stand exactly once and in
the order of the form, and no code block is left open. A person who types ``### Based on`` into a free text field of the
form, or a client that forgot to mask it, gets a red answer with the reason and not a submission that says something other
than what its author meant. A client writes free text with :func:`mask` (a line that starts with ``#``, a backtick or a
tilde gets a backslash), and the reader takes it away again.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .common import CATEGORIES, TYPES, md

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
#: The one heading after these that nexdeck adds (the version it was written by); the form does not have it.
VERSION_LABEL = "nexdeck version"
LICENSE_SENTENCE = "I submit this under the MIT License and I have the right to do so."
NO_RESPONSE = "_No response_"
_HEADING = re.compile(r"^### (.+?)[ \t]*$")
_OPEN = re.compile(r"^(`{3,}|~{3,})(.*)$")
_TICKED = re.compile(r"^\s*- \[[xX]\]", re.MULTILINE)
_EDGE = ("#", "`", "~")


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
    #: What is wrong with the shape of the body (a heading twice, missing, out of order; a code block left open).
    problems: list[str] = field(default_factory=list)

    @property
    def structured(self) -> bool:
        return bool({"type", "definition"} & self.seen)


def mask(text: str) -> str:
    """A text of the author for one field: no line of it can be read as a heading or as the edge of a code block."""
    out = []
    for line in text.replace("\r\n", "\n").split("\n"):
        bare = line.lstrip()
        if bare[:1] in _EDGE or (bare[:1] == "\\" and bare[1:2] in (*_EDGE, "\\")):
            line = line[: len(line) - len(bare)] + "\\" + bare
        out.append(line)
    return "\n".join(out)


def unmask(text: str) -> str:
    """What :func:`mask` made of a text, as the author wrote it."""
    out = []
    for line in text.split("\n"):
        bare = line.lstrip()
        if bare[:1] == "\\" and bare[1:2] in (*_EDGE, "\\"):
            line = line[: len(line) - len(bare)] + bare[1:]
        out.append(line)
    return "\n".join(out)


def fence_of(text: str) -> str:
    """A code fence longer than any run of backticks in the text, so that nothing inside it can close it."""
    longest = max((len(run) for run in re.findall(r"`+", text)), default=0)
    return "`" * max(3, longest + 1)


def _value(text: str) -> str:
    text = text.strip()
    return "" if text == NO_RESPONSE else text


def _opens(line: str) -> tuple[str, int] | None:
    """``(sign, length)`` when the line opens a code block (three or more backticks or tildes)."""
    found = _OPEN.match(line.lstrip())
    if found is None or (found.group(1)[0] == "`" and "`" in found.group(2)):
        return None
    return found.group(1)[0], len(found.group(1))


def _closes(line: str, fence: tuple[str, int]) -> bool:
    """A line of nothing but the sign of the fence, at least as many as opened it."""
    bare = line.strip()
    return len(bare) >= fence[1] and set(bare) == {fence[0]}


def _sections(text: str) -> tuple[list[tuple[str, str]], bool]:
    """``(label, text)`` for every ``### heading``, and whether a code block was left open.

    A heading inside a fenced block is part of the block; a block ends with a line of at least as many of its sign as opened it.
    """
    found: list[tuple[str, list[str]]] = []
    fence: tuple[str, int] | None = None
    for line in text.split("\n"):
        heading = None
        if fence is None:
            fence = _opens(line)
            heading = None if fence else _HEADING.match(line)
        elif _closes(line, fence):
            fence = None
        if heading:
            found.append((heading.group(1).strip(), []))
        elif found:
            found[-1][1].append(line)
    return [(label, "\n".join(lines)) for label, lines in found], fence is not None


def _unfence(value: str) -> str:
    """The text inside the block that fills the whole field; any other text as it is."""
    lines = value.split("\n")
    fence = _opens(lines[0]) if len(lines) >= 2 else None
    if fence and _closes(lines[-1], fence):
        return "\n".join(lines[1:-1])
    return value


def _named(value: str, names: dict[str, str]) -> str:
    """The key of a dropdown entry, from its key or its label; anything else stays as it was written."""
    lowered = value.strip().lower()
    return next((key for key, label in names.items() if lowered in (key, label.lower())), lowered)


def _shape(labels: list[str], open_block: bool) -> list[str]:
    """Why the known headings are not exactly those of the form: once each, in its order, and no block left open."""
    known = list(LABELS.values())
    seen = [label for label in labels if label in known or label == VERSION_LABEL]
    problems = [
        f"The heading '{md(label[:60])}' is not a field of the form, and what stands under it would be lost. Write the line without ### in front."
        for label in dict.fromkeys(labels)
        if label not in known and label != VERSION_LABEL
    ][:5]
    for label in [*known, VERSION_LABEL]:
        if seen.count(label) > 1:
            problems.append(
                f"The heading '{label}' stands {seen.count(label)} times. Each field of the form stands once; "
                "a line that starts with ### in a text field is read as a new field."
            )
    problems += [f"The heading '{label}' is missing. Use the form of the New issue page, or nexdeck, and keep its headings." for label in known if label not in seen]
    if not problems and seen != [*known, *([VERSION_LABEL] if VERSION_LABEL in seen else [])]:
        problems.append("The headings are not in the order of the form: " + ", ".join(known) + ". Keep them as they were.")
    if open_block:
        problems.append("A code block (three backticks or tildes) is not closed. Close it, or write the lines without the fence.")
    return problems


def parse(body: str) -> Form:
    """The fields of an issue body. What is missing is empty; ``problems`` says what is wrong with its shape."""
    by_label = {label: key for key, label in LABELS.items()}
    form = Form()
    sections, open_block = _sections((body or "").replace("\r\n", "\n"))
    for label, raw in sections:
        key = by_label.get(label)
        if key is None or key in form.seen:
            continue
        value = _value(raw)
        form.seen.add(key)
        if key == "license":
            form.licensed = bool(_TICKED.search(value))
        elif key == "definition":
            form.definition = _unfence(value).strip("\n") + ("\n" if value else "")
        elif key == "type":
            form.type = _named(value, TYPES)
        elif key == "category":
            form.category = _named(value, CATEGORIES)
        else:
            setattr(form, key, unmask(value))
    if form.structured:
        form.problems = _shape([label for label, _text in sections], open_block)
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
    version: str = "",
) -> str:
    """The body of an issue the way the form writes it, for a client that makes the issue itself (with ``version``: nexdeck's)."""
    fence = fence_of(definition)
    fenced = f"{fence}yaml\n" + definition.rstrip("\n") + f"\n{fence}"
    box = f"- [{'x' if licensed else ' '}] {LICENSE_SENTENCE}"
    parts = [
        (LABELS["type"], TYPES[type]),
        (LABELS["category"], CATEGORIES[category]),
        (LABELS["definition"], fenced),
        (LABELS["description"], mask(description) if description.strip() else NO_RESPONSE),
        (LABELS["changes"], mask(changes) if changes.strip() else NO_RESPONSE),
        (LABELS["based_on"], mask(based_on) if based_on.strip() else NO_RESPONSE),
        (LABELS["update_of"], mask(update_of) if update_of.strip() else NO_RESPONSE),
        (LABELS["license"], box),
    ]
    if version:
        parts.append((VERSION_LABEL, version))
    return "\n\n".join(f"### {label}\n\n{value}" for label, value in parts) + "\n"
