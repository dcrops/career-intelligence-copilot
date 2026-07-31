# FR-012 — Submission Assistance

**Status:** **Complete** — documentation frozen  
**Date:** 2026-07-31  
**Recommendation:** **FR-012 ACCEPTED**  
**Next:** Begin **FR-013** Application Pipeline Tracking

Milestone acceptance records:
[M0](fr012_m0_submission_contracts.md),
[M1](fr012_m1_submission_orchestration.md),
[M2](fr012_m2_owner_workflow.md).

**No new ADR.** FR-012 introduces a dedicated submission coordinator, offline
adapters, append-only attempt audit, and a thin CLI. It does not amend ADR-002
(Opportunity SoT), ADR-003 (thin in-repo acquisition workflow), or ADR-004
(review boundary). Package integrity remains in FR-010. Pipeline lifecycle remains
FR-013. A new ADR would be warranted only if attempts became Opportunity SoT,
PipelineStatus advanced from FR-012, or the FR-008 graph absorbed submission —
none occurred.

---

## 1. Summary

FR-012 delivers **owner-assisted application submission**: readiness validation,
explicit Owner Approval, Assisted Submission via channel adapters, Manual Completion
attestation, and append-only SubmissionAttempt / SubmissionEvidence audit — without
silent submit, live board automation, or PipelineStatus writes.

| Milestone | Delivered |
|-----------|-----------|
| M0 | Domain contracts, state machine, append-only `SubmissionAttemptStore` |
| M1 | `SubmissionOrchestrator`, `SubmissionAdapter`, fake / manual-assisted adapters |
| M2 | Owner-operable `cic submission` workflow (CLI = interface only) |
| Close-out | Documentation freeze |

---

## 2. Final Architecture

```
Owner
  → cic submission (thin CLI)
  → SubmissionOrchestrator
       → ApplicationPackageService (integrity / verify)
       → SubmissionAdapter (channel only)
       → SubmissionAttemptStore (append-only)
  → SubmissionAttempt + SubmissionEvidence (audit)
```

| Component | Owns | Does not own |
|-----------|------|--------------|
| `cic submission` | Parsing, formatting, exit codes | Gates, policy, persistence |
| `SubmissionOrchestrator` | Sequencing, gates, duplicate/idempotency policy, outcome mapping | Package rules, channel mechanics, PipelineStatus |
| `ApplicationPackageService` | Package integrity / verification | Submission |
| `SubmissionAdapter` | Channel-specific execute + structured result | Approval, duplicates, store writes |
| `SubmissionAttemptStore` | Append-only attempt snapshots | Business policy |
| FR-008 runner | Untouched | No submit node wiring |

---

## 3. Validation Results

| Evidence | Result |
|----------|--------|
| Submission unit + functional | **86 passed** |
| Manual CLI harness (`cli`) | **PASS** |
| Full repository suite at freeze | **1145 passed** |

Confirmed behaviours: Submission Readiness check; fake Assisted Submission; manual-assisted
→ Manual Action Required; Manual Completion; duplicate protection; idempotent open
reclaim; outcome_unknown fail-closed; evidence recording; JSON persistence / reload;
CLI usability; deterministic exits.

No genuine defects discovered at close-out. No M0/M1 contract changes required.

---

## 4. Documentation Updated

| Document | Change |
|----------|--------|
| Functional specification | FR-012 complete and frozen; FR-013 next |
| Domain model | Submission Attempt frozen |
| Testing strategy | FR-012 coverage frozen |
| Implementation notes | Freeze invariants |
| Engineering principles | Submission lesson (orchestrator vs service; append-only audit) |
| Roadmap / changelog | FR-012 completed; FR-013 Now |
| Phase history / executive summary / repository guide | Status aligned |
| AGENTS / README | FR-012 frozen; FR-013 next |
| ADR README | Close-out linked; no new ADR |
| Milestone evals M0–M2 | Point to this freeze report |
| This report | `docs/eval/fr012_submission_assistance.md` |

---

## 5. Lessons Learned

1. **M0 → M1 → M2 → Close-out** — contracts first, behaviour second, owner interface
   third, freeze last. Validated again after FR-010/FR-011.
2. **Orchestration coordinates; services execute; adapters channel; CLI presents** —
   `SubmissionOrchestrator` vs `ApplicationPackageService` vs `SubmissionAdapter`
   vs `cic submission` stayed clean.
3. **Frozen contracts enable safe behaviour** — M1/M2 built on M0 without schema reopen.
4. **Deterministic / offline first** — fake + manual-assisted adapters proved policy
   without network or Playwright.
5. **Append-only audit + explicit Owner Approval** — never silent submit; uncertain
   outcomes stay `outcome_unknown` / `manual_action_required` / `failed`.
6. **Capability ≠ interface** — M2 is the owner-operable workflow; CLI is incidental.
7. **Documentation-first engineering** — Architecture Brief → named orchestrator +
   refined M2 before code reduced rework.

---

## 6. Deferred Work

| Item | Belongs to | Classification |
|------|------------|----------------|
| Pipeline lifecycle / interview / rejection / offer | FR-013 | Deferred |
| Browser automation / Playwright | Future FR (needs evidence) | Deferred |
| SEEK / LinkedIn / Indeed / ATS automation | Future FR | Deferred |
| Credentials / CAPTCHA / email submit | Future FR | Deferred |
| Retry / resume engines / background workers | Future FR | Deferred |
| FR-008 `submit` node wiring | Deliberate deferral — ADR-003 | Deferred |
| Multi-agent submission | FR-014+ | Deferred |
| Structured force/unknown fields beyond evidence.message | Future review | Accepted for now |

Nothing above remains as open FR-012 implementation work.

---

## 7. Technical Debt

| Item | Classification | Notes |
|------|----------------|-------|
| Force / unknown ack in `evidence.message` | Accepted | Avoided M0 schema churn |
| `--fake-outcome` CLI flag | Accepted | Offline test aid only |
| Duplicate ULID helpers across packages | Accepted | Avoids cross-package coupling |
| Live channel adapters | Deferred | Not in FR-012 exit |

---

## 8. Scope Confirmation (close-out)

| Constraint | Held |
|------------|------|
| No browser automation | Yes |
| No network integration | Yes |
| No PipelineStatus writes | Yes |
| No FR-008 changes | Yes |
| No new submission channels | Yes |
| No behavioural changes during close-out | Yes |

---

## 9. Final Status

**FR-012 ACCEPTED.** Documentation and exit criteria are **FROZEN**.

Do not reopen without explicit owner request.

The repository is ready to commence **FR-013** Application Pipeline Tracking.

Validate first. Change second. Never silently submit.
