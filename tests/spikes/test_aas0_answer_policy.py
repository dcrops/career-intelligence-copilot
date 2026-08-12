"""Unit tests for AAS-0 answer policy (never guess)."""

from __future__ import annotations

import sys
from pathlib import Path

SPIKES = Path(__file__).resolve().parents[2] / "spikes"
if str(SPIKES) not in sys.path:
    sys.path.insert(0, str(SPIKES))

from aas0.answer_policy import (  # noqa: E402
    AnswerDecision,
    KnownAnswers,
    merge_owner_extra,
    resolve_answer,
    should_pause,
)


def _known() -> KnownAnswers:
    return KnownAnswers(
        full_name="Ada Lovelace",
        email="ada@example.com",
        phone="0400 000 000",
        location="Melbourne, VIC",
        linkedin_url="https://www.linkedin.com/in/ada/",
        portfolio_url="https://example.com/portfolio/",
        github_url="https://github.com/ada",
    )


def test_email_phone_name_autofill() -> None:
    known = _known()
    email = resolve_answer("Email address", known)
    assert email.decision is AnswerDecision.KNOWN
    assert email.value == "ada@example.com"
    phone = resolve_answer("Mobile phone", known)
    assert phone.value == "0400 000 000"
    first = resolve_answer("First name", known)
    assert first.value == "Ada"
    last = resolve_answer("Last name", known)
    assert last.value == "Lovelace"


def test_salary_and_years_always_pause() -> None:
    known = _known()
    assert should_pause("What is your salary expectation?", known)
    assert should_pause("Years of AI engineering experience", known)
    assert should_pause("Do you require sponsorship?", known)


def test_unrecognized_label_pauses() -> None:
    known = _known()
    result = resolve_answer("Favourite IDE colour theme?", known)
    assert result.decision is AnswerDecision.PAUSE


def test_owner_extra_answers_exact_question() -> None:
    known = merge_owner_extra(
        _known(),
        "Are you an Australian citizen?",
        "Yes",
    )
    result = resolve_answer("Are you an Australian citizen?", known)
    assert result.decision is AnswerDecision.KNOWN
    assert result.value == "Yes"
    assert result.reason == "owner_approved_extra"


def test_never_uses_missing_contact_field() -> None:
    known = KnownAnswers(full_name="Ada Lovelace")
    result = resolve_answer("Email", known)
    assert result.decision is AnswerDecision.PAUSE
    assert result.reason == "missing_known_value"
