# FR-015 M3 — Owner CLI and Audit Presentation

**Date:** 2026-08-05  
**Status:** Complete (M3)  
**Architecture:** [ADR-007](../adr/007_bounded_agentic_workflow.md)  
**Preceding:** [M2 runtime](fr015_m2_agent_runtime.md)  
**Next:** [acceptance](fr015_bounded_agentic_workflow.md) / [M4](fr015_m4_evaluation.md)  
**Does not begin:** FR-016

---

## 1. CLI design

Smallest useful surface under `cic agent`:

| Command | Purpose |
|---------|---------|
| `cic agent run <opportunity_id> --approve` | Start BOPA (`prepare_for_owner_review`) |
| `cic agent resume <agent_run_id> --approve` | Resume from checkpoint after SoT re-inspect |
| `cic agent show <agent_run_id>` | Owner report (readiness, steps, stop, next action) |
| `cic agent history <agent_run_id>` | Append-only audit event log |
| `cic agent list [--opportunity …]` | List runs (newest first) |

Shared options: `--agent-runs-dir`, `--dir`, `--packages-dir`, `--runs-dir`,
`--truth-reports-dir`, `--profile`, `--cv-dir`, `--cover-letter-dir`,
`--max-steps`, `--verbose`, `--yaml`, `--llm` (optional OpenAI proposer),
`--override-material-benefit`.

**Defaults:** deterministic proposer (not LLM). `--approve` is mandatory for
`run` / `resume` (same gate discipline as FR-010/011).

**Non-goals in M3:** chat UI, discovery, submit, pipeline writes, FR-008 invoke.

---

## 2. Owner workflow

```text
cic agent run opp_… --approve
  → inspect readiness → (prepare / truth as policy allows) → stop
  → print report (readiness, proposed, policy, executed, stop, owner action)

# on truth block / owner edits:
cic truth validate-package …
cic agent resume agr_… --approve

cic agent show agr_…
cic agent history agr_…
cic agent list
```

Agent status ≠ Opportunity pipeline status (stated on every report).

### Owner stop statuses (OAT-001 Phase 4 polish)

| `status` | Legal next step |
|----------|-----------------|
| `awaiting_owner` | `cic agent resume <run_id> --approve` (add flags as guided) |
| `failed` | Start a **new** `cic agent run <opportunity_id> --approve` — resume is not available |

### Material-benefit stop

When preparation refuses Silver/Bronze without `consider_cv_tailoring`, BOPA stops with
`material_benefit_required` (not `unexpected_failure`). Owner action points at
`--override-material-benefit` on resume or a new run. Service gate behaviour is unchanged.

### Show report (polish)

`cic agent show` includes:

1. **Initial inspection** summary (even when step 0 is not `inspect_readiness`)
2. Observed readiness including **pipeline** stage (informational only — no pipeline authority)
3. Steps / policy / results
4. **Truth blockers** (owner-facing labels such as unsupported certification/technology)
5. Owner action mapped to legal next step for the run status

---

## 3. Implementation summary

| Piece | Location |
|-------|----------|
| Presentation | `career_intelligence.agent.presentation` |
| Runtime factory | `career_intelligence.agent.factory.build_agent_runtime` |
| Store list | `JsonDirectoryAgentRunStore.list_runs` |
| CLI | `cic agent` in `cli/main.py` |

Live wiring: `LiveReadinessBuilder` + `ServiceActionExecutor` + store under
`data/agent_runs/`. Proposer suggests; ToolPolicy authorises; services execute.

---

## 4. Audit presentation

`cic agent show` prints:

1. Initial inspection summary
2. Observed readiness (primary state, decision, artefacts, package, truth, pipeline, hash)
3. Per-step proposed action (+ rationale with `--verbose`)
4. Policy result (allow/deny + reason)
5. Executed service action / idempotent skip
6. Result refs (preparation run / truth reports when present)
7. Owner-facing truth blockers when present
8. Stop reason + run/checkpoint identity
9. Owner action required (mapped from stop reason **and** run status)
10. Explicit note: no submit / no pipeline advance; failed → new run; awaiting_owner → resume

`cic agent history` lists append-only events (`action_blocked`, `stop_recorded`, …).

---

## 5. Resume behaviour

- Requires `--approve`.
- Rebuilds readiness from SoT; forces inspect first.
- Does not re-run completed preparation/truth when already satisfied.
- Same max-steps / repeated-action / injection invariants as M2.

---

## 6. Manual validation

```
python scripts/run_fr015_m3_manual.py
```

**RESULT: PASS**

| ID | Journey | Result |
|----|---------|--------|
| A | Happy path CLI run → `completed_for_owner_review` | PASS |
| B | Truth failure show | PASS |
| C | Invalid-state show | PASS |
| D | Provider-unavailable show | PASS |
| E | Resume without duplicate prepare | PASS |
| F | Policy-blocked visible in history | PASS |
| G | Injection cannot grant validate/submit | PASS |

Evidence: `data/_fr015_m3_manual/summary.json`

---

## 7. Tests

| Suite | Result |
|-------|--------|
| `tests/unit/agent/` (incl. CLI + presentation) | **59 passed** (with prior M1/M2) |
| `tests/functional/test_fr015_m3_agent_cli.py` | **PASS** |
| Combined agent unit + FR-015 functional | **62 passed** |

---

## 8. Documentation updates

Changelog 1.96; functional spec; roadmap; AGENTS; repository guide; testing
strategy; implementation notes; domain model; ADR index; M2 “next” pointer.

---

## 9. Repository status

| Milestone | Status |
|-----------|--------|
| M0 spike | Accepted |
| M1 contracts + ADR-007 | Complete |
| M2 runtime | Complete |
| **M3 owner CLI** | **Complete** |
| M4 hardening / freeze | Not started |
| FR-016 | Not started |

FR-008–FR-014 behaviour unchanged. M2 invariants preserved.
