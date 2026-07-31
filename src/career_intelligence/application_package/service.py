"""Standalone Application Package composition service (FR-010).

Composes existing FR-006 and FR-007 generation services for Opportunities whose
owner decision is ``apply``. Does not extend orchestration, mutate Opportunity
records, write PipelineStatus, or duplicate document-generation logic.

Regeneration semantics (M1)
---------------------------
* One Opportunity → one current package (``opportunity_id`` is the identity).
* ``prepare`` always replaces the previous package for that id — no versioning.
* Generation runs fully in memory before any draft or manifest write.
* Draft files use a stable stem (``opportunity_id``) and overwrite in place.
* The previous manifest remains the current package until both draft sets and
  the new manifest write succeed. A failure before manifest save leaves the
  prior package loadable (draft bytes may already be partially overwritten).
* With identical inputs and the same ``prepared_at``, repeated ``prepare`` calls
  produce identical manifests and identical draft file bytes (idempotent).
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

from career_intelligence.cover_letter import (
    CoverLetterGenerationOptions,
    CoverLetterGenerationService,
    CoverLetterPlanOptions,
    CoverLetterPlanService,
    DeterministicCoverLetterPlanner,
    write_cover_letter_drafts,
)
from career_intelligence.cover_letter import (
    default_generated_dir as default_cover_letter_dir,
)
from career_intelligence.cv_generation import (
    CvGenerationOptions,
    CvGenerationService,
    DeterministicTailoringPlanner,
    TailoringOptions,
    TailoringPlanService,
    write_tailored_cv_drafts,
)
from career_intelligence.cv_generation import (
    default_generated_dir as default_cv_dir,
)
from career_intelligence.opportunities import Opportunity, OpportunityService
from career_intelligence.profile import CareerProfile, CareerProfileService

from .errors import (
    ApplicationPackageEligibilityError,
    ApplicationPackageIntegrityError,
)
from .json_store import JsonDirectoryPackageStore
from .models import (
    AcquisitionProvenance,
    ApplicationPackageManifest,
    DocumentArtefactRefs,
    EvidenceTrace,
)
from .store import ApplicationPackageStore

DEFAULT_PACKAGES_ROOT = (
    Path(__file__).resolve().parents[3] / "data" / "application_packages"
)
_REPO_ROOT = Path(__file__).resolve().parents[3]
_SERVICE_MANAGED_DIR = "."


class ApplicationPackageService:
    """Prepare, reload, and regenerate the current Application Package."""

    def __init__(
        self,
        opportunities: OpportunityService,
        *,
        profile: CareerProfile | CareerProfileService,
        store: ApplicationPackageStore | None = None,
        packages_root: Path | None = None,
        cv_output_dir: Path | None = None,
        cover_letter_output_dir: Path | None = None,
        tailoring_plan_service: TailoringPlanService | None = None,
        cv_generation_service: CvGenerationService | None = None,
        cover_letter_plan_service: CoverLetterPlanService | None = None,
        cover_letter_generation_service: CoverLetterGenerationService | None = None,
    ) -> None:
        self._opportunities = opportunities
        self._profile_source = profile
        root = packages_root or _configured_packages_root()
        self._store = store or JsonDirectoryPackageStore(root)
        self._cv_output_dir = cv_output_dir or default_cv_dir(_REPO_ROOT)
        self._cover_letter_output_dir = (
            cover_letter_output_dir or default_cover_letter_dir(_REPO_ROOT)
        )
        self._tailoring_plans = tailoring_plan_service or TailoringPlanService(
            DeterministicTailoringPlanner()
        )
        self._cv_generation = cv_generation_service or CvGenerationService()
        self._cover_letter_plans = cover_letter_plan_service or CoverLetterPlanService(
            DeterministicCoverLetterPlanner()
        )
        self._cover_letters = (
            cover_letter_generation_service or CoverLetterGenerationService()
        )

    @classmethod
    def from_paths(
        cls,
        *,
        opportunities_root: Path,
        packages_root: Path,
        profile: CareerProfile | CareerProfileService,
        cv_output_dir: Path | None = None,
        cover_letter_output_dir: Path | None = None,
    ) -> ApplicationPackageService:
        """Compose the service for explicit workspace directories."""
        return cls(
            OpportunityService.from_path(opportunities_root),
            profile=profile,
            packages_root=packages_root,
            cv_output_dir=cv_output_dir,
            cover_letter_output_dir=cover_letter_output_dir,
        )

    @property
    def opportunities(self) -> OpportunityService:
        return self._opportunities

    def exists(self, opportunity_id: str) -> bool:
        """Return whether a package manifest is present for the Opportunity."""
        return self._store.exists(opportunity_id)

    def get(
        self,
        opportunity_id: str,
        *,
        verify: bool = True,
    ) -> ApplicationPackageManifest:
        """Load the current package manifest for an Opportunity.

        Draft paths are resolved to absolute filesystem paths against this
        service's configured output directories. When ``verify`` is True (default),
        every referenced draft file must exist or
        ``ApplicationPackageIntegrityError`` is raised. The previous package
        remains the current one until a later ``prepare`` succeeds.
        """
        manifest = self._store.get(opportunity_id)
        resolved = self._resolve_manifest(manifest)
        if verify:
            self.verify_artefacts(resolved)
        return resolved

    def verify_artefacts(self, manifest: ApplicationPackageManifest) -> None:
        """Fail closed when referenced draft files are missing."""
        missing: list[str] = []
        for label, path in _draft_path_entries(manifest):
            if path is None:
                continue
            if not Path(path).is_file():
                missing.append(f"{label}={path}")
        if missing:
            raise ApplicationPackageIntegrityError(
                "Application package references missing draft files: "
                + "; ".join(missing)
            )

    def prepare(
        self,
        opportunity_id: str,
        *,
        tailoring_options: TailoringOptions | None = None,
        cv_options: CvGenerationOptions | None = None,
        cover_letter_plan_options: CoverLetterPlanOptions | None = None,
        cover_letter_options: CoverLetterGenerationOptions | None = None,
        prepared_at: datetime | None = None,
    ) -> ApplicationPackageManifest:
        """Compose FR-006 / FR-007 outputs into the current Application Package.

        Eligibility: owner decision must be ``apply``. Existing FR-006 and FR-007
        approval gates remain enforced via the supplied options. Regeneration
        replaces the previous package for the same opportunity_id. Opportunity
        index rows and immutable FR-002–FR-005 artefacts are never modified.

        Write order: in-memory generation → CV drafts → cover-letter drafts →
        manifest. The prior manifest remains current until this method returns
        successfully.
        """
        opportunity = self._opportunities.get(opportunity_id)
        self._require_apply(opportunity)

        artifacts = self._opportunities.load_artifacts(opportunity_id)
        strategy = artifacts.strategy
        profile = self._load_profile()

        resolved_tailoring = tailoring_options or TailoringOptions()
        resolved_cv = cv_options or CvGenerationOptions()
        resolved_cl_plan = cover_letter_plan_options or CoverLetterPlanOptions()
        resolved_cl = cover_letter_options or CoverLetterGenerationOptions()

        contact = resolved_cv.contact or resolved_cl.contact
        if contact is not None:
            if resolved_cv.contact is None:
                resolved_cv = resolved_cv.model_copy(update={"contact": contact})
            if resolved_cl.contact is None:
                resolved_cl = resolved_cl.model_copy(update={"contact": contact})

        # Fully generate in memory before any durable write.
        plan = self._tailoring_plans.plan(
            strategy, profile, options=resolved_tailoring
        )
        cv = self._cv_generation.generate(
            strategy, profile, plan, options=resolved_cv
        )
        cover_plan = self._cover_letter_plans.plan(
            strategy, profile, options=resolved_cl_plan
        )
        cover_letter = self._cover_letters.generate(
            strategy, profile, cover_plan, options=resolved_cl
        )

        stem = opportunity_id
        cv_drafts = write_tailored_cv_drafts(
            cv,
            plan,
            output_dir=self._cv_output_dir,
            stem=stem,
        )
        cover_drafts = write_cover_letter_drafts(
            cover_letter,
            cover_plan,
            output_dir=self._cover_letter_output_dir,
            stem=stem,
        )

        stamp = prepared_at or datetime.now(UTC)
        persisted = ApplicationPackageManifest(
            opportunity_id=opportunity_id,
            prepared_at=stamp,
            evidence=_evidence_trace(opportunity),
            cv=_relative_document_refs(cv_drafts),
            cover_letter=_relative_document_refs(cover_drafts),
            owner_review_required=True,
        )
        # Manifest is the commit point: prior package stays current until this succeeds.
        self._store.save(persisted)
        resolved = self._resolve_manifest(persisted)
        self.verify_artefacts(resolved)
        return resolved

    def _require_apply(self, opportunity: Opportunity) -> None:
        decision = opportunity.decision
        if decision is None or decision.decision != "apply":
            kind = decision.decision if decision is not None else "none"
            raise ApplicationPackageEligibilityError(
                "Application packages may only be prepared for Opportunities "
                f"with owner decision 'apply' (got '{kind}' for "
                f"{opportunity.opportunity_id})"
            )

    def _load_profile(self) -> CareerProfile:
        if isinstance(self._profile_source, CareerProfileService):
            return self._profile_source.load()
        return self._profile_source

    def _resolve_manifest(
        self, manifest: ApplicationPackageManifest
    ) -> ApplicationPackageManifest:
        return manifest.model_copy(
            update={
                "cv": _resolve_document_refs(manifest.cv, self._cv_output_dir),
                "cover_letter": _resolve_document_refs(
                    manifest.cover_letter, self._cover_letter_output_dir
                ),
            },
            deep=True,
        )


def _evidence_trace(opportunity: Opportunity) -> EvidenceTrace:
    identity = opportunity.identity
    return EvidenceTrace(
        opportunity_id=opportunity.opportunity_id,
        artifact_paths=dict(opportunity.artifact_paths),
        acquisition=AcquisitionProvenance(
            source_kind=identity.source_kind,
            platform_job_id=identity.platform_job_id,
            canonical_url=identity.canonical_url,
            source_url=identity.source_url,
            company=identity.company,
            title=identity.title,
            location_text=identity.location_text,
            content_fingerprint=identity.content_fingerprint,
        ),
        strategy_summary=opportunity.strategy_summary,
    )


def _relative_document_refs(drafts) -> DocumentArtefactRefs:
    """Persist portable filenames relative to the service draft directory."""
    return DocumentArtefactRefs(
        stem=drafts.stem,
        output_dir=_SERVICE_MANAGED_DIR,
        markdown_path=drafts.markdown_path.name,
        json_path=drafts.json_path.name,
        plan_json_path=drafts.plan_json_path.name,
        html_path=drafts.html_path.name if drafts.html_path is not None else None,
    )


def _resolve_document_refs(
    refs: DocumentArtefactRefs, base_dir: Path
) -> DocumentArtefactRefs:
    """Resolve relative draft filenames; leave absolute (M0) paths unchanged."""
    return DocumentArtefactRefs(
        stem=refs.stem,
        output_dir=str(base_dir.resolve()),
        markdown_path=_resolve_path(refs.markdown_path, base_dir),
        json_path=_resolve_path(refs.json_path, base_dir),
        plan_json_path=_resolve_path(refs.plan_json_path, base_dir),
        html_path=(
            _resolve_path(refs.html_path, base_dir)
            if refs.html_path is not None
            else None
        ),
    )


def _resolve_path(path_value: str, base_dir: Path) -> str:
    path = Path(path_value)
    if path.is_absolute():
        return str(path.resolve())
    return str((base_dir / path).resolve())


def _draft_path_entries(
    manifest: ApplicationPackageManifest,
) -> list[tuple[str, str | None]]:
    return [
        ("cv.markdown_path", manifest.cv.markdown_path),
        ("cv.json_path", manifest.cv.json_path),
        ("cv.plan_json_path", manifest.cv.plan_json_path),
        ("cv.html_path", manifest.cv.html_path),
        ("cover_letter.markdown_path", manifest.cover_letter.markdown_path),
        ("cover_letter.json_path", manifest.cover_letter.json_path),
        ("cover_letter.plan_json_path", manifest.cover_letter.plan_json_path),
        ("cover_letter.html_path", manifest.cover_letter.html_path),
    ]


def _configured_packages_root() -> Path:
    configured = os.getenv("CIC_APPLICATION_PACKAGES_DIR")
    return Path(configured) if configured else DEFAULT_PACKAGES_ROOT
