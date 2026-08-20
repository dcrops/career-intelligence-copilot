"""Typed contracts for Recruiter Document Truth Validation (FR-014 M1).

Foundation only: claim / catalogue / finding / report schemas and provenance rules.
No claim detectors, catalogue population, CLI, package gates, or submission wiring.

ADR-006 invariants:
- Detection certainty is distinct from evidence / truth validation.
- Overall PASS requires complete coverage and performed detection + validation.
- Empty findings alone must not imply PASS.
- Ambiguous detection on material Class A is review-required or blocking.
- JD / assessment / strategy / plans never authorize Class A capability.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal, get_args

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)

from career_intelligence.opportunities.models import OpportunityId

NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]

TruthReportId = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        pattern=r"^trp_[0-9A-HJKMNP-TV-Z]{26}$",
    ),
]

TruthFindingId = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        pattern=r"^tfd_[0-9A-HJKMNP-TV-Z]{26}$",
    ),
]

ClaimId = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        pattern=r"^tcl_[0-9A-HJKMNP-TV-Z]{26}$",
    ),
]

CatalogueEntryId = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        pattern=r"^tee_[0-9A-HJKMNP-TV-Z]{26}$",
    ),
]

ClaimClass = Literal["A", "B", "C", "D"]
CLAIM_CLASSES: tuple[ClaimClass, ...] = get_args(ClaimClass)

ClaimKind = Literal[
    "technology",
    "employment",
    "duration",
    "certification",
    "education",
    "domain",
    "project_delivery",
    "identity",
    "other",
]
CLAIM_KINDS: tuple[ClaimKind, ...] = get_args(ClaimKind)

ClaimSubject = Literal["candidate", "employer", "role", "project"]

ClaimStrength = Literal[
    "mentioned",
    "used",
    "experienced",
    "proficient",
    "strongest",
    "expert",
    "interested",
]
CLAIM_STRENGTHS: tuple[ClaimStrength, ...] = get_args(ClaimStrength)

# ADR-006: detection certainty ≠ evidence / truth status
DetectionCertainty = Literal["certain", "ambiguous"]
DETECTION_CERTAINTIES: tuple[DetectionCertainty, ...] = get_args(DetectionCertainty)

EvidenceStatus = Literal[
    "supported",
    "unsupported",
    "ambiguous",
    "contradictory",
    "not_applicable",
]
EVIDENCE_STATUSES: tuple[EvidenceStatus, ...] = get_args(EvidenceStatus)

FindingSeverity = Literal["info", "warning", "review_required", "blocking"]
FINDING_SEVERITIES: tuple[FindingSeverity, ...] = get_args(FindingSeverity)

TruthOutcome = Literal["pass", "warning", "review_required", "fail"]
TRUTH_OUTCOMES: tuple[TruthOutcome, ...] = get_args(TruthOutcome)

# Validator identity for persisted reports (freshness is content-hash based).
VALIDATOR_VERSION = "fr014-truth-alignment-2"

CoverageStatus = Literal["complete", "partial", "insufficient"]
COVERAGE_STATUSES: tuple[CoverageStatus, ...] = get_args(CoverageStatus)

EvidenceAuthority = Literal["candidate_authoritative", "context_only"]
EVIDENCE_AUTHORITIES: tuple[EvidenceAuthority, ...] = get_args(EvidenceAuthority)

EvidenceSourceKind = Literal[
    "career_profile",
    "profile_skill",
    "profile_experience",
    "profile_project",
    "profile_certification",
    "profile_education",
    "profile_identity",
    "job_analysis",
    "opportunity_assessment",
    "portfolio_match",
    "application_strategy",
    "tailoring_plan",
    "cover_letter_plan",
    "artefact_text",
    "other",
]
EVIDENCE_SOURCE_KINDS: tuple[EvidenceSourceKind, ...] = get_args(EvidenceSourceKind)

ArtefactKind = Literal[
    "cv_markdown",
    "cover_letter_markdown",
    "tailoring_plan",
    "cover_letter_plan",
    "other",
]

ValidationGate = Literal["generation_advisory", "post_edit_authoritative"]

CANDIDATE_AUTHORITATIVE_SOURCES: frozenset[EvidenceSourceKind] = frozenset(
    {
        "career_profile",
        "profile_skill",
        "profile_experience",
        "profile_project",
        "profile_certification",
        "profile_education",
        "profile_identity",
    }
)

CONTEXT_ONLY_SOURCES: frozenset[EvidenceSourceKind] = frozenset(
    {
        "job_analysis",
        "opportunity_assessment",
        "portfolio_match",
        "application_strategy",
        "tailoring_plan",
        "cover_letter_plan",
        "artefact_text",
    }
)

HIGH_CLAIM_STRENGTHS: frozenset[ClaimStrength] = frozenset(
    {"proficient", "strongest", "expert"}
)

_SEVERITY_RANK: dict[FindingSeverity, int] = {
    "info": 0,
    "warning": 1,
    "review_required": 2,
    "blocking": 3,
}

_OUTCOME_RANK: dict[TruthOutcome, int] = {
    "pass": 0,
    "warning": 1,
    "review_required": 2,
    "fail": 3,
}


class TruthModel(BaseModel):
    """Base model that rejects accidental schema drift."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class ArtefactRef(TruthModel):
    """Pointer to the recruiter-facing artefact under validation."""

    kind: ArtefactKind
    path: NonEmptyString | None = None
    content_fingerprint: NonEmptyString | None = None


class EvidenceProvenance(TruthModel):
    """Where a catalogue fact or finding citation came from."""

    source_kind: EvidenceSourceKind
    authority: EvidenceAuthority
    provenance_ref: NonEmptyString
    excerpt: NonEmptyString | None = None

    @model_validator(mode="after")
    def _authority_matches_source(self) -> EvidenceProvenance:
        if (
            self.source_kind in CANDIDATE_AUTHORITATIVE_SOURCES
            and self.authority != "candidate_authoritative"
        ):
            raise ValueError(
                "profile-derived sources must use authority=candidate_authoritative"
            )
        if (
            self.source_kind in CONTEXT_ONLY_SOURCES
            and self.authority != "context_only"
        ):
            raise ValueError(
                "JD / assessment / strategy / plan / artefact sources must use "
                "authority=context_only"
            )
        if (
            self.source_kind == "other"
            and self.authority == "candidate_authoritative"
        ):
            raise ValueError(
                "authority=candidate_authoritative requires a profile-derived "
                "source_kind (not 'other')"
            )
        return self


class CatalogueEvidenceEntry(TruthModel):
    """One normalised candidate or context fact in the evidence catalogue contract.

    M1 defines the schema only. Population from Career Profile is deferred to M2.
    """

    entry_id: CatalogueEntryId
    object_key: NonEmptyString
    display_label: NonEmptyString | None = None
    aliases: list[NonEmptyString] = Field(default_factory=list)
    claim_kinds: list[ClaimKind] = Field(default_factory=list)
    employment_kind: (
        Literal["commercial", "independent", "portfolio", "other"] | None
    ) = None
    recency: Literal["current", "recent", "historical", "unspecified"] | None = None
    # Deterministic tenure support for duration claims (years); None when unknown.
    supported_years: float | None = None
    provenance: EvidenceProvenance


class CandidateEvidenceCatalogue(TruthModel):
    """Contract for the deterministic evidence catalogue (no builder in M1)."""

    catalogue_id: NonEmptyString
    built_at: datetime
    profile_fingerprint: NonEmptyString | None = None
    entries: list[CatalogueEvidenceEntry] = Field(default_factory=list)

    @model_validator(mode="after")
    def _unique_entry_ids(self) -> CandidateEvidenceCatalogue:
        ids = [entry.entry_id for entry in self.entries]
        if len(ids) != len(set(ids)):
            raise ValueError("catalogue entry_id values must be unique")
        return self


class Claim(TruthModel):
    """Structured representation of a factual assertion (detected or planned)."""

    claim_id: ClaimId
    claim_class: ClaimClass
    claim_kind: ClaimKind
    subject: ClaimSubject
    predicate: NonEmptyString
    object_key: NonEmptyString
    strength: ClaimStrength
    surface_text: NonEmptyString
    source_artefact: ArtefactKind
    span_hint: NonEmptyString | None = None

    @model_validator(mode="after")
    def _class_subject_consistency(self) -> Claim:
        if self.claim_class == "A" and self.subject != "candidate":
            raise ValueError("Class A claims must have subject=candidate")
        if self.claim_class == "B" and self.subject not in {"employer", "role"}:
            raise ValueError("Class B claims must have subject=employer or role")
        return self


class TruthFinding(TruthModel):
    """One explainable finding: detection dimension + evidence dimension.

    ``detection_certainty`` answers: how sure are we this is the claim we think?
    ``evidence_status`` answers: does candidate evidence support it?
    These must not be collapsed (ADR-006).
    """

    finding_id: TruthFindingId
    claim: Claim
    detection_certainty: DetectionCertainty
    evidence_status: EvidenceStatus
    severity: FindingSeverity
    evidence_citations: list[EvidenceProvenance] = Field(default_factory=list)
    recommended_action: NonEmptyString
    notes: NonEmptyString | None = None

    @model_validator(mode="after")
    def _class_a_supported_needs_authoritative_citation(self) -> TruthFinding:
        if (
            self.claim.claim_class == "A"
            and self.evidence_status == "supported"
        ):
            authoritative = [
                cite
                for cite in self.evidence_citations
                if cite.authority == "candidate_authoritative"
            ]
            if not authoritative:
                raise ValueError(
                    "Class A supported findings require at least one "
                    "candidate_authoritative evidence citation"
                )
        return self

    @model_validator(mode="after")
    def _class_a_cannot_be_supported_by_context_only(self) -> TruthFinding:
        if self.claim.claim_class != "A" or self.evidence_status != "supported":
            return self
        if any(cite.authority == "context_only" for cite in self.evidence_citations):
            # Context citations may appear alongside authoritative ones for
            # leakage explanation, but support must not rely on them alone —
            # already enforced above. Reject pure context-only support lists.
            if all(
                cite.authority == "context_only" for cite in self.evidence_citations
            ):
                raise ValueError(
                    "Class A claims must not be supported by context-only sources "
                    "(JD / assessment / strategy / plans)"
                )
        return self

    @model_validator(mode="after")
    def _ambiguous_detection_severity(self) -> TruthFinding:
        if (
            self.detection_certainty == "ambiguous"
            and self.claim.claim_class == "A"
            and _SEVERITY_RANK[self.severity] < _SEVERITY_RANK["review_required"]
        ):
            raise ValueError(
                "ambiguous detection on Class A requires severity "
                "review_required or blocking"
            )
        if (
            self.detection_certainty == "ambiguous"
            and self.claim.claim_class == "A"
            and self.claim.strength in HIGH_CLAIM_STRENGTHS
            and self.severity != "blocking"
        ):
            raise ValueError(
                "ambiguous detection on high-strength Class A requires "
                "severity=blocking"
            )
        return self

    @model_validator(mode="after")
    def _unsupported_class_a_is_blocking(self) -> TruthFinding:
        if (
            self.claim.claim_class == "A"
            and self.evidence_status in {"unsupported", "contradictory"}
            and self.severity != "blocking"
        ):
            raise ValueError(
                "unsupported or contradictory Class A evidence requires "
                "severity=blocking"
            )
        return self


class TruthReport(TruthModel):
    """Explainable validation result for one artefact at one gate.

    Overall ``outcome=pass`` is never implied by an empty findings list alone.
    Coverage + performed detection/validation flags are required (ADR-006).
    """

    report_id: TruthReportId
    created_at: datetime
    gate: ValidationGate
    artefact: ArtefactRef
    opportunity_id: OpportunityId | None = None
    catalogue_id: NonEmptyString | None = None
    coverage_status: CoverageStatus
    detection_performed: bool
    validation_performed: bool
    findings: list[TruthFinding] = Field(default_factory=list)
    outcome: TruthOutcome
    summary: NonEmptyString
    validator_version: NonEmptyString = VALIDATOR_VERSION

    @model_validator(mode="after")
    def _unique_finding_ids(self) -> TruthReport:
        ids = [finding.finding_id for finding in self.findings]
        if len(ids) != len(set(ids)):
            raise ValueError("finding_id values must be unique within a report")
        return self

    @model_validator(mode="after")
    def _pass_requires_complete_assessed_coverage(self) -> TruthReport:
        if self.outcome != "pass":
            return self
        if self.coverage_status != "complete":
            raise ValueError(
                "outcome=pass requires coverage_status=complete "
                "(absence of detection is not proof of truth)"
            )
        if not self.detection_performed or not self.validation_performed:
            raise ValueError(
                "outcome=pass requires detection_performed and "
                "validation_performed to be true"
            )
        return self

    @model_validator(mode="after")
    def _outcome_matches_finding_severity(self) -> TruthReport:
        if not self.findings:
            return self
        worst = max(self.findings, key=lambda item: _SEVERITY_RANK[item.severity])
        expected = _outcome_for_severity(worst.severity)
        if _OUTCOME_RANK[self.outcome] < _OUTCOME_RANK[expected]:
            raise ValueError(
                f"outcome={self.outcome!r} is weaker than required by finding "
                f"severity={worst.severity!r} (need at least {expected!r})"
            )
        return self

    @model_validator(mode="after")
    def _insufficient_coverage_not_pass(self) -> TruthReport:
        if (
            self.coverage_status in {"partial", "insufficient"}
            and self.outcome == "pass"
        ):
            raise ValueError(
                "partial or insufficient coverage cannot yield outcome=pass"
            )
        if (
            self.coverage_status == "insufficient"
            and _OUTCOME_RANK[self.outcome] < _OUTCOME_RANK["review_required"]
        ):
            raise ValueError(
                "insufficient coverage requires outcome review_required or fail"
            )
        return self


def _outcome_for_severity(severity: FindingSeverity) -> TruthOutcome:
    if severity == "blocking":
        return "fail"
    if severity == "review_required":
        return "review_required"
    if severity == "warning":
        return "warning"
    return "pass"
