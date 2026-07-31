# Architecture Health Check — Post FR-010

**Date:** 2026-07-31  
**Scope:** Horizon 1A implementation after FR-008, FR-009, and FR-010 freeze  
**Principle:** Validate first. Change second.  
**Verdict:** **ARCHITECTURE HEALTHY**

Related close-outs: [FR-008](fr008_workflow_orchestration.md),
[FR-009](fr009_opportunity_review_queue.md),
[FR-010](fr010_application_package.md).  
ADRs: [002](../adr/002_opportunity_persistence.md),
[003](../adr/003_application_workflow_orchestration.md),
[004](../adr/004_opportunity_review_boundary.md).

---

## 1. Executive Summary

A post-FR-010 review of documentation and implementation found **no material
architectural drift**. Opportunity remains the system of record; FR-009 review,
duplicate, and recommendation surfaces remain derived projections; FR-010 package
preparation remains a standalone composition service outside the orchestration
runner; CLI and workflow nodes remain thin adapters; FR-002–FR-005 evidence remains
immutable; ADR-002 / ADR-003 / ADR-004 still match the code.

Only Low-severity consistency notes were found (wording lag; intentional unused
reserved node ids; documented FR-009 CLI convenience gaps). Two documentation
wording fixes were applied. No redesign and no functional changes are warranted.

**Recommendation:** Proceed to **FR-011** Application Preparation Orchestration on the
current architecture (Submission Assistance is now **FR-012**).

---

## 2. Overall Architectural Health

| Area | Assessment |
|------|------------|
| Responsibility separation | Healthy |
| Domain / SoT ownership | Healthy |
| Workflow and approval gates | Healthy |
| Deterministic-first / AI boundaries | Healthy |
| Coupling | Healthy |
| Documentation vs implementation | Healthy (minor wording fixed) |
| Unintentional technical debt | None material |
| FR-011 seam | Clear; no blocking redesign |

---

## 3. Strengths

1. **Clear SoT boundary** — `data/opportunities/` owns business truth; checkpoints
   (`data/workflow_runs/`) are recovery-only; package manifests
   (`data/application_packages/`) are a separate reference store.
2. **ADR-004 persistence move is real** — `PRE_APPROVAL_SEQUENCE` runs
   `persist` before `owner_review`; apply / skip / defer share `record_decision`.
3. **Derived projections compose** — `opportunity_comparison.sort_key` →
   `ReviewQueueService` → `OpportunityRecommendationService`; no second ranking
   implementation.
4. **FR-010 stayed outside the runner** — composition proved without expanding
   ADR-003; orchestration does not import package / CV / cover-letter packages.
5. **Evidence immutability at the store** — write-once artefact JSON;
   index-only `save` / `replace`; package prepare uses `load_artifacts` and does
   not write Opportunity rows or artefacts.
6. **Thin adapters** — `cic package` and workflow nodes wrap public services;
   eligibility and gates live in domain services.
7. **Deterministic routing** — `next_spike_node` is pure; LLM use remains inside
   FR-002/003 (and document generation) behind existing service boundaries.
8. **FR-011 seam is open** — standalone package + reserved `submit` /
   `prepare_package` node ids leave room for a thin submission capability without
   forcing a package/orchestration merge.

---

## 4. Findings

### Material findings

None. No High or Medium issues.

### Low findings (informational)

| ID | Severity | Description | Evidence | Impact | Remediation |
|----|----------|-------------|----------|--------|-------------|
| F1 | Low | Reserved workflow node ids (`prepare_package`, `submit`, `deduplicate`, `rank`, `track`) exist but are unused | `orchestration` known node ids; routing uses only pre-approval + `record_decision` | None today; placeholders for later FRs | Keep unused until product evidence justifies thin nodes; do not implement under this review |
| F2 | Low | No Typer surface for FR-009 review / duplicate / recommend actions | Services and scripts exist; FR-009 M4 deferred `cic opportunity recommend` as convenience | Owner uses services/scripts; not an ADR violation | Future enhancement only if owner wants CLI convenience — not architectural debt |
| F3 | Low | Minor acceptance/roadmap wording lag (historical FR-008 persist narrative; FR-010 “Next: Freeze…”) | `docs/10_roadmap.md`, `docs/eval/fr010_application_package.md` | Skimming risk only | **Fixed** in this review |

Deliberate deferrals already recorded in FR-008/009/010 evals (orchestration package
node, PipelineStatus, versioning, PDF/DOCX, transactional draft staging, etc.) are
**not** reclassified as new debt.

---

## 5. Documentation Consistency

| Check | Result |
|-------|--------|
| FR-010 marked complete/frozen; FR-011 next | Consistent across AGENTS, README, roadmap, changelog, phase history, domain model, testing strategy |
| Package described as standalone, not inside runner | Consistent |
| Opportunity as SoT; queue/recommendations derived | Consistent with ADR-004 and code |
| ADRs listed Accepted / implemented | Consistent |
| Diagrams / decision loop | Domain model loop matches implemented order (persist → review → package → submit planned) |

**Corrections applied (docs only):**

1. Clarified FR-008 vs FR-009 M1 persistence narrative in `docs/10_roadmap.md`.
2. Updated FR-010 acceptance “Next” / recommendation wording now that freeze is done
   (`docs/eval/fr010_application_package.md`).

No contradictions requiring architectural change were found.

---

## 6. Technical Debt Review

| Category | Result |
|----------|--------|
| Unintentionally introduced debt from FR-008–010 | **None material** |
| Accepted behavioural tradeoffs (e.g. manifest commit point; partial draft overwrite on mid-write failure) | Documented; intentional |
| Documented future enhancements / deliberate deferrals | Remain out of scope for this review |

Do not implement deferred items as part of “health.”

---

## 7. Roadmap Alignment

| Item | Alignment |
|------|-----------|
| FR-011 Application Preparation Orchestration | Dedicated coordinator over apply + FR-010 package prep; does not extend FR-008 |
| FR-012 Submission Assistance | Fits as a new capability consuming apply + package artefacts; never silent submit; fail closed — matches engineering principles and domain model |
| FR-013 Pipeline Tracking | Still the right home for `PipelineStatus` / lifecycle writes; package correctly does not claim `preparing` |
| FR-014–FR-016 | Still gated on deterministic workflow first (ADR-003 reconsideration conditions unchanged) |
| Horizon 1B | Correctly blocked until 1A usable end to end |

FR-011 onward does **not** require redesign of FR-008–FR-010 boundaries to start.
(Historical note: at health-check time the next FR was labelled Submission as FR-011;
remapping made Preparation Orchestration FR-011 and Submission FR-012.)

Suggested attachment (informational only — not a design mandate):

```
Opportunity(decision=apply)
  → ApplicationPackageService / FR-011 preparation orchestrator (documents ready)
  → FR-012 Submission Assistance (new service / thin adapter)
  → optional later thin orchestration "submit" node if evidence justifies it
```

---

## 8. Recommended Actions

| Action | Priority |
|--------|----------|
| Proceed to FR-011 Application Preparation Orchestration on the current architecture | Primary |
| Leave reserved orchestration node ids unused until justified | Keep |
| Do not reopen ADR-002 / ADR-003 / ADR-004 without failing product evidence | Keep |
| Optional later: FR-009 owner CLI convenience commands | Only if owner requests |

No architectural remediation backlog.

---

## 9. Overall Recommendation

**ARCHITECTURE HEALTHY**

The Horizon 1A stack through FR-010 faithfully follows the documented architecture.
There is no evidence of material drift, duplicated ownership, ADR violation, or
incorrect coupling that would require redesign.

Proceed to **FR-011** Application Preparation Orchestration (subsequently delivered
as M0; Submission Assistance is **FR-012** after remapping).
