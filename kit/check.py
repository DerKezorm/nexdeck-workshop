"""Checks one file of the workshop the way nexdeck does when a person saves it.

    python check.py FILE [--type card|integration|skin] [--scan LABEL=FILE ...]

``--scan`` reads a plain text of the submission (its description, its list of changes) and reports a key or a token in it.

Prints one JSON object on standard output. ``ok`` is false when anything is wrong; ``problems`` then lists every
reason, each with the place in the file. The exit code is 0 when ``ok``, 1 when not.
"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from nexdeck_kit import __version__  # noqa: E402
from nexdeck_kit.adapters.custom import present  # noqa: E402
from nexdeck_kit.adapters.base import AdapterError  # noqa: E402
from nexdeck_kit.adapters.rawread import refuse_a_command  # noqa: E402
from nexdeck_kit.cards import credentials, integration, load, pipeline, schema  # noqa: E402
from nexdeck_kit.cards import integration_schema as isch  # noqa: E402

from nexdeck_kit.skins import compile as skin_compile  # noqa: E402
from nexdeck_kit.skins import css as skin_css  # noqa: E402
from nexdeck_kit.skins import schema as skin_schema  # noqa: E402
from pydantic import ValidationError  # noqa: E402

from types import SimpleNamespace  # noqa: E402

#: The longest skin file nexdeck takes, and the names of the skins it ships, which no other skin may take.
SKIN_MAX = 200000
SHIPPED_SKINS = ['1984']

_CARD = re.compile(r"^nexdeck-card[ \t]*:", re.MULTILINE)
_INTEGRATION = re.compile(r"^nexdeck[ \t]*:[ \t]*[\"']?integration[\"']?[ \t]*(#.*)?$", re.MULTILINE)


def plain(text):
    """A text of the author as one string, English first."""
    if isinstance(text, dict):
        return str(text.get("en") or next(iter(text.values()), ""))
    return "" if text is None else str(text)


def problem(code, message, path="", line=None):
    return {"code": code, "message": message, "path": path, "line": line}


def is_skin(text):
    try:
        data = json.loads(text)
    except ValueError:
        return False
    return isinstance(data, dict) and data.get("nexdeck_skin") == 1


def kind_of(text):
    if is_skin(text):
        return "skin"
    if _CARD.search(text):
        return "card"
    if _INTEGRATION.search(text):
        return "integration"
    return None


def inspect(text, wanted=None):
    out = {"ok": False, "kit": __version__, "type": None, "problems": []}
    found = kind_of(text)
    names = {"card": "a card", "integration": "a connection", "skin": "a skin"}
    if found == "skin":
        if wanted and wanted != found:
            out["problems"].append(problem("type_mismatch", f"The submission says it is {names[wanted]}, the text is a skin."))
            return out
        out["type"] = found
        _skin(text, out)
        out["ok"] = not out["problems"]
        return out
    if len(text) > schema.MAX_DEFINITION:
        out["problems"].append(problem("too_long", f"The definition is {len(text)} characters long, the limit is {schema.MAX_DEFINITION}."))
        return out
    if re.search(r"^---[ \t\r]*$", text, re.MULTILINE):
        out["problems"].append(problem("one_document", "A submission is one card or one connection, as a single YAML document."))
        return out
    if found is None:
        out["problems"].append(problem("unknown_type", "The text is neither a card (nexdeck-card: 1), a connection (nexdeck: integration) nor a skin (\"nexdeck_skin\": 1)."))
        return out
    if wanted and wanted != found:
        out["problems"].append(problem("type_mismatch", f"The submission says it is {names[wanted]}, the text is {names[found]}."))
        return out
    out["type"] = found
    try:
        if found == "card":
            _card(text, out)
        else:
            _integration(text, out)
    except load.CardInvalid as failure:
        out["problems"] += [problem(p.code, p.message, p.path, p.line) for p in failure.problems]
    out["ok"] = not out["problems"]
    return out


def _card(text, out):
    loaded = load.load_definition(text, running_version=__version__)
    definition = loaded.definition
    extra = [problem(p.code, p.message, p.path, p.line) for p in load.check_for_submission(definition)]
    for index, request in enumerate(definition.requests):
        try:
            refuse_a_command(SimpleNamespace(raw_read_commands=None), request.path)
        except AdapterError as failure:
            extra.append(problem("command_refused", failure.message, f"requests[{index}].path", loaded.lines.get(("requests", index, "path"))))
    out.update(
        slug=definition.slug,
        name=definition.name,
        description=definition.description or "",
        version=definition.version,
        min_nexdeck=definition.min_nexdeck or __version__,
        form=definition.form,
        size=[definition.size.w, definition.size.h] if definition.size else None,
        min_size=[definition.min_size.w, definition.min_size.h] if definition.min_size else None,
        requires=list(definition.requires),
        reads=[{"kind": definition.requires[0], "path": request.path} for request in definition.requests],
        buttons=[{"label": plain(one.label), "method": one.method, "path": one.path} for one in definition.buttons],
    )
    out["class"] = "buttons" if definition.buttons else "read"
    if extra:
        out["problems"] += extra
        return
    try:
        answers = pipeline.demo_answers(definition)
        result = pipeline.run(definition, answers or {}, budget_ms=1000)
        out["widget_data"] = present(definition, result, pictures=False).model_dump(mode="json")
    except AdapterError as failure:
        out["problems"].append(problem("demo_failed", f"The demo data do not work with this card: {failure.message}", "demo"))
    except Exception as failure:  # noqa: BLE001 - a demo that breaks the pipeline is a reason, not a crash
        out["problems"].append(problem("demo_failed", f"The demo data do not work with this card: {type(failure).__name__}.", "demo"))


def _skin(text, out):
    """A skin is read and compiled as nexdeck does when it is saved; what is compiled is what the pictures wear."""
    if len(text) > SKIN_MAX:
        out["problems"].append(problem("too_long", f"The skin is {len(text)} characters long, the limit is {SKIN_MAX}."))
        return
    try:
        skin = skin_schema.SkinFile.model_validate(json.loads(text))
    except ValidationError as failure:
        out["problems"] += [problem("bad_skin", error["msg"], ".".join(str(step) for step in error["loc"])) for error in failure.errors()]
        return
    out.update(
        slug=skin.key, name=skin.name, description=skin.description, version=skin.version, min_nexdeck=__version__,
        requires=[], reads=[], buttons=[],
    )
    # A skin reads nothing and presses nothing: it reaches no further than any other.
    out["class"] = "read"
    if skin.key in SHIPPED_SKINS:
        out["problems"].append(problem("taken", f"{skin.key} is the name of a skin nexdeck ships; give yours another.", "key"))
        return
    try:
        out["compiled"] = skin_compile.compile_skin(skin).as_json()
    except skin_css.SkinCssError as failure:
        out["problems"] += [problem("bad_css", one.message, "css", one.line) for one in failure.problems]


def _integration(text, out):
    loaded = integration.load_integration(text)
    definition = loaded.definition
    out.update(
        slug=definition.short,
        name=definition.name,
        description=definition.description,
        version="",
        min_nexdeck=__version__,
        requires=[],
        reads=[{"kind": "custom:" + definition.short, "path": one.path} for one in definition.reads],
        buttons=[],
        read_labels=[one.label for one in definition.reads],
        category_hint=definition.category,
    )
    out["class"] = "login" if definition.auth.type == "session" else "read"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file")
    parser.add_argument("--type", choices=("card", "integration", "skin"))
    parser.add_argument("--scan", action="append", default=[], metavar="LABEL=FILE")
    arguments = parser.parse_args()
    text = Path(arguments.file).read_text(encoding="utf-8")
    result = inspect(text, arguments.type)
    for item in arguments.scan:
        label, _, name = item.partition("=")
        found = credentials._value(Path(name).read_text(encoding="utf-8"), structure=False)
        if found:
            result["problems"].append(problem("secret_in_text", f"The {label} looks like it holds {credentials.PHRASES[found]}. Take it out.", label))
            result["ok"] = False
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
