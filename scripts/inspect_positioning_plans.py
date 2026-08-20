"""Render PositioningPlan inspection for the four frozen evaluation jobs.

Does not generate CVs or cover letters. Does not call OpenAI.
"""

from __future__ import annotations

import json
from pathlib import Path

from career_intelligence.document_positioning import (
    build_positioning_plan,
    render_positioning_plan,
)
from career_intelligence.job_analysis.models import JobAnalysis
from career_intelligence.profile import CareerProfileService

REPO = Path(__file__).resolve().parents[1]


def _job(path: Path) -> JobAnalysis:
    if path.suffix == ".json" and path.name == "job_analysis.json":
        return JobAnalysis.model_validate(json.loads(path.read_text(encoding="utf-8")))
    payload = json.loads(path.read_text(encoding="utf-8"))
    return JobAnalysis.model_validate(payload["job_analysis"])


def main() -> None:
    profile = CareerProfileService.from_path(REPO / "data" / "career_profile.yaml").load()
    jobs = [
        (
            "E1 — Allura AI Engineer (control)",
            REPO / "manual_validation" / "outputs" / "001_strong_ai_engineer.json",
            "Applied AI Engineer control: DIRECT Python and REST APIs, "
            "`ai_lead` trajectory, methodology on because evaluation/governance "
            "appear in structured responsibilities. LLM/MLOps/GCP remain "
            "UNSUPPORTED unknown labels (catalogue v1 does not alias LLM → RAG).",
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
            "Mixed-fit specialist: AWS Bedrock is RELATED (promote AWS, forbid "
            "Bedrock experience), RAG is DIRECT via Retrieval-Augmented "
            "Generation, chatbot/conversational AI is an honest gap. Same "
            "`ai_lead` family as E1, but the transfer argument is the point.",
        ),
        (
            "E3 — Maincode AI Infrastructure Engineer",
            REPO
            / "manual_validation"
            / "outputs"
            / "012_maincode_ai_infrastructure_engineer.json",
            "Infra stretch: GPU/Linux/HPC stay UNSUPPORTED with no fabricated "
            "employment. Methodology omitted (no evaluation/governance needs). "
            "Portfolio is packed as candidate evidence only — not as GPU proof.",
        ),
        (
            "E4 — Repurpose AI Adoption Specialist",
            REPO
            / "manual_validation"
            / "outputs"
            / "008_repurpose_it_ai_adoption_specialist.json",
            "AI-adjacent adoption role: Copilot/Claude/AI tools are not claimed. "
            "`full_chapters` trajectory is the hiring argument (QA → DE → "
            "independent AI). Methodology on via risk-management wording.",
        ),
    ]
    parts = [
        "# Document Positioning M1 — Four-job PositioningPlan inspection",
        "",
        "Inspection artefact only. Not production document generation. "
        "Not an M5 A/B evaluation.",
        "",
        "Shared candidate evidence: `data/career_profile.yaml`.",
        "",
    ]
    for title, path, why in jobs:
        plan = build_positioning_plan(_job(path), profile)
        parts.append(render_positioning_plan(title, plan))
        parts.append("## Why this positioning differs")
        parts.append("")
        parts.append(why)
        parts.append("")
        parts.append("---")
        parts.append("")
    parts.extend(
        [
            "# Cross-job contrast",
            "",
            "- E1 vs E2: both `ai_lead`, but E2 is the only RELATED/Bedrock "
            "transfer case and the only chatbot gap.",
            "- E3 vs E1: same role family, but E3 has no DIRECT technologies and "
            "omits methodology — an honest stretch, not a skill dump.",
            "- E4 vs E1–E3: only `full_chapters`, because `role_family` is "
            "`ai_adjacent` and the profile has testing + DE + independent AI.",
            "",
        ]
    )
    out = REPO / "docs" / "eval" / "document_positioning_m1_inspection.md"
    out.write_text("\n".join(parts).rstrip() + "\n", encoding="utf-8")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
