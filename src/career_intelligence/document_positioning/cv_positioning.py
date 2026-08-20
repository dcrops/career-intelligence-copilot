"""Bounded CV positioning service (M3).

Pack → one composer call → claim checks → Master-adapt with rewrite-surface
overrides. Fail closed. Does not call FR-014. Not invoked by
``cic package prepare`` in M3 (M6 owns that wiring).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from pydantic import ValidationError

from career_intelligence.cv_generation.master_adapt import (
    adapt_master_cv_markdown,
    extract_h2_section,
    extract_master_project_bodies,
)
from career_intelligence.cv_generation.models import TailoringPlan
from career_intelligence.cv_generation.options import ContactDetails
from career_intelligence.document_positioning.builder import build_positioning_plan
from career_intelligence.document_positioning.cv_composer import (
    CvPositioningComposer,
    CvPositioningExtraction,
    ProjectRelevanceLine,
)
from career_intelligence.document_positioning.cv_pack import (
    CvPositioningPack,
    build_cv_positioning_pack,
)
from career_intelligence.document_positioning.cv_validation import (
    sanitize_optional_relevance_lines,
    validate_positioning_output,
)
from career_intelligence.document_positioning.errors import (
    CvPositioningProviderError,
    CvPositioningValidationError,
    ErrorDetail,
)
from career_intelligence.job_analysis.models import JobAnalysis
from career_intelligence.opportunity_assessment.models import OpportunityAssessment
from career_intelligence.profile.models import CareerProfile

_LOCKED_HEADINGS = (
    "professional experience",
    "courses & upskilling",
    "certifications",
    "earlier experience",
)
_CANONICAL_FOOTER = re.compile(
    r"(?:\n---\s*)?(?:\n\*Canonical Master CV[^*]*\*)?\s*$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class BoundedCvPositioningResult:
    markdown: str
    pack: CvPositioningPack
    extraction: CvPositioningExtraction
    include_methodology: bool


class BoundedCvPositioningService:
    """Deterministic pack + bounded writer + fail-closed validation."""

    def __init__(self, composer: CvPositioningComposer) -> None:
        self._composer = composer

    def compose(
        self,
        job: JobAnalysis,
        profile: CareerProfile,
        tailoring: TailoringPlan,
        master_markdown: str,
        *,
        assessment: OpportunityAssessment | None = None,
        contact: ContactDetails | None = None,
        target_role: str | None = None,
    ) -> BoundedCvPositioningResult:
        positioning = build_positioning_plan(job, profile, assessment=assessment)
        pack = build_cv_positioning_pack(
            job,
            profile,
            positioning,
            tailoring,
            master_markdown,
            assessment=assessment,
        )
        try:
            extraction = self._composer.compose(pack)
            if not isinstance(extraction, CvPositioningExtraction):
                extraction = CvPositioningExtraction.model_validate(extraction)
        except CvPositioningProviderError:
            raise
        except CvPositioningValidationError:
            raise
        except ValidationError as error:
            raise CvPositioningValidationError(
                [ErrorDetail.from_pydantic(item) for item in error.errors()]
            ) from error
        except Exception as error:
            raise CvPositioningProviderError(
                f"CV positioning composer failed: {error}"
            ) from error

        master_project_names = tuple(extract_master_project_bodies(master_markdown))
        raw_relevance = tuple(
            (item.project_name, item.line) for item in extraction.project_relevance
        )
        summary_errors = validate_positioning_output(
            summary=extraction.summary,
            relevance_lines=(),
            pack=pack,
            all_master_project_names=master_project_names,
        )
        if summary_errors:
            raise CvPositioningValidationError(
                [
                    ErrorDetail(loc=("positioned_prose",), msg=message, type="value_error")
                    for message in summary_errors
                ]
            )
        relevance = sanitize_optional_relevance_lines(
            summary=extraction.summary,
            relevance_lines=raw_relevance,
            pack=pack,
            all_master_project_names=master_project_names,
        )
        errors = validate_positioning_output(
            summary=extraction.summary,
            relevance_lines=relevance,
            pack=pack,
            all_master_project_names=master_project_names,
        )
        if errors:
            raise CvPositioningValidationError(
                [
                    ErrorDetail(loc=("positioned_prose",), msg=message, type="value_error")
                    for message in errors
                ]
            )
        if relevance != raw_relevance:
            extraction = extraction.model_copy(
                update={
                    "project_relevance": [
                        ProjectRelevanceLine(project_name=name, line=line)
                        for name, line in relevance
                    ]
                }
            )

        role = target_role or pack.role_title
        markdown = adapt_master_cv_markdown(
            master_markdown,
            profile=profile,
            plan=tailoring,
            target_role=role,
            contact=contact,
            omit_methodology=not pack.include_methodology,
            summary_override=extraction.summary,
            highlight_override=list(pack.selected_highlights),
            project_relevance_lines=dict(relevance),
        )
        lock_errors = validate_locked_master_sections(master_markdown, markdown)
        if lock_errors:
            raise CvPositioningValidationError(
                [
                    ErrorDetail(loc=("locked_sections",), msg=message, type="value_error")
                    for message in lock_errors
                ]
            )
        return BoundedCvPositioningResult(
            markdown=markdown,
            pack=pack,
            extraction=extraction,
            include_methodology=pack.include_methodology,
        )


def validate_locked_master_sections(master_markdown: str, positioned: str) -> list[str]:
    errors: list[str] = []
    for heading in _LOCKED_HEADINGS:
        original = extract_h2_section(master_markdown, heading)
        rendered = extract_h2_section(positioned, heading)
        if original is None:
            continue
        if rendered is None:
            errors.append(f"locked section '{heading}' was dropped")
            continue
        if _normalise_locked_section(original) != _normalise_locked_section(rendered):
            errors.append(f"locked section '{heading}' was rewritten")
    original_projects = extract_master_project_bodies(master_markdown)
    positioned_projects = extract_master_project_bodies(positioned)
    for name, body in positioned_projects.items():
        original = original_projects.get(name)
        if original is None:
            continue
        stripped = _strip_relevance_line(body)
        if stripped != original:
            errors.append(f"locked project body '{name}' was rewritten")
    return errors


def _normalise_locked_section(text: str) -> str:
    return _CANONICAL_FOOTER.sub("", text.strip()).strip()


def _strip_relevance_line(body: str) -> str:
    lines = body.split("\n")
    if lines and lines[0].startswith("*Relevant to this role:"):
        rest = lines[1:]
        if rest and rest[0].strip() == "":
            rest = rest[1:]
        return "\n".join(rest).strip()
    return body.strip()
