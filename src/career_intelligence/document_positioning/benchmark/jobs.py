"""Frozen E1–E4 evaluation job identities (M0 freeze; M5 must not substitute)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from career_intelligence.application_strategy.models import ApplicationStrategy
from career_intelligence.job_analysis.models import JobAnalysis
from career_intelligence.profile.models import CareerProfile

REPO = Path(__file__).resolve().parents[4]

AnalysisKind = Literal["golden_output", "job_analysis_json"]


class FrozenEvalJob(BaseModel):
    """One frozen M5 evaluation job. Identities are not editable during M5."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    job_id: Literal["E1", "E2", "E3", "E4"]
    name: str
    why: str
    advertisement_path: Path
    analysis_path: Path
    analysis_kind: AnalysisKind
    opportunity_id: str | None = None


FROZEN_EVAL_JOBS: tuple[FrozenEvalJob, ...] = (
    FrozenEvalJob(
        job_id="E1",
        name="Allura AI Engineer",
        why="G1 Allura; strong applied AI Engineer control",
        advertisement_path=REPO / "manual_validation" / "jobs" / "001_strong_ai_engineer.txt",
        analysis_path=REPO / "manual_validation" / "outputs" / "001_strong_ai_engineer.json",
        analysis_kind="golden_output",
    ),
    FrozenEvalJob(
        job_id="E2",
        name="CSK specialist",
        why="Mixed-fit specialist; related AWS + RAG; chatbot gap",
        advertisement_path=(
            REPO
            / "tests"
            / "fixtures"
            / "document_positioning"
            / "eval_jobs"
            / "02_csk_mixed_fit"
            / "job.txt"
        ),
        analysis_path=(
            REPO
            / "tests"
            / "fixtures"
            / "document_positioning"
            / "eval_jobs"
            / "02_csk_mixed_fit"
            / "job_analysis.json"
        ),
        analysis_kind="job_analysis_json",
        opportunity_id="opp_01M0E6GQ9XQH9DK9N5T0MS67N0",
    ),
    FrozenEvalJob(
        job_id="E3",
        name="Maincode AI Infrastructure",
        why="Honest stretch control; no invented GPU/Linux/HPC employment",
        advertisement_path=(
            REPO / "manual_validation" / "jobs" / "012_maincode_ai_infrastructure_engineer.txt"
        ),
        analysis_path=(
            REPO
            / "manual_validation"
            / "outputs"
            / "012_maincode_ai_infrastructure_engineer.json"
        ),
        analysis_kind="golden_output",
    ),
    FrozenEvalJob(
        job_id="E4",
        name="Repurpose AI Adoption Specialist",
        why="Adoption/enablement; QA → DE → AI trajectory may be the argument",
        advertisement_path=(
            REPO / "manual_validation" / "jobs" / "008_repurpose_it_ai_adoption_specialist.txt"
        ),
        analysis_path=(
            REPO / "manual_validation" / "outputs" / "008_repurpose_it_ai_adoption_specialist.json"
        ),
        analysis_kind="golden_output",
    ),
)

CAREER_PROFILE_PATH = REPO / "data" / "career_profile.yaml"
MASTER_CV_PATH = REPO / "career-documents" / "cv" / "master_ai_engineer_cv.md"


def job_by_id(job_id: str) -> FrozenEvalJob:
    for job in FROZEN_EVAL_JOBS:
        if job.job_id == job_id:
            return job
    raise KeyError(f"Unknown frozen eval job: {job_id}")


def load_job_analysis(job: FrozenEvalJob) -> JobAnalysis:
    payload = json.loads(job.analysis_path.read_text(encoding="utf-8"))
    if job.analysis_kind == "job_analysis_json":
        return JobAnalysis.model_validate(payload)
    return JobAnalysis.model_validate(payload["job_analysis"])


def load_advertisement(job: FrozenEvalJob) -> str:
    return job.advertisement_path.read_text(encoding="utf-8")


def eval_strategy(
    job_analysis: JobAnalysis,
    profile: CareerProfile,
    source_path: Path | None = None,
) -> ApplicationStrategy:
    """Platinum eval wrapper. Not ``cic package prepare``.

    E1/E3/E4 copy frozen golden ``portfolio_emphasis``. E2's tracked freeze is
    job analysis only, so emphasis falls back to live CareerProfile order.
    """
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
                "evidence": [
                    {
                        "origin": "portfolio_match",
                        "portfolio_project_id": project.id,
                    }
                ],
            }
            for index, project in enumerate(profile.projects, start=1)
        ]
    return ApplicationStrategy.model_validate(
        {
            "application_tier": "platinum",
            "pursuit_posture": "prioritise",
            "practical_value": "career_priority",
            "effort_level": "full",
            "summary": "M5 evaluation strategy wrapper; not a production package.",
            "reasons": [
                {
                    "kind": "alignment",
                    "summary": "Evaluation wrapper.",
                    "importance": "material",
                    "evidence": [
                        {
                            "origin": "job_analysis",
                            "job_evidence": {
                                "source": "role_family",
                                "name": job_analysis.role_family.family,
                            },
                        }
                    ],
                }
            ],
            "risks_or_gaps": [
                {
                    "summary": "Evaluation wrapper.",
                    "importance": "minor",
                    "evidence": [
                        {
                            "origin": "job_analysis",
                            "job_evidence": {"source": "compensation"},
                        }
                    ],
                }
            ],
            "manual_checks": [
                {
                    "summary": "Evaluation wrapper.",
                    "why_it_matters": "Not used for production generation.",
                    "could_change_recommendation": False,
                    "evidence": [
                        {
                            "origin": "job_analysis",
                            "job_evidence": {"source": "compensation"},
                        }
                    ],
                }
            ],
            "next_actions": [
                {
                    "kind": "consider_owner_review",
                    "summary": "Evaluation only.",
                    "evidence": [
                        {
                            "origin": "job_analysis",
                            "job_evidence": {
                                "source": "role_family",
                                "name": job_analysis.role_family.family,
                            },
                        }
                    ],
                }
            ],
            "portfolio_emphasis": emphasis,
            "assumptions": ["M5 evaluation wrapper."],
            "decision_blockers": [],
            "owner_review_required": True,
            "insufficient_information": False,
            "job_analysis": job_analysis,
        }
    )
