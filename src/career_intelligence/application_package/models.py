"""Typed models for Application Package manifests (FR-010).

One Opportunity maps to one current package. Regeneration replaces the previous
manifest. Generated CV and cover-letter content lives in existing draft writers;
this package persists only deterministic references and evidence traceability.

M1 stores draft paths as filenames relative to the service-configured output
directories (portable, deterministic). Absolute paths from M0 manifests still
load and resolve.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import (
    AnyHttpUrl,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
)

from career_intelligence.opportunities.models import (
    OpportunityId,
    SourceKind,
    StrategySummary,
)

NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class PackageModel(BaseModel):
    """Base model that rejects accidental schema drift."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class DocumentArtefactRefs(PackageModel):
    """Filesystem references produced by existing FR-006 / FR-007 draft writers.

    ``output_dir`` is ``"."`` when paths are relative filenames under the
    service-configured draft directory. Absolute paths remain accepted for
    manifests written by M0.
    """

    stem: NonEmptyString
    output_dir: NonEmptyString
    markdown_path: NonEmptyString
    json_path: NonEmptyString
    plan_json_path: NonEmptyString
    html_path: NonEmptyString | None = None
    pdf_path: NonEmptyString | None = None


class AcquisitionProvenance(PackageModel):
    """Acquisition identity copied from the Opportunity for package traceability."""

    source_kind: SourceKind
    platform_job_id: NonEmptyString | None = None
    canonical_url: AnyHttpUrl | None = None
    source_url: AnyHttpUrl | None = None
    company: NonEmptyString | None = None
    title: NonEmptyString | None = None
    location_text: NonEmptyString | None = None
    content_fingerprint: NonEmptyString | None = None


class EvidenceTrace(PackageModel):
    """Traceability from the package back to immutable Opportunity evidence."""

    opportunity_id: OpportunityId
    artifact_paths: dict[str, NonEmptyString] = Field(default_factory=dict)
    acquisition: AcquisitionProvenance
    strategy_summary: StrategySummary | None = None


class ApplicationPackageManifest(PackageModel):
    """Current Application Package for one Opportunity (replace-on-regenerate).

    Package identity equals ``opportunity_id``. Owner review remains mandatory
    before any external use — the same invariant carried by FR-006 and FR-007
    artefacts. Regeneration replaces this record; there is no version history.
    """

    opportunity_id: OpportunityId
    prepared_at: datetime
    evidence: EvidenceTrace
    cv: DocumentArtefactRefs
    cover_letter: DocumentArtefactRefs
    owner_review_required: Literal[True] = True
