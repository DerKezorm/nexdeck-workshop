"""The workflows as files: what wakes them, what they may do, and that no text of a stranger reaches a shell."""

from __future__ import annotations

from typing import Any

import pytest
import yaml

from tools.common import ROOT

NAMES = ("submit", "daily", "moderate", "test")


def _load(name: str) -> dict[str, Any]:
    flow = yaml.safe_load((ROOT / ".github" / "workflows" / f"{name}.yml").read_text(encoding="utf-8"))
    flow["on"] = flow.pop(True, flow.get("on"))  # YAML reads a bare ``on`` as true
    return flow  # type: ignore[no-any-return]


@pytest.mark.parametrize("name", NAMES)
def test_karten13_workflows_are_plain_yaml_with_a_job(name: str) -> None:
    flow = _load(name)
    assert flow["name"] == name and flow["jobs"]


def _writer(name: str) -> dict[str, Any]:
    """The concurrency of the job that writes: the whole workflow's, or the job's own."""
    flow = _load(name)
    jobs = [job for job in flow["jobs"].values() if job.get("concurrency", {}).get("group") == "workshop-write"]
    return flow["concurrency"] if "concurrency" in flow else jobs[0]["concurrency"]  # type: ignore[no-any-return]


def test_karten13_ec9_the_actions_that_write_go_one_after_the_other_and_none_is_cancelled() -> None:
    for name in ("submit", "daily", "moderate"):
        assert _writer(name) == {"group": "workshop-write", "cancel-in-progress": False}, name


def test_karten13_b3_a_manual_removal_is_written_down_by_a_job_that_is_never_dropped() -> None:
    """Inputs are no state: the job that records them has a group of its own per run, and the writer waits for it."""
    jobs = _load("moderate")["jobs"]
    group = jobs["record"]["concurrency"]["group"]
    assert "github.run_id" in group and group != "workshop-write" and jobs["record"]["concurrency"]["cancel-in-progress"] is False
    assert jobs["moderate"]["needs"] == ["record"] and "!cancelled()" in jobs["moderate"]["if"]
    runs = " ".join(step.get("run", "") for step in jobs["record"]["steps"])
    assert "tools.orders" in runs and "push.sh" in runs


def test_karten13_the_triggers() -> None:
    assert _load("submit")["on"] == {"issues": {"types": ["opened", "edited"]}}
    assert "schedule" in _load("daily")["on"] and "workflow_dispatch" in _load("daily")["on"]
    moderate = _load("moderate")["on"]
    assert moderate["issue_comment"] == {"types": ["created"]} and moderate["workflow_dispatch"]["inputs"]["level"]["options"] == ["harmful", "not_useful"]
    assert "push" in _load("test")["on"]


def test_karten13_the_test_workflow_only_reads() -> None:
    assert _load("test")["permissions"] == {"contents": "read"}


def test_karten13_no_text_of_a_stranger_goes_into_a_command() -> None:
    """Titles, bodies and comments are read by the Python tools through the API, never pasted into a shell line."""
    for name in NAMES:
        for job in _load(name)["jobs"].values():
            for step in job["steps"]:
                if "run" in step:
                    for word in ("issue.title", "issue.body", "comment.body", "head_ref"):
                        assert word not in step["run"], (name, step)


def test_karten13_the_commands_of_the_comments_are_only_taken_from_people() -> None:
    condition = _load("moderate")["jobs"]["moderate"]["if"]
    assert "user.type != 'Bot'" in condition
    for command in ("/remove", "/withdraw", "/restore", "/recheck"):
        assert f"startsWith(github.event.comment.body, '{command}')" in condition


def test_karten13_b3_every_write_action_runs_the_same_work_from_the_state() -> None:
    """Submissions and the daily run take up everything that is open (the run that woke them may have been dropped)."""
    for name, command in (("submit", "python -m tools.work --issue"), ("daily", "python -m tools.work --daily")):
        steps = [step.get("run", "") for step in _load(name)["jobs"][name]["steps"]]
        assert any(step.startswith(command) for step in steps), name
