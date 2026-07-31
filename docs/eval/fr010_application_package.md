# FR-010 — Application Package Preparation

**Status:** **Complete** — documentation frozen  
**Date:** 2026-07-31  
**Recommendation:** **FR-010 ACCEPTED**  
**Next:** Begin **FR-011** Application Preparation Orchestration (FR-010 frozen;
Submission Assistance is now **FR-012**)

Milestone acceptance records: [M0](fr010_m0_application_package.md),
[M1](fr010_m1_package_durability.md), [M2](fr010_m2_owner_cli.md).

No new ADR: FR-010 composes existing ADR-002 / ADR-003 / ADR-004 boundaries without
amending their decisions.

---

## 1. Executive Summary

FR-010 delivers a **standalone Application Package composition service** that prepares
one current package (Tailoring Plan + Tailored CV + Cover Letter) for an Opportunity
whose owner decision is `apply`. The durable record is a **manifest of references** —
generated drafts stay under existing FR-006/FR-007 writers; Opportunity evidence stays
immutable. Regeneration replaces the current package. A thin `cic package` CLI gives
the owner prepare / show / verify without inventing business rules.

M0 established composition and eligibility; M1 hardened durability, relative paths,
idempotency, and fail-closed integrity; M2 exposed owner operations. Acceptance
criteria are covered by unit, functional, and offline manual validation. Architecture
invariants (single service implementation, thin CLI, immutable evidence, no
orchestration expansion) hold.

**Verdict: FR-010 ACCEPTED.** Freeze FR-010 and begin FR-011 Application Preparation
Orchestration (Submission Assistance is now FR-012).

---

## 2. Objectives Achieved

| Objective | Status |
|-----------|--------|
| Connect `apply` opportunities to FR-006 / FR-007 document generation | Met (M0) |
| One Opportunity → one current package; regeneration replaces | Met (M0) |
| Manifest-only persistence; no duplicated CV/CL in Opportunity storage | Met (M0) |
| Preserve FR-006 / FR-007 owner-approval gates | Met (M0–M2) |
| Full evidence traceability (Opportunity, artefacts, acquisition) | Met (M0) |
| Portable relative draft paths + resolve on load | Met (M1) |
| Manifest commit point; failed regen leaves prior package current | Met (M1) |
| Idempotent prepare (same inputs + `prepared_at`) | Met (M1) |
| Integrity verification (`exists`, `verify_artefacts`, `get(verify=True)`) | Met (M1) |
| Owner CLI: prepare / show / verify with explicit `--approve` | Met (M2) |
| No submission, PipelineStatus, orchestration, versioning, PDF/DOCX | Held (out of scope) |

No incomplete FR-010 implementation remains. Deferred items are classified below and
are **not** reopen criteria.

---

## 3. Final Architecture

```
Opportunity (decision=apply)
  → OpportunityService.load_artifacts()
  → TailoringPlanService + CvGenerationService (FR-006)
  → CoverLetterPlanService + CoverLetterGenerationService (FR-007)
  → existing draft writers (Markdown / HTML / JSON)
  → ApplicationPackageManifest under
      data/application_packages/{opportunity_id}/manifest.json
```

| Concern | Boundary |
|---------|----------|
| Business implementation | `ApplicationPackageService` only |
| Owner adapter | Thin `cic package` Typer sub-app |
| Opportunity rehydration | `OpportunityService.load_artifacts` (public; no YAML import) |
| Persistence | Manifest references only; drafts under `career-documents/**/generated/` |
| Orchestration | Unchanged (ADR-003); package node slots remain unused |
| Evidence | FR-002–FR-005 snapshots immutable; index rows not mutated by package prep |
| Lifecycle | No `PipelineStatus` write (FR-012) *(remap: pipeline tracking is FR-013)* |

---

## 4. Testing Summary

| Layer | Location | Role |
|-------|----------|------|
| Unit (service) | `tests/unit/application_package/test_service.py` | Eligibility, gates, replace, evidence |
| Unit (durability) | `tests/unit/application_package/test_durability.py` | Relative paths, idempotency, failure safety, integrity |
| Unit (CLI) | `tests/unit/application_package/test_cli.py` | `--approve`, prepare/show/verify, fail-closed |
| Functional | `tests/functional/test_fr010_application_package.py` | End-to-end package journey |

Full suite at M2 close: **1047 passed**. Acceptance criteria from the functional
specification and milestone evals are exercised; no speculative coverage was added at
close-out.

Does **not** claim coverage for: orchestration nodes, PipelineStatus, submission,
versioning, PDF/DOCX, contact-overlay CLI flags, interactive plan-review UX.

---

## 5. Manual Validation Summary

| Milestone | Harness | Result |
|-----------|---------|--------|
| M0 | `scripts/run_fr010_application_package_manual.py demo` | Pass (offline) |
| M1 | same `demo` against durability workspace | Pass (offline) |
| M2 | `… manual.py cli --workspace data/_fr010_m2_manual` | Pass (offline) |

Owner flow validated:

```
cic opportunity decide <opp_id> apply
cic package prepare <opp_id> --approve [--override-material-benefit]
cic package show <opp_id>
cic package verify <opp_id>
```

Manual validation is **complete** for FR-010. Behaviour matches the final service and
CLI contracts recorded in the milestone evals.

---

## 6. Documentation Updated

| Document | Change |
|----------|--------|
| `AGENTS.md`, `README.md` | FR-010 complete/frozen; FR-011 next |
| `docs/00_repository_guide.md`, `01_executive_summary.md` | Status aligned |
| `docs/04_functional_specification.md` | FR-010 complete and frozen |
| `docs/06_domain_model.md` | Application Package entity complete |
| `docs/07_testing_strategy.md` | FR-010 coverage complete/frozen |
| `docs/08_implementation_notes.md` | M0–M2 historical; freeze note |
| `docs/10_roadmap.md` | FR-010 completed; FR-011 next |
| `docs/11_changelog.md` | v1.63 close-out summary |
| `docs/12_phase_history.md` | Current focus → FR-011 |
| `docs/adr/README.md` | Close-out record linked |
| Milestone evals M0/M1/M2 | Historical status; point to this report |
| `data/application_packages/README.md` | Store semantics unchanged |

`docs/02_problem_definition.md`, `03_product_vision.md`, and
`05_engineering_principles.md` needed no FR-010 status edits.

---

## 7. Technical Debt Remaining

| Item | Classification | Notes |
|------|----------------|-------|
| Partial draft overwrite if write fails mid-set | Accepted behaviour | Manifest is commit point; re-prepare converges |
| Material-benefit override often needed for non-platinum/gold apply | Accepted behaviour | Existing FR-006/007 gates; package service does not auto-override |
| Wall-clock `prepared_at` on CLI prepare | Accepted behaviour | Service default; adequate for owner use |

Items from M0 marked “future enhancement” that **M1/M2 delivered** (relative paths,
owner CLI) are closed — not remaining debt.

---

## 8. Deferred Enhancements

### Future Enhancement

| Item | Rationale |
|------|-----------|
| Contact / presentation option flags on `cic package prepare` | FR-006/007 support contact; not required for FR-010 exit |
| Optional interactive two-step plan-approval UX | Boolean gates suffice; richer UX is optional later |
| Package list command across opportunities | Convenience only |
| Clearer material-benefit override UX when applying then packaging | Product polish |
| Transactional draft staging (temp → rename for both draft sets) | Would avoid partial overwrite; not required for single-user |

### Deliberate Deferral

| Item | Belongs to / why |
|------|------------------|
| Orchestration `prepare_package` node / second interrupt | ADR-003 reconsideration; product evidence first |
| `PipelineStatus.preparing` write | FR-012 *(remap: now FR-013)* |
| Package versioning | Owner ruled out; replace-on-regenerate is the model |
| Submission assistance | FR-011 *(remap: preparation orchestration is FR-011; submission is FR-012)* |
| PDF / DOCX export | Later document-surface work |
| Ranking / duplicate / review-queue changes | FR-009 frozen |

Do **not** implement these under FR-010. Do not reopen FR-010 to absorb them.

---

## 9. Lessons Learned

1. **Compose before orchestrate** — proving package composition outside the runner
   avoided premature ADR-003 changes while still delivering owner value.
2. **Manifest as commit point** — a small durability rule gave clear failure semantics
   without transactional filesystem complexity.
3. **Reuse gates, don’t reinvent** — packaging as a composer of FR-006/007 options kept
   approval semantics consistent and testable.
4. **Thin CLI last** — M0/M1 locked the service; M2 added only an adapter, so CLI tests
   stay shallow and behaviour stays in one place.
5. **Milestone evals as history** — keeping M0–M2 reports and a single freeze report
   matches the FR-008 / FR-009 close-out pattern and prevents “still in progress” drift.

---

## 10. Recommendation

**FR-010 ACCEPTED.**

FR-010 documentation and exit criteria are frozen. Begin **FR-011** Application
Preparation Orchestration as the next active Horizon 1A requirement (Submission
Assistance is now **FR-012**). Do not reopen FR-010 without
explicit owner request.
