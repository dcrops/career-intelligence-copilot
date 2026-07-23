"""Unit tests for opportunity identity derivation (M1)."""

from __future__ import annotations

from career_intelligence.job_analysis.models import JobPosting
from career_intelligence.opportunities.identity import (
    build_identity,
    content_fingerprint,
    derive_source_facets,
    new_opportunity_id,
)


def test_new_opportunity_id_is_opp_ulid() -> None:
    first = new_opportunity_id()
    second = new_opportunity_id()
    assert first.startswith("opp_")
    assert second.startswith("opp_")
    assert first != second
    assert len(first) == 30


def test_seek_job_id_extraction() -> None:
    kind, job_id, canonical = derive_source_facets(
        "https://au.seek.com/job/93487188?ref=search#sol=abc"
    )
    assert kind == "seek"
    assert job_id == "93487188"
    assert canonical == "https://au.seek.com/job/93487188"


def test_linkedin_current_job_id_extraction() -> None:
    kind, job_id, canonical = derive_source_facets(
        "https://www.linkedin.com/jobs/search-results/?currentJobId=4427312832&keywords=ai"
    )
    assert kind == "linkedin"
    assert job_id == "4427312832"
    assert canonical == "https://www.linkedin.com/jobs/view/4427312832"


def test_indeed_jk_extraction() -> None:
    kind, job_id, canonical = derive_source_facets(
        "https://au.indeed.com/viewjob?jk=abcdef0123456789&from=serp"
    )
    assert kind == "indeed"
    assert job_id == "abcdef0123456789"
    assert canonical == "https://www.indeed.com/viewjob?jk=abcdef0123456789"


def test_manual_and_unknown_urls() -> None:
    assert derive_source_facets(None) == ("manual", None, None)
    kind, job_id, canonical = derive_source_facets("https://example.com/careers/ai-role")
    assert kind == "other"
    assert job_id is None
    assert canonical == "https://example.com/careers/ai-role"


def test_source_url_preserved_and_fingerprint_stable() -> None:
    posting = JobPosting.model_validate(
        {
            "raw_text": "  AI Engineer\nPython required.  \n",
            "title": "AI Engineer",
            "company": "Acme",
            "source_url": "https://au.seek.com/job/111",
        }
    )
    identity = build_identity(posting)
    assert str(identity.source_url) == "https://au.seek.com/job/111"
    assert identity.platform_job_id == "111"
    assert identity.content_fingerprint == content_fingerprint(posting.raw_text)
    again = content_fingerprint("AI Engineer\nPython required.")
    assert identity.content_fingerprint == again


def test_no_deduplication_same_platform_id_allowed() -> None:
    """FR-014 is out of scope — identical facets still yield distinct opportunity ids."""
    posting = JobPosting.model_validate(
        {
            "raw_text": "Role body",
            "source_url": "https://au.seek.com/job/999",
        }
    )
    first = build_identity(posting)
    second = build_identity(posting)
    assert first.platform_job_id == second.platform_job_id == "999"
    assert first.opportunity_id != second.opportunity_id
