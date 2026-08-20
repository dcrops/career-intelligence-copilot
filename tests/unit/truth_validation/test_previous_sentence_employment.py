"""Bounded previous-sentence employer bind for first-person delivery claims."""

from __future__ import annotations

from pathlib import Path

from career_intelligence.profile import CareerProfileService
from career_intelligence.profile.models import CareerProfile
from career_intelligence.truth_validation import TruthValidationService

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"
LIVE_PROFILE = Path(__file__).resolve().parents[3] / "data" / "career_profile.yaml"

NBN_KEY = "experience-nbn-data-engineer-2020"


def _profile(**changes: object) -> CareerProfile:
    base = CareerProfileService.from_path(FIXTURES / "minimal_valid_profile.yaml").load()
    data = base.model_dump(mode="python")
    data.update(changes)
    return CareerProfile.model_validate(data)


def _live() -> CareerProfile:
    return CareerProfileService.from_path(LIVE_PROFILE).load()


def _report(markdown: str, profile: CareerProfile | None = None):
    return TruthValidationService().validate_markdown(
        markdown=markdown,
        profile=profile or _live(),
    )


def _finding(report, kind: str, key: str | None = None):
    return next(
        item
        for item in report.findings
        if item.claim.claim_kind == kind and (key is None or item.claim.object_key == key)
    )


def _delivery_findings(report):
    return [item for item in report.findings if item.claim.claim_kind == "project_delivery"]


def test_same_sentence_nbn_delivery_remains_supported() -> None:
    report = _report(
        "At nbn Australia, I developed and maintained enterprise data pipelines "
        "using AWS, Python, and SQL."
    )
    assert _delivery_findings(report) == []
    employment = _finding(report, "employment", NBN_KEY)
    assert employment.evidence_status == "supported"
    assert report.outcome in {"pass", "warning"}


def test_previous_sentence_nbn_truthful_pipeline_delivery_is_supported() -> None:
    report = _report(
        "My experience as a Data Engineer at nbn Australia further complements "
        "the requirements of this position. I developed and maintained enterprise "
        "data pipelines using AWS services, Python, and SQL."
    )
    assert _delivery_findings(report) == []
    employment = _finding(report, "employment", NBN_KEY)
    assert employment.evidence_status == "supported"
    assert report.outcome in {"pass", "warning"}


def test_frozen_e2_sentence_pair_is_supported() -> None:
    report = _report(
        "My experience as a Data Engineer at nbn Australia further complements "
        "the requirements of this position. I developed and maintained enterprise "
        "data pipelines using AWS services, Python, and SQL, ensuring reliable "
        "production data systems."
    )
    assert _delivery_findings(report) == []
    employment = _finding(report, "employment", NBN_KEY)
    assert employment.evidence_status == "supported"
    assert report.outcome in {"pass", "warning"}


def test_previous_sentence_nbn_invented_gpu_delivery_is_not_supported() -> None:
    report = _report(
        "My experience as a Data Engineer at nbn Australia further complements "
        "the requirements of this position. I developed large-scale GPU training "
        "clusters."
    )
    delivery = _delivery_findings(report)
    assert delivery
    assert all(item.evidence_status != "supported" for item in delivery)
    assert any(item.severity in {"review_required", "blocking"} for item in delivery)
    assert not any(
        item.claim.claim_kind == "employment"
        and item.claim.object_key == NBN_KEY
        and item.evidence_status == "supported"
        and item.claim.predicate == "has_employment"
        and "gpu" in item.claim.surface_text.casefold()
        for item in report.findings
    )
    assert report.outcome in {"fail", "review_required"}


def test_previous_sentence_without_known_employer_does_not_bind() -> None:
    report = _report(
        "This role strongly interests me. I developed enterprise data pipelines "
        "using AWS."
    )
    delivery = _delivery_findings(report)
    assert delivery
    assert any(item.severity in {"review_required", "blocking"} for item in delivery)
    assert not any(
        item.claim.object_key == NBN_KEY and item.evidence_status == "supported"
        for item in report.findings
        if item.claim.claim_kind == "employment" and item.claim.predicate == "has_employment"
    )


def test_employer_two_sentences_back_does_not_bind() -> None:
    report = _report(
        "At nbn Australia I worked as a Data Engineer. This experience "
        "strengthened my engineering discipline. I developed enterprise data "
        "pipelines using AWS."
    )
    delivery = _delivery_findings(report)
    assert delivery
    assert any(item.severity in {"review_required", "blocking"} for item in delivery)
    assert not any(
        item.claim.object_key == NBN_KEY
        and item.evidence_status == "supported"
        and item.claim.predicate == "has_employment"
        and "pipelines" in (item.claim.span_hint or "").casefold()
        for item in report.findings
    )


def test_named_project_delivery_takes_precedence() -> None:
    report = _report(
        "My experience as a Data Engineer at nbn Australia further complements "
        "the requirements of this position. I developed the Governance-Aware "
        "Document Intelligence RAG."
    )
    delivery = _finding(report, "project_delivery")
    assert delivery.evidence_status == "supported"
    assert "rag" in delivery.claim.object_key.casefold() or "governance" in (
        delivery.claim.object_key.casefold()
    )


def test_employer_requirement_does_not_authorise_delivery() -> None:
    report = _report(
        "The role requires enterprise data pipelines. I developed enterprise "
        "data pipelines using AWS."
    )
    delivery = _delivery_findings(report)
    assert delivery
    assert any(item.severity in {"review_required", "blocking"} for item in delivery)
    requirement = [
        item
        for item in report.findings
        if item.claim.claim_class == "B"
    ]
    assert all(item.evidence_status != "supported" or item.claim.claim_class == "B" for item in requirement)
    assert not any(
        item.claim.object_key == NBN_KEY and item.evidence_status == "supported"
        for item in report.findings
        if item.claim.predicate == "has_employment"
    )


def test_multiple_employers_in_previous_sentence_fail_closed() -> None:
    profile = _profile(
        experience=[
            {
                "id": "nbn-data-engineer-2020",
                "kind": "employment",
                "organisation": "nbn Australia",
                "title": "Data Engineer",
                "start_date": "2020-03",
                "end_date": "2023-10",
                "location": "Melbourne",
                "highlights": [
                    "Developed and maintained enterprise data pipelines and "
                    "operational reporting solutions using AWS services, "
                    "Python, SQL, and Apache NiFi."
                ],
                "technologies": ["Python", "SQL", "AWS"],
            },
            {
                "id": "bakers-delight-test-analyst",
                "kind": "employment",
                "organisation": "Bakers Delight",
                "title": "Test Analyst",
                "start_date": "2015-01",
                "end_date": "2017-01",
                "location": "Melbourne",
                "highlights": ["Tested retail systems."],
                "technologies": ["SQL"],
            },
        ]
    )
    report = _report(
        "I worked at nbn Australia and Bakers Delight. I developed and "
        "maintained enterprise data pipelines using AWS services, Python, "
        "and SQL.",
        profile,
    )
    delivery = _delivery_findings(report)
    assert delivery
    assert any(item.severity in {"review_required", "blocking"} for item in delivery)
    assert not any(
        item.claim.predicate == "has_employment" and item.evidence_status == "supported"
        for item in report.findings
        if "pipelines" in (item.claim.span_hint or item.claim.surface_text).casefold()
    )
