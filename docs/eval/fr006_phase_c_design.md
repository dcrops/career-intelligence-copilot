# FR-006 Phase C Design

**Status:** Completed (part of FR-006 close-out)  
**Date:** 2026-07-23

## Principle

The deterministic Tailoring Plan is authoritative. The LLM is a **rendering layer**
only: it rewrites Professional Summary prose from plan-derived structured inputs.
It must never analyse the job description, rank projects, select technologies, or
invent evidence.

## Flow

```
CareerProfile + ApplicationStrategy
        → TailoringPlanService / DeterministicTailoringPlanner
        → Trusted TailoringPlan
        → CvGenerationService
              ├─ rewrite_summary=False → profile summary (default)
              └─ rewrite_summary=True + SummaryRewriter
                    → validate allowlists
                    → on failure: fallback_profile_copy
        → Trusted TailoredCv
```

## Components

| Module | Role |
|--------|------|
| `summary_rewriter.py` | Protocol, input dataclasses, `SUMMARY_PROMPT_VERSION` |
| `summary_prompt.py` | Load versioned `prompts/cv_summary_vN.md`; format tagged input |
| `summary_input.py` | Build plan-derived input (no raw JD) |
| `summary_validation.py` | Tech/employer/project/cert/years/commercial claim checks |
| `fixture_summary_rewriter.py` | Offline deterministic rewriter |
| `openai_summary_rewriter.py` | `gpt-4o-mini`, temperature 0, Responses `parse` |
| `CvGenerationOptions.rewrite_summary` | Default `False` |
| `TailoredCv.summary_source` | Provenance for tests and owner review |

## Prompt versions

| Version | File | Notes |
|---------|------|-------|
| v1 | `prompts/cv_summary_v1.md` | Historical baseline — retain for diffs |
| v2 | `prompts/cv_summary_v2.md` | **Current** — employer-relevant lead; capabilities before chronology and project names |

Future improvements: add `cv_summary_vN.md`, bump `SUMMARY_PROMPT_VERSION`, keep prior files.

## Runtime (manual runner)

Corpus FR-006 runs reuse saved strategy JSON and therefore skip the FR-002/003 live
OpenAI branch. Before constructing `OpenAISummaryRewriter`, the CV runner calls
`truststore.inject_into_ssl()` (same path as `run_application_strategy_manual.py`)
and requires `OPENAI_API_KEY`. Provider failures are classified
(Connection / Auth / RateLimit / Timeout / APIStatus) and **fail-soft** to the
profile summary.

## Owner-approved decisions

- Fail-soft to profile summary
- Opt-in (`rewrite_summary=False` by default)
- Length target 70–110 words; hard max 140
- Keep Summary themes section in Markdown during development
- Model: `gpt-4o-mini`
- Prompt on disk (versioned), not embedded in Python source

## Manual validation (Bluefin — close-out)

Job: Bluefin AI Systems Developer (`002_bluefin_ai_systems_developer`).

Confirmed:

- `summary_source=openai_rewrite`
- Prompt **v2**
- No hallucinated / unsupported technologies (e.g. Terraform, Rails) in the summary
- No unsupported experience claims relative to profile + plan
- Deterministic Tailoring Plan unchanged by Phase C

Procedure: [fr006_manual_validation.md](fr006_manual_validation.md).

## Not in scope (“Phase D”)

Presentation-only enhancements (dynamic layouts, adaptive section ordering, richer
document formats) are **not** FR-006. See functional specification FR-006 § Out of scope.
