"""Regenerate CV + Cover Letter from calibrated live strategy JSON.

Uses FR-006/FR-007 manual runners with --override-material-benefit for silver
packages. Produces Markdown, HTML, and PDF drafts.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
LIVE = REPO / "manual_validation" / "outputs" / "live"
PY = [sys.executable]

# Post-calibration regenerated packages (strategy already rematched into live/).
STEMS = [
    "001_strong_ai_engineer",
    "002_bluefin_ai_systems_developer",
    "006_senior_ai_engineer_kogan",
    "008_repurpose_it_ai_adoption_specialist",
    "009_forever_new_senior_ai_automation_engineer_digital",
    "010_pisell_ai_quality_systems_reliability_engineer",
    "013_pay_com_au_ai_automation_engineer",
    "014_anton_ai_automation_engineer",
    "015_expedient_software_junior_full_stack_developer",
    "016_robert_half_ai_engineer",
    "017_mars_recruitment_AI_Engineer",
    "job",
]


def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd))
    subprocess.run(cmd, cwd=REPO, check=True)


def main() -> None:
    for stem in STEMS:
        strategy = LIVE / f"{stem}.json"
        if not strategy.is_file():
            print(f"SKIP missing strategy {strategy}")
            continue
        run(
            [
                *PY,
                "scripts/run_cv_generation_manual.py",
                "--strategy-json",
                str(strategy),
                "--override-material-benefit",
            ]
        )
        run(
            [
                *PY,
                "scripts/run_cover_letter_manual.py",
                "--strategy-json",
                str(strategy),
                "--override-material-benefit",
            ]
        )
    print("Done regenerating CV + cover letter drafts (md/html/pdf).")


if __name__ == "__main__":
    main()
