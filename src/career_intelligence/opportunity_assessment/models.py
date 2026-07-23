"""Typed domain models for FR-003 Opportunity Assessment.

These models compare a trusted JobAnalysis against a trusted CareerProfile and
produce evidence-backed fit analysis. They intentionally omit application tiers,
effort guidance, apply/skip recommendations, quota fields, and predictive scores.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from career_intelligence.job_analysis.models import JobAnalysis

NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]

FitJudgment = Literal["strong", "moderate", "mixed", "weak", "misaligned", "unknown"]

FitDimension = Literal["technical", "commercial", "portfolio"]

FindingKind = Literal[
    "alignment",
    "partial_alignment",
    "transferable_alignment",
    "gap",
    "conflict",
    "uncertainty",
    "assumption",
]

FindingImportance = Literal["material", "minor"]

JobEvidenceSource = Literal[
    "role_family",
    "seniority",
    "technology",
    "responsibility",
    "experience_requirement",
    "compensation",
    "location",
    "work_arrangement",
    "employment",
]

ProfileEvidenceSource = Literal[
    "skill",
    "experience",
    "project",
    "certification",
    "goal",
    "preference",
    "identity",
]

_EVIDENCE_KINDS = frozenset(
    {
        "alignment",
        "partial_alignment",
        "transferable_alignment",
        "gap",
        "conflict",
    }
)


class AssessmentModel(BaseModel):
    """Base model that rejects accidental schema drift."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class JobEvidenceRef(AssessmentModel):
    """Pointer to an analysed job requirement with optional supporting excerpt."""

    source: JobEvidenceSource
    item_index: int | None = Field(default=None, ge=0)
    name: NonEmptyString | None = None
    excerpt: NonEmptyString | None = None

    @model_validator(mode="after")
    def list_sources_require_item_index(self) -> JobEvidenceRef:
        if self.source in _LIST_JOB_SOURCES and self.item_index is None:
            raise ValueError(f"{self.source} job evidence requires item_index")
        return self


_LIST_JOB_SOURCES = frozenset(
    {
        "technology",
        "responsibility",
        "experience_requirement",
    }
)


class ProfileEvidenceRef(AssessmentModel):
    """Pointer to a career-profile entity. ``ref`` must resolve at service validation."""

    source: ProfileEvidenceSource
    ref: NonEmptyString
    excerpt: NonEmptyString | None = None

    @field_validator("ref")
    @classmethod
    def ref_is_exact_catalogue_token(cls, value: str) -> str:
        """Reject trailing punctuation that LLMs often append to catalogue tokens.

        Example failure: ``experience:chase-risk-compliance-ai-engineer.``
        Validation remains fail-closed — no silent stripping/repair.
        """
        if value != value.strip():
            raise ValueError(
                "profile evidence ref must not include leading/trailing whitespace"
            )
        if value[-1] in ".,;:!?)]":
            raise ValueError(
                "profile evidence ref must be an exact catalogue token with no "
                "trailing punctuation "
                f"(got '{value}')"
            )
        if ":" not in value:
            raise ValueError(
                "profile evidence ref must use namespace:id form "
                f"(got '{value}')"
            )
        return value


class FitFinding(AssessmentModel):
    """One atomic, explainable fit claim within a dimension."""

    kind: FindingKind
    summary: NonEmptyString
    detail: NonEmptyString | None = None
    importance: FindingImportance
    job_evidence: list[JobEvidenceRef] = Field(default_factory=list)
    profile_evidence: list[ProfileEvidenceRef] = Field(default_factory=list)
    assumption: NonEmptyString | None = None

    @model_validator(mode="after")
    def finding_fields_are_consistent(self) -> FitFinding:
        if self.kind == "assumption":
            if self.assumption is None:
                raise ValueError("assumption finding requires assumption text")
        else:
            if self.assumption is not None:
                raise ValueError("assumption text is only allowed when kind is 'assumption'")

        if self.kind in _EVIDENCE_KINDS:
            if not self.job_evidence:
                raise ValueError(f"{self.kind} finding requires at least one job evidence ref")
            if self.kind != "gap" and not self.profile_evidence:
                raise ValueError(f"{self.kind} finding requires at least one profile evidence ref")

        return self


class FitDimensionAssessment(AssessmentModel):
    """Evidence-backed fit analysis for one Phase 2 dimension."""

    dimension: FitDimension
    judgment: FitJudgment
    summary: NonEmptyString
    findings: list[FitFinding] = Field(min_length=1)

    @model_validator(mode="after")
    def judgment_reflects_material_gaps(self) -> FitDimensionAssessment:
        """Reject strong judgments that ignore material gap/conflict findings.

        No silent repair: assessors must emit a calibrated judgment.
        """
        has_material_negative = any(
            finding.importance == "material" and finding.kind in {"gap", "conflict"}
            for finding in self.findings
        )
        if has_material_negative and self.judgment == "strong":
            raise ValueError(
                f"{self.dimension} judgment 'strong' is inconsistent with material "
                "gap/conflict findings"
            )
        return self


class AssessmentSummary(AssessmentModel):
    """Cross-dimensional synthesis without tier or effort guidance."""

    summary: NonEmptyString
    key_alignments: list[NonEmptyString] = Field(default_factory=list, max_length=5)
    key_gaps: list[NonEmptyString] = Field(default_factory=list, max_length=5)


class OpportunityAssessment(AssessmentModel):
    """Trusted fit analysis comparing one job analysis to the candidate profile.

    ``job_analysis`` is bound by ``OpportunityAssessmentService`` from the
    caller-supplied trusted input. The profile is not embedded; profile-side
    grounding lives in ``ProfileEvidenceRef`` entries within findings.
    """

    job_analysis: JobAnalysis
    technical_fit: FitDimensionAssessment
    commercial_fit: FitDimensionAssessment
    portfolio_fit: FitDimensionAssessment
    summary: AssessmentSummary

    @model_validator(mode="after")
    def dimensions_match_declared_facet(self) -> OpportunityAssessment:
        expected: dict[FitDimension, FitDimensionAssessment] = {
            "technical": self.technical_fit,
            "commercial": self.commercial_fit,
            "portfolio": self.portfolio_fit,
        }
        for dimension, assessment in expected.items():
            if assessment.dimension != dimension:
                raise ValueError(
                    f"{dimension}_fit.dimension must be '{dimension}', "
                    f"got '{assessment.dimension}'"
                )
        return self
