"""Demo data with a key or a password are refused, with the place and the key, never the value (S3 of the review, stage 8)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from tests.conftest import ALICE, FakeHub, form_body, run, sample
from tools.common import ROOT, demo_secrets

VALUE = sample("good", "value-card.yaml")
SECRET = "0123456789abcdef" * 2


def _files(root: Path) -> list[str]:
    return sorted(path.relative_to(root).as_posix() for path in (root / "entries").rglob("*") if path.is_file()) if (root / "entries").exists() else []


def with_demo(demo: str) -> str:
    return VALUE.replace("  q: {count: 7}", f"  q: {demo}")


def test_karten8s_s3_a_demo_with_a_key_is_red_with_place_and_key_and_never_the_value(ctx: Any, hub: FakeHub, root: Path) -> None:
    hub.submit(3, ALICE, form_body(with_demo(f'{{count: 7, auth: {{password: "hunter2hunter2", session_token: "{SECRET}"}}}}')))
    run(ctx, 3)
    comment = hub.last_comment(3)
    assert hub.issues[3]["state"] == "open" and "cannot be accepted yet" in comment
    assert "demo.q.auth.password" in comment and r"demo.q.auth.session\_token" in comment, "the bot writes the place as plain text"
    assert "hunter2hunter2" not in comment and SECRET not in comment
    assert _files(root) == []


@pytest.mark.parametrize("value", ['"[hidden]"', '"…"', '"..."', '"xxxx-xxxx"', '"<your key>"', '""', "null"])
def test_karten8s_s3_a_placeholder_under_such_a_key_is_taken(ctx: Any, hub: FakeHub, root: Path, value: str) -> None:
    hub.submit(3, ALICE, form_body(with_demo(f"{{count: 7, apiKey: {value}}}")))
    run(ctx, 3)
    assert hub.issues[3]["state"] == "closed", hub.last_comment(3)


@pytest.mark.parametrize(
    "key", ["apikey", "API_KEY", "X-ApiKey", "token", "refresh_token", "Secret", "password", "db_passwd", "Authorization",
            "cookie", "sessionId", "private_key", "client_secret", "aws_access_key"],
)
def test_karten8s_s3_the_keys_of_the_list_count_in_any_case_and_as_a_part(key: str) -> None:
    assert demo_secrets({"a": {key: "abc", "list": [{key: 5}], "title": "secret plans", "monkey": "x"}}) == [(f"demo.a.{key}", key), (f"demo.a.list[0].{key}", key)]


@pytest.mark.parametrize("key", ["X-Api-Key", "privateKey", "accessKey", "passphrase", "pwd", "auth", "Api Key"])
def test_karten8t_b8_a_credential_spelled_otherwise_is_found_in_demo_data(key: str) -> None:
    assert demo_secrets({"a": {key: "k7Hq2pLw9Z0a", "title": "Dune"}}) == [(f"demo.a.{key}", key)]


@pytest.mark.parametrize("key", ["userName", "login", "title", "monkey", "keyword", "author"])
def test_karten8t_b8_names_that_only_say_who_asks_or_hold_no_credential_stay(key: str) -> None:
    assert demo_secrets({"a": {key: "someone"}}) == []


def test_karten8t_b8_the_rule_is_the_one_of_the_kit() -> None:
    assert (ROOT / "kit" / "nexdeck_kit" / "credential_names.py").is_file()
    assert "def is_access_name" in (ROOT / "kit" / "nexdeck_kit" / "credential_names.py").read_text(encoding="utf-8")
