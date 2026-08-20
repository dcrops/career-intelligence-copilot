"""Render M2 PositioningPlan + TailoringPlan inspection for the four frozen jobs.

Does not generate CVs or cover letters. Does not call OpenAI. Does not wire
PositioningPlan into package prepare.
"""

from __future__ import annotations

import json
from pathlib import Path

from career_intelligence.application_strategy.models import ApplicationStrategy
from career_intelligence.cv_generation import (
    DeterministicTailoringPlanner,
    TailoringOptions,
    TailoringPlanService,
)
from career_intelligence.document_positioning import (
    SupportStatus,
    build_positioning_plan,
    render_positioning_plan,
)
from career_intelligence.job_analysis.models import JobAnalysis
from career_intelligence.profile import CareerProfileService

REPO = Path(__file__).resolve().parents[1]


def _strategy(job: JobAnalysis):
    payload = {
        "application_tier": "platinum",
        "pursuit_posture": "prioritise",
        "practical_value": "career_priority",
        "effort_level": "full",
        "summary": "Inspection-only strategy wrapper; not a production package.",
        "reasons": [
            {
                "kind": "alignment",
                "summary": "Inspection wrapper.",
                "importance": "material",
                "evidence": [
                    {
                        "origin": "job_analysis",
                        "job_evidence": {"source": "role_family", "name": job.role_family.family},
                    }
                ],
            }
        ],
        "risks_or_gaps": [
            {
                "summary": "Inspection wrapper.",
                "importance": "minor",
                "evidence": [
                    {"origin": "job_analysis", "job_evidence": {"source": "compensation"}}
                ],
            }
        ],
        "manual_checks": [
            {
                "summary": "Inspection wrapper.",
                "why_it_matters": "Not used for generation.",
                "could_change_recommendation": False,
                "evidence": [
                    {"origin": "job_analysis", "job_evidence": {"source": "compensation"}}
                ],
            }
        ],
        "next_actions": [
            {
                "kind": "consider_owner_review",
                "summary": "Inspection only.",
                "evidence": [
                    {
                        "origin": "job_analysis",
                        "job_evidence": {"source": "role_family", "name": job.role_family.family},
                    }
                ],
            }
        ],
        "portfolio_emphasis": [],
        "assumptions": ["Inspection wrapper."],
        "decision_blockers": [],
        "owner_review_required": True,
        "insufficient_information": False,
        "job_analysis": job,
    }
    return ApplicationStrategy.model_validate(payload)


def _tailoring(job: JobAnalysis, profile):
    return TailoringPlanService(DeterministicTailoringPlanner()).plan(
        _strategy(job),
        profile,
        options=TailoringOptions(owner_approved_to_tailor=True),
    )


_PLANNER_STATUS = {
    "supported": "DIRECT",
    "related": "RELATED",
    "unsupported": "UNSUPPORTED",
}

_POS_STATUS = {
    SupportStatus.SUPPORTED_DIRECT: "DIRECT",
    SupportStatus.SUPPORTED_RELATED: "RELATED",
    SupportStatus.UNSUPPORTED: "UNSUPPORTED",
}


def _job(path: Path) -> JobAnalysis:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if path.name == "job_analysis.json":
        return JobAnalysis.model_validate(payload)
    return JobAnalysis.model_validate(payload["job_analysis"])


def _render_tailoring(plan) -> list[str]:
    lines = [
        "### TailoringPlan technology classifications",
        "",
        "| Requested | Planner support | Identity | Promoted profile evidence | may_claim_requested |",
        "|---|---|---|---|---|",
    ]
    for item in plan.jd_priorities:
        if item.kind != "technology":
            continue
        lines.append(
            "| "
            + " | ".join(
                [
                    item.label,
                    _PLANNER_STATUS[item.candidate_support],
                    item.requested_capability_identity or "—",
                    item.related_profile_capability or "—",
                    str(item.may_claim_requested),
                ]
            )
            + " |"
        )
    promoted = ", ".join(item.skill_name for item in plan.skills_to_promote) or "none"
    lines.extend(["", f"**skills_to_promote:** {promoted}", ""])
    return lines


def main() -> None:
    profile = CareerProfileService.from_path(REPO / "data" / "career_profile.yaml").load()
    jobs = [
        (
            "E1 — Allura AI Engineer (control)",
            REPO / "manual_validation" / "outputs" / "001_strong_ai_engineer.json",
            "Python and REST APIs remain DIRECT. LLM is now DIRECT via CareerProfile "
            "skill `LLM application development` (not a RAG shortcut). "
            "Google Cloud / MLOps / DevOps stay honest gaps.",
        ),
        (
            "E2 — CSK mixed-fit specialist",
            REPO
            / "tests"
            / "fixtures"
            / "document_positioning"
            / "eval_jobs"
            / "02_csk_mixed_fit"
            / "job_analysis.json",
            "RAG DIRECT. AWS Bedrock RELATED via AWS (`may_claim_requested=False`). "
            "Chatbot/conversational AI remains UNSUPPORTED. Bedrock is not a "
            "promoted candidate skill.",
        ),
        (
            "E3 — Maincode AI Infrastructure Engineer",
            REPO
            / "manual_validation"
            / "outputs"
            / "012_maincode_ai_infrastructure_engineer.json",
            "GPU/Linux/HPC stay UNSUPPORTED. No infrastructure invention.",
        ),
        (
            "E4 — Repurpose AI Adoption Specialist",
            REPO
            / "manual_validation"
            / "outputs"
            / "008_repurpose_it_ai_adoption_specialist.json",
            "Copilot/Claude remain unclaimed unless evidenced. QA→DE→AI trajectory "
            "is unchanged (`full_chapters` on PositioningPlan).",
        ),
    ]
    parts = [
        "# Document Positioning M2 — Four-job capability inspection",
        "",
        "Inspection artefact only. Not production document generation. "
        "Not an M5 A/B evaluation. PositioningPlan is still **not** wired into "
        "`cic package prepare`.",
        "",
        "Shared candidate evidence: `data/career_profile.yaml`.",
        "",
        "TailoringPlan classifications use the same catalogue as PositioningPlan.",
        "",
    ]
    for title, path, why in jobs:
        job = _job(path)
        positioning = build_positioning_plan(job, profile)
        tailoring = _tailoring(job, profile)
        parts.append(render_positioning_plan(title, positioning))
        parts.extend(_render_tailoring(tailoring))
        parts.append("## Why this positioning differs")
        parts.append("")
        parts.append(why)
        parts.append("")
        disagreements: list[str] = []
        by_label = {
            item.label.casefold(): item
            for item in tailoring.jd_priorities
            if item.kind == "technology"
        }
        for need in positioning.employer_needs:
            if need.need.kind != "technology":
                continue
            priority = by_label.get(need.need.label.casefold())
            if priority is None:
                disagreements.append(f"{need.need.label}: missing from TailoringPlan")
                continue
            pos = _POS_STATUS[need.classification.status]
            plan = _PLANNER_STATUS[priority.candidate_support]
            if pos != plan:
                disagreements.append(f"{need.need.label}: PositioningPlan {pos} vs TailoringPlan {plan}")
        parts.append("### Shared-technology agreement")
        parts.append("")
        if disagreements:
            parts.append("Disagreements:")
            parts.extend(f"- {item}" for item in disagreements)
        else:
            parts.append(
                "PositioningPlan and TailoringPlan agree on every shared JobAnalysis technology."
            )
        parts.append("")
        parts.append("---")
        parts.append("")
    parts.extend(
        [
            "# Cross-job contrast",
            "",
            "- E1 vs M1: LLM is now DIRECT because the profile skill "
            "`LLM application development` resolves to identity `llm`. RAG is a "
            "different identity and is not used as a shortcut.",
            "- E2: Bedrock stays RELATED; chatbot stays a gap. Correct gaps are "
            "success, not extra green matches.",
            "- E3: infrastructure asks remain unsupported.",
            "- E4: trajectory_mode remains `full_chapters`.",
            "",
        ]
    )
    out = REPO / "docs" / "eval" / "document_positioning_m2_inspection.md"
    out.write_text("\n".join(parts).rstrip() + "\n", encoding="utf-8")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
