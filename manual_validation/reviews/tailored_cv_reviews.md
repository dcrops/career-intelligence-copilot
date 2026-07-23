# FR-006 Manual Validation Reviews

Owner review log for Tailoring Plan (Q1) and Tailored CV (Q2/Q3) checks.

**FR-006 status:** Completed (2026-07-23). Deterministic planning/render + optional
OpenAI summary rewrite (prompt v2) closed after Bluefin validation
(`summary_source=openai_rewrite`). Entries below remain historical review notes.

---

# FR-006 Manual Validation

## Job
013 - Pay.com.au - AI Automation Engineer

## Date
2026-07-23

## Q1 - Tailoring Plan

Status: PARTIAL FAIL

### Findings

- Responsibility priorities contain truncated text:
  - "Ship With Production Discipline Human The"
  - "Package What You Build Into Shareable"

- AI automation capabilities appear under-emphasised.

- TypeScript appears as a summary theme despite no demonstrated candidate evidence.

- Project ordering should be reviewed for automation relevance.

## Q2 - Tailored CV

Status: PASS

### Findings

- Skill emphasis follows the Tailoring Plan.
- Project order follows the Tailoring Plan.
- Experience scope follows the Tailoring Plan.
- Renderer introduced no additional prioritisation.

## Overall

Renderer is behaving correctly.

Further work required in:
- Job Analysis extraction and/or
- Deterministic Tailoring Planner.

# FR-006 Manual Validation

## Job
002 - Bluefin Resources - AI Systems Developer

## Date
2026-07-23

## Q1 - Tailoring Plan

Status: FAIL

### Findings

- The plan confuses JD requirements with candidate-supported emphasis.
- Terraform, PostgreSQL and Ruby on Rails appear as summary themes despite insufficient demonstrated candidate evidence.
- Technology priority explanations incorrectly say technologies are “promoted” merely because they appear in the JD.
- Python is not emphasised despite the role being an AI Systems Developer position; this requires comparison with the original JD and JobAnalysis.
- Project ordering is plausible and can be retained.

## Q2 - Tailored CV

Status: PASS

### Findings

- Emphasised skills match the Tailoring Plan.
- Project order matches the Tailoring Plan.
- Experience scope matches the Tailoring Plan.
- The renderer did not introduce unsupported reprioritisation.

## Overall

The renderer is operating correctly.

The Tailoring Planner needs to separate:

1. employer requirements,
2. candidate-supported strengths,
3. unsupported gaps,
4. evidence-backed summary themes.

Phase C must not begin until summary themes are restricted to evidence-backed candidate capabilities.

# FR-006 Manual Validation

## Job
011 - Officeworks - AI Engineer

## Date
2026-07-23

## Q1 - Tailoring Plan

Status: FAIL

### Findings

- The plan again confuses employer requirements with candidate-supported CV emphasis.
- JavaScript, TypeScript and React appear as summary themes without confirmed candidate evidence.
- Technology explanations incorrectly use “promoted” merely because a technology appears in the JD.
- The plan may under-emphasise relevant applied-AI capabilities such as FastAPI, OpenAI APIs, LangChain and REST APIs.
- Project ordering is plausible.

## Q2 - Tailored CV

Status: PASS

### Findings

- Emphasised skills match the approved plan.
- Project order matches the approved plan.
- Experience scope matches the approved plan.
- The renderer performs no independent reprioritisation.

## Overall

The Tailoring Planner needs to separate:

1. JD requirements,
2. candidate-supported strengths,
3. unsupported gaps,
4. evidence-backed summary themes.

Phase C must not begin until unsupported JD technologies are excluded from summary themes.

## Q1 - Tailoring Plan

Status: PASS WITH UPSTREAM ISSUE

### Findings

- Supported and unsupported employer technologies are now correctly separated.
- TypeScript is marked unsupported and excluded from summary themes and promoted skills.
- Summary themes are evidence-backed: Python, SQL and Operational intelligence.
- Project ordering remains plausible.
- Some responsibility labels remain malformed in the reused upstream JobAnalysis:
  - "Ship With Production Discipline Human The"
  - "Package What You Build Into Shareable"
- These malformed responsibilities are safely classified as unsupported and do not enter the CV.

## Q2 - Tailored CV

Status: PASS

### Findings

- Emphasised skills match the Tailoring Plan.
- Project order matches the Tailoring Plan.
- Experience scope matches the Tailoring Plan.
- Unsupported TypeScript is not promoted or claimed.
- Renderer introduced no independent reprioritisation.

## Overall

FR-006 deterministic planning and rendering pass for Job 013.

A separate FR-002 extraction-quality issue remains for malformed responsibility labels.

## Q1 - Tailoring Plan

Status: PASS WITH CLASSIFICATION FOLLOW-UP

### Findings

- Unsupported JD technologies are correctly retained as employer requirements but excluded from promoted skills and summary themes.
- LLM is correctly mapped to the evidence-backed profile capability "LLM application development."
- Summary themes are restrained and evidence-grounded:
  - LLM application development
  - Operational intelligence
- Project ordering is plausible.
- AWS is classified as unsupported. Review whether an active AWS certification should qualify as related evidence without implying production AWS experience.
- "Build capabilities into production" is classified as unsupported. Existing production-engineering practices may justify a related classification.
- The material-benefit override was unnecessary because this Platinum role already allowed tailoring.

## Q2 - Tailored CV

Status: PASS

### Findings

- Emphasised skills match the Tailoring Plan.
- Project order matches the Tailoring Plan.
- Experience scope matches the Tailoring Plan.
- Unsupported technologies do not appear as promoted capabilities.
- The renderer introduced no independent reprioritisation.

## Overall

FR-006 deterministic planning and rendering pass for Job 002.

The original unsupported-technology leakage is resolved. Two non-blocking evidence-classification questions remain around certification evidence and responsibility-level related evidence.