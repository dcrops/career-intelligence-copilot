"""Deterministic PositioningPlan policies (trajectory and methodology).

These rules use structured JobAnalysis fields and CareerProfile title identity.
They do not score, and they do not special-case employers.
"""

from __future__ import annotations

from career_intelligence.document_positioning.catalogue import normalise_label
from career_intelligence.document_positioning.models import TrajectoryMode
from career_intelligence.job_analysis.models import JobAnalysis
from career_intelligence.profile.models import CareerProfile, ExperienceEntry

# Title identity only — aligned with cover_letter.evidence_pack, but this
# module must not import cover-letter production code.
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

# Whole-token employer signals that methodology would strengthen the argument.
# "quality" alone is omitted — it appears in unrelated product wording.
_METHODOLOGY_TOKENS = frozenset(
    {
        "evaluation",
        "monitoring",
        "orchestration",
        "governance",
        "compliance",
        "hitl",
        "reviewable",
        "traceable",
        "explainable",
        "reliability",
        "validation",
    }
)
_METHODOLOGY_PHRASES = (
    ("human", "in", "the", "loop"),
    ("risk", "management"),
)

_AI_BUILD_FAMILIES = frozenset(
    {"ai_engineering", "ai_solutions", "ml_engineering"}
)
_BRIDGE_FAMILIES = frozenset({"data_engineering", "software_engineering"})


def decide_trajectory(
    job: JobAnalysis,
    profile: CareerProfile,
) -> tuple[TrajectoryMode, str]:
    """Return trajectory_mode and a one-sentence rationale.

    Policy (no numeric thresholds):
    - ``ai_adjacent`` with testing + data-engineering + independent AI employment
      chapters → ``full_chapters`` (the career path is the hiring argument).
    - ``data_engineering`` / ``software_engineering`` with testing employment →
      ``bridge`` (testing packed only as reliability evidence).
    - Otherwise → ``ai_lead`` (do not pack weak testing rows as the lead story).

    Frozen eval jobs: E4 is ``ai_adjacent``; E1–E3 are ``ai_engineering``.
    ``bridge`` is defined for software/data-engineering families and is covered
    by a synthetic test rather than invented scores on the AI-engineer ads.
    """
    has_testing = any(_is_testing_role(entry) for entry in profile.experience)
    has_de = any(_is_data_engineering_role(entry) for entry in profile.experience)
    has_independent_ai = any(
        entry.kind == "independent_engineering" for entry in profile.experience
    )
    family = job.role_family.family

    if family == "ai_adjacent":
        if has_testing and has_de and has_independent_ai:
            return (
                "full_chapters",
                "Role family is AI-adjacent and the profile has testing, "
                "data-engineering, and independent AI chapters, so the career "
                "trajectory is the hiring argument.",
            )
        return (
            "ai_lead",
            "Role family is AI-adjacent but the profile is missing a testing, "
            "data-engineering, or independent AI chapter, so the plan leads "
            "with available AI evidence.",
        )

    if family in _BRIDGE_FAMILIES and has_testing:
        return (
            "bridge",
            f"Role family is {family} and the profile has testing employment, "
            "so testing is packed only as a reliability bridge rather than as "
            "the lead story.",
        )

    if family in _AI_BUILD_FAMILIES:
        return (
            "ai_lead",
            f"Role family is {family}, so positioning leads with AI evidence "
            "and does not use the QA→DE→AI chapter walk as the primary argument.",
        )

    return (
        "ai_lead",
        f"Role family is {family}; default trajectory is AI-lead.",
    )


def decide_include_methodology(
    job: JobAnalysis,
    profile: CareerProfile,
) -> tuple[bool, str]:
    """Include Master methodology when the job's structured needs invoke it."""
    if profile.engineering_methodology is None:
        return (
            False,
            "CareerProfile has no engineering_methodology section.",
        )
    if _job_signals_methodology(job):
        return (
            True,
            "Structured employer needs include evaluation, orchestration, "
            "governance, reliability, or equivalent methodology signals.",
        )
    return (
        False,
        "Structured employer needs do not invoke evaluation, orchestration, "
        "governance, or equivalent methodology signals.",
    )


def _job_signals_methodology(job: JobAnalysis) -> bool:
    blobs = [tech.name for tech in job.technologies]
    blobs.extend(item.description for item in job.responsibilities)
    blobs.extend(item.description for item in job.experience_requirements)
    return any(_text_signals_methodology(blob) for blob in blobs)


def _text_signals_methodology(text: str) -> bool:
    tokens = normalise_label(text).split()
    if any(token in _METHODOLOGY_TOKENS for token in tokens):
        return True
    for phrase in _METHODOLOGY_PHRASES:
        width = len(phrase)
        for index in range(len(tokens) - width + 1):
            if tuple(tokens[index : index + width]) == phrase:
                return True
    return False


def _is_testing_role(entry: ExperienceEntry) -> bool:
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


def _title_contains(title: str, phrases: tuple[str, ...]) -> bool:
    return any(phrase in title for phrase in phrases)
