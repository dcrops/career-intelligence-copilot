<!--
GENERATED MASTERCLASS SNAPSHOT — DO NOT EDIT BY HAND.
Authoritative source: docs/06_domain_model.md
Mode: section snapshot ('### Multi-Agent Orchestration (FR-016)' → '### Agent Evaluation & Observability (FR-017)')
Regenerate: python scripts/build_masterclass_package.py <FR_ID>
Repository documentation remains the source of truth.
-->

### Multi-Agent Orchestration (FR-016)

**ADR:** [ADR-008](adr/008_multi_agent_orchestration.md)  
**Spike:** [eval/fr016_m0_engineering_spike.md](eval/fr016_m0_engineering_spike.md)
(Accepted with revisions)  
**M1:** [eval/fr016_m1_orchestration_contracts.md](eval/fr016_m1_orchestration_contracts.md)

Constrained multi-agent substrate (learning + future permission separation). Not
strong near-term commercial automation. Prep/Truth/Review persona split rejected.

| Concept | Role |
|---------|------|
| OrchestrationGoal / OrchestrationRun | Parent DOS run (audit/recovery; not Opportunity SoT) |
| OrchestrationObservation | Derived cross-surface observation for routing |
| DelegationPolicy | Sole admission for specialist invocation |
| Handoff | Typed, append-only, idempotent specialist handoff |
| OBS / OperationalBrief | Read-only briefing specialist + derived brief |
| BOPA (child) | Frozen FR-015 specialist; mutating allow-list unchanged |
| Specialist registry | Static OBS + BOPA boundaries |

**M1 delivered:** contracts + DelegationPolicy + OBS ToolPolicy + unit tests.  
**M2 delivered:** DOS runtime, OBS, BOPA adapter, corpus A–O, go/no-go
**GO AS LEARNING PROOF ONLY**
([eval/fr016_m2_supervisor_runtime.md](eval/fr016_m2_supervisor_runtime.md)).  
**M3 delivered:** `cic agent orchestrate` owner CLI
([eval/fr016_m3_owner_cli.md](eval/fr016_m3_owner_cli.md)).  
**M4 delivered:** final corpus 20/20, safety/product review, study-aid source, freeze
([eval/fr016_m4_evaluation.md](eval/fr016_m4_evaluation.md)).  
**Frozen:** [acceptance](eval/fr016_multi_agent_orchestration.md).  
**Academy bridge:** [masterclass/FR016/README.md](masterclass/FR016/README.md).  
**Academy package:** [masterclass/FR016/](masterclass/FR016/) (`MANIFEST.md` + `sources/`).
