# FR-011 M0 — Application Preparation Orchestration

**Date:** 2026-07-31  
**Status:** Complete (M0) — historical milestone record. FR-011 closed out:
[fr011_application_preparation.md](fr011_application_preparation.md). Succeeded by
[M1 executable CLI](fr011_m1_executable_preparation.md).  
**Architecture:** Dedicated `ApplicationPreparationOrchestrator`; FR-008 runner
untouched; FR-010 package rules unchanged. ADR-002 / ADR-003 / ADR-004 unchanged.  
**Preceding capability:** [FR-010 acceptance](fr010_application_package.md)

---

## 1. Architectural decisions

| Decision | Choice | Why |
|----------|--------|-----|
| Dedicated orchestrator | New package `career_intelligence.application_preparation` | Coordinate preparation without expanding the frozen FR-008 graph |
| Upstream work | Preconditions only | Analyse / assess / match / strategy already durable on the Opportunity |
| Sequencing | Inline in the orchestrator | Two-step linear path; no separate `routing.py` until branching/resume evidence |
| Package rules | Stay in `ApplicationPackageService` | No business-logic move; gates pass through |
| Run persistence | `data/preparation_runs/` | Audit/recovery only — not Opportunity SoT |
| FR numbering | Preparation = FR-011; Submission → FR-012 (+ cascade) | Owner-directed remapping |

```
Opportunity (decision=apply, FR-002–FR-005 present)
  → validate_preconditions
  → ApplicationPackageService.prepare (FR-010)
  → PreparationRunState completed
```

---

## 2. Implementation summary

| API | Role |
|-----|------|
| `ApplicationPreparationOrchestrator.run(...)` | Fixed sequence; returns completed or failed run state |
| `ApplicationPreparationOrchestrator.get(run_id)` | Reload run |
| `PreparationRunState` | Typed audit contract (`apr_<ULID>`) |
| `InMemoryPreparationRunStore` / JSON adapter | Replaceable run store |

Public surface: `career_intelligence.application_preparation`.

FR-006/007 options are caller-supplied. The orchestrator invents no gates and writes
no `PipelineStatus`.

---

## 3. Validation results

### Unit / functional

`tests/unit/application_preparation/`, `tests/functional/test_fr011_application_preparation.py`

| Check | Result |
|-------|--------|
| Happy path validate → prepare | Pass |
| Non-apply fails at validate | Pass |
| Missing opportunity fails at validate | Pass |
| Gate failure fails at prepare | Pass |
| JSON run reload | Pass |
| Functional: verifiable package | Pass |

### Manual

```
python scripts/run_fr011_preparation_manual.py --workspace data/_fr011_m0_manual
```

RESULT: PASS (offline).

---

## 4. Technical debt

| Item | Classification | Notes |
|------|----------------|-------|
| Duplicate ULID helper vs orchestration | accepted for M0 | Avoids preparation → orchestration import |
| Broad `except Exception` on prepare | accepted | Surfaces FR-006/007 errors into failed run without inventing success |
| No CLI | deliberate deferral | Manual script + public API enough for M0 |
| No resume / branching | deliberate deferral | Extract routing only with product evidence |
| FR-008 `prepare_package` node still unused | deliberate deferral | Runner stays frozen |

---

## 5. Recommendations for M1 (historical)

| Recommendation | Classification | Disposition |
|----------------|----------------|-------------|
| Optional `cic preparation run` thin CLI | future enhancement | **Done** — M1 |
| Resume / retry failed runs | future enhancement (needs evidence) | Remains out of FR-011 |
| Wire FR-008 `prepare_package` node | deliberate deferral — ADR-003 | Remains deferred |
| Submission assistance | FR-012 | Remains FR-012 |
| PipelineStatus `preparing` | FR-013 | Remains FR-013 |

Validate first. Change second.

---

## Full suite

```
python -m pytest -q
1054 passed in 23.59s
```

Baseline at FR-010 freeze was 1047; M0 adds 7 focused preparation tests.
