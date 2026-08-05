"""Contract-invariant helpers for TruthReport / catalogue (FR-014 M1).

These functions re-check ADR-006 rules for callers that assemble reports outside
Pydantic construction, and provide a single place for explainable ErrorDetail lists.
Detectors and catalogue builders are out of scope for M1.
"""

from __future__ import annotations

from career_intelligence.truth_validation.errors import ErrorDetail, TruthContractError
from career_intelligence.truth_validation.models import (
    CANDIDATE_AUTHORITATIVE_SOURCES,
    CONTEXT_ONLY_SOURCES,
    HIGH_CLAIM_STRENGTHS,
    CandidateEvidenceCatalogue,
    CatalogueEvidenceEntry,
    TruthFinding,
    TruthReport,
)


def validate_catalogue_contract(
    catalogue: CandidateEvidenceCatalogue,
) -> None:
    """Fail closed if catalogue entries violate authority / provenance rules."""
    errors: list[ErrorDetail] = []
    for index, entry in enumerate(catalogue.entries):
        errors.extend(_entry_errors(entry, index=index))
    if errors:
        raise TruthContractError(errors)


def validate_truth_report_contract(report: TruthReport) -> None:
    """Fail closed if a report violates ADR-006 pass / detection / evidence rules.

    Pydantic validators already enforce most rules at construction time. This helper
    re-states them for service-layer callers and regression tests.
    """
    errors: list[ErrorDetail] = []

    if report.outcome == "pass":
        if report.coverage_status != "complete":
            errors.append(
                ErrorDetail(
                    loc=("coverage_status",),
                    msg=(
                        "outcome=pass requires coverage_status=complete; "
                        "non-detection is not proof of truth"
                    ),
                    type="value_error",
                )
            )
        if not report.detection_performed or not report.validation_performed:
            errors.append(
                ErrorDetail(
                    loc=("detection_performed", "validation_performed"),
                    msg=(
                        "outcome=pass requires detection_performed and "
                        "validation_performed"
                    ),
                    type="value_error",
                )
            )

    if report.coverage_status == "insufficient" and report.outcome in {
        "pass",
        "warning",
    }:
        errors.append(
            ErrorDetail(
                loc=("outcome",),
                msg="insufficient coverage requires review_required or fail",
                type="value_error",
            )
        )

    for index, finding in enumerate(report.findings):
        errors.extend(_finding_errors(finding, index=index))

    if errors:
        raise TruthContractError(errors)


def expected_minimum_severity_for_finding(finding: TruthFinding) -> str:
    """Return the minimum severity required by ADR-006 for this finding."""
    claim = finding.claim
    if claim.claim_class == "A" and finding.evidence_status in {
        "unsupported",
        "contradictory",
    }:
        return "blocking"
    if (
        claim.claim_class == "A"
        and finding.detection_certainty == "ambiguous"
        and claim.strength in HIGH_CLAIM_STRENGTHS
    ):
        return "blocking"
    if claim.claim_class == "A" and finding.detection_certainty == "ambiguous":
        return "review_required"
    return "info"


def _entry_errors(
    entry: CatalogueEvidenceEntry,
    *,
    index: int,
) -> list[ErrorDetail]:
    errors: list[ErrorDetail] = []
    source = entry.provenance.source_kind
    authority = entry.provenance.authority
    loc_base: tuple[str | int, ...] = ("entries", index, "provenance")

    if source in CANDIDATE_AUTHORITATIVE_SOURCES and authority != "candidate_authoritative":
        errors.append(
            ErrorDetail(
                loc=loc_base + ("authority",),
                msg="profile-derived sources require candidate_authoritative",
                type="value_error",
            )
        )
    if source in CONTEXT_ONLY_SOURCES and authority != "context_only":
        errors.append(
            ErrorDetail(
                loc=loc_base + ("authority",),
                msg=(
                    "JD / assessment / strategy / plan sources require "
                    "context_only authority"
                ),
                type="value_error",
            )
        )
    if authority == "candidate_authoritative" and source in CONTEXT_ONLY_SOURCES:
        errors.append(
            ErrorDetail(
                loc=loc_base + ("authority",),
                msg=(
                    "context-only sources must never authorize candidate "
                    "capability (authority cannot be candidate_authoritative)"
                ),
                type="value_error",
            )
        )
    return errors


def _finding_errors(finding: TruthFinding, *, index: int) -> list[ErrorDetail]:
    errors: list[ErrorDetail] = []
    loc_base: tuple[str | int, ...] = ("findings", index)
    minimum = expected_minimum_severity_for_finding(finding)
    rank = {"info": 0, "warning": 1, "review_required": 2, "blocking": 3}
    if rank[finding.severity] < rank[minimum]:  # type: ignore[index]
        errors.append(
            ErrorDetail(
                loc=loc_base + ("severity",),
                msg=f"severity must be at least {minimum!r} for this finding",
                type="value_error",
            )
        )

    if (
        finding.claim.claim_class == "A"
        and finding.evidence_status == "supported"
        and not any(
            cite.authority == "candidate_authoritative"
            for cite in finding.evidence_citations
        )
    ):
        errors.append(
            ErrorDetail(
                loc=loc_base + ("evidence_citations",),
                msg=(
                    "Class A supported findings require candidate_authoritative "
                    "citations"
                ),
                type="value_error",
            )
        )
    return errors
