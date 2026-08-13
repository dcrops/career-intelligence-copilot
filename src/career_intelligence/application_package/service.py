"""Standalone Application Package composition service (FR-010).

Composes existing FR-006 and FR-007 generation services for Opportunities whose
owner decision is ``apply``. Does not extend orchestration, mutate Opportunity
records, write PipelineStatus, or duplicate document-generation logic.

Regeneration semantics (M1)
---------------------------
* One Opportunity → one current package (``opportunity_id`` is the identity).
* ``prepare`` replaces the previous package for that id — no versioning.
* CV production uses Master-CV editorial adaptation (``adapt_from_master``).
  Cover-letter production uses one bounded LLM composition call from a
  deterministic evidence pack. Technical generation failure is fail-closed:
  no silent fallback to the old deterministic cover-letter composer.
* Owner-edited Markdown (hash differs from the generated-content fingerprint)
  is preserved; HTML/PDF are refreshed from the current file.
* Pass ``regenerate=True`` to overwrite owner-edited Markdown.
* Both documents are generated in memory before any draft write. A failure
  before manifest save leaves the prior package loadable and does not write
  new Markdown.
* Draft files use a stable stem (``opportunity_id``) and overwrite in place
  when generation runs.
* With identical inputs and the same ``prepared_at``, repeated ``prepare`` calls
  produce identical manifests and identical draft file bytes when the cover-letter
  composer is deterministic (tests). Live OpenAI composition is not byte-idempotent.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

from career_intelligence.candidate_contact import (
    CandidateContactConfigError,
    require_contact_details,
)
from career_intelligence.cover_letter import (
    CoverLetterError,
    CoverLetterGenerationOptions,
    CoverLetterGenerationService,
    CoverLetterGenerationValidationError,
    CoverLetterPlanOptions,
    CoverLetterPlanService,
    DeterministicCoverLetterPlanner,
    write_cover_letter_drafts,
)
from career_intelligence.cover_letter.bounded_composer import (
    CoverLetterComposer,
    FixtureCoverLetterComposer,
    OpenAICoverLetterComposer,
)
from career_intelligence.cover_letter import (
    default_generated_dir as default_cover_letter_dir,
)
from career_intelligence.cover_letter.draft_writer import (
    DraftWriteResult as CoverLetterDraftWriteResult,
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
from career_intelligence.cv_generation.draft_writer import DraftWriteResult
from career_intelligence.document_rendering.service import render_document_from_markdown
from career_intelligence.opportunities import Opportunity, OpportunityService
from career_intelligence.profile import CareerProfile, CareerProfileService

from .errors import (
    ApplicationPackageContactError,
    ApplicationPackageEligibilityError,
    ApplicationPackageGenerationError,
    ApplicationPackageIntegrityError,
)
from .external_upload import ExternalUploadPaths, materialize_external_upload_pdfs
from .json_store import JsonDirectoryPackageStore
from .prose_guard import markdown_sha256, should_preserve_owner_markdown
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
        cover_letter_composer: CoverLetterComposer | None = None,
        master_cv_path: Path | None = None,
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
        self._cover_letters = cover_letter_generation_service
        self._cover_letter_composer = cover_letter_composer
        self._master_cv_path = master_cv_path

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
        regenerate: bool = False,
    ) -> ApplicationPackageManifest:
        """Compose FR-006 / FR-007 outputs into the current Application Package.

        Eligibility: owner decision must be ``apply``. Existing FR-006 and FR-007
        approval gates remain enforced via the supplied options. Regeneration
        replaces the previous package for the same opportunity_id unless existing
        Markdown has been owner-edited (hash differs from the generated
        fingerprint). Pass ``regenerate=True`` to overwrite edited Markdown.
        Opportunity index rows and immutable FR-002–FR-005 artefacts are never
        modified.

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
        try:
            contact = require_contact_details(contact)
        except CandidateContactConfigError as error:
            raise ApplicationPackageContactError(error.message) from error
        cv_update: dict[str, object] = {
            "contact": contact,
            "adapt_from_master": True,
            "rewrite_summary": False,
        }
        master_cv_path = (
            resolved_cv.master_cv_path
            or (str(self._master_cv_path) if self._master_cv_path else None)
            or os.environ.get("CIC_MASTER_CV_PATH")
        )
        if master_cv_path:
            cv_update["master_cv_path"] = master_cv_path
        resolved_cv = resolved_cv.model_copy(update=cv_update)
        resolved_cl = resolved_cl.model_copy(update={"contact": contact})

        stem = opportunity_id
        previous = self._previous_manifest(opportunity_id)
        cv_markdown_path = self._cv_output_dir / f"{stem}.md"
        cl_markdown_path = self._cover_letter_output_dir / f"{stem}.md"
        preserve_cv = should_preserve_owner_markdown(
            cv_markdown_path,
            previous.cv_generated_markdown_sha256 if previous is not None else None,
            regenerate=regenerate,
        )
        preserve_cl = should_preserve_owner_markdown(
            cl_markdown_path,
            (
                previous.cover_letter_generated_markdown_sha256
                if previous is not None
                else None
            ),
            regenerate=regenerate,
        )

        cv = None
        plan = None
        cover_letter = None
        cover_plan = None
        evidence_pack = None
        if not preserve_cv:
            plan = self._tailoring_plans.plan(
                strategy, profile, options=resolved_tailoring
            )
            cv = self._cv_generation.generate(
                strategy, profile, plan, options=resolved_cv
            )
        if not preserve_cl:
            cover_plan = self._cover_letter_plans.plan(
                strategy, profile, options=resolved_cl_plan
            )
            cover_letter, evidence_pack = self._compose_cover_letter(
                strategy, profile, cover_plan, resolved_cl
            )

        if preserve_cv:
            render_document_from_markdown(cv_markdown_path)
            cv_drafts = _existing_cv_drafts(self._cv_output_dir, stem)
            cv_fingerprint = (
                previous.cv_generated_markdown_sha256 if previous is not None else None
            )
        else:
            assert cv is not None and plan is not None
            cv_drafts = write_tailored_cv_drafts(
                cv,
                plan,
                output_dir=self._cv_output_dir,
                stem=stem,
            )
            cv_fingerprint = markdown_sha256(cv_drafts.markdown_path)

        if preserve_cl:
            render_document_from_markdown(cl_markdown_path)
            cover_drafts = _existing_cover_letter_drafts(
                self._cover_letter_output_dir, stem
            )
            cl_fingerprint = (
                previous.cover_letter_generated_markdown_sha256
                if previous is not None
                else None
            )
        else:
            assert cover_letter is not None and cover_plan is not None
            cover_drafts = write_cover_letter_drafts(
                cover_letter,
                cover_plan,
                output_dir=self._cover_letter_output_dir,
                stem=stem,
            )
            if evidence_pack is not None:
                from career_intelligence.cover_letter.bounded_generation import (
                    write_evidence_pack,
                )

                write_evidence_pack(
                    self._cover_letter_output_dir / f"{stem}.evidence_pack.json",
                    evidence_pack,
                )
            cl_fingerprint = markdown_sha256(cover_drafts.markdown_path)

        stamp = prepared_at or datetime.now(UTC)
        persisted = ApplicationPackageManifest(
            opportunity_id=opportunity_id,
            prepared_at=stamp,
            evidence=_evidence_trace(opportunity),
            cv=_relative_document_refs(cv_drafts),
            cover_letter=_relative_document_refs(cover_drafts),
            owner_review_required=True,
            cv_generated_markdown_sha256=cv_fingerprint,
            cover_letter_generated_markdown_sha256=cl_fingerprint,
        )
        # Manifest is the commit point: prior package stays current until this succeeds.
        self._store.save(persisted)
        resolved = self._resolve_manifest(persisted)
        self.verify_artefacts(resolved)
        self.ensure_external_upload_pdfs(resolved)
        return resolved

    def ensure_external_upload_pdfs(
        self,
        manifest: ApplicationPackageManifest | None = None,
        *,
        opportunity_id: str | None = None,
    ) -> ExternalUploadPaths:
        """Materialize byte-identical employer-facing PDFs under package ``export/``.

        Authoritative draft paths on the manifest are unchanged. Safe to call
        repeatedly (idempotent when bytes already match).
        """
        if manifest is None:
            if opportunity_id is None:
                raise ValueError("opportunity_id or manifest is required")
            manifest = self.get(opportunity_id, verify=True)
        else:
            # Ensure absolute draft paths for copy source.
            if not Path(manifest.cv.pdf_path or "").is_file():
                manifest = self._resolve_manifest(manifest)
        profile = self._load_profile()
        root = self._packages_root()
        return materialize_external_upload_pdfs(
            manifest,
            packages_root=root,
            full_name=profile.identity.full_name,
        )

    def _packages_root(self) -> Path:
        store = self._store
        if isinstance(store, JsonDirectoryPackageStore):
            return store.root
        return _configured_packages_root()

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

    def _compose_cover_letter(
        self,
        strategy,
        profile: CareerProfile,
        cover_plan,
        options: CoverLetterGenerationOptions,
    ):
        """One bounded LLM composition attempt. Never falls back to deterministic prose."""
        from career_intelligence.cover_letter.bounded_generation import (
            BoundedCoverLetterService,
        )

        try:
            result = BoundedCoverLetterService(self._resolve_cover_letter_composer()).compose(
                strategy,
                profile,
                cover_plan,
                options=options,
            )
        except CoverLetterGenerationValidationError as error:
            details = "; ".join(item.msg for item in error.errors) or str(error)
            raise ApplicationPackageGenerationError(
                "Bounded cover-letter generation failed closed (unsupported or "
                f"invalid composition): {details}. The previous package remains "
                "current; no deterministic fallback was used."
            ) from error
        except CoverLetterError as error:
            raise ApplicationPackageGenerationError(
                "Bounded cover-letter generation failed closed: "
                f"{error}. The previous package remains current; no deterministic "
                "fallback was used."
            ) from error
        return result.letter, result.pack

    def _resolve_cover_letter_composer(self) -> CoverLetterComposer:
        if self._cover_letter_composer is not None:
            return self._cover_letter_composer
        mode = os.environ.get("CIC_COVER_LETTER_COMPOSER", "openai").strip().lower()
        if mode in {"fixture", "offline"}:
            return FixtureCoverLetterComposer()
        return OpenAICoverLetterComposer()

    def _previous_manifest(
        self, opportunity_id: str
    ) -> ApplicationPackageManifest | None:
        if not self.exists(opportunity_id):
            return None
        return self.get(opportunity_id, verify=False)

    def load_profile(self) -> CareerProfile:
        """Return the Career Profile bound to this package service (FR-014 gates)."""
        return self._load_profile()

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


def _existing_cv_drafts(output_dir: Path, stem: str) -> DraftWriteResult:
    return DraftWriteResult(
        output_dir=output_dir,
        stem=stem,
        markdown_path=output_dir / f"{stem}.md",
        json_path=output_dir / f"{stem}.json",
        plan_json_path=output_dir / f"{stem}.tailoring_plan.json",
        html_path=output_dir / f"{stem}.html",
        pdf_path=output_dir / f"{stem}.pdf",
    )


def _existing_cover_letter_drafts(
    output_dir: Path, stem: str
) -> CoverLetterDraftWriteResult:
    return CoverLetterDraftWriteResult(
        output_dir=output_dir,
        stem=stem,
        markdown_path=output_dir / f"{stem}.md",
        json_path=output_dir / f"{stem}.json",
        plan_json_path=output_dir / f"{stem}.cover_letter_plan.json",
        html_path=output_dir / f"{stem}.html",
        pdf_path=output_dir / f"{stem}.pdf",
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
        pdf_path=drafts.pdf_path.name if drafts.pdf_path is not None else None,
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
        pdf_path=(
            _resolve_path(refs.pdf_path, base_dir) if refs.pdf_path is not None else None
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
        ("cv.pdf_path", manifest.cv.pdf_path),
        ("cover_letter.markdown_path", manifest.cover_letter.markdown_path),
        ("cover_letter.json_path", manifest.cover_letter.json_path),
        ("cover_letter.plan_json_path", manifest.cover_letter.plan_json_path),
        ("cover_letter.html_path", manifest.cover_letter.html_path),
        ("cover_letter.pdf_path", manifest.cover_letter.pdf_path),
    ]


def _configured_packages_root() -> Path:
    configured = os.getenv("CIC_APPLICATION_PACKAGES_DIR")
    return Path(configured) if configured else DEFAULT_PACKAGES_ROOT
