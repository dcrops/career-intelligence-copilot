"""Deterministic evidence pack for bounded LLM cover-letter composition.

CareerProfile, CoverLetterPlan, ApplicationStrategy, and caller ContactDetails
remain authoritative. The pack lists only claims the composer may use.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from career_intelligence.application_strategy.models import ApplicationStrategy
from career_intelligence.cover_letter.models import CoverLetterPlan
from career_intelligence.cover_letter.project_eli10 import project_narrative
from career_intelligence.cv_generation.options import ContactDetails
from career_intelligence.profile.models import CareerProfile, ExperienceEntry, Project

NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]

ExperienceChapter = Literal[
    "commercial_testing_automation",
    "commercial_data_engineering",
    "independent_ai_engineering",
    "study",
    "other_commercial",
]

_MAX_RESPONSIBILITIES = 4
_MAX_HIGHLIGHTS = 3
_MAX_TESTING_ROLES = 2

# Title identity only — not highlights. A Data Engineer who mentions automated
# testing is not a testing/QA role.
_TESTING_TITLE_PHRASES = (
    "test analyst",
    "test engineer",
    "tester",
    "qa analyst",
    "qa engineer",
    "quality analyst",
    "quality engineer",
    "quality assurance",
    "sdet",
    "software tester",
    "test automation",
)
_DATA_ENGINEER_TITLE_PHRASES = ("data engineer", "data engineering")
_AI_STUDY_HINTS = ("ai engineering", "llm", "applied ai")
_AUTOMATION_EVIDENCE_HINTS = (
    "selenium",
    "automation",
    "automated",
    "pytest",
    "cucumber",
    "gherkin",
)
_ML_LABELS = (
    "tensorflow",
    "pytorch",
    "keras",
    "scikit-learn",
    "machine learning",
    "deep learning",
)
_CHAPTER_ORDER: dict[ExperienceChapter, int] = {
    "commercial_testing_automation": 0,
    "commercial_data_engineering": 1,
    "independent_ai_engineering": 2,
    "study": 3,
    "other_commercial": 4,
}


class PackModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class PackExperience(PackModel):
    id: NonEmptyString
    kind: Literal["employment", "independent_engineering", "professional_development"]
    organisation: NonEmptyString
    title: NonEmptyString
    relationship: Literal["commercial_employment", "independent_rd", "study"]
    chapter: ExperienceChapter
    start_date: NonEmptyString
    end_date: NonEmptyString | None = None
    highlights: list[NonEmptyString] = Field(default_factory=list)
    technologies: list[NonEmptyString] = Field(default_factory=list)


class PackProject(PackModel):
    id: NonEmptyString
    name: NonEmptyString
    purpose: NonEmptyString
    what_was_built: NonEmptyString
    engineering: NonEmptyString
    technologies: list[NonEmptyString] = Field(default_factory=list)
    outcomes: list[NonEmptyString] = Field(default_factory=list)
    relationship: Literal["independent_portfolio"] = "independent_portfolio"


class RoleContext(PackModel):
    company: NonEmptyString
    role_title: NonEmptyString
    role_family: NonEmptyString
    responsibilities: list[NonEmptyString] = Field(default_factory=list)
    employer_mentioned_technologies: list[NonEmptyString] = Field(default_factory=list)


class PackContact(PackModel):
    email: NonEmptyString | None = None
    phone: NonEmptyString | None = None
    location: NonEmptyString | None = None
    linkedin_url: NonEmptyString | None = None
    portfolio_url: NonEmptyString | None = None
    github_url: NonEmptyString | None = None


class TrajectoryChapter(PackModel):
    order: int = Field(ge=1)
    name: ExperienceChapter
    experience_ids: list[NonEmptyString] = Field(min_length=1)


class CareerTrajectory(PackModel):
    """Ordered career chapters the LLM may phrase but must not collapse."""

    authorised_duration_claim: NonEmptyString | None = None
    chapters: list[TrajectoryChapter] = Field(default_factory=list)


class CoverLetterEvidencePack(PackModel):
    """Approved evidence the LLM may express — not a letter draft."""

    candidate_name: NonEmptyString
    target_role: NonEmptyString
    identity_summary: NonEmptyString | None = None
    role_context: RoleContext
    experience: list[PackExperience] = Field(default_factory=list)
    projects: list[PackProject] = Field(default_factory=list)
    approved_claims: list[NonEmptyString] = Field(default_factory=list)
    career_trajectory: CareerTrajectory
    contact: PackContact
    commercial_ai_employment: bool
    candidate_has_ml_expertise: bool
    allowed_employer_names: list[NonEmptyString] = Field(default_factory=list)
    allowed_project_names: list[NonEmptyString] = Field(default_factory=list)
    allowed_technologies: list[NonEmptyString] = Field(default_factory=list)
    constraints: list[NonEmptyString] = Field(default_factory=list)


def build_cover_letter_evidence_pack(
    *,
    profile: CareerProfile,
    strategy: ApplicationStrategy,
    plan: CoverLetterPlan,
    contact: ContactDetails | None = None,
) -> CoverLetterEvidencePack:
    """Select supported evidence from existing typed sources only."""
    experience = _select_experience(profile)
    projects = _select_projects(profile, plan)
    approved_claims = [
        item.claim.strip() for item in plan.relevant_evidence if item.claim.strip()
    ]
    allowed_tech = _unique(
        *[entry.technologies for entry in experience],
        *[item.technologies for item in projects],
    )
    allowed_employers = _unique(
        [entry.organisation for entry in experience],
        [plan.company_alignment.company],
    )
    allowed_projects = [item.name for item in projects]
    commercial_ai = _has_commercial_ai_employment(profile)
    has_ml = _has_ml_expertise(profile, allowed_tech)
    pack_contact = _pack_contact(contact)
    trajectory = _career_trajectory(experience, approved_claims, profile.identity.summary)
    return CoverLetterEvidencePack(
        candidate_name=profile.identity.full_name,
        target_role=profile.identity.target_role,
        identity_summary=(profile.identity.summary or None),
        role_context=_role_context(strategy, plan),
        experience=experience,
        projects=projects,
        approved_claims=approved_claims,
        career_trajectory=trajectory,
        contact=pack_contact,
        commercial_ai_employment=commercial_ai,
        candidate_has_ml_expertise=has_ml,
        allowed_employer_names=allowed_employers,
        allowed_project_names=allowed_projects,
        allowed_technologies=allowed_tech,
        constraints=_constraints(
            commercial_ai_employment=commercial_ai,
            candidate_has_ml_expertise=has_ml,
            contact=pack_contact,
            trajectory=trajectory,
        ),
    )


def _role_context(
    strategy: ApplicationStrategy,
    plan: CoverLetterPlan,
) -> RoleContext:
    job = strategy.job_analysis
    responsibilities = [
        item.description.strip()
        for item in job.responsibilities[:_MAX_RESPONSIBILITIES]
        if item.description.strip()
    ]
    mentioned = _unique([tech.name for tech in job.technologies])
    return RoleContext(
        company=plan.company_alignment.company,
        role_title=plan.role_motivation.role_title,
        role_family=job.role_family.family,
        responsibilities=responsibilities,
        employer_mentioned_technologies=mentioned,
    )


def _select_experience(profile: CareerProfile) -> list[PackExperience]:
    selected: list[PackExperience] = []
    seen: set[str] = set()

    def _add(entry: ExperienceEntry) -> None:
        if entry.id in seen:
            return
        seen.add(entry.id)
        selected.append(_pack_experience(entry))

    for entry in _testing_employment(profile)[:_MAX_TESTING_ROLES]:
        _add(entry)
    for entry in profile.experience:
        if entry.kind == "employment" and _is_data_engineering_role(entry):
            _add(entry)
    for entry in profile.experience:
        if entry.kind == "independent_engineering":
            _add(entry)
    study = [
        entry
        for entry in profile.experience
        if entry.kind == "professional_development" and _looks_like_ai_study(entry)
    ]
    study.sort(key=lambda item: item.start_date, reverse=True)
    if study:
        _add(study[0])
    selected.sort(key=lambda item: (_CHAPTER_ORDER[item.chapter], item.start_date))
    return selected


def _testing_employment(profile: CareerProfile) -> list[ExperienceEntry]:
    """Testing/QA employment by role title, ranked by substance then evidence."""
    testing = [
        entry
        for entry in profile.experience
        if entry.kind == "employment" and _is_testing_role(entry)
    ]
    testing.sort(
        key=lambda entry: (
            -_tenure_days(entry),
            -int(_has_automation_evidence(entry)),
            entry.start_date.isoformat(),
        )
    )
    return testing


def _select_projects(
    profile: CareerProfile,
    plan: CoverLetterPlan,
) -> list[PackProject]:
    by_id = {project.id: project for project in profile.projects}
    packed: list[PackProject] = []
    for item in plan.strongest_projects:
        project = by_id.get(item.project_id)
        if project is None:
            continue
        packed.append(_pack_project(project, item.business_outcome, item.fit_focus))
    return packed


def _pack_experience(entry: ExperienceEntry) -> PackExperience:
    relationship: Literal["commercial_employment", "independent_rd", "study"]
    if entry.kind == "independent_engineering":
        relationship = "independent_rd"
    elif entry.kind == "professional_development":
        relationship = "study"
    else:
        relationship = "commercial_employment"
    return PackExperience(
        id=entry.id,
        kind=entry.kind,
        organisation=entry.organisation,
        title=entry.title,
        relationship=relationship,
        chapter=_chapter_for(entry),
        start_date=entry.start_date.isoformat(),
        end_date=entry.end_date.isoformat() if entry.end_date else None,
        highlights=list(entry.highlights[:_MAX_HIGHLIGHTS]),
        technologies=list(entry.technologies),
    )


def _pack_project(
    project: Project,
    business_outcome: str | None,
    fit_focus: str | None,
) -> PackProject:
    narrative = project_narrative(
        project_id=project.id,
        project_name=project.name,
        profile_project=project,
        emphasis=project.summary,
        business_outcome=business_outcome,
        fit_focus=fit_focus,
    )
    outcomes = list(project.outcomes) or [narrative.outcome]
    return PackProject(
        id=project.id,
        name=project.name,
        purpose=project.summary.strip(),
        what_was_built=narrative.does,
        engineering=narrative.engineering,
        technologies=list(project.technologies),
        outcomes=outcomes,
        relationship="independent_portfolio",
    )


def _pack_contact(contact: ContactDetails | None) -> PackContact:
    if contact is None:
        return PackContact()
    payload = contact.model_dump(exclude_none=True)
    return PackContact.model_validate(payload)


def _career_trajectory(
    experience: list[PackExperience],
    approved_claims: list[str],
    identity_summary: str | None,
) -> CareerTrajectory:
    grouped: dict[ExperienceChapter, list[str]] = {}
    for item in experience:
        if item.chapter == "study":
            continue
        grouped.setdefault(item.chapter, []).append(item.id)
    chapters: list[TrajectoryChapter] = []
    order = 1
    for name in (
        "commercial_testing_automation",
        "commercial_data_engineering",
        "independent_ai_engineering",
    ):
        ids = grouped.get(name)  # type: ignore[arg-type]
        if not ids:
            continue
        chapters.append(TrajectoryChapter(order=order, name=name, experience_ids=ids))
        order += 1
    return CareerTrajectory(
        authorised_duration_claim=_authorised_duration_claim(
            approved_claims, identity_summary
        ),
        chapters=chapters,
    )


def _authorised_duration_claim(
    approved_claims: list[str],
    identity_summary: str | None,
) -> str | None:
    candidates = [text.strip() for text in (*approved_claims, identity_summary or "") if text]
    for text in candidates:
        lowered = text.casefold()
        if "across" not in lowered:
            continue
        if "year" not in lowered:
            continue
        sentence = text.split(".")[0].strip()
        return sentence or None
    return None


def _has_commercial_ai_employment(profile: CareerProfile) -> bool:
    for entry in profile.experience:
        if entry.kind != "employment":
            continue
        blob = f"{entry.title} {' '.join(entry.highlights)}".casefold()
        if "ai engineer" in blob or "artificial intelligence" in blob:
            return True
    return False


def _has_ml_expertise(profile: CareerProfile, allowed_tech: list[str]) -> bool:
    haystack = " ".join(allowed_tech).casefold()
    for skill in (*profile.skills.technical, *profile.skills.domain):
        haystack = f"{haystack} {skill.name.casefold()}"
    return any(label in haystack for label in _ML_LABELS)


def _chapter_for(entry: ExperienceEntry) -> ExperienceChapter:
    if entry.kind == "independent_engineering":
        return "independent_ai_engineering"
    if entry.kind == "professional_development":
        return "study"
    if _is_testing_role(entry):
        return "commercial_testing_automation"
    if _is_data_engineering_role(entry):
        return "commercial_data_engineering"
    return "other_commercial"


def _is_testing_role(entry: ExperienceEntry) -> bool:
    """True only when the employment title is a testing/QA role."""
    if entry.kind != "employment":
        return False
    title = entry.title.casefold()
    if _title_contains(title, _DATA_ENGINEER_TITLE_PHRASES):
        return False
    return _title_contains(title, _TESTING_TITLE_PHRASES)


def _is_data_engineering_role(entry: ExperienceEntry) -> bool:
    if entry.kind != "employment":
        return False
    return _title_contains(entry.title.casefold(), _DATA_ENGINEER_TITLE_PHRASES)


def _has_automation_evidence(entry: ExperienceEntry) -> bool:
    blob = f"{' '.join(entry.highlights)} {' '.join(entry.technologies)}".casefold()
    return any(hint in blob for hint in _AUTOMATION_EVIDENCE_HINTS)


def _looks_like_ai_study(entry: ExperienceEntry) -> bool:
    blob = f"{entry.title} {' '.join(entry.highlights)}".casefold()
    return any(hint in blob for hint in _AI_STUDY_HINTS)


def _title_contains(title: str, phrases: tuple[str, ...]) -> bool:
    return any(phrase in title for phrase in phrases)


def _tenure_days(entry: ExperienceEntry) -> int:
    end = entry.end_date or date.today()
    return max(0, (end - entry.start_date).days)


def _constraints(
    *,
    commercial_ai_employment: bool,
    candidate_has_ml_expertise: bool,
    contact: PackContact,
    trajectory: CareerTrajectory,
) -> list[str]:
    constraints = [
        "Use only facts in this evidence pack. Do not invent employment, "
        "technologies, metrics, qualifications, or project outcomes.",
        "Independent R&D / portfolio work is not commercial employment, "
        "consulting, or client delivery.",
        "Do not claim the candidate was employed as an AI Engineer unless "
        "commercial_ai_employment is true.",
        "Employer-mentioned technologies are job context, not candidate claims, "
        "unless they also appear in allowed_technologies.",
        "Explain what selected projects do (purpose, then what was built) before "
        "listing implementation technologies.",
        "Open by connecting one or more packed employer needs from role_context "
        "to packed candidate evidence. Do not open with generic relevance, "
        "background-fit, or enthusiasm.",
        "Close in one or two sentences by connecting packed evidence to "
        "contribution to this role. Do not repeat the opening. Do not use "
        "generic conversation-request filler or exaggerated enthusiasm.",
        "Write in Australian English.",
    ]
    if trajectory.chapters:
        names = ", then ".join(item.name.replace("_", " ") for item in trajectory.chapters)
        constraints.append(
            "Keep career chapters distinct and in this order: "
            f"{names}. Phrase them naturally; do not reorder or collapse them."
        )
        constraints.append(
            "Do not claim the career started in Data Engineering or at the "
            "Data Engineering employer. Commercial testing/automation, if packed, "
            "precedes Data Engineering."
        )
    if trajectory.authorised_duration_claim:
        constraints.append(
            "If mentioning overall experience length, use the authorised duration "
            f"claim as written: '{trajectory.authorised_duration_claim}'. "
            "Do not change its subject to Data Engineering, AI Engineering, or "
            "a single employer."
        )
        constraints.append(
            "Do not imply 10+ years of Data Engineering or 10+ years of AI Engineering."
        )
    if not commercial_ai_employment:
        constraints.append(
            "There is no commercial AI Engineering employment in the pack. "
            "Describe applied AI work as independent / portfolio engineering."
        )
    if not candidate_has_ml_expertise:
        constraints.append(
            "Do not claim machine learning, deep learning, TensorFlow, PyTorch, "
            "or ML expertise."
        )
    if any(
        item.name == "commercial_testing_automation" for item in trajectory.chapters
    ):
        constraints.append(
            "Where packed testing/automation employment exists, you may connect "
            "that background to current emphasis on testing, verification and "
            "reliability in AI systems — using only packed facts."
        )
    if contact.portfolio_url and contact.github_url:
        constraints.append(
            "Include a short paragraph pointing the recruiter to the Portfolio "
            "and GitHub already shown in the letter header as working examples "
            "and engineering evidence for the packed projects. Do not paste "
            "those URLs into the body. Do not invent other links. Do not claim "
            "commercial AI delivery, ML expertise, metrics, users, clients, "
            "deployments, or adoption."
        )
    else:
        constraints.append(
            "Do not mention Portfolio or GitHub URLs that are not in contact."
        )
    return constraints


def _unique(*groups: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for group in groups:
        for item in group:
            text = item.strip()
            key = text.casefold()
            if not text or key in seen:
                continue
            seen.add(key)
            ordered.append(text)
    return ordered
