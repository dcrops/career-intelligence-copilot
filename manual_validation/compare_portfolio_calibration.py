"""Corpus before/after portfolio ranking comparison for FR-004 calibration.

Uses stored JobAnalysis from preferred strategy packages + live CareerProfile.
Does not call OpenAI. Analysis-only helper under manual_validation/.
"""

from __future__ import annotations

import json
from pathlib import Path

from career_intelligence.job_analysis.models import JobAnalysis
from career_intelligence.portfolio_matching.deterministic_matcher import DeterministicMatcher
from career_intelligence.portfolio_matching.service import PortfolioMatchingService
from career_intelligence.profile import CareerProfileService

ROOT = Path(__file__).resolve().parents[1]
OUTS = ROOT / "manual_validation" / "outputs"
LIVE = OUTS / "live"
PROFILE = ROOT / "data" / "career_profile.yaml"

FOCUS = {
    "001_strong_ai_engineer": "Allura",
    "017_mars_recruitment_AI_Engineer": "Mars",
    "002_bluefin_ai_systems_developer": "Bluefin",
    "009_forever_new_senior_ai_automation_engineer_digital": "Forever New",
    "011_officeworks_ai_engineer": "Officeworks",
    "013_pay_com_au_ai_automation_engineer": "pay.com.au",
    "job": "Harbour",
    "008_repurpose_it_ai_adoption_specialist": "Repurpose",
    "006_senior_ai_engineer_kogan": "Kogan",
}


def preferred_paths() -> dict[str, Path]:
    paths: dict[str, Path] = {}
    for p in sorted(OUTS.glob("*.json")):
        if "after" in p.name:
            continue
        paths[p.stem] = p
    for p in sorted(LIVE.glob("*.json")):
        paths[p.stem] = p
    return paths


def stored_ranks(data: dict) -> list[str]:
    pm = data.get("portfolio_match") or {}
    return [e["project_id"] for e in pm.get("ranked_projects") or []]


def main() -> None:
    profile = CareerProfileService.from_path(PROFILE).load()
    service = PortfolioMatchingService(DeterministicMatcher())
    paths = preferred_paths()

    print("stem | label | before top3 -> after top3 | PH before/after | CIC before/after")
    print("-" * 100)
    improved = []
    worsened = []
    unchanged = []
    for stem, label in FOCUS.items():
        path = paths.get(stem)
        if path is None:
            print(f"{stem}: MISSING")
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        before = stored_ranks(data)
        ja = JobAnalysis.model_validate(data["job_analysis"])
        after_match = service.match(ja, profile)
        after = [e.project_id for e in after_match.ranked_projects]

        def pos(ranks: list[str], pid: str) -> str:
            try:
                return str(ranks.index(pid) + 1)
            except ValueError:
                return "-"

        ph_b, ph_a = pos(before, "public-holiday-entitlements"), pos(
            after, "public-holiday-entitlements"
        )
        cic_b, cic_a = pos(before, "career-intelligence-copilot"), pos(
            after, "career-intelligence-copilot"
        )
        changed = before[:3] != after[:3]
        flag = "CHANGED" if changed else "same"
        print(
            f"{label:12} | {before[:3]} -> {after[:3]} | PH {ph_b}->{ph_a} | "
            f"CIC {cic_b}->{cic_a} | {flag}"
        )
        # Heuristic quality notes for focus jobs
        if label in {"Allura", "Mars"}:
            if after and after[0] != "public-holiday-entitlements":
                if before and before[0] == "public-holiday-entitlements":
                    improved.append(label)
            elif after and after[0] == "public-holiday-entitlements":
                worsened.append(f"{label} PH still #1")
        if label == "Bluefin":
            if after[:2] == before[:2] or (
                after
                and after[0] == "operational-intelligence-copilot"
            ):
                unchanged.append("Bluefin lead preserved/Ops")
            else:
                worsened.append(f"Bluefin lead now {after[:2]}")
        if changed and label not in {"Allura", "Mars"}:
            # surface for manual review
            pass

    print("\nAll preferred packages (top-1 before -> after):")
    top1_before = {}
    top1_after = {}
    for stem, path in sorted(paths.items()):
        if "after" in stem:
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        before = stored_ranks(data)
        if not before or "job_analysis" not in data:
            continue
        ja = JobAnalysis.model_validate(data["job_analysis"])
        after = [e.project_id for e in service.match(ja, profile).ranked_projects]
        b1 = before[0] if before else None
        a1 = after[0] if after else None
        top1_before[b1] = top1_before.get(b1, 0) + 1
        top1_after[a1] = top1_after.get(a1, 0) + 1
        if b1 != a1:
            print(f"  {stem}: {b1} -> {a1}")

    print("\nTop-1 counts BEFORE:", dict(sorted(top1_before.items(), key=lambda x: -x[1])))
    print("Top-1 counts AFTER: ", dict(sorted(top1_after.items(), key=lambda x: -x[1])))
    print("Improved focus:", improved)
    print("Worsened focus:", worsened)
    print("Preserved:", unchanged)


if __name__ == "__main__":
    main()
