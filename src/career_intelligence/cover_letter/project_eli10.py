"""Product-style project narratives for cover letter composition.

Emphasise engineering capabilities first. Domain context is secondary and only
used to make the product understandable.
"""

from __future__ import annotations

from dataclasses import dataclass

from career_intelligence.profile.models import Project


@dataclass(frozen=True)
class ProjectNarrative:
    """Plain-English product framing for one portfolio project."""

    does: str
    engineering: str
    outcome: str


# Engineering-first narratives grounded in Career Profile project intent.
_NARRATIVES: dict[str, ProjectNarrative] = {
    "career-intelligence-copilot": ProjectNarrative(
        does=(
            "orchestrates LLMs with deterministic decision support to analyse "
            "structured inputs, rank options with evidence, and draft reviewable "
            "outputs under human approval"
        ),
        engineering=(
            "LLM orchestration, deterministic decision support, structured "
            "evaluation, explainable recommendations and human-in-the-loop "
            "release workflows"
        ),
        outcome=(
            "high-stakes recommendations stay evidence-backed and reviewable "
            "instead of opaque model answers"
        ),
    ),
    "governance-document-rag": ProjectNarrative(
        does=(
            "lets teams ask questions across large document collections and "
            "returns answers tied back to the original source material"
        ),
        engineering=(
            "retrieval orchestration, grounding checks, evaluation harnesses "
            "and explainability controls around LLM responses"
        ),
        outcome=(
            "organisations get trusted document answers they can verify, which "
            "improves governance and reduces blind trust in AI output"
        ),
    ),
    "operational-intelligence-copilot": ProjectNarrative(
        does=(
            "turns operational data into plain-English questions and "
            "explainable insights for decision makers"
        ),
        engineering=(
            "intent routing, analytics workflows, anomaly detection and "
            "evidence-backed LLM reasoning with clear decision trails"
        ),
        outcome=(
            "managers can spot trends, risks and opportunities faster with "
            "insights they can check"
        ),
    ),
    "payroll-diagnostics-engine": ProjectNarrative(
        does=(
            "checks payroll data against deterministic business rules and "
            "flags anomalies with explainable findings"
        ),
        engineering=(
            "rule engines, automated validation, explainable diagnostics and "
            "executive-ready reporting"
        ),
        outcome=(
            "teams spend less time on manual investigation and can act on "
            "compliance issues with more confidence"
        ),
    ),
    "public-holiday-entitlements": ProjectNarrative(
        does=(
            "calculates public-holiday entitlements from location and rules "
            "so HR and payroll teams get consistent results"
        ),
        engineering=(
            "deterministic business rules, geospatial logic, API integration "
            "and compliance-oriented reporting"
        ),
        outcome=(
            "compliance decisions stay consistent and are easier to defend"
        ),
    ),
}


def project_narrative(
    *,
    project_id: str,
    project_name: str,
    profile_project: Project | None = None,
    emphasis: str | None = None,
    business_outcome: str | None = None,
    fit_focus: str | None = None,
) -> ProjectNarrative:
    """Return engineering-first product framing for a project."""
    known = _NARRATIVES.get(project_id)
    if known is not None:
        return known

    does = _fallback_does(profile_project, emphasis, project_name)
    engineering = (fit_focus or "production-minded AI Engineering delivery").strip()
    outcome = (
        business_outcome
        or "delivers clearer, more reviewable engineering outcomes"
    ).strip()
    return ProjectNarrative(does=does, engineering=engineering, outcome=outcome)


def eli10_project_clause(
    *,
    project_id: str,
    project_name: str,
    profile_project: Project | None = None,
    emphasis: str | None = None,
) -> str:
    """Backwards-compatible mid-sentence clause for what the product does."""
    narrative = project_narrative(
        project_id=project_id,
        project_name=project_name,
        profile_project=profile_project,
        emphasis=emphasis,
    )
    return narrative.does.lstrip()


def _fallback_does(
    profile_project: Project | None,
    emphasis: str | None,
    project_name: str,
) -> str:
    if profile_project is not None:
        rewritten = _first_sentence(profile_project.summary)
        if rewritten:
            return rewritten
    if emphasis:
        rewritten = _first_sentence(emphasis)
        if rewritten:
            return rewritten
    return (
        f"is a production-style AI Engineering project ({project_name}) built "
        "to solve a concrete operational problem with reviewable outputs"
    )


def _first_sentence(summary: str) -> str | None:
    text = " ".join(summary.split()).strip().rstrip(".")
    if not text:
        return None
    for sep in (". ", "; "):
        if sep in text:
            text = text.split(sep, 1)[0].strip()
            break
    folded = text.casefold()
    if folded.startswith("demonstrates ") and " capability" in folded:
        remainder = text.split(".", 1)
        if len(remainder) > 1 and remainder[1].strip():
            text = remainder[1].strip().rstrip(".")
    if text and text[0].isupper():
        text = text[0].lower() + text[1:]
    for prefix in (
        "demonstrates operational intelligence capability for ",
        "demonstrates ",
        "helps an ai engineering job seeker ",
        "enables an ai engineering job seeker ",
    ):
        if text.casefold().startswith(prefix):
            text = text[len(prefix) :]
            break
    if len(text) > 180:
        text = text[:177].rsplit(" ", 1)[0].rstrip(",;:")
    if not text:
        return None
    if not text.casefold().startswith(("is ", "lets ", "turns ", "checks ", "calculates ")):
        return f"is software that {text}"
    return text
