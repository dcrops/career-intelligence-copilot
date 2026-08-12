"""FR-014 M4 deterministic non-technology claim validation."""

from __future__ import annotations

from pathlib import Path

from career_intelligence.profile import CareerProfileService
from career_intelligence.profile.models import CareerProfile
from career_intelligence.truth_validation import TruthValidationService

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"


def _profile(**changes: object) -> CareerProfile:
    base = CareerProfileService.from_path(FIXTURES / "minimal_valid_profile.yaml").load()
    data = base.model_dump(mode="python")
    data.update(changes)
    return CareerProfile.model_validate(data)


def _report(markdown: str, profile: CareerProfile | None = None):
    return TruthValidationService().validate_markdown(markdown=markdown, profile=profile or _profile())


def _finding(report, kind: str, key: str | None = None):
    return next(
        item for item in report.findings
        if item.claim.claim_kind == kind and (key is None or item.claim.object_key == key)
    )


def test_commercial_employment_honesty() -> None:
    failed = _report("I have commercial AI engineering experience.")
    assert _finding(failed, "employment", "commercial_ai_engineering").severity == "blocking"

    passed = _report("I have commercial software engineering experience.")
    assert _finding(passed, "employment", "commercial_software_engineering").evidence_status == "supported"


def test_independent_and_ai_employment_support() -> None:
    independent = _profile(experience=[{
        "id": "independent", "kind": "independent_engineering", "organisation": "Self",
        "title": "Independent Engineer", "start_date": "2024-01", "end_date": "2025-01",
        "location": "Melbourne", "highlights": ["Built client systems."], "technologies": ["Python"],
    }])
    assert _finding(_report("I have independent engineering experience.", independent), "employment").evidence_status == "supported"

    ai = _profile(experience=[{
        "id": "ai-role", "kind": "employment", "organisation": "Example",
        "title": "AI Engineer", "start_date": "2024-01", "end_date": "2025-01",
        "location": "Melbourne", "highlights": ["Delivered LLM applications."], "technologies": ["Python"],
    }])
    assert _finding(_report("I have commercial AI engineering experience.", ai), "employment").evidence_status == "supported"


def test_certification_and_domain_support() -> None:
    certified = _profile(certifications=[{
        "id": "aws-saa", "name": "AWS Certified Solutions Architect", "issuer": "AWS",
        "status": "active",
    }], skills={
        "technical": [{"name": "Python", "evidence": "experience:example-role"}],
        "domain": [{"name": "financial services", "evidence": "project:example-project"}],
        "soft": [],
    })
    assert _finding(_report("I hold AWS Certified Solutions Architect.", certified), "certification").evidence_status == "supported"
    assert _finding(_report("I hold AWS Certified Solutions Architect."), "certification").severity == "blocking"
    assert _finding(_report("I have experience in financial services.", certified), "domain").evidence_status == "supported"
    assert _finding(_report("I have experience in healthcare.", certified), "domain").severity == "blocking"


def test_nested_aws_developer_associate_supported_without_truncated_twin() -> None:
    """FR-019 dogfood: full Associate title must not emit a blocking truncated twin."""
    certified = _profile(certifications=[{
        "id": "aws-certified-developer-associate",
        "name": "AWS Certified Developer - Associate",
        "issuer": "Amazon Web Services",
        "status": "active",
    }])
    markdown = "- **AWS Certified Developer - Associate** — Amazon Web Services"
    report = _report(markdown, certified)
    cert_findings = [f for f in report.findings if f.claim.claim_kind == "certification"]
    assert len(cert_findings) == 1
    finding = cert_findings[0]
    assert finding.claim.object_key == "awscertifieddeveloperassociate"
    assert finding.evidence_status == "supported"
    assert finding.severity == "info"
    assert report.outcome == "pass"
    assert not any(
        f.claim.object_key == "awscertifieddeveloper" for f in cert_findings
    )


def test_nested_aws_developer_associate_unsupported_remains_blocking() -> None:
    """Without profile evidence, the Associate expression still fail-closes."""
    markdown = "- **AWS Certified Developer - Associate** — Amazon Web Services"
    report = _report(markdown)
    cert_findings = [f for f in report.findings if f.claim.claim_kind == "certification"]
    assert len(cert_findings) == 1
    finding = cert_findings[0]
    # Well-known short label is the only lexicon hit without a catalogue entry.
    assert finding.claim.object_key == "awscertifieddeveloper"
    assert finding.severity == "blocking"
    assert finding.evidence_status == "unsupported"
    assert report.outcome == "fail"


def test_distinct_certifications_validated_independently() -> None:
    certified = _profile(certifications=[
        {
            "id": "aws-certified-developer-associate",
            "name": "AWS Certified Developer - Associate",
            "issuer": "Amazon Web Services",
            "status": "active",
        },
        {
            "id": "databricks-certified-data-engineer-professional",
            "name": "Databricks Certified Data Engineer Professional",
            "issuer": "Databricks",
            "status": "active",
        },
    ])
    markdown = (
        "## Certifications\n"
        "- **AWS Certified Developer - Associate** — Amazon Web Services\n"
        "- **Databricks Certified Data Engineer Professional** — Databricks\n"
        "- **Certified Kubernetes Administrator** — CNCF\n"
    )
    report = _report(markdown, certified)
    cert_findings = [f for f in report.findings if f.claim.claim_kind == "certification"]
    by_key = {f.claim.object_key: f for f in cert_findings}
    assert "awscertifieddeveloperassociate" in by_key
    assert by_key["awscertifieddeveloperassociate"].evidence_status == "supported"
    assert "awscertifieddeveloper" not in by_key
    assert by_key["databrickscertifieddataengineerprofessional"].evidence_status == "supported"
    assert by_key["certifiedkubernetesadministrator"].severity == "blocking"
    assert report.outcome == "fail"


def test_duration_and_project_delivery() -> None:
    supported = _report("I have One year of Python experience.")
    assert _finding(supported, "duration", "python").evidence_status == "supported"
    overclaim = _report("I have Ten years of Python experience.")
    assert _finding(overclaim, "duration", "python").severity == "blocking"
    ambiguous = _report("I have Two years of Quantum capability.")
    assert _finding(ambiguous, "duration").severity == "review_required"

    delivered = _report("I built Example Project.")
    assert _finding(delivered, "project_delivery", "exampleproject").evidence_status == "supported"
    uncertain = _report("I built the Redwolf Platform.")
    assert _finding(uncertain, "project_delivery").severity in {"review_required", "blocking"}


def test_redwolf_regression_remains_blocking() -> None:
    report = _report(
        "Roles centred on Python, TypeScript, and Vue are where I do my best engineering work.",
    )
    assert report.outcome == "fail"
    assert _finding(report, "technology", "python").evidence_status == "supported"
    assert _finding(report, "technology", "typescript").severity == "blocking"
    assert _finding(report, "technology", "vue").severity == "blocking"
