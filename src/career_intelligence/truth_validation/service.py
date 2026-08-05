"""TruthValidationService — catalogue + deterministic claim validation (FR-014).

Validates recruiter-facing Markdown for technology and M4 claim kinds
(employment honesty, certification, duration, project delivery, domain).
No rewriting or LLM judgement. CLI / package gates live in M3 modules.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from career_intelligence.profile.models import CareerProfile
from career_intelligence.truth_validation.hashing import markdown_content_hash
from career_intelligence.truth_validation.catalogue import (
    build_catalogue_from_profile,
    catalogue_entry_by_key,
    catalogue_supports_kind,
    catalogue_supports_technology,
)
from career_intelligence.truth_validation.contracts import validate_truth_report_contract
from career_intelligence.truth_validation.detection import (
    DetectedTechnologySpan,
    detect_technology_spans,
)
from career_intelligence.truth_validation.extended_claims import (
    DetectedExtendedSpan,
    detect_extended_spans,
)
from career_intelligence.truth_validation.ids import (
    new_claim_id,
    new_truth_finding_id,
    new_truth_report_id,
)
from career_intelligence.truth_validation.models import (
    HIGH_CLAIM_STRENGTHS,
    VALIDATOR_VERSION,
    ArtefactKind,
    ArtefactRef,
    CandidateEvidenceCatalogue,
    Claim,
    FindingSeverity,
    TruthFinding,
    TruthOutcome,
    TruthReport,
    ValidationGate,
)
from career_intelligence.truth_validation.normalise import normalise_object_key


class TruthValidationService:
    """Deterministic recruiter-document truth validation (technology + M4 kinds)."""

    def build_catalogue(
        self,
        profile: CareerProfile,
        *,
        built_at: datetime | None = None,
        catalogue_id: str | None = None,
    ) -> CandidateEvidenceCatalogue:
        """Populate CandidateEvidenceCatalogue from authoritative profile sources."""
        return build_catalogue_from_profile(
            profile,
            built_at=built_at,
            catalogue_id=catalogue_id,
        )

    def validate_markdown(
        self,
        *,
        markdown: str,
        profile: CareerProfile | None = None,
        catalogue: CandidateEvidenceCatalogue | None = None,
        artefact_kind: ArtefactKind = "cover_letter_markdown",
        artefact_path: str | None = None,
        gate: ValidationGate = "post_edit_authoritative",
        opportunity_id: str | None = None,
        context_technology_labels: list[str] | None = None,
        created_at: datetime | None = None,
    ) -> TruthReport:
        """Detect and validate recruiter-facing claims in Markdown; return a TruthReport.

        Covers technology (M2) plus employment, certification, duration, delivery,
        and domain (M4). ``context_technology_labels`` expand the tech scan lexicon
        only and never authorize Class A support.
        """
        if catalogue is None:
            if profile is None:
                raise ValueError("profile or catalogue is required")
            catalogue = self.build_catalogue(profile)
        elif profile is None:
            pass

        when = created_at or datetime.now(tz=UTC)
        technology_spans = detect_technology_spans(
            markdown,
            catalogue,
            extra_labels=context_technology_labels,
        )
        extended_spans = detect_extended_spans(markdown, catalogue)
        findings = [
            self._finding_for_span(span, catalogue, artefact_kind=artefact_kind)
            for span in technology_spans
        ]
        seen = {("technology", finding.claim.object_key, finding.claim.span_hint) for finding in findings}
        for span in extended_spans:
            key = (span.claim_kind, span.object_key, span.sentence[:240])
            if key not in seen:
                findings.append(
                    self._finding_for_extended_span(
                        span, catalogue, artefact_kind=artefact_kind
                    )
                )
                seen.add(key)
        outcome = _aggregate_outcome(findings)
        summary = _summary_for(findings, outcome)
        report = TruthReport(
            report_id=new_truth_report_id(),
            created_at=when,
            gate=gate,
            artefact=ArtefactRef(
                kind=artefact_kind,
                path=artefact_path,
                content_fingerprint=markdown_content_hash(markdown),
            ),
            opportunity_id=opportunity_id,  # type: ignore[arg-type]
            catalogue_id=catalogue.catalogue_id,
            coverage_status="complete",
            detection_performed=True,
            validation_performed=True,
            findings=findings,
            outcome=outcome,
            summary=summary,
            validator_version=VALIDATOR_VERSION,
        )
        validate_truth_report_contract(report)
        return report

    def validate_markdown_path(
        self,
        path: Path,
        *,
        profile: CareerProfile | None = None,
        catalogue: CandidateEvidenceCatalogue | None = None,
        artefact_kind: ArtefactKind | None = None,
        gate: ValidationGate = "post_edit_authoritative",
        opportunity_id: str | None = None,
        context_technology_labels: list[str] | None = None,
    ) -> TruthReport:
        """Validate a Markdown file on disk."""
        from career_intelligence.truth_validation.hashing import read_markdown

        text = read_markdown(path)
        kind = artefact_kind or _infer_artefact_kind(path)
        return self.validate_markdown(
            markdown=text,
            profile=profile,
            catalogue=catalogue,
            artefact_kind=kind,
            artefact_path=str(path),
            gate=gate,
            opportunity_id=opportunity_id,
            context_technology_labels=context_technology_labels,
        )

    def _finding_for_span(
        self,
        span: DetectedTechnologySpan,
        catalogue: CandidateEvidenceCatalogue,
        *,
        artefact_kind: ArtefactKind,
    ) -> TruthFinding:
        claim = Claim(
            claim_id=new_claim_id(),
            claim_class=span.claim_class,
            claim_kind="technology",
            subject=(
                "candidate"
                if span.claim_class in {"A", "C"}
                else "role"
            ),
            predicate=(
                "has_skill"
                if span.claim_class == "A"
                else "requires_skill"
                if span.claim_class == "B"
                else "interested_in_skill"
            ),
            object_key=span.object_key,
            strength=span.strength,
            surface_text=span.surface_text,
            source_artefact=artefact_kind,
            span_hint=span.sentence[:240],
        )
        detection_certainty = span.detection_certainty  # type: ignore[assignment]

        if span.claim_class == "B":
            return TruthFinding(
                finding_id=new_truth_finding_id(),
                claim=claim,
                detection_certainty=detection_certainty,
                evidence_status="not_applicable",
                severity="info",
                evidence_citations=[],
                recommended_action="none — employer/role context; not a candidate claim",
                notes=span.sentence[:300],
            )

        if span.claim_class == "C":
            supported = catalogue_supports_technology(catalogue, span.label)
            return TruthFinding(
                finding_id=new_truth_finding_id(),
                claim=claim,
                detection_certainty=detection_certainty,
                evidence_status="not_applicable",
                severity="info" if not _implies_expertise(span) else "warning",
                evidence_citations=(
                    [supported.provenance] if supported is not None else []
                ),
                recommended_action=(
                    "none — aspiration framing"
                    if not _implies_expertise(span)
                    else "ensure aspiration does not imply existing expertise"
                ),
                notes=span.sentence[:300],
            )

        # Class A — candidate capability
        entry = catalogue_supports_technology(catalogue, span.label)
        if entry is not None:
            return TruthFinding(
                finding_id=new_truth_finding_id(),
                claim=claim,
                detection_certainty=detection_certainty,
                evidence_status="supported",
                severity="info",
                evidence_citations=[entry.provenance],
                recommended_action="none — supported by candidate evidence",
                notes=(
                    f"Supported via {entry.provenance.source_kind} "
                    f"({entry.provenance.provenance_ref})"
                ),
            )

        # Unsupported Class A
        severity: FindingSeverity
        if detection_certainty == "ambiguous":
            severity = (
                "blocking"
                if span.strength in HIGH_CLAIM_STRENGTHS
                else "review_required"
            )
            evidence_status = "ambiguous"
            action = (
                "clarify framing or remove unsupported capability implication "
                f"for {span.surface_text}"
            )
        else:
            severity = "blocking"
            evidence_status = "unsupported"
            action = (
                "remove or reframe unsupported candidate technology claim: "
                f"{span.surface_text}"
            )

        return TruthFinding(
            finding_id=new_truth_finding_id(),
            claim=claim,
            detection_certainty=detection_certainty,
            evidence_status=evidence_status,
            severity=severity,
            evidence_citations=[],
            recommended_action=action,
            notes=(
                f"No candidate_authoritative catalogue entry for "
                f"{normalise_object_key(span.label)!r}. "
                "JD/context labels cannot authorize capability. "
                f"Sentence: {span.sentence[:240]}"
            ),
        )

    def _finding_for_extended_span(
        self,
        span: DetectedExtendedSpan,
        catalogue: CandidateEvidenceCatalogue,
        *,
        artefact_kind: ArtefactKind,
    ) -> TruthFinding:
        claim = Claim(
            claim_id=new_claim_id(),
            claim_class=span.claim_class,
            claim_kind=span.claim_kind,
            subject="candidate" if span.claim_class in {"A", "C"} else "role",
            predicate=span.predicate,
            object_key=span.object_key,
            strength=span.strength,
            surface_text=span.surface_text,
            source_artefact=artefact_kind,
            span_hint=span.sentence[:240],
        )
        certainty = span.detection_certainty  # type: ignore[assignment]
        if span.claim_class == "B":
            return _non_candidate_finding(claim, certainty, span.sentence, "employer/role context")
        if span.claim_class == "C":
            return _non_candidate_finding(claim, certainty, span.sentence, "aspiration framing")

        if span.claim_kind == "employment":
            entry = catalogue_entry_by_key(catalogue, span.object_key, kinds=("employment",))
            return self._supported_or_blocking(
                claim, certainty, entry, span.sentence, "employment history"
            )
        if span.claim_kind in {"certification", "domain"}:
            entry = catalogue_supports_kind(
                catalogue, span.object_key, kinds=(span.claim_kind,)
            )
            return self._supported_or_blocking(
                claim, certainty, entry, span.sentence, span.claim_kind
            )
        if span.claim_kind == "project_delivery":
            entry = catalogue_supports_kind(
                catalogue, span.object_key, kinds=("project_delivery",)
            )
            if certainty == "ambiguous":
                return _review_finding(claim, certainty, span.sentence, "identify the delivered project before external use")
            return self._supported_or_blocking(
                claim, certainty, entry, span.sentence, "project delivery"
            )
        # duration
        entry = catalogue_entry_by_key(catalogue, span.object_key)
        if certainty == "ambiguous" or span.years_precision == "ambiguous":
            return _review_finding(claim, certainty, span.sentence, "clarify the duration subject before external use")
        if entry is None or entry.supported_years is None:
            return _review_finding(claim, certainty, span.sentence, "candidate evidence cannot deterministically estimate this duration")
        if span.claimed_years is not None and span.claimed_years > entry.supported_years + 0.5:
            return TruthFinding(
                finding_id=new_truth_finding_id(), claim=claim,
                detection_certainty=certainty, evidence_status="contradictory",
                severity="blocking", evidence_citations=[entry.provenance],
                recommended_action="reduce or remove duration claim unsupported by candidate evidence",
                notes=f"Claimed {span.claimed_years:g} years; supported {entry.supported_years:g} years. {span.sentence[:200]}",
            )
        return self._supported_or_blocking(claim, certainty, entry, span.sentence, "duration")

    def _supported_or_blocking(
        self, claim: Claim, certainty: str, entry: object | None, sentence: str, label: str
    ) -> TruthFinding:
        if entry is not None:
            provenance = entry.provenance  # type: ignore[union-attr]
            return TruthFinding(
                finding_id=new_truth_finding_id(), claim=claim,
                detection_certainty=certainty, evidence_status="supported", severity="info",
                evidence_citations=[provenance], recommended_action="none — supported by candidate evidence",
                notes=f"Supported {label}: {sentence[:240]}",
            )
        return TruthFinding(
            finding_id=new_truth_finding_id(), claim=claim,
            detection_certainty=certainty, evidence_status="unsupported", severity="blocking",
            evidence_citations=[], recommended_action=f"remove or reframe unsupported candidate {label} claim",
            notes=f"No candidate-authoritative support. {sentence[:240]}",
        )


def _non_candidate_finding(
    claim: Claim, certainty: str, sentence: str, reason: str
) -> TruthFinding:
    return TruthFinding(
        finding_id=new_truth_finding_id(), claim=claim,
        detection_certainty=certainty, evidence_status="not_applicable", severity="info",
        evidence_citations=[], recommended_action=f"none — {reason}",
        notes=sentence[:300],
    )


def _review_finding(
    claim: Claim, certainty: str, sentence: str, action: str
) -> TruthFinding:
    return TruthFinding(
        finding_id=new_truth_finding_id(), claim=claim,
        detection_certainty=certainty, evidence_status="ambiguous",
        severity="review_required", evidence_citations=[],
        recommended_action=action, notes=sentence[:300],
    )


def _implies_expertise(span: DetectedTechnologySpan) -> bool:
    return span.strength in HIGH_CLAIM_STRENGTHS


def _aggregate_outcome(findings: list[TruthFinding]) -> TruthOutcome:
    if not findings:
        return "pass"
    rank = {"info": 0, "warning": 1, "review_required": 2, "blocking": 3}
    worst = max(findings, key=lambda item: rank[item.severity])
    if worst.severity == "blocking":
        return "fail"
    if worst.severity == "review_required":
        return "review_required"
    if worst.severity == "warning":
        return "warning"
    return "pass"


def _summary_for(findings: list[TruthFinding], outcome: TruthOutcome) -> str:
    blocking = sum(1 for item in findings if item.severity == "blocking")
    review = sum(1 for item in findings if item.severity == "review_required")
    supported = sum(
        1
        for item in findings
        if item.claim.claim_class == "A" and item.evidence_status == "supported"
    )
    employer = sum(1 for item in findings if item.claim.claim_class == "B")
    if outcome == "pass":
        return (
            f"Truth validation complete: {supported} supported candidate "
            f"claim(s), {employer} employer-context mention(s); no blocking issues."
        )
    return (
        f"Truth validation {outcome}: {blocking} blocking, "
        f"{review} review-required, {supported} supported, "
        f"{employer} employer-context finding(s)."
    )


def _fingerprint(markdown: str) -> str:
    return markdown_content_hash(markdown)


def _infer_artefact_kind(path: Path) -> ArtefactKind:
    name = path.name.casefold()
    parts = str(path).casefold().replace("\\", "/")
    if "cover" in name or "cover-letter" in parts or "cover_letter" in parts:
        return "cover_letter_markdown"
    if name.endswith(".md"):
        return "cv_markdown"
    return "cover_letter_markdown"
