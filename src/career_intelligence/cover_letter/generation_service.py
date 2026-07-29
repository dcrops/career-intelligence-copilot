"""Public trust boundary for CoverLetter rendering (FR-007 Phase B)."""

from __future__ import annotations

from pydantic import ValidationError

from career_intelligence.application_strategy.models import ApplicationStrategy
from career_intelligence.cv_generation.options import ContactDetails
from career_intelligence.profile.models import CareerProfile

from .composer import compose_cover_letter_paragraphs
from .errors import (
    CoverLetterGenerationGateError,
    CoverLetterGenerationValidationError,
    ErrorDetail,
)
from .fidelity import validate_fidelity
from .models import CoverLetter, CoverLetterPlan
from .options import CoverLetterGenerationOptions
from .render_markdown import render_markdown


class CoverLetterGenerationService:
    """Render an approved CoverLetterPlan into a trusted CoverLetter."""

    def generate(
        self,
        strategy: ApplicationStrategy,
        profile: CareerProfile,
        plan: CoverLetterPlan,
        *,
        options: CoverLetterGenerationOptions | None = None,
    ) -> CoverLetter:
        resolved = options or CoverLetterGenerationOptions()
        if not resolved.cover_letter_plan_approved:
            raise CoverLetterGenerationGateError(
                "cover_letter_plan_approved must be True before generating a "
                "CoverLetter"
            )

        self._reject_mismatched_postings(strategy, plan)
        self._reject_strategy_plan_drift(strategy, plan)

        contact = _contact_as_dict(resolved.contact)
        paragraphs = compose_cover_letter_paragraphs(
            plan,
            profile,
            contact=contact,
        )
        assumptions = list(plan.assumptions) + [
            "Cover letter composed deterministically from CoverLetterPlan fields "
            "and Career Profile evidence (narrative rendering; no LLM rewrite)."
        ]

        draft = CoverLetter.model_construct(
            full_name=profile.identity.full_name,
            company=plan.company_alignment.company,
            role_title=plan.role_motivation.role_title,
            salutation="Hello,",
            paragraphs=paragraphs,
            rendered_markdown="pending",
            contact=contact,
            job_analysis=strategy.job_analysis,
            application_tier=strategy.application_tier,
            pursuit_posture=strategy.pursuit_posture,
            assumptions=assumptions,
            cover_letter_plan_approved=True,
            owner_review_required=True,
            composition_source="deterministic_composition",
        )
        rendered = render_markdown(draft)
        letter = self._validate(
            {
                "full_name": profile.identity.full_name,
                "company": plan.company_alignment.company,
                "role_title": plan.role_motivation.role_title,
                "salutation": "Hello,",
                "paragraphs": paragraphs,
                "rendered_markdown": rendered,
                "contact": contact,
                "job_analysis": strategy.job_analysis,
                "application_tier": strategy.application_tier,
                "pursuit_posture": strategy.pursuit_posture,
                "assumptions": assumptions,
                "cover_letter_plan_approved": True,
                "owner_review_required": True,
                "composition_source": "deterministic_composition",
            }
        )
        validate_fidelity(letter, plan)
        return letter

    def _reject_mismatched_postings(
        self,
        strategy: ApplicationStrategy,
        plan: CoverLetterPlan,
    ) -> None:
        if strategy.job_analysis.posting != plan.job_analysis.posting:
            raise CoverLetterGenerationGateError(
                "ApplicationStrategy and CoverLetterPlan job postings do not match"
            )

    def _reject_strategy_plan_drift(
        self,
        strategy: ApplicationStrategy,
        plan: CoverLetterPlan,
    ) -> None:
        if strategy.application_tier != plan.application_tier:
            raise CoverLetterGenerationGateError(
                "application_tier drifted between ApplicationStrategy and CoverLetterPlan"
            )
        if strategy.pursuit_posture != plan.pursuit_posture:
            raise CoverLetterGenerationGateError(
                "pursuit_posture drifted between ApplicationStrategy and CoverLetterPlan"
            )

    def _validate(self, payload: dict[str, object]) -> CoverLetter:
        try:
            return CoverLetter.model_validate(payload)
        except ValidationError as error:
            raise CoverLetterGenerationValidationError(
                [ErrorDetail.from_pydantic(item) for item in error.errors()]
            ) from error


def _contact_as_dict(contact: ContactDetails | None) -> dict[str, str] | None:
    if contact is None:
        return None
    payload = contact.model_dump(exclude_none=True)
    return {key: value for key, value in payload.items() if value} or None
