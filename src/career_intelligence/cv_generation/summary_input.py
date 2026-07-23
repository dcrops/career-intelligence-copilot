"""Build plan-derived SummaryRewriteInput without raw job-description text."""

from __future__ import annotations

from career_intelligence.profile.models import CareerProfile

from .models import TailoringPlan
from .summary_rewriter import (
    SUMMARY_PROMPT_VERSION,
    PreferredProjectInput,
    PreferredSkillInput,
    SummaryRewriteInput,
    SummaryThemeInput,
)

_DEFAULT_CONSTRAINTS = (
    "Do not invent technologies, employers, projects, certifications, "
    "achievements, or years of experience.",
    "Do not claim commercial employment or client delivery unless already "
    "stated in SourceSummary.",
    "Independent engineering and portfolio work are not paid employment.",
    "Professional-development-only capabilities must not be overstated as "
    "production tenure.",
    "Cover MandatoryThemes; do not introduce other themes.",
    "Never mention ProhibitedTechnologies.",
)


def build_summary_rewrite_input(
    profile: CareerProfile,
    plan: TailoringPlan,
) -> SummaryRewriteInput:
    source = (profile.identity.summary or "").strip()
    if not source:
        source = (
            f"{profile.identity.full_name} is targeting the role of "
            f"{profile.identity.target_role}."
        )

    themes = tuple(
        SummaryThemeInput(
            rank=item.rank,
            theme=item.theme,
            rationale=item.rationale,
        )
        for item in plan.summary_themes
    )
    skills = tuple(
        PreferredSkillInput(skill_name=item.skill_name, category=item.category)
        for item in plan.skills_to_promote
    )

    projects_by_id = {project.id: project for project in profile.projects}
    preferred_projects: list[PreferredProjectInput] = []
    allowed_project_names: list[str] = []
    allowed_technologies: list[str] = []

    for skill in plan.skills_to_promote:
        allowed_technologies.append(skill.skill_name)

    for item in plan.projects_to_emphasise:
        project = projects_by_id.get(item.project_id)
        if project is None:
            continue
        preferred_projects.append(
            PreferredProjectInput(
                name=project.name,
                summary=project.summary,
                outcomes=tuple(project.outcomes),
            )
        )
        allowed_project_names.append(project.name)
        allowed_technologies.extend(project.technologies)

    prohibited = tuple(
        dict.fromkeys(
            priority.label
            for priority in plan.jd_priorities
            if priority.candidate_support == "unsupported"
        )
    )

    allowed_employers = tuple(
        dict.fromkeys(entry.organisation for entry in profile.experience)
    )
    allowed_certifications = tuple(
        dict.fromkeys(cert.name for cert in profile.certifications)
    )

    return SummaryRewriteInput(
        source_summary=source,
        mandatory_themes=themes,
        preferred_skills=skills,
        preferred_projects=tuple(preferred_projects),
        allowed_technologies=tuple(dict.fromkeys(allowed_technologies)),
        prohibited_technologies=prohibited,
        allowed_employers=allowed_employers,
        allowed_project_names=tuple(dict.fromkeys(allowed_project_names)),
        allowed_certifications=allowed_certifications,
        constraints=_DEFAULT_CONSTRAINTS,
        prompt_version=SUMMARY_PROMPT_VERSION,
    )


def known_entity_catalogues(profile: CareerProfile) -> dict[str, tuple[str, ...]]:
    """Full profile catalogues used to detect invented named entities."""
    return {
        "known_employers": tuple(
            dict.fromkeys(entry.organisation for entry in profile.experience)
        ),
        "known_projects": tuple(dict.fromkeys(project.name for project in profile.projects)),
        "known_certifications": tuple(
            dict.fromkeys(cert.name for cert in profile.certifications)
        ),
        "known_technologies": tuple(
            dict.fromkeys(
                [
                    *(skill.name for skill in profile.skills.technical),
                    *(skill.name for skill in profile.skills.domain),
                    *(skill.name for skill in profile.skills.soft),
                    *(
                        tech
                        for project in profile.projects
                        for tech in project.technologies
                    ),
                    *(
                        tech
                        for entry in profile.experience
                        for tech in entry.technologies
                    ),
                ]
            )
        ),
    }
