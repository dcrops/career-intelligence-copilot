# FR-013 M4 — Reporting, Continuity & Acceptance

**Date:** 2026-08-05  
**Status:** Complete (M4) — FR-013 frozen.  
**Acceptance:** [fr013_application_pipeline_tracking.md](fr013_application_pipeline_tracking.md)  
**Architecture:** [ADR-005](../adr/005_application_pipeline_lifecycle.md) unchanged  
**Preceding:** [M3 owner workflow](fr013_m3_owner_workflow.md)

---

## 1. Executive summary

M4 closes FR-013 with derived reporting, owner-controlled pipeline CSV export,
end-to-end manual acceptance, and documentation freeze. No domain redesign.
No FR-014 work.

---

## 2. Reporting capability

`PipelineTrackingService.summary_report()` / `cic pipeline report` derive from
existing Opportunity fields + PipelineEvents:

| Signal | Source |
|--------|--------|
| Counts by status / outcome | Opportunity current state |
| Active / submitted / awaiting / interviewing / offer / terminal | Status snapshot |
| Interview / offer / acceptance rates | Post-submit cohort ratios |
| Follow-ups due / overdue | `outcome.follow_up_date` vs reference date |
| Ageing (days in current status) | Last status/correction event → now |
| History entry count | Event store |

Also: `cic pipeline due`, ageing section in report.

---

## 3. CSV continuity

| Path | Role |
|------|------|
| `cic opportunity export` | Existing full Opportunity CSV (already includes status/outcome) |
| `cic pipeline export` | Focused operational CSV (`data/exports/pipeline.csv`) with days-in-status |

**No legacy migration.** Owner-controlled, deterministic UTF-8-SIG. Does not sync
two-way with `applications/application_tracker.csv`.

---

## 4. Manual validation

```bash
python scripts/run_fr013_pipeline_manual.py accept --workspace data/_fr013_m4_manual
```

Multi-opportunity journey: offer/accept, reject/correct/reject, withdraw +
follow-up/evidence, report, due, export, check. **RESULT: PASS**

---

## 5. Owner experience review

| Area | Assessment |
|------|------------|
| Command names | Natural verbs (submit, interview, reject, offer, report) |
| Grouping | Single `pipeline` app; help lists all commands |
| Discoverability | Help text enumerates commands; report/due/export added |
| Consistency | Matches FR-010/011/012 thin CLI pattern |
| Refinements in M4 | Expanded help; ASCII history arrows (Windows); report/due/export |

No material rename of M3 commands.

---

## 6. Testing summary

| Suite | Result |
|-------|--------|
| `tests/unit/pipeline/` | Pass |
| Functional FR-013 M2/M3/M4 | Pass |
| Combined FR-013 focused | **82 passed** |
| Manual accept | PASS |

---

## 7. Documentation updates

Freeze report, functional spec FR-013 complete, domain/testing/implementation
notes, roadmap (FR-014 Now), changelog, AGENTS/README/repository guide.

---

## 8. Definition of Done review

All FR-013 DoD items met — see acceptance report §16.

---

## 9. Technical debt

See acceptance report §12. None block exit.

---

## 10. Acceptance recommendation

**Accept and freeze FR-013.** Next: FR-014.
