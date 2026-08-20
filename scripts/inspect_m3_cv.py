"""Render M3 bounded CV positioning inspection for the four frozen jobs.

Uses the fixture composer (no OpenAI). Does not write live application packages.
Does not wire PositioningPlan into cic package prepare.
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
from career_intelligence.cv_generation.master_adapt import (
    DEFAULT_MASTER_CV_PATH,
    extract_h2_section,
    extract_master_summary,
    load_master_cv_markdown,
)
from career_intelligence.document_positioning import (
    BoundedCvPositioningService,
    FixtureCvPositioningComposer,
    SupportStatus,
)
from career_intelligence.job_analysis.models import JobAnalysis
from career_intelligence.profile import CareerProfileService
from career_intelligence.profile.models import CareerProfile

REPO = Path(__file__).resolve().parents[1]


def _job(path: Path) -> JobAnalysis:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if path.name == "job_analysis.json":
        return JobAnalysis.model_validate(payload)
    return JobAnalysis.model_validate(payload["job_analysis"])


def _strategy(job: JobAnalysis, profile: CareerProfile, source: Path) -> ApplicationStrategy:
    payload = json.loads(source.read_text(encoding="utf-8"))
    emphasis = None
    if source.name != "job_analysis.json":
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
            "summary": "Inspection-only strategy wrapper; not a production package.",
            "reasons": [
                {
                    "kind": "alignment",
                    "summary": "Inspection wrapper.",
                    "importance": "material",
                    "evidence": [
                        {
                            "origin": "job_analysis",
                            "job_evidence": {
                                "source": "role_family",
                                "name": job.role_family.family,
                            },
                        }
                    ],
                }
            ],
            "risks_or_gaps": [
                {
                    "summary": "Inspection wrapper.",
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
                    "summary": "Inspection wrapper.",
                    "why_it_matters": "Not used for generation.",
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
                    "summary": "Inspection only.",
                    "evidence": [
                        {
                            "origin": "job_analysis",
                            "job_evidence": {
                                "source": "role_family",
                                "name": job.role_family.family,
                            },
                        }
                    ],
                }
            ],
            "portfolio_emphasis": emphasis,
            "assumptions": ["Inspection wrapper."],
            "decision_blockers": [],
            "owner_review_required": True,
            "insufficient_information": False,
            "job_analysis": job,
        }
    )


def _status_line(pack) -> list[str]:
    lines = ["### Classifications used", ""]
    for item in pack.employer_needs:
        status = {
            SupportStatus.SUPPORTED_DIRECT: "DIRECT",
            SupportStatus.SUPPORTED_RELATED: "RELATED",
            SupportStatus.UNSUPPORTED: "UNSUPPORTED",
        }[item.status]
        extra = ""
        if item.status is SupportStatus.SUPPORTED_RELATED:
            extra = f" (promote {item.promotable_profile_label}; may_claim_requested=False)"
        lines.append(f"- **{item.label}** → {status}{extra}")
    return lines


def main() -> None:
    profile = CareerProfileService.from_path(REPO / "data" / "career_profile.yaml").load()
    master = load_master_cv_markdown(DEFAULT_MASTER_CV_PATH)
    master_summary = extract_master_summary(master) or ""
    service = BoundedCvPositioningService(FixtureCvPositioningComposer())
    jobs = [
        (
            "E1 — Allura AI Engineer",
            REPO / "manual_validation" / "outputs" / "001_strong_ai_engineer.json",
            "AI-lead. Python/REST/LLM DIRECT. GCP/MLOps/DevOps remain gaps. Methodology on.",
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
            "RAG DIRECT. AWS RELATED for Bedrock; Bedrock not claimed. Chatbot gap. Methodology on.",
        ),
        (
            "E3 — Maincode AI Infrastructure",
            REPO
            / "manual_validation"
            / "outputs"
            / "012_maincode_ai_infrastructure_engineer.json",
            "GPU/Linux/HPC stay gaps. Methodology off. Watch for over-positioning.",
        ),
        (
            "E4 — Repurpose AI Adoption Specialist",
            REPO
            / "manual_validation"
            / "outputs"
            / "008_repurpose_it_ai_adoption_specialist.json",
            "full_chapters trajectory. Copilot/Claude unclaimed. Methodology on.",
        ),
    ]
    parts = [
        "# Document Positioning M3 — Four-job CV positioning inspection",
        "",
        "Offline inspection with `FixtureCvPositioningComposer`. Not live OpenAI. "
        "Not production `cic package prepare`. Not an M5 A/B evaluation. "
        "CSK live application package was not regenerated.",
        "",
        "Shared candidate evidence: `data/career_profile.yaml` + "
        "`career-documents/cv/master_ai_engineer_cv.md`.",
        "",
        "Project selection uses frozen golden `application_strategy.portfolio_emphasis` "
        "for E1/E3/E4. E2's tracked freeze is job analysis only, so emphasis falls "
        "back to live CareerProfile projects. Empty-emphasis wrappers were not used.",
        "",
        "## Original Master summary",
        "",
        master_summary,
        "",
        "---",
        "",
    ]
    for title, path, why in jobs:
        job = _job(path)
        tailoring = TailoringPlanService(DeterministicTailoringPlanner()).plan(
            _strategy(job, profile, path),
            profile,
            options=TailoringOptions(owner_approved_to_tailor=True),
        )
        result = service.compose(job, profile, tailoring, master)
        pack = result.pack
        parts.append(f"# {title}")
        parts.append("")
        parts.append(why)
        parts.append("")
        parts.append("## Positioned summary")
        parts.append("")
        parts.append(result.extraction.summary)
        parts.append("")
        parts.append("## Selected highlights")
        parts.append("")
        for item in pack.selected_highlights:
            parts.append(f"- {item}")
        parts.append("")
        parts.append("## Selected projects")
        parts.append("")
        for project in pack.selected_projects:
            parts.append(f"- {project.name} (`{project.project_id}`)")
        if result.extraction.project_relevance:
            parts.append("")
            parts.append("## Project relevance lines")
            parts.append("")
            for item in result.extraction.project_relevance:
                parts.append(f"- **{item.project_name}:** {item.line}")
        else:
            parts.append("")
            parts.append("## Project relevance lines")
            parts.append("")
            parts.append("- None generated for this job.")
        parts.append("")
        parts.append("## Methodology")
        parts.append("")
        parts.append(f"- **include_methodology:** `{pack.include_methodology}`")
        parts.append(f"- {pack.include_methodology_rationale}")
        present = extract_h2_section(result.markdown, "ai engineering methodology")
        parts.append(f"- Section present in Markdown: `{present is not None}`")
        parts.append("")
        parts.extend(_status_line(pack))
        parts.append("")
        parts.append("## Evidence refs used")
        parts.append("")
        for item in pack.candidate_evidence:
            parts.append(f"- `{item.ref}` ({item.source})")
        parts.append("")
        parts.append("## Validation")
        parts.append("")
        parts.append("Composer output passed M3 deterministic validators (fail-closed).")
        parts.append("FR-014 was **not** run; this is not package Truth PASS.")
        parts.append("")
        parts.append("---")
        parts.append("")
    parts.extend(
        [
            "# Quality notes (fixture inspection, not M5)",
            "",
            "- The fixture writer is pack-faithful and explicit (`Authorised capabilities "
            "include …`). That is useful for validating policy and commercially weak. "
            "Live OpenAI composition exists as `OpenAICvPositioningComposer` but is "
            "**not wired** into package prepare in M3. Do not treat fixture wording as "
            "M5 recruiter preference.",
            "- Fixture project relevance currently collapses to `demonstrates Python "
            "delivery…` even on RAG-heavy jobs. Policy-safe, repetitive, and "
            "under-positioned. A live writer must use packed project technologies "
            "without inventing employer tools.",
            "- Highlight selection currently reorders existing Master bullets rather than "
            "inventing achievements. Across AI-family jobs the same four Master bullets "
            "often remain; that is bounded, not richly job-specific.",
            "- E1 does not invent GCP/MLOps/DevOps. LLM is positioned from "
            "`LLM application development`, not as a RAG shortcut. ADF appears as "
            "RELATED evidence for data pipelines; that is catalogue-correct, not a GCP claim.",
            "- E2 names AWS as related evidence and does not claim Bedrock experience. "
            "Chatbot/conversational AI is not claimed. RAG is DIRECT.",
            "- E3 correctly omits methodology and does not name GPU/Linux/HPC. It still "
            "surfaces truthful AI/Python portfolio projects because those are the "
            "authorised CareerProfile evidence. That is not invented infrastructure "
            "employment, but the scan layer can still look stronger than the stretch "
            "role warrants. Watch this at M5.",
            "- E4 leads with QA → DE → AI. Portfolio project *names* include the word "
            "Copilot (Career Intelligence Copilot); that is not a GitHub Copilot or "
            "Claude product claim. DIRECT claimable labels are thin because Copilot/"
            "Claude/AI tools are unsupported, so the pack leans on trajectory + Master "
            "summary.",
            "- Project relevance lines are optional one-liners above locked project "
            "bodies. They were implemented, not deferred.",
            "",
        ]
    )
    out = REPO / "docs" / "eval" / "document_positioning_m3_inspection.md"
    out.write_text("\n".join(parts).rstrip() + "\n", encoding="utf-8")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
