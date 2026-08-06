# FR-016 M3 — Minimal Owner Workflow for Learning Proof

**Date:** 2026-08-06  
**Status:** Complete (M3) — **historical milestone record**  
**Succeeded by:** [M4](fr016_m4_evaluation.md);
[acceptance](fr016_multi_agent_orchestration.md) (FR-016 Complete / Frozen)  
**Architecture:** [ADR-008](../adr/008_multi_agent_orchestration.md)  
**Preceding:** [M2 runtime / go-no-go](fr016_m2_supervisor_runtime.md)
(**GO AS LEARNING PROOF ONLY**)  
**Did not begin in M3:** M4 freeze, FR-017, product expansion, study-aid generation
(M4 later completed the freeze; this report remains the M3 historical record)

---

## 1. Executive summary

M3 makes the M2 multi-agent learning proof **minimally owner-operable** under:

```text
cic agent orchestrate …
```

Owner can run / resume / show / history / list bounded orchestration journeys and
see specialist selection, authority, typed handoffs, policy results, child
AgentRun / OBS brief refs, stop reasons, and next actions.

**Binding M2 verdict remains explicit in every report:** FR-016 is a learning
proof and future substrate — **not** the preferred daily replacement for
`cic agent run`.

No new specialists, no frameworks, no LLM supervisor, no discovery/submit/pipeline
authority.

---

## 2. CLI design

Extended existing `cic agent` (consistent with FR-015) rather than a top-level
`cic orchestrate` namespace.

| Command | Purpose |
|---------|---------|
| `cic agent orchestrate run <opp> --goal <g> --approve` | Start DOS |
| `cic agent orchestrate resume <orr_…> --approve` | Resume after SoT re-inspect |
| `cic agent orchestrate show <orr_…>` | Owner report |
| `cic agent orchestrate history <orr_…>` | Append-only audit |
| `cic agent orchestrate list` | List runs |
| `cic agent orchestrate check-delegation …` | Teaching: policy admit/deny without execute |

Shared path overrides mirror `cic agent` (`--dir`, `--packages-dir`,
`--agent-runs-dir`, `--orchestration-runs-dir`, …).

`--approve` is mandatory for `run` / `resume`.

---

## 3. Supported owner goals

| `--goal` | Maps to | Behaviour |
|----------|---------|-------------|
| `brief` | `brief_opportunity_readiness` | DOS → OBS |
| `prepare` | `coordinate` (no synthesize) | DOS → BOPA |
| `prepare_then_brief` | `coordinate` + `synthesize_after_prepare` | DOS → BOPA → OBS |

No additional goals or specialists.

---

## 4. Implementation summary

| Piece | Location |
|-------|----------|
| Goals | `career_intelligence.multi_agent.goals` |
| Factory | `build_orchestration_supervisor` |
| Presentation | `presentation.py` (M3 owner report) |
| CLI | `cic agent orchestrate` in `cli/main.py` |
| Store | `data/orchestration_runs/` |

BOPA allow-list / ToolPolicy unchanged.

---

## 5–7. Presentation (selection, authority, handoff/audit)

`show` prints:

1. Learning-proof banner + preference for `cic agent run`
2. Owner goal + opportunity + status / stop / steps
3. Parent / child IDs (orchestration, BOPA AgentRun, OBS brief)
4. Observed derived state
5. Specialist visits
6. Per-handoff: selection reason, delegation policy, lifecycle, **authority
   boundary** (BOPA vs OBS allow-list summary), child result refs
7. Owner action mapped to legal next command
8. Safety footer (no submit / pipeline / truth waive / discovery)

`history` lists append-only orchestration events.

---

## 8. Resume behaviour

Unchanged from M2: re-inspect SoT; skip unchanged OBS brief; BOPA child resume /
idempotent prep; `--approve` required; global limits preserved.

---

## 9. Manual validation

`python scripts/run_fr016_m3_manual.py` covers A–I (offline DOS + CLI approve gate
+ illegal delegation deny).

| ID | Journey | Expected |
|----|---------|----------|
| A | brief | OBS briefing |
| B | prepare | BOPA → owner stop |
| C | prepare_then_brief | BOPA → OBS |
| D | truth blocked | OBS explains; no waive |
| E | interviewing + prepare goal | OBS brief-first |
| F | illegal delegation | deny visible |
| G | resume | no duplicate child prep |
| H | audit reconstruction | parent → handoff → child |
| I | safety | no pipeline/submit APIs |

---

## 10. Tests

| Suite | Result |
|-------|--------|
| `tests/unit/multi_agent/` (incl. `test_cli_m3.py`) | green |
| `tests/unit/agent/test_cli.py` | green |
| M2 corpus (via runtime tests) | green |

---

## 11. Documentation updated

- This M3 eval
- Implementation notes / changelog / roadmap / functional spec pointers
- ADR-008 milestone note
- Repository navigation (agent help text)

---

## 12. Remaining limitations

- Live `orchestrate run` needs a real Opportunity corpus (same as `cic agent`)
- No product dashboard / chat
- No FR-017 eval harness
- Happy-path prep still better via `cic agent run`
- M4 documentation freeze completed after this milestone
  ([fr016_m4_evaluation.md](fr016_m4_evaluation.md);
  [fr016_multi_agent_orchestration.md](fr016_multi_agent_orchestration.md))

---

## 13. Final repository status

| Item | Status |
|------|--------|
| M2 go/no-go | **GO AS LEARNING PROOF ONLY** (unchanged) |
| M3 owner CLI | **Complete** |
| M4 | Not started |
| FR-017 | Not started |
| Daily prep recommendation | **`cic agent run`** |

---

## Owner next step

Acknowledge M3. Request M4 only when ready to freeze FR-016 documentation for the
learning-proof close-out (still without product-value claims).
