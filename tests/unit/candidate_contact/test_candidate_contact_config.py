"""Unit tests for owner candidate-contact configuration."""

from __future__ import annotations

from pathlib import Path

import pytest

from career_intelligence.candidate_contact import (
    CandidateContactConfigError,
    load_candidate_contact,
    require_contact_details,
)
from career_intelligence.cv_generation.options import ContactDetails


def _write_contact(path: Path, **fields: str) -> Path:
    lines = [f"{key}: {value}" for key, value in fields.items()]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


VALID = {
    "email": "candidate@example.com",
    "phone": '"0400 000 000"',
    "location": "Melbourne, VIC",
    "linkedin_url": "https://www.linkedin.com/in/example/",
    "portfolio_url": "https://example.com/portfolio/",
    "github_url": "https://github.com/example",
}


def test_load_valid_candidate_contact(tmp_path: Path) -> None:
    path = _write_contact(tmp_path / "candidate_contact.yaml", **VALID)
    contact = load_candidate_contact(path)
    assert contact.email == "candidate@example.com"
    assert contact.portfolio_url == "https://example.com/portfolio/"
    assert contact.github_url == "https://github.com/example"


def test_missing_required_field_fails_closed(tmp_path: Path) -> None:
    incomplete = dict(VALID)
    del incomplete["portfolio_url"]
    path = _write_contact(tmp_path / "candidate_contact.yaml", **incomplete)
    with pytest.raises(CandidateContactConfigError, match="portfolio_url"):
        load_candidate_contact(path)


def test_missing_file_fails_closed(tmp_path: Path) -> None:
    missing = tmp_path / "missing.yaml"
    with pytest.raises(CandidateContactConfigError, match="contact config file"):
        load_candidate_contact(missing)


def test_malformed_url_fails_closed(tmp_path: Path) -> None:
    bad = dict(VALID)
    bad["github_url"] = "github.com/example"
    path = _write_contact(tmp_path / "candidate_contact.yaml", **bad)
    with pytest.raises(CandidateContactConfigError, match="http"):
        load_candidate_contact(path)


def test_require_contact_details_rejects_partial_overlay() -> None:
    with pytest.raises(CandidateContactConfigError, match="phone"):
        require_contact_details(ContactDetails(email="candidate@example.com"))
