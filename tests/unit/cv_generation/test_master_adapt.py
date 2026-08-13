"""Tests for Master-CV editorial baseline adaptation (Slice 1)."""

from __future__ import annotations

from pathlib import Path

from career_intelligence.cv_generation import (
    ContactDetails,
    CvGenerationOptions,
    CvGenerationService,
)
from tests.unit.cv_generation.helpers import make_plan, minimal_profile, strategy_from_payload


_MINI_MASTER = """# Test Candidate

Melbourne, VIC

**AI Engineer**

---

## Professional Summary

Experienced engineer with commercial data engineering and independent AI work.

## Technical Skills

**AI Engineering:** Python · FastAPI

## Professional Experience

### Data Engineer — Example Company

*Jan 2022 – Jan 2023 · Melbourne*

- Built validated data pipelines.

## Featured AI Projects

### Example Project

**Overview:** A production-minded example kept verbatim.

**Engineering Highlights:**

- Kept highlight

### Other Project

**Overview:** Should be dropped when not in the plan.

## AI Engineering Methodology

Applies AI to improve engineering quality.

**Planning:** Product vision

## Certifications

- Example Cert
"""


def test_adapt_from_master_keeps_project_overview_and_drops_methodology(
    tmp_path: Path,
) -> None:
    master_path = tmp_path / "master.md"
    master_path.write_text(_MINI_MASTER, encoding="utf-8", newline="\n")
    profile = minimal_profile()
    strategy = strategy_from_payload()
    plan = make_plan(profile=profile, strategy=strategy)
    cv = CvGenerationService().generate(
        strategy,
        profile,
        plan,
        options=CvGenerationOptions(
            tailoring_plan_approved=True,
            adapt_from_master=True,
            master_cv_path=str(master_path),
            contact=ContactDetails(email="candidate@example.com"),
        ),
    )

    assert cv.summary_source == "master_baseline"
    assert cv.engineering_methodology is None
    assert "A production-minded example kept verbatim" in cv.rendered_markdown
    assert "Should be dropped when not in the plan" not in cv.rendered_markdown
    assert "## AI Engineering Methodology" not in cv.rendered_markdown
    assert "### Example Project" in cv.rendered_markdown
    assert cv.summary and "commercial data engineering" in cv.summary
    assert "**Python**" in cv.rendered_markdown
