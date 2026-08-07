<!--
GENERATED MASTERCLASS SNAPSHOT — DO NOT EDIT BY HAND.
Authoritative source: docs/04_functional_specification.md
Mode: section snapshot ('## FR-016 Multi-Agent Orchestration' → '## FR-017 Agent Evaluation & Observability')
Regenerate: python scripts/build_masterclass_package.py <FR_ID>
Repository documentation remains the source of truth.
-->

## FR-016 Multi-Agent Orchestration

**Phase:** Horizon 1A Stage 10  
**Status:** **Complete / Frozen / Accepted** — learning proof only (**GO AS LEARNING
PROOF ONLY**); prefer `cic agent run` for ordinary preparation; Engineering
Learning Academy ready
([acceptance](eval/fr016_multi_agent_orchestration.md);
[eval/fr016_m4_evaluation.md](eval/fr016_m4_evaluation.md);
[ADR-008](adr/008_multi_agent_orchestration.md)).  
*(Originally planned as FR-015; renumbered 2026-08-05.)*

Only after bounded agents (FR-015) are reliable — **FR-015 is complete and frozen**.

**Approved purpose (owner):** constrained learning milestone in production
multi-agent engineering, and architectural substrate for future
permission-separated capabilities (e.g. Job Discovery). Do **not** claim strong
near-term commercial value.

**Topology:** Deterministic Orchestration Supervisor (DOS) + frozen BOPA +
read-only Operational Briefing Specialist (OBS); typed handoffs; DelegationPolicy
+ per-specialist ToolPolicy; deterministic default; optional LLM propose only
behind policy. Prep/Truth/Review persona splitting is **rejected as multi-agent
theatre**.

Package: `career_intelligence.multi_agent` (distinct from FR-008
`orchestration` and FR-015 `agent`).

Acceptance Criteria

✓ Pattern choice is justified in an ADR or engineering note.
  → [ADR-008](adr/008_multi_agent_orchestration.md); [M0](eval/fr016_m0_engineering_spike.md).

✓ Specialists have distinct tools/context boundaries.
  → M1 registry + OBS vs BOPA allow-lists
  ([eval/fr016_m1_orchestration_contracts.md](eval/fr016_m1_orchestration_contracts.md)).

○ Loop detection and stop conditions remain enforced across agents.
  → Contracted in M1; **enforced in M2 runtime** (corpus I/J + limits).

✓ M2 go/no-go evidence (DOS/OBS value, complexity, continue vs defer).
  → **GO AS LEARNING PROOF ONLY**
  ([eval/fr016_m2_supervisor_runtime.md](eval/fr016_m2_supervisor_runtime.md)).

○ M3–M4 minimal owner surface / freeze only if owner requests learning close-out.
  → **M3 complete**; **M4 complete** — FR-016 **Complete / Frozen**
  ([acceptance](eval/fr016_multi_agent_orchestration.md);
  [eval/fr016_m4_evaluation.md](eval/fr016_m4_evaluation.md)).

---
