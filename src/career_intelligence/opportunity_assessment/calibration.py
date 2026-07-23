"""Deterministic calibration checks for opportunity-assessment payloads.

These checks reject internally inconsistent or mis-grounded assessor claims.
They never silently repair judgments or rewrite findings.
"""

from __future__ import annotations

from career_intelligence.job_analysis.models import JobAnalysis
from career_intelligence.profile.models import CareerProfile, ExperienceEntry

from .errors import ErrorDetail, OpportunityAssessmentValidationError
from .models import FitFinding, OpportunityAssessment

# Industry nouns that may appear in experience_requirement text, mapped to
# support tokens that must appear in cited employment evidence.
_INDUSTRY_SUPPORT: dict[str, frozenset[str]] = {
    "retail": frozenset(
        {
            "retail",
            "fashion",
            "clothing",
            "apparel",
            "ecommerce",
            "e-commerce",
            "ecom",
            "merchant",
            "store",
            "supermarket",
            "grocery",
            "bakery",
            "bakers delight",
        }
    ),
    "fashion": frozenset({"fashion", "clothing", "apparel", "retail", "bakers delight"}),
    "banking": frozenset({"bank", "banking", "fintech", "financial services"}),
    "fintech": frozenset({"fintech", "bank", "banking", "financial services"}),
    "healthcare": frozenset({"health", "healthcare", "hospital", "clinical", "medical"}),
    "insurance": frozenset({"insurance", "insurer", "underwriting"}),
    "telecom": frozenset({"telecom", "telecommunications", "nbn", "telco"}),
    "telecommunications": frozenset({"telecom", "telecommunications", "nbn", "telco"}),
    "government": frozenset({"government", "public sector", "agency"}),
}

_PRODUCTION_DELIVERY_MARKERS = (
    "production",
    "shipping",
    "ship ",
    "llm/agent",
    "llm agent",
    "agent application",
    "commercial production",
    "production-grade",
    "production grade",
)


def validate_calibration(
    assessment: OpportunityAssessment,
    profile: CareerProfile,
) -> None:
    """Reject mis-grounded industry or commercial-production employment claims."""
    errors: list[ErrorDetail] = []

    for dimension_name, dimension in (
        ("technical_fit", assessment.technical_fit),
        ("commercial_fit", assessment.commercial_fit),
        ("portfolio_fit", assessment.portfolio_fit),
    ):
        for finding_index, finding in enumerate(dimension.findings):
            loc = (dimension_name, "findings", finding_index)
            _check_industry_alignment(
                finding,
                assessment.job_analysis,
                profile,
                loc,
                errors,
            )
            if dimension_name == "commercial_fit":
                _check_commercial_production_employment_alignment(
                    finding,
                    assessment.job_analysis,
                    profile,
                    loc,
                    errors,
                )

    if errors:
        raise OpportunityAssessmentValidationError(errors)


def _check_industry_alignment(
    finding: FitFinding,
    job_analysis: JobAnalysis,
    profile: CareerProfile,
    loc: tuple[str | int, ...],
    errors: list[ErrorDetail],
) -> None:
    if finding.kind != "alignment":
        return

    industry_keys = _industry_keys_from_finding(finding, job_analysis)
    if not industry_keys:
        return

    support_tokens: set[str] = set()
    for key in industry_keys:
        support_tokens |= set(_INDUSTRY_SUPPORT.get(key, frozenset({key})))

    experience_refs = [
        ref for ref in finding.profile_evidence if ref.source == "experience"
    ]
    if not experience_refs:
        errors.append(
            ErrorDetail(
                loc=(*loc, "profile_evidence"),
                msg=(
                    "industry alignment requires experience profile evidence that "
                    "supports the stated industry requirement"
                ),
                type="value_error",
            )
        )
        return

    if not any(
        _experience_supports_industry(_resolve_experience(profile, ref.ref), support_tokens)
        for ref in experience_refs
        if _resolve_experience(profile, ref.ref) is not None
    ):
        errors.append(
            ErrorDetail(
                loc=(*loc, "profile_evidence"),
                msg=(
                    "cited experience does not support the industry requirement "
                    f"({', '.join(sorted(industry_keys))}); industry alignment "
                    "requires evidence that genuinely matches the required industry"
                ),
                type="value_error",
            )
        )


def _check_commercial_production_employment_alignment(
    finding: FitFinding,
    job_analysis: JobAnalysis,
    profile: CareerProfile,
    loc: tuple[str | int, ...],
    errors: list[ErrorDetail],
) -> None:
    """Reject commercial alignments that treat independent/portfolio work as employment."""
    if finding.kind != "alignment":
        return
    if not _finding_or_job_claims_production_delivery(finding, job_analysis):
        return

    for profile_index, profile_ref in enumerate(finding.profile_evidence):
        if profile_ref.source == "project":
            errors.append(
                ErrorDetail(
                    loc=(*loc, "profile_evidence", profile_index),
                    msg=(
                        "commercial_fit alignment for production delivery cannot cite "
                        "portfolio projects as commercial employment evidence"
                    ),
                    type="value_error",
                )
            )
            continue
        if profile_ref.source != "experience":
            continue
        entry = _resolve_experience(profile, profile_ref.ref)
        if entry is None:
            continue
        if entry.kind != "employment":
            errors.append(
                ErrorDetail(
                    loc=(*loc, "profile_evidence", profile_index),
                    msg=(
                        "commercial_fit alignment for production delivery cannot cite "
                        f"experience kind '{entry.kind}' as commercial employment; "
                        "use partial_alignment/gap and reserve alignment for employment"
                    ),
                    type="value_error",
                )
            )


def _industry_keys_from_finding(
    finding: FitFinding,
    job_analysis: JobAnalysis,
) -> set[str]:
    texts: list[str] = [
        finding.summary.casefold(),
        (finding.detail or "").casefold(),
    ]
    for job_ref in finding.job_evidence:
        if job_ref.excerpt:
            texts.append(job_ref.excerpt.casefold())
        if job_ref.name:
            texts.append(job_ref.name.casefold())
        if (
            job_ref.source == "experience_requirement"
            and job_ref.item_index is not None
            and job_ref.item_index < len(job_analysis.experience_requirements)
        ):
            texts.append(
                job_analysis.experience_requirements[job_ref.item_index].description.casefold()
            )

    blob = " ".join(texts)
    return {key for key in _INDUSTRY_SUPPORT if key in blob}


def _finding_or_job_claims_production_delivery(
    finding: FitFinding,
    job_analysis: JobAnalysis,
) -> bool:
    texts: list[str] = [
        finding.summary.casefold(),
        (finding.detail or "").casefold(),
    ]
    for job_ref in finding.job_evidence:
        if job_ref.excerpt:
            texts.append(job_ref.excerpt.casefold())
        if job_ref.name:
            texts.append(job_ref.name.casefold())
        if (
            job_ref.source == "experience_requirement"
            and job_ref.item_index is not None
            and job_ref.item_index < len(job_analysis.experience_requirements)
        ):
            texts.append(
                job_analysis.experience_requirements[job_ref.item_index].description.casefold()
            )
    blob = " ".join(texts)
    return any(marker in blob for marker in _PRODUCTION_DELIVERY_MARKERS)


def _resolve_experience(profile: CareerProfile, ref: str) -> ExperienceEntry | None:
    if not ref.startswith("experience:"):
        return None
    identifier = ref.split(":", 1)[1]
    for entry in profile.experience:
        if entry.id == identifier:
            return entry
    return None


def _experience_supports_industry(
    entry: ExperienceEntry | None,
    support_tokens: set[str],
) -> bool:
    if entry is None:
        return False
    blob = " ".join(
        [
            entry.organisation,
            entry.title,
            *entry.highlights,
            *entry.technologies,
        ]
    ).casefold()
    return any(token in blob for token in support_tokens)
