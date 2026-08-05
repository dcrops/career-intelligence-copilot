"""Unit tests for FR-014 M1 truth-validation models and ADR-006 invariants."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from career_intelligence.truth_validation import (
    Claim,
    EvidenceProvenance,
    TruthFinding,
    TruthReport,
    expected_minimum_severity_for_finding,
    new_claim_id,
    new_truth_finding_id,
    new_truth_report_id,
    validate_catalogue_contract,
    validate_truth_report_contract,
)
from tests.unit.truth_validation.helpers import (
    make_catalogue,
    make_catalogue_entry,
    make_claim,
    make_finding,
    make_provenance,
    make_report,
)


def test_id_patterns_and_generators() -> None:
    report = make_report(report_id=new_truth_report_id())
    assert report.report_id.startswith("trp_")
    finding = make_finding(finding_id=new_truth_finding_id())
    assert finding.finding_id.startswith("tfd_")
    claim = make_claim(claim_id=new_claim_id())
    assert claim.claim_id.startswith("tcl_")


def test_rejects_bad_report_id() -> None:
    with pytest.raises(ValidationError):
        make_report(report_id="rpt_01ARZ3NDEKTSV4RRFFQ69G5FAA")


def test_extra_fields_forbidden() -> None:
    with pytest.raises(ValidationError):
        TruthReport.model_validate(
            {
                **make_report().model_dump(mode="python"),
                "surprise": True,
            }
        )


def test_class_a_requires_candidate_subject() -> None:
    with pytest.raises(ValidationError):
        make_claim(claim_class="A", subject="employer")


def test_class_b_requires_employer_or_role_subject() -> None:
    claim = make_claim(
        claim_class="B",
        subject="role",
        predicate="requires_skill",
        object_key="vue",
        surface_text="The role uses Vue",
        strength="mentioned",
    )
    assert claim.claim_class == "B"
    with pytest.raises(ValidationError):
        make_claim(claim_class="B", subject="candidate")


def test_profile_source_must_be_candidate_authoritative() -> None:
    with pytest.raises(ValidationError):
        make_provenance(
            source_kind="profile_skill",
            authority="context_only",
        )


def test_jd_and_plan_sources_must_be_context_only() -> None:
    for source in (
        "job_analysis",
        "opportunity_assessment",
        "application_strategy",
        "tailoring_plan",
        "cover_letter_plan",
    ):
        cite = make_provenance(
            source_kind=source,
            authority="context_only",
            provenance_ref=f"{source}:1",
        )
        assert cite.authority == "context_only"
        with pytest.raises(ValidationError):
            make_provenance(
                source_kind=source,
                authority="candidate_authoritative",
                provenance_ref=f"{source}:1",
            )


def test_class_a_supported_requires_authoritative_citation() -> None:
    with pytest.raises(ValidationError):
        make_finding(
            evidence_status="supported",
            evidence_citations=[
                make_provenance(
                    source_kind="job_analysis",
                    authority="context_only",
                    provenance_ref="job_analysis:tech:vue",
                )
            ],
        )


def test_class_a_supported_with_profile_citation_passes() -> None:
    finding = make_finding(
        evidence_status="supported",
        evidence_citations=[make_provenance()],
    )
    assert finding.evidence_status == "supported"


def test_unsupported_class_a_must_be_blocking() -> None:
    with pytest.raises(ValidationError):
        make_finding(
            evidence_status="unsupported",
            severity="warning",
            evidence_citations=[],
            recommended_action="remove or reframe unsupported claim",
        )
    finding = make_finding(
        claim=make_claim(object_key="vue", surface_text="I am proficient in Vue"),
        detection_certainty="certain",
        evidence_status="unsupported",
        severity="blocking",
        evidence_citations=[],
        recommended_action="remove unsupported Vue capability claim",
    )
    assert finding.severity == "blocking"


def test_ambiguous_detection_class_a_requires_review_or_blocking() -> None:
    with pytest.raises(ValidationError):
        make_finding(
            detection_certainty="ambiguous",
            evidence_status="ambiguous",
            severity="warning",
            evidence_citations=[],
            recommended_action="owner review framing",
        )
    finding = make_finding(
        detection_certainty="ambiguous",
        evidence_status="ambiguous",
        severity="review_required",
        evidence_citations=[],
        recommended_action="owner review framing",
    )
    assert finding.severity == "review_required"


def test_ambiguous_high_strength_class_a_must_block() -> None:
    with pytest.raises(ValidationError):
        make_finding(
            claim=make_claim(strength="expert", surface_text="I am an expert in Vue"),
            detection_certainty="ambiguous",
            evidence_status="ambiguous",
            severity="review_required",
            evidence_citations=[],
            recommended_action="clarify or remove",
        )
    finding = make_finding(
        claim=make_claim(strength="proficient", surface_text="I am proficient in Vue"),
        detection_certainty="ambiguous",
        evidence_status="ambiguous",
        severity="blocking",
        evidence_citations=[],
        recommended_action="clarify or remove",
    )
    assert expected_minimum_severity_for_finding(finding) == "blocking"


def test_pass_rejected_when_coverage_insufficient() -> None:
    with pytest.raises(ValidationError):
        make_report(
            coverage_status="insufficient",
            detection_performed=False,
            validation_performed=False,
            findings=[],
            outcome="pass",
            summary="No findings",
        )


def test_empty_findings_without_performed_flags_cannot_pass() -> None:
    """ADR-006: non-detection must not silently become PASS."""
    with pytest.raises(ValidationError):
        make_report(
            coverage_status="complete",
            detection_performed=False,
            validation_performed=False,
            findings=[],
            outcome="pass",
            summary="Nothing detected so it must be fine",
        )


def test_empty_findings_with_complete_assessed_coverage_may_pass() -> None:
    report = make_report(
        coverage_status="complete",
        detection_performed=True,
        validation_performed=True,
        findings=[],
        outcome="pass",
        summary="Assessed; no material Class A claims detected.",
    )
    validate_truth_report_contract(report)
    assert report.outcome == "pass"


def test_insufficient_coverage_requires_review_or_fail() -> None:
    with pytest.raises(ValidationError):
        make_report(
            coverage_status="insufficient",
            detection_performed=False,
            validation_performed=False,
            findings=[],
            outcome="warning",
            summary="Detector not run",
        )
    report = make_report(
        coverage_status="insufficient",
        detection_performed=False,
        validation_performed=False,
        findings=[],
        outcome="review_required",
        summary="Coverage insufficient; owner review required.",
    )
    validate_truth_report_contract(report)


def test_outcome_must_reflect_blocking_finding() -> None:
    finding = make_finding(
        claim=make_claim(object_key="typescript", surface_text="I work best in TypeScript"),
        evidence_status="unsupported",
        severity="blocking",
        evidence_citations=[],
        recommended_action="remove unsupported TypeScript claim",
    )
    with pytest.raises(ValidationError):
        make_report(
            findings=[finding],
            outcome="pass",
            summary="should not pass",
        )
    report = make_report(
        findings=[finding],
        outcome="fail",
        summary="Unsupported candidate technology claim.",
    )
    assert report.outcome == "fail"


def test_detection_certainty_distinct_from_evidence_status() -> None:
    """Both dimensions coexist on a finding and answer different questions."""
    finding = make_finding(
        detection_certainty="certain",
        evidence_status="unsupported",
        severity="blocking",
        evidence_citations=[],
        recommended_action="remove claim",
    )
    assert finding.detection_certainty == "certain"
    assert finding.evidence_status == "unsupported"
    dumped = finding.model_dump()
    assert "detection_certainty" in dumped
    assert "evidence_status" in dumped
    assert dumped["detection_certainty"] != dumped["evidence_status"]


def test_catalogue_rejects_jd_as_candidate_authoritative() -> None:
    with pytest.raises(ValidationError):
        make_catalogue_entry(
            object_key="vue",
            provenance={
                "source_kind": "job_analysis",
                "authority": "candidate_authoritative",
                "provenance_ref": "job_analysis:tech:vue",
            },
        )


def test_catalogue_contract_helper_accepts_valid_entries() -> None:
    catalogue = make_catalogue(
        entries=[
            make_catalogue_entry(),
            make_catalogue_entry(
                object_key="vue",
                provenance=make_provenance(
                    source_kind="job_analysis",
                    authority="context_only",
                    provenance_ref="job_analysis:tech:vue",
                    excerpt="Vue",
                ),
            ),
        ]
    )
    validate_catalogue_contract(catalogue)


def test_claim_and_finding_round_trip() -> None:
    claim = Claim.model_validate(make_claim().model_dump(mode="python"))
    finding = TruthFinding.model_validate(
        make_finding(claim=claim).model_dump(mode="python")
    )
    assert finding.claim.claim_id == claim.claim_id


def test_evidence_provenance_other_cannot_be_authoritative() -> None:
    with pytest.raises(ValidationError):
        EvidenceProvenance.model_validate(
            {
                "source_kind": "other",
                "authority": "candidate_authoritative",
                "provenance_ref": "mystery",
            }
        )
