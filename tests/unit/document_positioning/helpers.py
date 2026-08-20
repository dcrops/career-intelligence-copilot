"""Builders for document-positioning unit tests."""

from __future__ import annotations

from pathlib import Path

from career_intelligence.application_strategy.models import ApplicationStrategy
from career_intelligence.job_analysis.models import JobAnalysis
from career_intelligence.opportunity_assessment.models import OpportunityAssessment
from career_intelligence.profile.models import CareerProfile

from tests.unit.application_strategy.helpers import (
    assessment_payload,
    job_analysis_payload,
    portfolio_project_evidence,
)
from tests.unit.cv_generation.helpers import strategy_from_payload

REPO = Path(__file__).resolve().parents[3]


def tech(name: str, level: str = "required") -> dict[str, object]:
    return {
        "name": name,
        "level": level,
        "evidence": [{"excerpt": f"{name} required", "section": "requirements"}],
    }


def responsibility(description: str) -> dict[str, object]:
    return {
        "description": description,
        "evidence": [{"excerpt": description, "section": "responsibilities"}],
    }


def experience_requirement(description: str, level: str = "required") -> dict[str, object]:
    return {
        "description": description,
        "level": level,
        "evidence": [{"excerpt": description, "section": "requirements"}],
    }


def analysis_with(
    *,
    family: str = "ai_engineering",
    title: str = "AI Engineer",
    technologies: list[dict[str, object]] | None = None,
    responsibilities: list[dict[str, object]] | None = None,
    experience_requirements: list[dict[str, object]] | None = None,
) -> JobAnalysis:
    payload = job_analysis_payload(
        posting={
            "raw_text": f"{title}. Synthetic posting for positioning tests.",
            "title": title,
            "company": "Example Co",
        },
        role_family={
            "family": family,
            "evidence": [{"excerpt": title, "section": "title"}],
        },
        technologies=technologies or [tech("Python")],
        responsibilities=responsibilities
        or [responsibility("Build LLM applications")],
        experience_requirements=experience_requirements or [],
    )
    return JobAnalysis.model_validate(payload)


def specialist_job() -> JobAnalysis:
    return analysis_with(
        title="Specialist AI Engineer",
        technologies=[
            tech("RAG"),
            tech("AWS Bedrock"),
            tech("chatbots"),
            tech("Python"),
        ],
        responsibilities=[
            responsibility(
                "Implement retrieval-augmented generation, orchestration, "
                "and evaluation pipelines"
            )
        ],
        experience_requirements=[
            experience_requirement(
                "Deep experience building chatbots and conversational AI"
            )
        ],
    )


def adoption_job() -> JobAnalysis:
    return analysis_with(
        family="ai_adjacent",
        title="AI Adoption Specialist",
        technologies=[tech("AI tools"), tech("Copilot")],
        responsibilities=[
            responsibility(
                "Identify opportunities to improve efficiency, quality, "
                "and risk management"
            )
        ],
    )


def specialist_profile() -> CareerProfile:
    return CareerProfile.model_validate(
        {
            "schema_version": "1",
            "identity": {
                "full_name": "Test Candidate",
                "target_role": "AI Engineer",
                "summary": "Builds evidence-backed AI systems.",
            },
            "experience": [
                {
                    "id": "independent-ai",
                    "kind": "independent_engineering",
                    "organisation": "Independent",
                    "title": "AI Engineer - Independent Research & Development",
                    "start_date": "2024-01",
                    "end_date": None,
                    "highlights": ["Delivered retrieval-augmented generation systems."],
                    "technologies": ["Python", "Retrieval-Augmented Generation"],
                },
                {
                    "id": "nbn-de",
                    "kind": "employment",
                    "organisation": "Example Telco",
                    "title": "Data Engineer",
                    "start_date": "2020-01",
                    "end_date": "2023-01",
                    "highlights": ["Built reporting solutions using AWS services."],
                    "technologies": ["AWS", "Python"],
                },
                {
                    "id": "qa-role",
                    "kind": "employment",
                    "organisation": "Example QA",
                    "title": "Test Analyst",
                    "start_date": "2015-01",
                    "end_date": "2018-01",
                    "highlights": ["Automated regression testing."],
                    "technologies": ["Selenium WebDriver"],
                },
            ],
            "skills": {
                "technical": [
                    {
                        "name": "Python",
                        "evidence": "experience:independent-ai; experience:nbn-de",
                    },
                    {"name": "AWS", "evidence": "experience:nbn-de"},
                ],
                "domain": [
                    {
                        "name": "Retrieval-Augmented Generation",
                        "evidence": "project:rag-project",
                    }
                ],
                "soft": [],
            },
            "projects": [
                {
                    "id": "rag-project",
                    "name": "Document Intelligence RAG",
                    "summary": "Grounded answers over organisational documents.",
                    "technologies": ["Python", "Retrieval-Augmented Generation"],
                    "outcomes": ["Grounded responses with evaluation."],
                    "demonstrates": ["Retrieval-Augmented Generation"],
                }
            ],
            "certifications": [
                {
                    "id": "aws-dev",
                    "name": "AWS Certified Developer - Associate",
                    "issuer": "Amazon Web Services",
                    "status": "active",
                    "date_obtained": "2023-01",
                }
            ],
            "engineering_methodology": {
                "philosophy": "Traceable and reviewable AI systems.",
                "categories": [
                    {"name": "Quality", "practices": ["Evaluation", "Validation"]}
                ],
            },
            "goals": {"primary": "Secure an AI Engineering role."},
            "preferences": {"remote": "flexible"},
        }
    )


def poisoned_assessment(job: JobAnalysis) -> OpportunityAssessment:
    """Assessment whose key_alignments falsely claim Bedrock alignment."""
    payload = assessment_payload(job)
    payload["summary"] = {
        "summary": "Misleading free-text synthesis.",
        "key_alignments": [
            "Technical skills in AI engineering, particularly in AWS Bedrock and Python."
        ],
        "key_gaps": ["Chatbots"],
    }
    return OpportunityAssessment.model_validate(payload)


def golden_job_analysis(stem: str) -> JobAnalysis:
    path = REPO / "manual_validation" / "outputs" / f"{stem}.json"
    import json

    payload = json.loads(path.read_text(encoding="utf-8"))
    return JobAnalysis.model_validate(payload["job_analysis"])


def golden_output_path(stem: str) -> Path:
    return REPO / "manual_validation" / "outputs" / f"{stem}.json"


def csk_job_analysis_path() -> Path:
    return (
        REPO
        / "tests"
        / "fixtures"
        / "document_positioning"
        / "eval_jobs"
        / "02_csk_mixed_fit"
        / "job_analysis.json"
    )


def eval_strategy(
    job: JobAnalysis,
    profile: CareerProfile,
    source_path: Path | None = None,
) -> ApplicationStrategy:
    """Platinum inspection/eval strategy with real portfolio emphasis.

    E1/E3/E4 copy ``portfolio_emphasis`` from frozen golden outputs. E2's
    tracked freeze is job analysis only, so emphasis falls back to live
    CareerProfile projects. This is not ``cic package prepare``.
    """
    import json

    emphasis = None
    if source_path is not None and source_path.name != "job_analysis.json":
        payload = json.loads(source_path.read_text(encoding="utf-8"))
        raw = payload.get("application_strategy")
        if isinstance(raw, dict) and raw.get("portfolio_emphasis"):
            emphasis = raw["portfolio_emphasis"]
    if not emphasis:
        emphasis = [
            {
                "project_id": project.id,
                "source_rank": index,
                "summary": project.summary or project.name,
                "evidence": [portfolio_project_evidence(project.id)],
            }
            for index, project in enumerate(profile.projects, start=1)
        ]
    return strategy_from_payload(job_analysis=job, portfolio_emphasis=emphasis)


def live_profile() -> CareerProfile:
    from career_intelligence.profile import CareerProfileService

    return CareerProfileService.from_path(REPO / "data" / "career_profile.yaml").load()


def csk_job_analysis() -> JobAnalysis:
    path = (
        REPO
        / "tests"
        / "fixtures"
        / "document_positioning"
        / "eval_jobs"
        / "02_csk_mixed_fit"
        / "job_analysis.json"
    )
    import json

    return JobAnalysis.model_validate(json.loads(path.read_text(encoding="utf-8")))
