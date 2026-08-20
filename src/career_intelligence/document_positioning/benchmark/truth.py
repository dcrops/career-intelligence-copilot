"""FR-014 Truth evaluation for M5 documents.

Local M3/M4 validators are not a substitute. This module calls
``TruthValidationService.validate_markdown`` and the external-use gate.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from career_intelligence.profile.models import CareerProfile
from career_intelligence.truth_validation.gates import evaluate_report_for_external_use
from career_intelligence.truth_validation.models import ArtefactKind, TruthReport
from career_intelligence.truth_validation.service import TruthValidationService


class TruthDocumentRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    artefact_kind: ArtefactKind
    outcome: str
    coverage_status: str
    detection_performed: bool
    validation_performed: bool
    external_use_allowed: bool
    blocking_count: int
    review_required_count: int
    finding_summaries: list[str] = Field(default_factory=list)
    messages: list[str] = Field(default_factory=list)
    content_hash: str
    report_id: str


class TruthPairRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    job_id: str
    system: str
    cv: TruthDocumentRecord
    cover_letter: TruthDocumentRecord
    pair_external_use_allowed: bool
    truth_failure: bool


def evaluate_markdown_truth(
    markdown: str,
    *,
    profile: CareerProfile,
    artefact_kind: ArtefactKind,
    artefact_path: str | None = None,
    context_technology_labels: list[str] | None = None,
    service: TruthValidationService | None = None,
) -> tuple[TruthDocumentRecord, TruthReport]:
    bound = service or TruthValidationService()
    report = bound.validate_markdown(
        markdown=markdown,
        profile=profile,
        artefact_kind=artefact_kind,
        artefact_path=artefact_path,
        context_technology_labels=context_technology_labels,
    )
    allowed, messages = evaluate_report_for_external_use(
        report, current_markdown=markdown
    )
    blocking = [item for item in report.findings if item.severity == "blocking"]
    review = [item for item in report.findings if item.severity == "review_required"]
    summaries = [
        f"{item.severity}:{item.claim.claim_class}:{item.claim.object_key}"
        for item in report.findings
        if item.severity in {"blocking", "review_required"}
    ]
    record = TruthDocumentRecord(
        artefact_kind=artefact_kind,
        outcome=report.outcome,
        coverage_status=report.coverage_status,
        detection_performed=report.detection_performed,
        validation_performed=report.validation_performed,
        external_use_allowed=allowed,
        blocking_count=len(blocking),
        review_required_count=len(review),
        finding_summaries=summaries,
        messages=list(messages),
        content_hash=report.artefact.content_fingerprint,
        report_id=report.report_id,
    )
    return record, report


def evaluate_document_pair(
    *,
    job_id: str,
    system: str,
    cv_markdown: str,
    letter_markdown: str,
    profile: CareerProfile,
    context_technology_labels: list[str] | None = None,
    service: TruthValidationService | None = None,
) -> TruthPairRecord:
    bound = service or TruthValidationService()
    cv, _ = evaluate_markdown_truth(
        cv_markdown,
        profile=profile,
        artefact_kind="cv_markdown",
        artefact_path=f"{job_id}/{system}/cv.md",
        context_technology_labels=context_technology_labels,
        service=bound,
    )
    letter, _ = evaluate_markdown_truth(
        letter_markdown,
        profile=profile,
        artefact_kind="cover_letter_markdown",
        artefact_path=f"{job_id}/{system}/letter.md",
        context_technology_labels=context_technology_labels,
        service=bound,
    )
    allowed = cv.external_use_allowed and letter.external_use_allowed
    return TruthPairRecord(
        job_id=job_id,
        system=system,
        cv=cv,
        cover_letter=letter,
        pair_external_use_allowed=allowed,
        truth_failure=not allowed,
    )
