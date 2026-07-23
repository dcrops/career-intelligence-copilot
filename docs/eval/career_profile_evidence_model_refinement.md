# Career Profile Evidence Model Refinement Report

**Status:** Complete — Career Profile enrichment only (Phase C was out of scope for this report; FR-006 Phase C has since been completed separately).
**Date:** 2026-07-23  
**Trigger:** FR-006 deterministic validation (Officeworks / Snowflake over-emphasis)

This is a Career Profile enrichment, not an FR-006 redesign and not a Snowflake-specific bug fix.

---

## Proposed model

Skills remain truthful capability claims. Evidence strength records *how* a capability is demonstrated so planners can prioritise without inventing or deleting facts.

### Structured refs (preferred for new edits)

```text
Skill
  name: str
  evidence: str | None          # legacy; still supported
  evidence_refs: list[SkillEvidenceRef]  # optional; wins when present

SkillEvidenceRef
  kind: employment | independent_engineering | portfolio_project
        | certification | professional_development | coursework
  ref:  experience:<id> | project:<id> | certification:<id> | …
```

### Resolution (deterministic)

1. If `evidence_refs` is non-empty → use as-is.
2. Else parse legacy `evidence` tokens (`experience:id; project:id; certification:id`).
3. Map experience entries by `ExperienceEntry.kind` → evidence kind.
4. Map projects → `portfolio_project`; certifications → `certification`.
5. Strongest kind on a skill = minimum rank among resolved refs.
6. Named capability lookup also considers project technologies when no skill row exists.

### Strength ordering (strongest first)

| Kind | Role |
|------|------|
| `employment` | Production work under employment |
| `independent_engineering` | Independent engineering experience entries |
| `portfolio_project` | Portfolio / shipped projects |
| `certification` | Credential evidence |
| `professional_development` | Structured upskilling (e.g. studied Snowflake) |
| `coursework` | Coursework-only demonstration |
| `unspecified` | No resolvable evidence |

No numeric scoring engine — callers compare kinds via `evidence_strength_rank(kind)` (lower = stronger).

---

## Rationale

FR-006 previously treated every profile technology as equally strong evidence. That made PD-only tools (Snowflake studied during upskilling) compete with employment/portfolio capabilities (Python, FastAPI, OpenAI APIs, LangChain) for promotion and summary themes.

Keeping PD capabilities on the profile preserves truthfulness. Ranking by evidence strength improves:

- CV generation emphasis
- future job / portfolio matching
- interview prep and gap analysis

without hard-coding weights or redesigning TailoringPlan / Phase C.

---

## Planner changes (FR-006 consumer only)

`DeterministicTailoringPlanner`:

- **Promoted skills:** among JD-relevant matches, sort by JD level, then evidence strength, then name.
- **Summary themes:** among supported/related themes, sort by support class, then evidence strength, then JD priority order.
- PD-backed items keep truthful promotion/theme eligibility; rationales note that PD ranks below employment/portfolio demonstration.

No Phase C work. No TailoredCv render changes required.

---

## Files modified

| Path | Change |
|------|--------|
| `src/career_intelligence/profile/evidence.py` | New resolution + ranking helpers |
| `src/career_intelligence/profile/models.py` | `SkillEvidenceRef`; `Skill.evidence_refs` |
| `src/career_intelligence/profile/__init__.py` | Public exports |
| `src/career_intelligence/cv_generation/deterministic_planner.py` | Evidence-aware promotion/theme ranking |
| `tests/unit/profile/test_evidence.py` | Resolution/ranking unit tests |
| `tests/unit/cv_generation/test_deterministic_planner.py` | PD-below-employment ranking regression |
| `tests/unit/cv_generation/test_planner_corpus_regression.py` | Officeworks / Bluefin corpus checks |

---

## Migration approach

**Backwards compatible.** Live `data/career_profile.yaml` needs no rewrite.

- Existing `Skill.evidence` strings continue to load and resolve.
- Experience `kind` already distinguishes employment vs professional development (Snowflake → `experience:data-engineering-development-2023` → PD).
- Optional: gradually add explicit `evidence_refs` on skills for clarity; not required for this refinement.
- Downstream code that ignores evidence strength behaves as before; planners that opt in get better prioritisation.

---

## Validation results

Re-ran regression jobs via corpus planner tests + full suite.

| Check | Result |
|-------|--------|
| Python strongly promoted (Officeworks) | Pass — ahead of Snowflake |
| FastAPI / OpenAI APIs / LangChain (Bluefin-related) | Pass — LLM-related emphasis retained; unsupported stacks excluded |
| Snowflake recognised, not over-prioritised | Pass — `candidate_support=supported`; ranks below Python when both emphasised |
| Deterministic behaviour stable | Pass — existing unit + corpus assertions green |

**Full suite:** `597 passed`

---

## Test count

| Suite | Count |
|-------|-------|
| Full `pytest` | **597 passed** |
| New evidence unit tests | 5 |
| New / extended planner ranking + corpus tests | 3 (1 unit ranking + 2 corpus) |

---

## Out of scope (explicit)

- Phase C (LLM summary rewrite) — out of scope for this enrichment report (completed later under FR-006)
- FR-006 architecture redesign
- Hard-coded numeric skill weights
- Removing PD capabilities from the Career Profile
