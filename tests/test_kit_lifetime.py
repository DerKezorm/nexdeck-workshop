"""The kit knows how long the ticket of a session holds and which answers mean it ran out (nexdeck KARTEN-3, lifetime and renew_on)."""

from __future__ import annotations

import pytest

from tests.conftest import sample
from tools import kitcheck

CONNECTION = sample("good", "session-connection.yaml")
TICKET = "  ticket: {from: json, at: token}\n"


def _with(extra: str) -> str:
    assert TICKET in CONNECTION
    return CONNECTION.replace(TICKET, TICKET + extra)


@pytest.mark.parametrize(
    "extra",
    ["  lifetime: 3600\n", "  lifetime: {from: json, at: expires_in}\n", "  renew_on: [401, 500]\n", "  lifetime: {from: json, at: expires_in}\n  renew_on: [401, 500]\n"],
)
def test_karten8n2_a_connection_may_say_how_long_its_ticket_holds_and_when_to_sign_in_again(extra: str) -> None:
    answer = kitcheck.check(_with(extra), "integration")
    assert answer["ok"] is True, answer["problems"]
    assert answer["class"] == "login"


@pytest.mark.parametrize("extra", ["  lifetime: 0\n", "  lifetime: soon\n", "  renew_on: [404]\n", "  renew_on: []\n", "  renew_on: [500, 500]\n"])
def test_karten8n2_a_lifetime_or_renew_on_that_makes_no_sense_is_a_reason(extra: str) -> None:
    answer = kitcheck.check(_with(extra), "integration")
    assert answer["ok"] is False and answer["problems"]
