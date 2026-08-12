"""Unit tests for cover-letter Portfolio/GitHub navigation paragraph."""

from __future__ import annotations

from career_intelligence.cover_letter.composer import (
    _compose_portfolio_body_note,
    _portfolio_lead,
)
from tests.unit.cover_letter.helpers import make_plan, minimal_profile, strategy_from_payload


def test_portfolio_nav_paragraph_requires_urls() -> None:
    plan = make_plan(profile=minimal_profile(), strategy=strategy_from_payload())
    assert _compose_portfolio_body_note(plan, contact=None) is None
    assert (
        _compose_portfolio_body_note(
            plan,
            contact={"portfolio_url": "https://example.com/portfolio/"},
        )
        is None
    )


def test_portfolio_nav_paragraph_is_labelled_when_urls_present() -> None:
    plan = make_plan(profile=minimal_profile(), strategy=strategy_from_payload())
    note = _compose_portfolio_body_note(
        plan,
        contact={
            "portfolio_url": "https://example.com/portfolio/",
            "github_url": "https://github.com/example",
        },
    )
    assert note is not None
    assert "**Portfolio:**" in note
    assert "**GitHub:**" in note
    assert "https://example.com/portfolio/" in note
    assert "https://github.com/example" in note
    assert "available in my portfolio" not in note.casefold()
    assert "slideware" not in note.casefold()


def test_generated_letter_keeps_portfolio_nav_as_own_paragraph() -> None:
    from tests.unit.cover_letter.helpers import default_contact, make_letter

    letter = make_letter(contact=default_contact())
    nav_paras = [
        p
        for p in letter.paragraphs
        if p.startswith("You can view examples of my AI engineering work here:")
    ]
    assert len(nav_paras) == 1
    assert "**Portfolio:**" in nav_paras[0]
    assert "**GitHub:**" in nav_paras[0]
    assert "\n\n" in nav_paras[0]


def test_portfolio_lead_without_url_does_not_claim_site() -> None:
    lead = _portfolio_lead(None, count=2)
    assert "from my portfolio" not in lead.casefold()
    assert "Two projects are especially useful" in lead
