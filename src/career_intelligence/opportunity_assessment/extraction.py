"""Internal assessment schema for FR-003 AI-backed assessors.

``OpportunityAssessmentExtraction`` is the structured-output contract for assessors.
It intentionally excludes ``job_analysis`` and any caller-owned profile binding —
the service alone binds trusted inputs after assessment.

Nested finding types here are extraction-specific (not domain ``FitFinding``) so the
JSON Schema emitted to the model enforces non-empty evidence arrays for kinds that
require them. Domain ``FitFinding`` validators remain the fail-closed trust boundary
and are unchanged.

``kind`` is declared first in every branch, and the union is a plain ``Union`` rather
than a Pydantic discriminated union: a ``Field(discriminator=...)`` emits ``oneOf``,
which OpenAI structured outputs rejects (``'oneOf' is not permitted``). A plain union
emits ``anyOf``, and the leading ``Literal`` ``kind`` const keeps branches unambiguous.
"""

from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import Field, model_validator

from .models import (
    AssessmentModel,
    AssessmentSummary,
    FindingImportance,
    FitDimension,
    FitJudgment,
    JobEvidenceRef,
    NonEmptyString,
    ProfileEvidenceRef,
)

RequiredJobEvidence = Annotated[list[JobEvidenceRef], Field(min_length=1)]
RequiredProfileEvidence = Annotated[list[ProfileEvidenceRef], Field(min_length=1)]


class AlignmentExtractionFinding(AssessmentModel):
    kind: Literal["alignment"]
    summary: NonEmptyString
    detail: NonEmptyString | None = None
    importance: FindingImportance
    job_evidence: RequiredJobEvidence
    profile_evidence: RequiredProfileEvidence
    assumption: None = None


class PartialAlignmentExtractionFinding(AssessmentModel):
    kind: Literal["partial_alignment"]
    summary: NonEmptyString
    detail: NonEmptyString | None = None
    importance: FindingImportance
    job_evidence: RequiredJobEvidence
    profile_evidence: RequiredProfileEvidence
    assumption: None = None


class TransferableAlignmentExtractionFinding(AssessmentModel):
    kind: Literal["transferable_alignment"]
    summary: NonEmptyString
    detail: NonEmptyString | None = None
    importance: FindingImportance
    job_evidence: RequiredJobEvidence
    profile_evidence: RequiredProfileEvidence
    assumption: None = None


class ConflictExtractionFinding(AssessmentModel):
    kind: Literal["conflict"]
    summary: NonEmptyString
    detail: NonEmptyString | None = None
    importance: FindingImportance
    job_evidence: RequiredJobEvidence
    profile_evidence: RequiredProfileEvidence
    assumption: None = None


class GapExtractionFinding(AssessmentModel):
    kind: Literal["gap"]
    summary: NonEmptyString
    detail: NonEmptyString | None = None
    importance: FindingImportance
    job_evidence: RequiredJobEvidence
    profile_evidence: list[ProfileEvidenceRef] = Field(default_factory=list)
    assumption: None = None


class UncertaintyExtractionFinding(AssessmentModel):
    kind: Literal["uncertainty"]
    summary: NonEmptyString
    detail: NonEmptyString | None = None
    importance: FindingImportance
    job_evidence: list[JobEvidenceRef] = Field(default_factory=list)
    profile_evidence: list[ProfileEvidenceRef] = Field(default_factory=list)
    assumption: None = None


class AssumptionExtractionFinding(AssessmentModel):
    kind: Literal["assumption"]
    summary: NonEmptyString
    detail: NonEmptyString | None = None
    importance: FindingImportance
    job_evidence: list[JobEvidenceRef] = Field(default_factory=list)
    profile_evidence: list[ProfileEvidenceRef] = Field(default_factory=list)
    assumption: NonEmptyString


ExtractionFitFinding = Union[
    AlignmentExtractionFinding,
    PartialAlignmentExtractionFinding,
    TransferableAlignmentExtractionFinding,
    ConflictExtractionFinding,
    GapExtractionFinding,
    UncertaintyExtractionFinding,
    AssumptionExtractionFinding,
]


class ExtractionFitDimensionAssessment(AssessmentModel):
    """Extraction-side dimension assessment with schema-enforced findings."""

    dimension: FitDimension
    judgment: FitJudgment
    summary: NonEmptyString
    findings: Annotated[list[ExtractionFitFinding], Field(min_length=1)]

    @model_validator(mode="after")
    def judgment_reflects_material_gaps(self) -> ExtractionFitDimensionAssessment:
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


class OpportunityAssessmentExtraction(AssessmentModel):
    """Fields an assessor may produce. Excludes ``job_analysis`` by design."""

    technical_fit: ExtractionFitDimensionAssessment
    commercial_fit: ExtractionFitDimensionAssessment
    portfolio_fit: ExtractionFitDimensionAssessment
    summary: AssessmentSummary
