"""Fidelity checks between CoverLetterPlan and rendered CoverLetter."""

from __future__ import annotations

from .errors import CoverLetterGenerationValidationError, ErrorDetail
from .models import CoverLetter, CoverLetterPlan


def validate_fidelity(letter: CoverLetter, plan: CoverLetterPlan) -> None:
    """Ensure the letter surfaces company, role, and planned portfolio evidence."""
    errors: list[ErrorDetail] = []
    body = " ".join(letter.paragraphs).casefold()

    company = plan.company_alignment.company.casefold()
    if company not in body and company not in letter.company.casefold():
        errors.append(
            ErrorDetail(
                loc=("paragraphs",),
                msg="cover letter must reference the planned company",
                type="value_error",
            )
        )

    role = plan.role_motivation.role_title.casefold()
    if role not in body and role not in letter.role_title.casefold():
        errors.append(
            ErrorDetail(
                loc=("paragraphs",),
                msg="cover letter must reference the planned role title",
                type="value_error",
            )
        )

    if plan.strongest_projects:
        named = any(
            project.project_name.casefold() in body
            for project in plan.strongest_projects
        )
        if not named:
            errors.append(
                ErrorDetail(
                    loc=("paragraphs",),
                    msg="cover letter must reference at least one planned portfolio project",
                    type="value_error",
                )
            )

    if letter.owner_review_required is not True:
        errors.append(
            ErrorDetail(
                loc=("owner_review_required",),
                msg="owner_review_required must be True",
                type="value_error",
            )
        )

    if errors:
        raise CoverLetterGenerationValidationError(errors)
