# FR-012 M0 — Submission Assistance Contracts

**Date:** 2026-07-31  
**Status:** Complete (M0) — historical milestone record. FR-012 closed out:
[fr012_submission_assistance.md](fr012_submission_assistance.md). Succeeded by
[M1 orchestration](fr012_m1_submission_orchestration.md).
**Architecture:** Dedicated `career_intelligence.submission` foundation;
`SubmissionOrchestrator` named for M1 (consistent with FR-011); FR-008 runner
untouched; FR-010 package rules unchanged; no PipelineStatus.  
**Preceding capability:** [FR-011 acceptance](fr011_application_preparation.md)

---

## 1. Architectural decisions

| Decision | Choice | Why |
|----------|--------|-----|
| Coordinating name | **`SubmissionOrchestrator`** (not `SubmissionService`) | Primary responsibility is sequencing gates → adapter → store while delegating package rules to `ApplicationPackageService` — same pattern as `ApplicationPreparationOrchestrator`. `*Service` in this repo owns entity business rules. |
| M2 milestone | Owner-operable assisted-manual **workflow** | Capability is approve → attempt → evidence → inspectable outcome; CLI is interface only |
| Persistence | Append-only attempt identity under `data/submission_attempts/` | Audit only — not Opportunity SoT; never delete; terminal attempts immutable |
| Package rules | Stay in `ApplicationPackageService` | No business-logic move into FR-012 |
| FR-008 / PipelineStatus | Untouched | Submission audit ≠ pipeline lifecycle (FR-013) |
| Live automation | Deferred past M2 | Assisted-manual first; Validate first |

```
Owner (future CLI)
  → SubmissionOrchestrator (M1+)
       → ApplicationPackageService (integrity)
       → SubmissionAdapter (M1+)
       → SubmissionAttemptStore (M0)
```

---

## 2. Implementation summary

| API | Role |
|-----|------|
| `SubmissionAttempt` / `SubmissionEvidence` | Typed contracts (`sub_<ULID>`) |
| `validate_status_transition` / `apply_status_transition` | Deterministic state machine |
| `validate_evidence_for_status` | Fail-closed evidence requirements |
| `InMemorySubmissionAttemptStore` / `JsonDirectorySubmissionAttemptStore` | Append-only create / save / load / list |

Public surface: `career_intelligence.submission`.

Statuses: `ready`, `in_progress`, `submitted`, `manual_completed`,
`manual_action_required`, `failed`, `outcome_unknown`, `cancelled`.

Channels (contracts only): `manual_assisted`, `fake`. Modes: `assist_only`,
`adapter_action`.

M0 does **not** implement orchestrator behaviour, adapters, CLI, network, or
Opportunity / PipelineStatus writes.

---

## 3. Validation results

### Unit

`tests/unit/submission/` — models, transitions, evidence, append-only store
(memory + JSON).

| Check | Result |
|-------|--------|
| Schema / id pattern | Pass |
| Package opportunity mismatch rejected | Pass |
| Allowed / illegal transitions | Pass |
| Terminal immutability | Pass |
| `outcome_unknown` cannot become success | Pass |
| Evidence fail-closed by status | Pass |
| Create / load / list / filter | Pass |
| Duplicate create refused | Pass |
| JSON reload across instances | Pass |
| No delete API | Pass |

### Full suite

```
python -m pytest -q
1113 passed in 25.07s
```

Baseline at FR-011 freeze was 1059; M0 adds 54 focused submission contract tests.

---

## 4. Documentation updated

| Document | Change |
|----------|--------|
| Functional specification | FR-012 expanded: Orchestrator decision, M0–M2+Close-out, refined M2 |
| Domain model | Submission Attempt entity |
| Testing strategy | FR-012 M0 coverage section |
| Implementation notes | FR-012 M0 notes |
| Roadmap | FR-012 M0 progress |
| Changelog | v1.69 |
| AGENTS / README | Current focus = FR-012 M0 complete |
| Engineering principles | Outcome logging attributed to FR-013 |

---

## 5. Technical debt

| Item | Classification | Notes |
|------|----------------|-------|
| Duplicate ULID helper vs preparation / orchestration | accepted for M0 | Avoids cross-package coupling |
| Store `save` rewrites current attempt snapshot | accepted | Append-only identity = no delete / no terminal rewrite; in-flight advances are validated replacements |
| Gate / idempotency policy not enforced in store | deliberate deferral | M1 orchestrator owns policy |
| No orchestrator / adapters / CLI | deliberate deferral | M1 / M2 |

---

## 6. Recommendations for M1

| Recommendation | Classification |
|----------------|----------------|
| Implement `SubmissionOrchestrator` with gates + fake / manual-assisted adapters | M1 scope |
| Enforce owner `--approve-submit` and package `verify` | M1 scope |
| Duplicate success guard + force-new-attempt | M1 scope |
| Owner-operable workflow via thin CLI | M2 (capability), CLI incidental |

Validate first. Change second.

---

## 7. Readiness for M1

**Ready.** Contracts, transitions, evidence rules, and append-only persistence are
frozen as the M0 foundation. M1 may introduce orchestration behaviour and
deterministic adapters without reopening M0 schemas unless a concrete defect
appears.
