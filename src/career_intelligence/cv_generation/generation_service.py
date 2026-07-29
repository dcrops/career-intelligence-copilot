"""Public trust boundary for TailoredCv rendering (FR-006 Phase B/C).

Deterministic plan remains authoritative. Phase C may rewrite summary prose
only via an injected SummaryRewriter; failures fall back to the profile summary.
"""

from __future__ import annotations

from pydantic import ValidationError

from career_intelligence.application_strategy.models import ApplicationStrategy
from career_intelligence.job_analysis.models import JobPosting
from career_intelligence.profile.models import CareerProfile, ExperienceEntry, Project

from .baseline import (
    CERTIFICATIONS_BASELINE_ASSUMPTION,
    active_certifications_baseline,
)
from .content_selection import select_by_relevance, select_engineering_highlights
from .errors import (
    CvGenerationError,
    CvGenerationGateError,
    CvGenerationValidationError,
    ErrorDetail,
)
from .fidelity import validate_fidelity
from .fixture_summary_rewriter import FixtureSummaryRewriter
from .models import TailoredCv, TailoringPlan
from .openai_summary_rewriter import OpenAISummaryRewriter
from .options import CvGenerationOptions
from .render_markdown import contact_as_dict, render_markdown
from .summary_input import build_summary_rewrite_input, known_entity_catalogues
from .summary_prompt import SUMMARY_PROMPT_VERSION
from .summary_rewriter import SummaryRewriter, SummarySource
from .summary_validation import validate_rewritten_summary
from .theme_aware_summary import compose_theme_aware_summary

_MAX_EXPERIENCE_HIGHLIGHTS = 4
_MAX_PROJECT_OUTCOMES = 2
_MAX_PROJECT_DEMONSTRATES = 5
_MAX_SELECTED_HIGHLIGHTS = 5


class CvGenerationService:
    """Render a trusted TailoredCv from an approved TailoringPlan.

    The service contains no emphasis policy. Ordering and inclusion come only
    from the TailoringPlan. Callers must set ``tailoring_plan_approved=True``.

    Phase C: pass ``summary_rewriter`` and set ``options.rewrite_summary=True``.
    """

    def __init__(self, summary_rewriter: SummaryRewriter | None = None) -> None:
        self._summary_rewriter = summary_rewriter

    def generate(
        self,
        strategy: ApplicationStrategy,
        profile: CareerProfile,
        plan: TailoringPlan,
        *,
        options: CvGenerationOptions | None = None,
    ) -> TailoredCv:
        resolved = options or CvGenerationOptions()
        if not resolved.tailoring_plan_approved:
            raise CvGenerationGateError(
                "tailoring_plan_approved must be True before generating a "
                "TailoredCv"
            )
        if resolved.rewrite_summary and self._summary_rewriter is None:
            raise CvGenerationGateError(
                "rewrite_summary=True requires a SummaryRewriter on "
                "CvGenerationService"
            )

        self._reject_mismatched_postings(strategy, plan)
        self._reject_strategy_plan_drift(strategy, plan)

        projects = self._render_projects(profile, plan)
        skills = self._render_skills(plan)
        experience = self._render_experience(profile, plan)
        certifications = active_certifications_baseline(profile)
        relevance_terms = _relevance_terms(plan)
        # Impact-first ordering: curated lead bullet stays first; remaining
        # profile highlights are relevance-ranked without inventing text.
        selected_highlights = select_engineering_highlights(
            profile.selected_engineering_highlights,
            relevance_terms,
            max_items=_MAX_SELECTED_HIGHLIGHTS,
        )
        methodology = _methodology_payload(profile)

        summary, summary_source, rewrite_assumptions = self._resolve_summary(
            profile, plan, resolved
        )

        contact = contact_as_dict(resolved.contact)
        assumptions = list(plan.assumptions) + rewrite_assumptions + [
            CERTIFICATIONS_BASELINE_ASSUMPTION,
        ]
        if selected_highlights != list(profile.selected_engineering_highlights):
            assumptions.append(
                "Selected engineering highlights ordered by TailoringPlan "
                "relevance; only Career Profile highlight text was used."
            )
        assumptions.append(
            "Experience highlights and project demonstrates/outcomes were "
            "selected from Career Profile text by TailoringPlan relevance."
        )
        target_role = _resolve_target_role(strategy, profile)
        draft = {
            "job_analysis": strategy.job_analysis,
            "full_name": profile.identity.full_name,
            "target_role": target_role,
            "summary": summary,
            "summary_source": summary_source,
            "summary_themes": [theme.theme for theme in plan.summary_themes],
            "selected_engineering_highlights": selected_highlights,
            "skills": skills,
            "projects": projects,
            "experience": experience,
            "engineering_methodology": methodology,
            "certifications": certifications,
            "certifications_source": "profile_active_baseline",
            "contact": contact,
            "rendered_markdown": "pending",
            "owner_review_required": True,
            "tailoring_plan_approved": True,
            "experience_guidance_kind": plan.experience_guidance.kind,
            "assumptions": assumptions,
        }

        cv = self._validate(draft)
        markdown = render_markdown(cv, presentation=resolved.presentation)
        cv = self._validate({**draft, "rendered_markdown": markdown})
        validate_fidelity(cv, plan)
        return cv

    def _resolve_summary(
        self,
        profile: CareerProfile,
        plan: TailoringPlan,
        options: CvGenerationOptions,
    ) -> tuple[str | None, SummarySource, list[str]]:
        profile_summary = profile.identity.summary
        if not options.rewrite_summary:
            themes = [theme.theme for theme in plan.summary_themes]
            promoted = [skill.skill_name for skill in plan.skills_to_promote]
            if themes or promoted:
                methodology_philosophy = None
                if profile.engineering_methodology is not None:
                    methodology_philosophy = (
                        profile.engineering_methodology.philosophy
                    )
                composed = compose_theme_aware_summary(
                    source_summary=profile_summary,
                    target_role=profile.identity.target_role,
                    themes=themes,
                    promoted_skills=promoted,
                    methodology_philosophy=methodology_philosophy,
                )
                return (
                    composed,
                    "theme_aware_composition",
                    [
                        "Summary composed via FR-006c Summary Intelligence "
                        "from TailoringPlan themes/promoted skills and Career "
                        "Profile evidence (rewrite_summary=False)."
                    ],
                )
            return (
                profile_summary,
                "profile_copy",
                [
                    "Summary copied from the career profile "
                    "(rewrite_summary=False; no themes or promoted skills)."
                ],
            )

        if not plan.summary_themes:
            return (
                profile_summary,
                "profile_copy",
                [
                    "Summary rewrite skipped because TailoringPlan.summary_themes "
                    "is empty; profile summary retained."
                ],
            )

        assert self._summary_rewriter is not None
        rewrite_input = build_summary_rewrite_input(profile, plan)
        catalogues = known_entity_catalogues(profile)
        try:
            extraction = self._summary_rewriter.rewrite(rewrite_input)
            validation = validate_rewritten_summary(
                extraction.summary,
                rewrite_input,
                known_employers=catalogues["known_employers"],
                known_projects=catalogues["known_projects"],
                known_certifications=catalogues["known_certifications"],
                known_technologies=catalogues["known_technologies"],
            )
            if not validation.ok:
                return (
                    profile_summary,
                    "fallback_profile_copy",
                    [
                        "Summary rewrite failed validation; fell back to profile "
                        "summary. "
                        + "; ".join(validation.errors),
                        f"summary_prompt_version={SUMMARY_PROMPT_VERSION}",
                    ],
                )
            source = _rewrite_source_for(self._summary_rewriter)
            model_note = ""
            model = getattr(self._summary_rewriter, "model", None)
            if isinstance(model, str) and model:
                model_note = f", model={model}"
            return (
                extraction.summary,
                source,
                [
                    f"Summary rewritten via Phase C ({source}; "
                    f"prompt={SUMMARY_PROMPT_VERSION}{model_note})."
                ],
            )
        except (CvGenerationError, CvGenerationValidationError, Exception) as error:
            return (
                profile_summary,
                "fallback_profile_copy",
                [
                    "Summary rewrite failed; fell back to profile summary: "
                    f"{error}",
                    f"summary_prompt_version={SUMMARY_PROMPT_VERSION}",
                ],
            )

    def _reject_mismatched_postings(
        self,
        strategy: ApplicationStrategy,
        plan: TailoringPlan,
    ) -> None:
        if _same_posting(strategy.job_analysis.posting, plan.job_analysis.posting):
            return
        raise CvGenerationGateError(
            "ApplicationStrategy and TailoringPlan must refer to the same "
            "JobPosting identity"
        )

    def _reject_strategy_plan_drift(
        self,
        strategy: ApplicationStrategy,
        plan: TailoringPlan,
    ) -> None:
        if plan.application_tier != strategy.application_tier:
            raise CvGenerationGateError(
                "TailoringPlan.application_tier does not match ApplicationStrategy"
            )
        if plan.pursuit_posture != strategy.pursuit_posture:
            raise CvGenerationGateError(
                "TailoringPlan.pursuit_posture does not match ApplicationStrategy"
            )

    def _render_projects(
        self,
        profile: CareerProfile,
        plan: TailoringPlan,
    ) -> list[dict[str, object]]:
        by_id = {project.id: project for project in profile.projects}
        relevance_terms = _relevance_terms(plan)
        rendered: list[dict[str, object]] = []
        for item in plan.projects_to_emphasise:
            project = by_id.get(item.project_id)
            if project is None:
                raise CvGenerationValidationError(
                    [
                        ErrorDetail(
                            loc=("projects",),
                            msg=(
                                f"plan project_id '{item.project_id}' is absent "
                                "from the career profile"
                            ),
                            type="value_error",
                        )
                    ]
                )
            rendered.append(_project_payload(project, relevance_terms))
        return rendered

    def _render_skills(self, plan: TailoringPlan) -> list[dict[str, object]]:
        skills: list[dict[str, object]] = []
        for item in plan.skills_to_promote:
            skills.append(
                {
                    "skill_name": item.skill_name,
                    "category": item.category,
                    "emphasised": True,
                }
            )
        for item in plan.skills_not_emphasised:
            skills.append(
                {
                    "skill_name": item.skill_name,
                    "category": item.category,
                    "emphasised": False,
                }
            )
        return skills

    def _render_experience(
        self,
        profile: CareerProfile,
        plan: TailoringPlan,
    ) -> list[dict[str, object]]:
        by_id = {entry.id: entry for entry in profile.experience}
        relevance_terms = _relevance_terms(plan)
        rendered: list[dict[str, object]] = []
        for experience_id in plan.experience_guidance.included_experience_ids:
            entry = by_id.get(experience_id)
            if entry is None:
                raise CvGenerationValidationError(
                    [
                        ErrorDetail(
                            loc=("experience",),
                            msg=(
                                f"plan experience id '{experience_id}' is absent "
                                "from the career profile"
                            ),
                            type="value_error",
                        )
                    ]
                )
            rendered.append(_experience_payload(entry, relevance_terms))
        return rendered

    def _validate(self, payload: dict[str, object]) -> TailoredCv:
        try:
            return TailoredCv.model_validate(payload)
        except ValidationError as error:
            raise CvGenerationValidationError(
                [ErrorDetail.from_pydantic(item) for item in error.errors()]
            ) from error


def _relevance_terms(plan: TailoringPlan) -> list[str]:
    terms: list[str] = []
    for theme in plan.summary_themes:
        terms.append(theme.theme)
    for skill in plan.skills_to_promote:
        terms.append(skill.skill_name)
    for priority in plan.jd_priorities:
        if priority.candidate_support != "unsupported":
            terms.append(priority.label)
    return terms


def _methodology_payload(profile: CareerProfile) -> dict[str, object] | None:
    methodology = profile.engineering_methodology
    if methodology is None:
        return None
    return {
        "philosophy": methodology.philosophy,
        "categories": [
            {"name": category.name, "practices": list(category.practices)}
            for category in methodology.categories
        ],
    }


def _rewrite_source_for(rewriter: SummaryRewriter) -> SummarySource:
    if isinstance(rewriter, OpenAISummaryRewriter):
        return "openai_rewrite"
    if isinstance(rewriter, FixtureSummaryRewriter):
        return "fixture_rewrite"
    # Custom test doubles default to fixture_rewrite semantics.
    return "fixture_rewrite"


def _project_payload(
    project: Project,
    relevance_terms: list[str],
) -> dict[str, object]:
    return {
        "project_id": project.id,
        "name": project.name,
        "summary": project.summary,
        "technologies": list(project.technologies),
        "outcomes": select_by_relevance(
            project.outcomes,
            relevance_terms,
            max_items=_MAX_PROJECT_OUTCOMES,
            min_items=min(1, len(project.outcomes)),
        ),
        "demonstrates": select_by_relevance(
            project.demonstrates,
            relevance_terms,
            max_items=_MAX_PROJECT_DEMONSTRATES,
            min_items=min(3, len(project.demonstrates)),
        ),
    }


def _experience_payload(
    entry: ExperienceEntry,
    relevance_terms: list[str],
) -> dict[str, object]:
    start = entry.start_date.isoformat()[:7]
    end = entry.end_date.isoformat()[:7] if entry.end_date is not None else None
    return {
        "experience_id": entry.id,
        "kind": entry.kind,
        "organisation": entry.organisation,
        "title": entry.title,
        "start_date": start,
        "end_date": end,
        "location": entry.location,
        "highlights": select_by_relevance(
            entry.highlights,
            relevance_terms,
            max_items=_MAX_EXPERIENCE_HIGHLIGHTS,
            min_items=min(2, len(entry.highlights)),
        ),
        "technologies": list(entry.technologies),
    }


def _resolve_target_role(
    strategy: ApplicationStrategy,
    profile: CareerProfile,
) -> str:
    posting_title = (strategy.job_analysis.posting.title or "").strip()
    if posting_title:
        return posting_title
    return profile.identity.target_role


def _same_posting(left: JobPosting, right: JobPosting) -> bool:
    return (
        left.raw_text == right.raw_text
        and left.title == right.title
        and left.company == right.company
        and left.source_url == right.source_url
    )
