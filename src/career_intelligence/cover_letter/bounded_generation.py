"""Compose a CoverLetter from a deterministic pack + bounded LLM paragraphs.

Production package prepare uses this path (one composer call, no retry).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from career_intelligence.application_strategy.models import ApplicationStrategy
from career_intelligence.cover_letter.bounded_composer import (
    CoverLetterComposer,
    CoverLetterExtraction,
)
from career_intelligence.cover_letter.errors import (
    CoverLetterGenerationGateError,
    CoverLetterGenerationValidationError,
    ErrorDetail,
)
from career_intelligence.cover_letter.evidence_pack import (
    CoverLetterEvidencePack,
    build_cover_letter_evidence_pack,
)
from career_intelligence.cover_letter.fidelity import validate_fidelity
from career_intelligence.cover_letter.models import CoverLetter, CoverLetterPlan
from career_intelligence.cover_letter.options import CoverLetterGenerationOptions
from career_intelligence.cover_letter.render_markdown import render_markdown
from career_intelligence.cv_generation.options import ContactDetails
from career_intelligence.profile.models import CareerProfile
from career_intelligence.truth_validation.gates import evaluate_report_for_external_use
from career_intelligence.truth_validation.models import TruthReport
from career_intelligence.truth_validation.service import TruthValidationService

_FORBIDDEN_PHRASES = (
    "prototype theatre",
    "slideware",
    "i am excited",
    "i am passionate",
    "i am writing to apply",
    "world-class",
    "leverage synergies",
    "most relevant portfolio evidence",
    "application strategy",
    "strongest project",
)

_COMMERCIAL_AI_PHRASES = (
    "employed as an ai engineer",
    "commercial ai engineering employment",
    "paid ai engineering role",
    "ai engineering consultant",
)

_ML_PHRASES = (
    "tensorflow",
    "pytorch",
    "keras",
    "scikit-learn",
    "deep learning",
    "machine learning engineer",
    "ml expertise",
)

_METRIC_RE = re.compile(r"\b\d+(?:\.\d+)?\s*%|\b(?:aud|usd)\s*\$?\d", re.IGNORECASE)

EXPERIMENT_STEM_SUFFIX = "bounded_llm"
RETEST_STEM_SUFFIX = "bounded_llm_retest"


def experiment_stem(opportunity_id: str, suffix: str = EXPERIMENT_STEM_SUFFIX) -> str:
    return f"{opportunity_id}.{suffix}"


@dataclass(frozen=True)
class BoundedCoverLetterResult:
    letter: CoverLetter
    pack: CoverLetterEvidencePack
    extraction: CoverLetterExtraction


@dataclass(frozen=True)
class BoundedTruthAssessment:
    report: TruthReport
    external_use_allowed: bool
    messages: tuple[str, ...]


class BoundedCoverLetterService:
    """Pack → one composer call → claim checks → CoverLetter. Truth is separate."""

    def __init__(
        self,
        composer: CoverLetterComposer,
        *,
        truth_service: TruthValidationService | None = None,
    ) -> None:
        self._composer = composer
        self._truth = truth_service or TruthValidationService()

    def compose(
        self,
        strategy: ApplicationStrategy,
        profile: CareerProfile,
        plan: CoverLetterPlan,
        *,
        options: CoverLetterGenerationOptions | None = None,
    ) -> BoundedCoverLetterResult:
        resolved = options or CoverLetterGenerationOptions()
        if not resolved.cover_letter_plan_approved:
            raise CoverLetterGenerationGateError(
                "cover_letter_plan_approved must be True before bounded "
                "cover letter composition"
            )
        pack = build_cover_letter_evidence_pack(
            profile=profile,
            strategy=strategy,
            plan=plan,
            contact=resolved.contact,
        )
        extraction = self._composer.compose(pack)
        errors = validate_composed_paragraphs(
            extraction.paragraphs,
            pack,
            profile=profile,
        )
        if errors:
            raise CoverLetterGenerationValidationError(
                [
                    ErrorDetail(loc=("paragraphs",), msg=message, type="value_error")
                    for message in errors
                ]
            )
        letter = _build_letter(
            strategy=strategy,
            profile=profile,
            plan=plan,
            paragraphs=list(extraction.paragraphs),
            contact=resolved.contact,
        )
        validate_fidelity(letter, plan)
        return BoundedCoverLetterResult(
            letter=letter,
            pack=pack,
            extraction=extraction,
        )

    def assess_truth(
        self,
        *,
        markdown: str,
        profile: CareerProfile,
        artefact_path: str | None,
        opportunity_id: str | None,
    ) -> BoundedTruthAssessment:
        report = self._truth.validate_markdown(
            markdown=markdown,
            profile=profile,
            artefact_kind="cover_letter_markdown",
            artefact_path=artefact_path,
            opportunity_id=opportunity_id,
        )
        allowed, messages = evaluate_report_for_external_use(
            report,
            current_markdown=markdown,
        )
        return BoundedTruthAssessment(
            report=report,
            external_use_allowed=allowed,
            messages=tuple(messages),
        )


def write_evidence_pack(path: Path, pack: CoverLetterEvidencePack) -> None:
    path.write_text(
        json.dumps(pack.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def write_truth_report(path: Path, report: TruthReport) -> None:
    path.write_text(
        json.dumps(report.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def validate_composed_paragraphs(
    paragraphs: list[str],
    pack: CoverLetterEvidencePack,
    *,
    profile: CareerProfile,
) -> list[str]:
    """Reject unsupported claims before truth validation. Do not auto-repair."""
    errors: list[str] = []
    body = " ".join(paragraphs)
    folded = body.casefold()

    for phrase in _FORBIDDEN_PHRASES:
        if phrase in folded:
            errors.append(f"composed prose contains forbidden phrase '{phrase}'")

    if not pack.commercial_ai_employment:
        for phrase in _COMMERCIAL_AI_PHRASES:
            if _has_unnegated_phrase(folded, phrase):
                errors.append(
                    "composed prose recasts independent AI work as commercial "
                    f"AI employment ('{phrase}')"
                )
        if _has_unnegated_phrase(folded, "commercial ai employment"):
            errors.append(
                "composed prose recasts independent AI work as commercial "
                "AI employment ('commercial ai employment')"
            )

    if not pack.candidate_has_ml_expertise:
        for phrase in _ML_PHRASES:
            if phrase in folded:
                errors.append(
                    f"composed prose claims unsupported ML expertise ('{phrase}')"
                )

    if _METRIC_RE.search(body):
        packed = " ".join(
            pack.approved_claims + [item.purpose for item in pack.projects]
        )
        if not _METRIC_RE.search(packed):
            errors.append(
                "composed prose invents a metric not present in the evidence pack"
            )

    allowed_orgs = {name.casefold() for name in pack.allowed_employer_names}
    for entry in profile.experience:
        name = entry.organisation.casefold()
        if name and name not in allowed_orgs and name in folded:
            errors.append(
                f"composed prose mentions organisation '{entry.organisation}' "
                "that was not supplied in the evidence pack"
            )

    allowed_projects = {name.casefold() for name in pack.allowed_project_names}
    for project in profile.projects:
        name = project.name.casefold()
        if name and name not in allowed_projects and name in folded:
            errors.append(
                f"composed prose mentions project '{project.name}' that was "
                "not supplied in the evidence pack"
            )

    invented_url = False
    allowed_urls = {
        value.casefold()
        for value in (
            pack.contact.linkedin_url,
            pack.contact.portfolio_url,
            pack.contact.github_url,
        )
        if value
    }
    if "github.com/" in folded:
        allowed = (pack.contact.github_url or "").casefold()
        if not allowed or allowed not in folded:
            invented_url = True
    for match in re.findall(r"https?://[^\s)]+", body, flags=re.IGNORECASE):
        if match.rstrip(".,;").casefold() not in allowed_urls:
            invented_url = True
    if invented_url:
        errors.append(
            "composed prose includes a URL that was not supplied in contact"
        )

    return errors


def _has_unnegated_phrase(folded: str, phrase: str) -> bool:
    start = 0
    while True:
        pos = folded.find(phrase, start)
        if pos < 0:
            return False
        window = folded[max(0, pos - 24) : pos]
        if not re.search(r"\bnot\b(?:\s+conventional)?\s+$", window):
            return True
        start = pos + len(phrase)


def _build_letter(
    *,
    strategy: ApplicationStrategy,
    profile: CareerProfile,
    plan: CoverLetterPlan,
    paragraphs: list[str],
    contact: ContactDetails | None,
) -> CoverLetter:
    contact_dict = _contact_as_dict(contact)
    assumptions = list(plan.assumptions) + [
        "Cover letter composed by a bounded LLM from a deterministic evidence "
        "pack; CareerProfile remains authoritative (experimental path)."
    ]
    try:
        draft = CoverLetter.model_construct(
            full_name=profile.identity.full_name,
            company=plan.company_alignment.company,
            role_title=plan.role_motivation.role_title,
            salutation="Hello,",
            paragraphs=paragraphs,
            rendered_markdown="pending",
            contact=contact_dict,
            job_analysis=strategy.job_analysis,
            application_tier=strategy.application_tier,
            pursuit_posture=strategy.pursuit_posture,
            assumptions=assumptions,
            cover_letter_plan_approved=True,
            owner_review_required=True,
            composition_source="bounded_llm_composition",
        )
        rendered = render_markdown(draft)
        return CoverLetter.model_validate(
            {
                "full_name": profile.identity.full_name,
                "company": plan.company_alignment.company,
                "role_title": plan.role_motivation.role_title,
                "salutation": "Hello,",
                "paragraphs": paragraphs,
                "rendered_markdown": rendered,
                "contact": contact_dict,
                "job_analysis": strategy.job_analysis,
                "application_tier": strategy.application_tier,
                "pursuit_posture": strategy.pursuit_posture,
                "assumptions": assumptions,
                "cover_letter_plan_approved": True,
                "owner_review_required": True,
                "composition_source": "bounded_llm_composition",
            }
        )
    except ValidationError as error:
        raise CoverLetterGenerationValidationError(
            [ErrorDetail.from_pydantic(item) for item in error.errors()]
        ) from error


def _contact_as_dict(contact: ContactDetails | None) -> dict[str, str] | None:
    if contact is None:
        return None
    payload = contact.model_dump(exclude_none=True)
    return {key: value for key, value in payload.items() if value} or None
