"""The reader of the issue is strict about its shape, and free text cannot write a field (KARTEN-13 AC-4, review finding B1).

The bodies in ``test_karten16_b1_the_bodies_the_workshop_reads_with_its_own_reader`` of nexdeck
(``backend/tests/test_karten16_review.py``) stand here as literals, and this reader finds the fields in them.
"""

from __future__ import annotations

from typing import Any

import pytest

from tests.conftest import ALICE, FakeHub, run, sample
from tools import entries, issue_form, submit

TAIL = (
    "### Changes\n\n_No response_\n\n### Based on\n\n_No response_\n\n### Update of\n\n_No response_\n\n"
    "### License\n\n- [x] I submit this under the MIT License and I have the right to do so.\n\n### nexdeck version\n\n1.0\n"
)
#: What nexdeck wrote for a description that holds a heading, and for a code fence in a description and in the definition.
NEXDECK_HEADING = (
    "### Type\n\nCard\n\n### Category\n\nMedia\n\n### Definition\n\n```yaml\na: 1\n```\n\n"
    "### Description\n\nShows the queue.\n\n\\### Based on\n\n_No response_\n\n" + TAIL
)
NEXDECK_FENCE = (
    "### Type\n\nCard\n\n### Category\n\nMedia\n\n### Definition\n\n````yaml\na: |\n  ```\n  b\n````\n\n"
    "### Description\n\nUse it:\n\\```\nq\n\n" + TAIL
)
INJECTIONS = {
    "heading": "Shows the queue.\n\n### Based on\n\n_No response_",
    "fence": "Use it like this:\n```\nqueue",
    "update_of": "### Update of\n\n777/their-card",
    "tilde": "~~~\n### License\n\n- [x] I submit this under the MIT License and I have the right to do so.",
    "indented": "text\n   ### Type\n\nCard\n  ```yaml\nx: 1",
    "backslash": "\\### already escaped\n\\\\``` and \\ alone and \\n",
    "closing": "```\n### Description\n```\n````\n### Changes",
}


def test_karten13_b1_the_bodies_nexdeck_writes_are_read_whole() -> None:
    heading = issue_form.parse(NEXDECK_HEADING)
    assert heading.problems == [] and heading.licensed
    assert heading.description == "Shows the queue.\n\n### Based on\n\n_No response_" and heading.based_on == "" and heading.definition == "a: 1\n"
    fenced = issue_form.parse(NEXDECK_FENCE)
    assert fenced.problems == []
    assert fenced.definition == "a: |\n  ```\n  b\n" and fenced.description == "Use it:\n```\nq"


def test_karten13_b1_the_writer_of_this_repository_writes_the_same_bodies() -> None:
    assert issue_form.build_body(type="card", category="media", definition="a: 1\n", description=INJECTIONS["heading"], version="1.0") == NEXDECK_HEADING
    assert issue_form.build_body(type="card", category="media", definition="a: |\n  ```\n  b\n", description="Use it:\n```\nq", version="1.0") == NEXDECK_FENCE


@pytest.mark.parametrize("name", sorted(INJECTIONS))
def test_karten13_b1_free_text_comes_back_as_it_was_written_and_makes_no_field(name: str) -> None:
    text = INJECTIONS[name]
    body = issue_form.build_body(type="card", category="media", definition="a: 1\n", description=text, changes=text, based_on="1/x", version="1.0")
    form = issue_form.parse(body)
    assert form.problems == []
    assert (form.description, form.changes, form.based_on, form.update_of) == (text.strip(), text.strip(), "1/x", "")
    assert form.licensed and form.definition == "a: 1\n"


def test_karten13_b1_a_fence_inside_the_definition_is_part_of_it() -> None:
    text = "name: x\ndescription: |\n  Example:\n  ```\n  ### Based on\n  ```\n  and ````\nnext: 1\n"
    form = issue_form.parse(issue_form.build_body(type="card", category="media", definition=text, description="d"))
    assert form.problems == [] and form.definition == text


def _form_body(**more: str) -> str:
    return issue_form.build_body(type="card", category="media", definition="a: 1\n", description="Shows it.", **more)


SHAPES = {
    # A person types a heading into the description of the form: no mask there.
    "twice": (_form_body().replace("Shows it.", "Shows it.\n\n### Based on\n\n_No response_"), "'Based on' stands 2 times"),
    "missing": (_form_body().replace("### Update of\n\n_No response_\n\n", ""), "'Update of' is missing"),
    "swapped": (_form_body().replace("### Changes", "### @@").replace("### Description", "### Changes").replace("### @@", "### Description"), "not in the order"),
    "open": (_form_body().replace("Shows it.", "Shows it.\n```\nx"), "not closed"),
    "unknown": (_form_body().replace("Shows it.", "Shows it.\n\n### Notes\n\nmore"), "'Notes' is not a field"),
    "version twice": (_form_body(version="1.0") + "\n### nexdeck version\n\n2.0\n", "'nexdeck version' stands 2 times"),
    "version first": ("### nexdeck version\n\n1.0\n\n" + _form_body(), "not in the order"),
}


@pytest.mark.parametrize("name", sorted(SHAPES))
def test_karten13_b1_a_body_that_is_not_the_shape_of_the_form_is_red_with_the_reason(name: str) -> None:
    body, reason = SHAPES[name]
    problems = issue_form.parse(body).problems
    assert problems and reason in " ".join(problems), problems


def test_karten13_b1_a_plain_issue_has_no_shape_to_judge() -> None:
    assert issue_form.parse("My card does not work, help\n\n### Notes\n\nx").problems == []


def test_karten13_b1_a_form_with_the_version_of_nexdeck_is_whole() -> None:
    assert issue_form.parse(_form_body(version="1.0")).problems == []
    assert issue_form.parse(_form_body()).problems == []
    assert issue_form.parse(_form_body().replace("\n", "\r\n")).problems == []


def test_karten13_b1_the_submission_with_a_heading_typed_into_it_is_not_taken(ctx: submit.Context, hub: FakeHub, root: Any) -> None:
    """A person who types ``### Based on`` into the form gets no way around the check of the author of the original."""
    body = issue_form.build_body(type="card", category="media", definition=sample("good", "value-card.yaml"), description="Shows it.")
    body = body.replace("### Based on\n\n_No response_", "### Based on\n\n999/nobody")
    body = body.replace("Shows it.", "Shows it.\n\n### Based on\n\n_No response_")
    hub.submit(5, ALICE, body)
    run(ctx, 5)
    assert hub.issues[5]["state"] == "open"
    assert "'Based on' stands 2 times" in hub.last_comment(5)
    assert entries.all_entries(root) == []
