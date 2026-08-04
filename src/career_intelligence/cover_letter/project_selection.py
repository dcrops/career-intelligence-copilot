"""Evidence-based portfolio project selection for FR-007 cover letters.

Ranks Career Profile projects against JobAnalysis / ApplicationStrategy signals
so letters highlight work that strengthens the application, not merely popular
projects.
"""

from __future__ import annotations

from dataclasses import dataclass

from career_intelligence.application_strategy.models import ApplicationStrategy
from career_intelligence.profile.models import CareerProfile, Project

# Low-signal tokens appear in almost every JD; do not let them dominate ranking.
_LOW_SIGNAL_TAGS = frozenset(
    {
        "python",
        "production",
        "api",
        "fastapi",
        "automation",
        "pipeline",
        "workflow",
        "business",
        "monitoring",
        "openai",
        "git",
        "docker",
    }
)

# Theme tags are grounded in each project's engineering capabilities.
_PROJECT_CATALOG: dict[str, dict[str, object]] = {
    "career-intelligence-copilot": {
        "tags": frozenset(
            {
                "llm",
                "agent",
                "agentic",
                "evaluation",
                "validation",
                "strategy",
                "assessment",
                "explainable",
                "human-in-the-loop",
                "pydantic",
                "orchestration",
                "architecture",
            }
        ),
        "concerns": frozenset({"llm_agents", "trust_explainability", "production"}),
        "outcome": (
            "high-stakes recommendations stay evidence-backed and reviewable"
        ),
        "fit_focus": (
            "LLM orchestration with deterministic decision support, structured "
            "evaluation and human approval workflows"
        ),
        "maturity": 3,
    },
    "governance-document-rag": {
        "tags": frozenset(
            {
                "rag",
                "document",
                "documents",
                "governance",
                "llm",
                "retrieval",
                "embedding",
                "grounding",
                "policy",
                "knowledge",
                "explainable",
                "evaluation",
                "compliance",
                "langchain",
                "chromadb",
            }
        ),
        "concerns": frozenset({"documents", "trust_explainability", "llm_agents"}),
        "outcome": (
            "document answers remain verifiable, which improves governance trust"
        ),
        "fit_focus": (
            "retrieval orchestration, grounding validation and evaluation "
            "controls around LLM responses"
        ),
        "maturity": 3,
    },
    "operational-intelligence-copilot": {
        "tags": frozenset(
            {
                "operational",
                "operations",
                "analytics",
                "anomaly",
                "insight",
                "insights",
                "llm",
                "executive",
                "decision",
                "reporting",
                "explainable",
                "fintech",
            }
        ),
        "concerns": frozenset({"ops_insights", "trust_explainability", "llm_agents"}),
        "outcome": "decision makers get faster insights they can actually check",
        "fit_focus": (
            "analytics workflows, anomaly detection and evidence-backed LLM "
            "reasoning with clear decision trails"
        ),
        "maturity": 3,
    },
    "payroll-diagnostics-engine": {
        "tags": frozenset(
            {
                "payroll",
                "rules",
                "rule",
                "deterministic",
                "compliance",
                "anomaly",
                "validation",
                "reporting",
                "diagnostics",
                "explainable",
            }
        ),
        "concerns": frozenset({"deterministic_rules", "trust_explainability"}),
        "outcome": "compliance issues are easier to investigate and act on",
        "fit_focus": (
            "deterministic rule engines with explainable diagnostics and "
            "automated validation"
        ),
        "maturity": 2,
    },
    "public-holiday-entitlements": {
        "tags": frozenset(
            {
                "holiday",
                "entitlement",
                "entitlements",
                "rules",
                "rule",
                "deterministic",
                "compliance",
                "hr",
                "payroll",
                "geospatial",
                "location",
            }
        ),
        "concerns": frozenset({"deterministic_rules"}),
        "outcome": "compliance decisions stay consistent and easier to defend",
        "fit_focus": (
            "deterministic business rules, geospatial logic and API-backed "
            "compliance reporting"
        ),
        "maturity": 2,
    },
}

# Hiring-manager concern clusters: what would create confidence for this employer?
_CONCERN_CLUSTERS: dict[str, frozenset[str]] = {
    "trust_explainability": frozenset(
        {
            "explainable",
            "grounding",
            "evaluation",
            "validation",
            "human-in-the-loop",
            "trusted",
            "transparency",
            "review",
        }
    ),
    "production": frozenset(
        {
            "production",
            "deploy",
            "deployment",
            "fastapi",
            "docker",
            "monitoring",
            "pipeline",
            "operate",
            "operating",
            "infrastructure",
            "scalable",
        }
    ),
    "deterministic_rules": frozenset(
        {
            "deterministic",
            "rules",
            "rule",
            "compliance",
            "payroll",
            "entitlement",
            "governance",
        }
    ),
    "llm_agents": frozenset(
        {
            "llm",
            "agent",
            "agentic",
            "rag",
            "orchestration",
            "openai",
            "langchain",
            "prompt",
        }
    ),
    "documents": frozenset(
        {
            "document",
            "documents",
            "rag",
            "retrieval",
            "knowledge",
            "policy",
            "governance",
        }
    ),
    "ops_insights": frozenset(
        {
            "operational",
            "operations",
            "analytics",
            "anomaly",
            "insight",
            "insights",
            "decision",
            "fintech",
        }
    ),
}


@dataclass(frozen=True)
class RankedProject:
    project: Project
    score: int
    selection_reason: str
    business_outcome: str
    fit_focus: str
    matched_tags: tuple[str, ...]


def select_projects_for_letter(
    profile: CareerProfile,
    strategy: ApplicationStrategy,
    *,
    max_projects: int = 3,
) -> list[RankedProject]:
    """Select projects a hiring manager would most want to discuss."""
    jd_tokens = _jd_requirement_tokens(strategy)
    active_concerns = _active_concerns(jd_tokens)
    emphasis_boost = {
        item.project_id: max(0, 10 - (index * 3))
        for index, item in enumerate(strategy.portfolio_emphasis[:5])
    }

    ranked: list[RankedProject] = []
    role_family = strategy.job_analysis.role_family.family
    ai_family = role_family in {"ai_engineering", "ai_adjacent"}
    ai_capability_tags = frozenset(
        {
            "llm",
            "rag",
            "retrieval",
            "orchestration",
            "agent",
            "agentic",
            "architecture",
            "evaluation",
            "embedding",
            "langchain",
            "openai",
        }
    )
    for project in profile.projects:
        catalog = _PROJECT_CATALOG.get(project.id)
        tags = set(catalog["tags"]) if catalog else _tags_from_project(project)
        matched = sorted(tags & jd_tokens)
        score = 0
        for tag in matched:
            score += 1 if tag in _LOW_SIGNAL_TAGS else 4
        score += emphasis_boost.get(project.id, 0)

        project_tech = {tech.casefold() for tech in project.technologies}
        for tech in project_tech & jd_tokens:
            score += 1 if tech in _LOW_SIGNAL_TAGS else 2

        # Prefer projects that answer employer concerns, not keyword frequency alone.
        if catalog is not None:
            project_concerns = set(catalog.get("concerns", frozenset()))  # type: ignore[arg-type]
            concern_hits = project_concerns & active_concerns
            score += len(concern_hits) * 5
            score += int(catalog.get("maturity", 1))  # type: ignore[arg-type]

        if ai_family:
            ai_hits = tags & ai_capability_tags
            score += len(ai_hits) * 3
            # Generic API/REST overlap alone should not outrank AI systems work.
            low_only = set(matched) <= (
                _LOW_SIGNAL_TAGS | {"rest", "rest apis", "rest api"}
            )
            if not ai_hits and low_only and matched:
                score = max(0, score - 5)

        if catalog is None:
            outcome = (
                project.outcomes[0]
                if project.outcomes
                else "clearer, more reviewable engineering outcomes"
            )
            fit_focus = "production-minded AI Engineering delivery"
            reason = (
                f"Selected because it addresses this role on {', '.join(matched[:4])}."
                if matched
                else "Selected as available portfolio evidence for this role."
            )
        else:
            outcome = str(catalog["outcome"])
            fit_focus = str(catalog["fit_focus"])
            concern_hits = set(catalog.get("concerns", frozenset())) & active_concerns  # type: ignore[arg-type]
            if concern_hits:
                reason = (
                    "Selected because it answers employer priorities around "
                    f"{', '.join(sorted(concern_hits)[:3])}."
                )
            elif matched:
                reason = (
                    "Selected for engineering overlap with this role on "
                    f"{', '.join(matched[:4])}."
                )
            elif project.id in emphasis_boost:
                reason = (
                    "Selected from ApplicationStrategy portfolio emphasis for "
                    "this opportunity."
                )
            else:
                reason = "Selected as supporting portfolio evidence for this role."

        ranked.append(
            RankedProject(
                project=project,
                score=score,
                selection_reason=reason,
                business_outcome=outcome,
                fit_focus=fit_focus,
                matched_tags=tuple(matched[:6]),
            )
        )

    ranked.sort(key=lambda item: (-item.score, item.project.name.casefold()))
    positive = [item for item in ranked if item.score > 0]
    pool = positive or ranked
    selected = list(pool[:max_projects])

    if len(selected) >= 3 and selected[2].score < max(4, int(selected[1].score * 0.55)):
        selected = selected[:2]
    if len(selected) >= 2:
        if len(selected) == 3 and selected[2].score >= max(6, selected[1].score):
            return selected[:3]
        return selected[:2]
    return selected[:1]


def _active_concerns(jd_tokens: set[str]) -> set[str]:
    active: set[str] = set()
    for name, signals in _CONCERN_CLUSTERS.items():
        if signals & jd_tokens:
            active.add(name)
    return active


def _jd_requirement_tokens(strategy: ApplicationStrategy) -> set[str]:
    job = strategy.job_analysis
    chunks: list[str] = []
    if job.posting.title:
        chunks.append(job.posting.title)
    if job.posting.raw_text:
        chunks.append(job.posting.raw_text[:2500])
    if job.role_family and job.role_family.evidence:
        chunks.append(job.role_family.evidence[0].excerpt)
    for tech in job.technologies:
        chunks.append(tech.name)
    for responsibility in job.responsibilities:
        chunks.append(responsibility.description)
    # Do not inject portfolio_emphasis project ids into the JD token set.
    # That creates circular reinforcement. Emphasis is applied via score boost only.

    text = " ".join(chunks).casefold()
    tokens: set[str] = set()
    phrases = (
        "human in the loop",
        "human-in-the-loop",
        "public holiday",
        "document intelligence",
        "operational intelligence",
        "business rules",
        "agentic workflow",
        "agentic workflows",
        "deterministic",
        "fintech",
    )
    for phrase in phrases:
        if phrase in text:
            tokens.add(phrase.replace(" ", "-") if " " in phrase else phrase)
            tokens.update(phrase.replace("-", " ").split())

    catalog_tags: set[str] = set()
    for entry in _PROJECT_CATALOG.values():
        catalog_tags.update(entry["tags"])  # type: ignore[arg-type]
    for signals in _CONCERN_CLUSTERS.values():
        catalog_tags.update(signals)

    for tag in catalog_tags:
        if tag in text:
            tokens.add(tag)
    return tokens


def _tags_from_project(project: Project) -> set[str]:
    parts = [
        project.name,
        project.summary,
        " ".join(project.technologies),
        " ".join(project.demonstrates),
        " ".join(project.outcomes),
    ]
    text = " ".join(parts).casefold()
    tokens = {tech.casefold() for tech in project.technologies}
    for word in text.replace("/", " ").replace("-", " ").split():
        cleaned = "".join(ch for ch in word if ch.isalnum())
        if len(cleaned) >= 4:
            tokens.add(cleaned)
    return tokens
