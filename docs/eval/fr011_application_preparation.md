# FR-011 — Application Preparation Orchestration

**Status:** **Complete** — documentation frozen  
**Date:** 2026-07-31  
**Recommendation:** **FR-011 ACCEPTED**  
**Next:** Begin **FR-012** Submission Assistance

Milestone acceptance records: [M0](fr011_m0_application_preparation.md),
[M1](fr011_m1_executable_preparation.md).

**No new ADR.** FR-011 introduces a dedicated preparation coordinator outside the
FR-008 runner and a thin CLI adapter. It does not amend ADR-002 (Opportunity SoT),
ADR-003 (thin in-repo acquisition workflow), or ADR-004 (review boundary). Package
business rules remain in FR-010. A new ADR would be warranted only if the FR-008
graph absorbed preparation or checkpoints merged with Opportunity storage — neither
occurred.

---

## 1. Summary

FR-011 delivers deterministic **application preparation orchestration**: the owner
invokes a thin CLI that runs `ApplicationPreparationOrchestrator`, which sequences
precondition checks and existing `ApplicationPackageService.prepare` without moving
business logic into the orchestrator or extending FR-008.

| Milestone | Delivered |
|-----------|-----------|
| M0 | `ApplicationPreparationOrchestrator`; run state under `data/preparation_runs/` |
| M1 | `cic preparation run` / `show` thin CLI |
| Close-out | Documentation freeze |

---

## 2. Final Architecture

```
Owner
  → cic preparation (thin CLI)
  → ApplicationPreparationOrchestrator
       → validate_preconditions (Opportunity apply + FR-002–FR-005 artefacts)
       → ApplicationPackageService.prepare (FR-010)
  → PreparationRunState (audit/recovery)
```

| Component | Responsibility |
|-----------|----------------|
| `cic preparation` | Interface only — gates pass-through; display run state |
| `ApplicationPreparationOrchestrator` | Sequencing, coordination, run state |
| `ApplicationPackageService` | Package construction, validation, preparation rules |
| FR-008 `ApplicationWorkflowRunner` | Untouched |
| Opportunity artefacts | Immutable preconditions — not re-produced |

`cic package` remains a supported **direct** package pathway. FR-011 adds the
**orchestration** pathway; it does not replace FR-010.

---

## 3. Documentation Updated

| Document | Change |
|----------|--------|
| `docs/04_functional_specification.md` | FR-011 complete and frozen; FR-012 next |
| `docs/10_roadmap.md` | FR-011 completed; FR-012 Now |
| `docs/11_changelog.md` | v1.68 close-out |
| `docs/12_phase_history.md` | Current focus → FR-012 |
| `docs/06_domain_model.md` | Preparation orchestration complete |
| `docs/07_testing_strategy.md` | FR-011 coverage frozen |
| `docs/08_implementation_notes.md` | Freeze invariants |
| `docs/05_engineering_principles.md` | Orchestration lesson |
| `docs/00_repository_guide.md`, `docs/01_executive_summary.md` | Status aligned |
| `AGENTS.md`, `README.md` | FR-011 frozen; FR-012 next |
| `docs/adr/README.md` | Close-out linked; no new ADR |
| Milestone evals M0/M1 | Point to this freeze report |
| This report | `docs/eval/fr011_application_preparation.md` |

---

## 4. Validation

| Evidence | Result |
|----------|--------|
| M0 manual (`demo`) | PASS |
| M1 manual (`cli`) | PASS |
| Automated suite at freeze | **1059 passed** |

---

## 5. Technical Debt (intentionally deferred)

| Item | Belongs to |
|------|------------|
| Submission Assistance | FR-012 |
| PipelineStatus / lifecycle tracking | FR-013 |
| Resume / retry of failed preparation runs | Future enhancement (needs evidence) |
| FR-008 `prepare_package` node wiring | Deliberate deferral — ADR-003 reconsideration |
| Multi-agent behaviour | FR-014+ |
| Package versioning / PDF/DOCX / interactive plan UX | Out of FR-011 (unchanged) |

Nothing above remains as open FR-011 implementation work.

---

## 6. Lessons Learned

1. **Orchestration coordinates; services execute** — preparation sequencing stayed
   outside FR-010 rules and outside FR-008.
2. **Interfaces remain thin** — CLI only maps owner commands to the orchestrator.
3. **Compose before expanding the runner** — a dedicated package proved the capability
   without ADR-003 reconsideration.
4. **Inline sequence until evidence** — no premature `routing.py` for a two-step path.
5. **Parallel pathways are acceptable** — `cic package` and `cic preparation` serve
   different intents (direct vs orchestrated).

---

## 7. Readiness

**FR-011 ACCEPTED.** Documentation and exit criteria are frozen. Do not reopen without
explicit owner request.

The repository is ready to commence **FR-012** Submission Assistance.
