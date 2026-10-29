"""The script that pushes what a run made (``push.sh``), against a repository on this machine."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from tools.common import ROOT

BASH = shutil.which("bash")
pytestmark = pytest.mark.skipif(BASH is None, reason="needs bash")


def _git(folder: Path, *arguments: str) -> str:
    done = subprocess.run(["git", *arguments], cwd=folder, capture_output=True, text=True, check=True)
    return done.stdout.strip()


@pytest.fixture
def clone(tmp_path: Path) -> Path:
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(origin)], check=True)
    work = tmp_path / "work"
    subprocess.run(["git", "clone", "-q", str(origin), str(work)], check=True)
    _git(work, "config", "user.name", "someone")
    _git(work, "config", "user.email", "someone@example.com")
    _git(work, "checkout", "-q", "-b", "main")
    (work / "README.md").write_text("start\n", encoding="utf-8")
    _git(work, "add", "README.md")
    _git(work, "commit", "-q", "-m", "start")
    _git(work, "push", "-q", "origin", "main")
    return work


def _push(work: Path, message: str = "Update") -> subprocess.CompletedProcess[str]:
    shutil.copyfile(ROOT / ".github" / "scripts" / "push.sh", work / "push.sh")
    env = {**os.environ, "GITHUB_TOKEN": "token-for-tests", "GITHUB_REF_NAME": "main"}
    return subprocess.run([str(BASH), "push.sh", message], cwd=work, env=env, capture_output=True, text=True, check=False)


def test_karten13_b6_the_files_of_a_run_are_pushed_as_the_bot_and_nothing_else(clone: Path) -> None:
    (clone / "state.json").write_text("{}\n", encoding="utf-8")
    (clone / "orders").mkdir()
    (clone / "orders" / "1-1.json").write_text("{}\n", encoding="utf-8")
    (clone / "entries" / "1" / "x").mkdir(parents=True)
    (clone / "entries" / "1" / "x" / "entry.json").write_text("{}\n", encoding="utf-8")
    (clone / ".outbox.json").write_text("[]\n", encoding="utf-8")
    (clone / "other.txt").write_text("not ours\n", encoding="utf-8")
    done = _push(clone)
    assert done.returncode == 0, done.stderr
    origin = clone.parent / "origin.git"
    files = _git(origin, "ls-tree", "-r", "--name-only", "main").splitlines()
    assert "state.json" in files and "orders/1-1.json" in files and "entries/1/x/entry.json" in files
    assert ".outbox.json" not in files and "other.txt" not in files and "push.sh" not in files
    assert _git(origin, "log", "-1", "--format=%an <%ae>|%s", "main") == "github-actions[bot] <41898282+github-actions[bot]@users.noreply.github.com>|Update"
    assert "token-for-tests" not in (clone / ".git" / "config").read_text(encoding="utf-8"), "the key is not kept in the repository"


def test_karten13_b6_a_run_that_changed_nothing_makes_no_commit(clone: Path) -> None:
    done = _push(clone)
    assert done.returncode == 0 and "Nothing to commit." in done.stdout
    assert _git(clone, "log", "--oneline").count("\n") == 0
    (clone / "orders").mkdir()
    (clone / "orders" / "1-1.json").write_text("{}\n", encoding="utf-8")
    assert _push(clone).returncode == 0
    (clone / "orders" / "1-1.json").unlink()  # an order carried out: its file is gone, and the removal is pushed as well
    assert _push(clone, "Carried out").returncode == 0
    assert "orders/1-1.json" not in _git(clone.parent / "origin.git", "ls-tree", "-r", "--name-only", "main")



def _other_person_pushes(clone: Path, name: str) -> None:
    """Somebody pushes to main from another clone, after the run took its checkout."""
    other = clone.parent / "other"
    subprocess.run(["git", "clone", "-q", str(clone.parent / "origin.git"), str(other)], check=True)
    _git(other, "config", "user.name", "someone")
    _git(other, "config", "user.email", "someone@example.com")
    (other / name).write_text("from somebody\n", encoding="utf-8")
    _git(other, "add", name)
    _git(other, "commit", "-q", "-m", f"Add {name}")
    _git(other, "push", "-q", "origin", "main")


def test_karten8n2_a_run_takes_in_what_was_pushed_since_its_checkout_before_it_pushes(clone: Path) -> None:
    _other_person_pushes(clone, "CHANGES.md")
    (clone / "state.json").write_text("{}\n", encoding="utf-8")
    done = _push(clone)
    assert done.returncode == 0, done.stderr
    origin = clone.parent / "origin.git"
    assert {"CHANGES.md", "state.json"} <= set(_git(origin, "ls-tree", "-r", "--name-only", "main").splitlines())
    assert _git(origin, "log", "--format=%s", "main").splitlines()[0] == "Update", "the run's commit sits on top of the newest main"


def test_karten8n2_a_push_that_is_refused_because_main_moved_is_tried_once_more(clone: Path) -> None:
    """The first push of the run is refused (a person pushed between the pull and the push); the second works."""
    origin = clone.parent / "origin.git"
    hook = origin / "hooks" / "pre-receive"
    marker = (clone.parent / "refused-once").as_posix()
    hook.write_text(f'#!/bin/sh\nif [ ! -e "{marker}" ]; then : > "{marker}"; echo "main moved" >&2; exit 1; fi\n', encoding="utf-8", newline="\n")
    hook.chmod(0o755)
    (clone / "state.json").write_text("{}\n", encoding="utf-8")
    done = _push(clone)
    assert done.returncode == 0, done.stderr
    assert "state.json" in _git(origin, "ls-tree", "-r", "--name-only", "main").splitlines()


def test_karten8n2_a_conflict_stops_the_run_with_an_error_and_pushes_nothing(clone: Path) -> None:
    _other_person_pushes(clone, "state.json")
    (clone / "state.json").write_text("{}\n", encoding="utf-8")
    done = _push(clone)
    assert done.returncode != 0
    assert _git(clone.parent / "origin.git", "show", "main:state.json") == "from somebody"
