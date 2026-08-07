<!--
GENERATED MASTERCLASS SNAPSHOT — DO NOT EDIT BY HAND.
Authoritative source: docs/04_functional_specification.md
Mode: section snapshot ('## FR-017 Agent Evaluation & Observability' → '## Horizon 1B — Recruiter and Market Engagement (FR-018–FR-024)')
Regenerate: python scripts/build_masterclass_package.py <FR_ID>
Repository documentation remains the source of truth.
-->

## FR-017 Agent Evaluation & Observability

**Phase:** Horizon 1A Stage 11  
**Status:** **Complete / Frozen / Accepted**
([eval/fr017_agent_evaluation_observability.md](eval/fr017_agent_evaluation_observability.md);
[M4](eval/fr017_m4_evaluation.md);
[ADR-009](adr/009_orchestration_evaluation_substrate.md);
Academy [masterclass/FR017/](masterclass/FR017/)). Learning/substrate;
**derive-only**; R1–R12; read-only `cic agent orchestrate metrics`; **must not block
Horizon 1B**. Do not reopen without owner request.  
*(Originally planned as FR-016; renumbered 2026-08-05.)*

**Narrowed intent (M0–M4):** orchestration-layer **derived metrics**, R1–R12, and
thin read-only CLI over existing FR-016 audits — mirror FR-015 observability. Not a
dashboard. Not a re-implementation of FR-008/014/015.

Historical laundry-list wording (traces, checkpoints, browser journeys, etc.) is
**dispositioned in M0** — most items already owned elsewhere or out of scope.

Acceptance Criteria (frozen)

● Derived orchestration metrics from existing audits only (no DOS behaviour change).

● Reconstructability R1–R12 demonstrated on offline corpus — M2 GO / M4 freeze.

● Child AgentRun token/cost reused via FR-015 helpers when present (null offline OK).

● Owner-operable read-only CLI (`metrics`, `metrics-corpus`) — M3.

● Horizon 1B is **not** gated on FR-017 completion.

---
