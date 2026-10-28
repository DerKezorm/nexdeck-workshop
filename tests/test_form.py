"""The issue form: what it asks, what it says before the submission goes out (KARTEN-13 AC-1, AC-10, AC-12)."""

from __future__ import annotations

from pathlib import Path

import yaml

from tests.conftest import sample
from tools import issue_form
from tools.common import CATEGORIES, ROOT

FORM = yaml.safe_load((ROOT / ".github" / "ISSUE_TEMPLATE" / "submit.yml").read_text(encoding="utf-8"))
FIELDS = {one["id"]: one for one in FORM["body"] if "id" in one}


def test_karten13_ac12_the_form_asks_for_exactly_one_category_of_the_list() -> None:
    category = FIELDS["category"]
    assert category["type"] == "dropdown"
    assert category["validations"]["required"] is True
    assert category["attributes"]["options"] == list(CATEGORIES.values())


def test_karten13_ac10_the_form_says_mit_before_the_submission_goes_out() -> None:
    top = "\n".join(str(one["attributes"].get("value", "")) for one in FORM["body"] if one["type"] == "markdown")
    assert "MIT License" in top
    box = FIELDS["license"]["attributes"]["options"][0]
    assert box["required"] is True and "MIT License" in box["label"]
    assert box["label"] == issue_form.LICENSE_SENTENCE
    assert (ROOT / "LICENSE").read_text(encoding="utf-8").startswith("MIT License")


def test_karten13_the_form_labels_are_the_ones_the_reader_looks_for() -> None:
    labels = {one["id"]: one["attributes"]["label"] for one in FORM["body"] if "id" in one}
    assert labels == {key: issue_form.LABELS[key] for key in labels}
    assert set(labels) == set(issue_form.LABELS)


def test_karten13_blank_issues_are_off() -> None:
    config = yaml.safe_load((ROOT / ".github" / "ISSUE_TEMPLATE" / "config.yml").read_text(encoding="utf-8"))
    assert config["blank_issues_enabled"] is False


def test_karten13_a_body_made_by_a_client_reads_back() -> None:
    text = sample("good", "value-card.yaml")
    body = issue_form.build_body(
        type="card", category="smart_home", definition=text, description="Shows it.", changes="First.", based_on="1/x", update_of="2/y"
    )
    form = issue_form.parse(body)
    assert (form.type, form.category) == ("card", "smart_home")
    assert form.definition == text
    assert (form.description, form.changes, form.based_on, form.update_of) == ("Shows it.", "First.", "1/x", "2/y")
    assert form.licensed and form.structured


def test_karten13_a_body_made_by_github_reads_the_same() -> None:
    body = (
        "### Type\n\nConnection\n\n### Category\n\nSmart home\n\n### Definition\n\n```yaml\nnexdeck: integration\n```\n\n"
        "### Description\n\nA box.\r\n\r\n### Changes\n\n_No response_\n\n### Based on\n\n_No response_\n\n"
        "### Update of\n\n_No response_\n\n### License\n\n- [X] I submit this under the MIT License and I have the right to do so.\n"
    )
    form = issue_form.parse(body)
    assert (form.type, form.category, form.description, form.changes) == ("integration", "smart_home", "A box.", "")
    assert form.definition == "nexdeck: integration\n"
    assert form.licensed


def test_karten13_a_heading_inside_the_definition_is_part_of_the_definition() -> None:
    text = sample("good", "value-card.yaml") + "### Description\n# not a heading\n"
    form = issue_form.parse(issue_form.build_body(type="card", category="media", definition=text, description="Real one."))
    assert form.description == "Real one."
    assert "### Description" in form.definition


def test_karten13_an_unticked_box_and_a_plain_issue() -> None:
    body = issue_form.build_body(type="card", category="media", definition="a: 1", description="x", licensed=False)
    assert issue_form.parse(body).licensed is False
    assert issue_form.parse("My card does not work, help").structured is False


def test_karten13_ac1_the_schemas_of_nexdeck_are_in_the_repository() -> None:
    for name in ("card", "integration"):
        assert Path(ROOT / "schema" / f"{name}.schema.json").is_file()
