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

Profile evidence refs use ``ExtractionProfileEvidenceRef`` (plain non-empty string)
rather than domain ``ProfileEvidenceRef``, so OpenAI structured output can constrain
``ref`` to the request catalogue via JSON Schema ``enum``, and the assessor may
narrowly canonicalise serialisation punctuation before domain validation.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Annotated, Literal, Union

from pydantic import Field, field_validator, model_validator

from .models import (
    AssessmentModel,
    AssessmentSummary,
    FindingImportance,
    FitDimension,
    FitJudgment,
    JobEvidenceRef,
    NonEmptyString,
    ProfileEvidenceSource,
)


class ExtractionProfileEvidenceRef(AssessmentModel):
    """Extraction-boundary profile pointer.

    Unlike domain ``ProfileEvidenceRef``, trailing serialisation punctuation is not
    rejected here (canonicalisation + catalogue enum handle that). Bare ids without
    ``namespace:id`` form are still rejected so extraction stays fail-closed on
    structural shape.
    """

    source: ProfileEvidenceSource
    ref: NonEmptyString
    excerpt: NonEmptyString | None = None

    @field_validator("ref")
    @classmethod
    def ref_has_namespace_form(cls, value: str) -> str:
        if ":" not in value:
            raise ValueError(
                "profile evidence ref must use namespace:id form "
                f"(got '{value}')"
            )
        return value


RequiredJobEvidence = Annotated[list[JobEvidenceRef], Field(min_length=1)]
RequiredProfileEvidence = Annotated[
    list[ExtractionProfileEvidenceRef], Field(min_length=1)
]


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
    profile_evidence: list[ExtractionProfileEvidenceRef] = Field(default_factory=list)
    assumption: None = None


class UncertaintyExtractionFinding(AssessmentModel):
    kind: Literal["uncertainty"]
    summary: NonEmptyString
    detail: NonEmptyString | None = None
    importance: FindingImportance
    job_evidence: list[JobEvidenceRef] = Field(default_factory=list)
    profile_evidence: list[ExtractionProfileEvidenceRef] = Field(default_factory=list)
    assumption: None = None


class AssumptionExtractionFinding(AssessmentModel):
    kind: Literal["assumption"]
    summary: NonEmptyString
    detail: NonEmptyString | None = None
    importance: FindingImportance
    job_evidence: list[JobEvidenceRef] = Field(default_factory=list)
    profile_evidence: list[ExtractionProfileEvidenceRef] = Field(default_factory=list)
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


def inject_profile_evidence_ref_catalogue_enum(
    schema: dict[str, object],
    catalogue: Sequence[str],
) -> dict[str, object]:
    """Constrain ``ExtractionProfileEvidenceRef.ref`` to exact catalogue tokens.

    Mutates a deep copy of ``schema`` so OpenAI structured output cannot emit
    free-form punctuation-contaminated refs. Empty catalogues leave the schema
    unchanged (caller should not request assessment without a profile catalogue).
    """
    import copy

    tokens = list(dict.fromkeys(token for token in catalogue if token))
    if not tokens:
        return schema

    patched = copy.deepcopy(schema)
    defs = patched.get("$defs")
    if not isinstance(defs, dict):
        defs = patched.get("definitions")
    if not isinstance(defs, dict):
        return patched

    for defn in defs.values():
        if not isinstance(defn, dict):
            continue
        props = defn.get("properties")
        if not isinstance(props, dict):
            continue
        # Extraction (and legacy domain) profile evidence ref shapes.
        if "ref" not in props or "source" not in props:
            continue
        source = props.get("source")
        if not isinstance(source, dict):
            continue
        source_enum = source.get("enum")
        if not isinstance(source_enum, list):
            continue
        if "experience" not in source_enum or "project" not in source_enum:
            continue
        ref_schema = props.get("ref")
        if not isinstance(ref_schema, dict):
            continue
        props["ref"] = {
            **{key: value for key, value in ref_schema.items() if key != "enum"},
            "enum": tokens,
            "type": "string",
        }
    return patched


def catalogue_constrained_extraction_type(
    catalogue: Sequence[str],
) -> type[OpportunityAssessmentExtraction]:
    """Return an extraction type whose JSON Schema enums ``ref`` to ``catalogue``."""
    tokens = tuple(dict.fromkeys(token for token in catalogue if token))

    class CatalogueConstrainedOpportunityAssessmentExtraction(
        OpportunityAssessmentExtraction
    ):
        @classmethod
        def model_json_schema(cls, *args: object, **kwargs: object) -> dict[str, object]:
            schema = OpportunityAssessmentExtraction.model_json_schema(*args, **kwargs)
            return inject_profile_evidence_ref_catalogue_enum(schema, tokens)

    CatalogueConstrainedOpportunityAssessmentExtraction.__name__ = (
        "OpportunityAssessmentExtraction"
    )
    CatalogueConstrainedOpportunityAssessmentExtraction.__qualname__ = (
        "OpportunityAssessmentExtraction"
    )
    return CatalogueConstrainedOpportunityAssessmentExtraction
