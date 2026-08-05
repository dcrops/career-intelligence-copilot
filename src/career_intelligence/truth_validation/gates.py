"""Fail-closed external-use gates for recruiter-facing Markdown (FR-014 M3).

A package is ready for external use only when every in-scope Markdown document
has a current TruthReport that:
- matches the Markdown content hash (not stale)
- has complete coverage with detection + validation performed
- has outcome ``pass`` or ``warning`` (not ``fail`` / ``review_required``)
- has no blocking findings

Missing or stale reports block. JD context never authorizes capability.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from career_intelligence.application_package.models import ApplicationPackageManifest
from career_intelligence.profile.models import CareerProfile
from career_intelligence.truth_validation.hashing import (
    hashes_match,
    markdown_content_hash,
    read_markdown,
)
from career_intelligence.truth_validation.models import (
    ArtefactKind,
    NonEmptyString,
    TruthOutcome,
    TruthReport,
)
from career_intelligence.truth_validation.service import TruthValidationService
from career_intelligence.truth_validation.store import JsonDirectoryTruthReportStore

_IN_SCOPE: tuple[tuple[ArtefactKind, str], ...] = (
    ("cv_markdown", "cv"),
    ("cover_letter_markdown", "cover_letter"),
)

_ALLOWED_OUTCOMES: frozenset[TruthOutcome] = frozenset({"pass", "warning"})


class TruthGateError(Exception):
    """Raised when external-use / submission truth preconditions fail."""


class DocumentTruthStatus(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    artefact_kind: ArtefactKind
    markdown_path: NonEmptyString
    content_hash: NonEmptyString | None = None
    report_id: NonEmptyString | None = None
    report_path: NonEmptyString | None = None
    outcome: TruthOutcome | None = None
    coverage_status: NonEmptyString | None = None
    fresh: bool = False
    external_use_allowed: bool = False
    messages: list[NonEmptyString] = Field(default_factory=list)


class PackageTruthStatus(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    opportunity_id: NonEmptyString
    documents: list[DocumentTruthStatus] = Field(default_factory=list)
    external_use_allowed: bool = False
    messages: list[NonEmptyString] = Field(default_factory=list)


def evaluate_report_for_external_use(
    report: TruthReport,
    *,
    current_markdown: str,
) -> tuple[bool, list[str]]:
    """Return (allowed, messages) for one report against current Markdown bytes."""
    messages: list[str] = []
    actual = markdown_content_hash(current_markdown)
    stored = report.artefact.content_fingerprint
    fresh = hashes_match(stored, actual)
    if not fresh:
        messages.append(
            f"Truth report {report.report_id} is stale relative to Markdown "
            f"(stored hash does not match current bytes)"
        )
    if report.coverage_status != "complete":
        messages.append(
            f"Coverage is {report.coverage_status!r}; require complete"
        )
    if not report.detection_performed:
        messages.append("Detection was not performed")
    if not report.validation_performed:
        messages.append("Validation was not performed")
    if report.outcome not in _ALLOWED_OUTCOMES:
        messages.append(
            f"Outcome is {report.outcome!r}; require pass or warning for external use"
        )
    blocking = [f for f in report.findings if f.severity == "blocking"]
    if blocking:
        messages.append(
            f"{len(blocking)} blocking finding(s) present "
            f"({', '.join(sorted({f.claim.object_key for f in blocking}))})"
        )
    if report.outcome == "review_required":
        messages.append("Review-required findings block external use (ADR-006)")
    allowed = (
        fresh
        and report.coverage_status == "complete"
        and report.detection_performed
        and report.validation_performed
        and report.outcome in _ALLOWED_OUTCOMES
        and not blocking
    )
    return allowed, messages


def evaluate_package_truth(
    *,
    manifest: ApplicationPackageManifest,
    profile: CareerProfile,
    store: JsonDirectoryTruthReportStore | None = None,
    service: TruthValidationService | None = None,
    revalidate: bool = False,
    context_technology_labels: list[str] | None = None,
) -> PackageTruthStatus:
    """Evaluate CV + cover-letter Markdown for fail-closed external use."""
    store = store or JsonDirectoryTruthReportStore()
    service = service or TruthValidationService()
    documents: list[DocumentTruthStatus] = []
    package_messages: list[str] = []

    for artefact_kind, attr in _IN_SCOPE:
        refs = getattr(manifest, attr)
        md_path = Path(refs.markdown_path)
        doc = _evaluate_document(
            opportunity_id=manifest.opportunity_id,
            artefact_kind=artefact_kind,
            markdown_path=md_path,
            profile=profile,
            store=store,
            service=service,
            revalidate=revalidate,
            context_technology_labels=context_technology_labels,
        )
        documents.append(doc)
        if not doc.external_use_allowed:
            package_messages.extend(
                f"{artefact_kind}: {msg}" for msg in doc.messages
            )

    allowed = bool(documents) and all(doc.external_use_allowed for doc in documents)
    if allowed:
        package_messages.append("Truth validation allows external use")
    else:
        package_messages.append("Truth validation blocks external use")

    return PackageTruthStatus(
        opportunity_id=manifest.opportunity_id,
        documents=documents,
        external_use_allowed=allowed,
        messages=package_messages,  # type: ignore[arg-type]
    )


def require_package_external_use(
    *,
    manifest: ApplicationPackageManifest,
    profile: CareerProfile,
    store: JsonDirectoryTruthReportStore | None = None,
    service: TruthValidationService | None = None,
    revalidate: bool = False,
) -> PackageTruthStatus:
    """Raise TruthGateError when the package is not ready for external use."""
    status = evaluate_package_truth(
        manifest=manifest,
        profile=profile,
        store=store,
        service=service,
        revalidate=revalidate,
    )
    if not status.external_use_allowed:
        detail = "; ".join(status.messages)
        raise TruthGateError(
            f"Truth validation blocks external use for "
            f"{manifest.opportunity_id}: {detail}"
        )
    return status


def _evaluate_document(
    *,
    opportunity_id: str,
    artefact_kind: ArtefactKind,
    markdown_path: Path,
    profile: CareerProfile,
    store: JsonDirectoryTruthReportStore,
    service: TruthValidationService,
    revalidate: bool,
    context_technology_labels: list[str] | None,
) -> DocumentTruthStatus:
    messages: list[str] = []
    if not markdown_path.is_file():
        return DocumentTruthStatus(
            artefact_kind=artefact_kind,
            markdown_path=str(markdown_path),
            external_use_allowed=False,
            messages=[f"Markdown missing: {markdown_path}"],
        )

    markdown = read_markdown(markdown_path)
    content_hash = markdown_content_hash(markdown)
    report: TruthReport | None = None
    report_path: Path | None = None

    if revalidate:
        report = service.validate_markdown(
            markdown=markdown,
            profile=profile,
            artefact_kind=artefact_kind,
            artefact_path=str(markdown_path),
            opportunity_id=opportunity_id,
            context_technology_labels=context_technology_labels,
        )
        report_path = store.save(report, as_current=True)
    else:
        report = store.load_current(opportunity_id, artefact_kind)
        report_path = (
            store.current_path(opportunity_id, artefact_kind) if report else None
        )

    if report is None:
        return DocumentTruthStatus(
            artefact_kind=artefact_kind,
            markdown_path=str(markdown_path),
            content_hash=content_hash,
            external_use_allowed=False,
            messages=[
                f"No current TruthReport for {artefact_kind}; "
                "run cic truth validate-package"
            ],
        )

    allowed, gate_messages = evaluate_report_for_external_use(
        report,
        current_markdown=markdown,
    )
    messages.extend(gate_messages)
    fresh = hashes_match(report.artefact.content_fingerprint, content_hash)
    return DocumentTruthStatus(
        artefact_kind=artefact_kind,
        markdown_path=str(markdown_path),
        content_hash=content_hash,
        report_id=report.report_id,
        report_path=str(report_path) if report_path else None,
        outcome=report.outcome,
        coverage_status=report.coverage_status,
        fresh=fresh,
        external_use_allowed=allowed,
        messages=messages,  # type: ignore[arg-type]
    )
