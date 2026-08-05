# FR-013 M3 — Owner Pipeline Workflow

**Date:** 2026-08-05  
**Status:** Complete (M3) — succeeded by
[M4 reporting & acceptance](fr013_m4_reporting_acceptance.md)
and [FR-013 freeze](fr013_application_pipeline_tracking.md).
**Architecture:** [ADR-005](../adr/005_application_pipeline_lifecycle.md) unchanged  
**Preceding:** [M2 tracking service](fr013_m2_pipeline_tracking.md)  
**Historical next (at M3):** M4 reporting / tracker continuity — **now complete**

---

## 1. Executive summary

M3 delivers a thin `cic pipeline` owner interface over the frozen M2
`PipelineTrackingService`. Commands read as career-pipeline actions (submit,
interview, reject, offer, history) — not event/projection mechanics.

ADR-005 invariants held: Opportunity remains aggregate root; append-only history;
explicit owner advancement; SubmissionAttempt citations are evidence only; no
auto-advance from FR-012.

**Projection watermark (`last_projected_event_id`):** **Not implemented.** Existing
`detect_divergence` / `repair` (reconcile) already cover consistency without
Opportunity schema churn.

---

## 2. Owner workflow

```
Generate package (FR-010/011)
  → Owner review (+ future FR-014 truth gate)
  → Render PDF
  → Submit manually and/or cic submission (FR-012 audit)
  → cic pipeline submit          ★ explicit lifecycle start for tracking
  → cic pipeline acknowledge     (optional; status unchanged)
  → cic pipeline interview --stage …
  → cic pipeline follow-up / note / evidence
  → cic pipeline reject | offer | withdraw | accept
  → cic pipeline correct …       (append-only fix)
  → cic pipeline show | history | list | check
```

---

## 3. CLI design

| Command | Owner intent |
|---------|----------------|
| `cic pipeline list [--all] [--status]` | Active applications (default) |
| `cic pipeline show <opp_id>` | Current status |
| `cic pipeline history <opp_id> [--verbose]` | Chronological append-only history |
| `cic pipeline preparing <opp_id>` | Package work in progress |
| `cic pipeline submit <opp_id>` | Record submitted (`--attempt-id` evidence only) |
| `cic pipeline acknowledge <opp_id>` | Employer ack (no status change) |
| `cic pipeline interview <opp_id> --stage …` | Enter interviewing or update stage |
| `cic pipeline reject / offer / accept / withdraw` | Terminal / offer moves |
| `cic pipeline follow-up --date\|--clear` | Reminder intent (no notifications) |
| `cic pipeline note / evidence` | Append-only notes / citations |
| `cic pipeline correct --to --note` | Fix mistaken status |
| `cic pipeline check / repair` | Consistency / recovery |

CLI is presentation only. Policy stays in `PipelineTrackingService`.

---

## 4. Implementation summary

| Component | Change |
|-----------|--------|
| `PipelineTrackingService` | `list_pipeline`, `record_acknowledgement`, `record_interview` |
| `cli/main.py` | `pipeline` Typer app |
| Tests | `test_cli.py`, `test_owner_ops.py`, `test_fr013_m3_owner_workflow.py` |
| Manual | `scripts/run_fr013_pipeline_manual.py journey` |

---

## 5. Application package integration

Package generation remains FR-010/011. Tracking does not start automatically when a
package is prepared. After submit (manual or FR-012), the owner runs
`cic pipeline submit`, optionally citing `--attempt-id` and
`--package-prepared-at` as evidence.

---

## 6. Follow-up design

`cic pipeline follow-up --date YYYY-MM-DD` records owner intent on Opportunity via
an append-only history entry. No email, no recruiter notification, no scheduler.

---

## 7. Notes model

`cic pipeline note` → `kind=note` history entry (append-only, chronological).
Does not rewrite prior notes. Optional mirror onto `OutcomeRecord.notes` only when
a status/outcome command includes a note in evidence (unchanged M2 projection).

---

## 8. Projection watermark decision

| Option | Verdict |
|--------|---------|
| Store `last_projected_event_id` on Opportunity | **Rejected for M3** |
| Rely on fold + `detect_divergence` / `repair` | **Accepted** |

Rationale: watermark adds schema migration and dual maintenance; divergence
detection already compares folded history to current fields.

---

## 9. Manual validation

```bash
python scripts/run_fr013_pipeline_manual.py journey --workspace data/_fr013_m3_manual
```

**RESULT: PASS** — preparing → submit → acknowledge → interviews → reject →
correct → offer → note → history/show/list/check.

---

## 10. Test results

| Suite | Result |
|-------|--------|
| `tests/unit/pipeline/` | Pass |
| `tests/functional/test_fr013_*.py` | Pass |
| Manual journey | PASS |

---

## 11. Documentation updated

Functional spec, domain model, testing strategy, implementation notes, roadmap,
changelog, AGENTS/README, this eval.

---

## 12. Final repository status

**At M3 delivery:** FR-013 M0–M3 complete; M4 next.  
**At FR-013 close-out:** M4 complete; FR-013 **ACCEPTED and FROZEN** —
[acceptance](fr013_application_pipeline_tracking.md). Next active FR: FR-014.
