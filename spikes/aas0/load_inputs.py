"""Read-only loaders for AAS-0 — no production mutation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from career_intelligence.application_package import ApplicationPackageService
from career_intelligence.candidate_contact import load_candidate_contact
from career_intelligence.opportunities import OpportunityService
from career_intelligence.profile import CareerProfileService
from career_intelligence.truth_validation.gates import (
    PackageTruthStatus,
    evaluate_package_truth,
)

from .answer_policy import KnownAnswers

SPIKE_DIR = Path(__file__).resolve().parent
REPO_ROOT = SPIKE_DIR.parents[1]
DEFAULT_OPPORTUNITY_ID = "opp_01KZQJY6AX3EGX7TGYTHR3ABG1"
DEFAULT_PROFILE_DIR = SPIKE_DIR / ".browser-profile"
DEFAULT_RUNS_DIR = SPIKE_DIR / "runs"


@dataclass(frozen=True)
class SpikeInputs:
    opportunity_id: str
    apply_url: str
    company: str | None
    title: str | None
    cv_pdf: Path
    cover_letter_pdf: Path
    cv_markdown: Path
    cover_letter_markdown: Path
    known: KnownAnswers
    truth: PackageTruthStatus
    package_ok: bool
    warnings: tuple[str, ...]


def load_spike_inputs(opportunity_id: str = DEFAULT_OPPORTUNITY_ID) -> SpikeInputs:
    """Load authoritative CIC inputs for the spike. Never regenerates documents."""
    warnings: list[str] = []
    profile = CareerProfileService().load()
    contact = load_candidate_contact()
    opportunities = OpportunityService()
    packages = ApplicationPackageService(opportunities, profile=profile)

    opportunity = opportunities.get(opportunity_id)
    identity = opportunity.identity
    apply_url = identity.canonical_url or identity.source_url
    if not apply_url:
        raise RuntimeError(
            f"Opportunity {opportunity_id} has no source_url/canonical_url; "
            "cannot open application."
        )

    manifest = packages.get(opportunity_id, verify=True)
    cv_pdf = Path(manifest.cv.pdf_path)
    cl_pdf = Path(manifest.cover_letter.pdf_path)
    cv_md = Path(manifest.cv.markdown_path)
    cl_md = Path(manifest.cover_letter.markdown_path)

    for label, path in (
        ("CV PDF", cv_pdf),
        ("cover-letter PDF", cl_pdf),
        ("CV markdown", cv_md),
        ("cover-letter markdown", cl_md),
    ):
        if not path.is_file():
            raise RuntimeError(f"Missing {label}: {path}")

    # Stem / opportunity correspondence check.
    if opportunity_id not in cv_pdf.name or opportunity_id not in cl_pdf.name:
        warnings.append(
            "PDF filenames do not contain opportunity_id — verify artefacts carefully."
        )

    # Warn if markdown newer than PDF (do not auto-regenerate).
    if cv_md.stat().st_mtime > cv_pdf.stat().st_mtime:
        warnings.append(
            f"CV markdown is newer than PDF ({cv_md.name} > {cv_pdf.name}). "
            "STOP and ask owner before live upload if content drifted."
        )
    if cl_md.stat().st_mtime > cl_pdf.stat().st_mtime:
        warnings.append(
            f"Cover-letter markdown is newer than PDF ({cl_md.name} > {cl_pdf.name}). "
            "STOP and ask owner before live upload if content drifted."
        )

    truth = evaluate_package_truth(manifest=manifest, profile=profile, revalidate=False)
    if not truth.external_use_allowed:
        warnings.append(
            "Package external-use gate is NOT allowed: "
            + "; ".join(truth.messages)
        )

    known = KnownAnswers(
        full_name=profile.identity.full_name,
        email=contact.email,
        phone=contact.phone,
        location=contact.location,
        linkedin_url=contact.linkedin_url,
        portfolio_url=contact.portfolio_url,
        github_url=contact.github_url,
        extras={},
    )

    return SpikeInputs(
        opportunity_id=opportunity_id,
        apply_url=str(apply_url),
        company=identity.company,
        title=identity.title,
        cv_pdf=cv_pdf.resolve(),
        cover_letter_pdf=cl_pdf.resolve(),
        cv_markdown=cv_md.resolve(),
        cover_letter_markdown=cl_md.resolve(),
        known=known,
        truth=truth,
        package_ok=True,
        warnings=tuple(warnings),
    )


def format_preflight_report(inputs: SpikeInputs) -> str:
    """Human-readable preflight for owner review before --authorize-live."""
    truth = inputs.truth
    lines = [
        "AAS-0 PREFLIGHT",
        "===============",
        f"opportunity_id: {inputs.opportunity_id}",
        f"company:        {inputs.company}",
        f"title:          {inputs.title}",
        f"apply_url:      {inputs.apply_url}",
        "",
        "LIMITATION: This spike targets SEEK-native application assistance,",
        "not a general employer ATS (Greenhouse/Lever/etc.).",
        "",
        "Artefacts:",
        f"  CV PDF:            {inputs.cv_pdf}",
        f"  Cover letter PDF:  {inputs.cover_letter_pdf}",
        f"  CV markdown:       {inputs.cv_markdown}",
        f"  CL markdown:       {inputs.cover_letter_markdown}",
        "",
        "Truth / external use:",
        f"  external_use_allowed: {truth.external_use_allowed}",
    ]
    for doc in truth.documents:
        lines.append(
            f"  - {doc.artefact_kind}: outcome={doc.outcome} "
            f"fresh={doc.fresh} allowed={doc.external_use_allowed}"
        )
    if truth.messages:
        lines.append("  messages:")
        for msg in truth.messages:
            lines.append(f"    - {msg}")
    lines.append("")
    lines.append("Seeded known answers (authoritative CIC only; no guessing):")
    for key, value in inputs.known.as_lookup().items():
        lines.append(f"  - {key}: {value}")
    lines.append("")
    if inputs.warnings:
        lines.append("WARNINGS:")
        for warning in inputs.warnings:
            lines.append(f"  ! {warning}")
    else:
        lines.append("WARNINGS: none")
    lines.append("")
    lines.append("Browser profile (dedicated Playwright Chromium):")
    lines.append(f"  {DEFAULT_PROFILE_DIR}")
    lines.append("  (no everyday Chrome profile; no password storage)")
    return "\n".join(lines) + "\n"
