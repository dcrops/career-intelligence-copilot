<!--
GENERATED MASTERCLASS SNAPSHOT — DO NOT EDIT BY HAND.
Authoritative source: docs/06_domain_model.md
Mode: section snapshot ('### Agent Evaluation & Observability (FR-017)' → '## Entity Relationships')
Regenerate: python scripts/build_masterclass_package.py <FR_ID>
Repository documentation remains the source of truth.
-->

### Agent Evaluation & Observability (FR-017)

**ADR:** [ADR-009](adr/009_orchestration_evaluation_substrate.md)  
**Acceptance:** [eval/fr017_agent_evaluation_observability.md](eval/fr017_agent_evaluation_observability.md)

Narrow derive-only evaluation over FR-016 audits. Not a dashboard. Not a second SoT.

| Concept | Role |
|---------|------|
| OrchestrationRunMetrics | Derived per-run metrics (not SoT) |
| HandoffMetrics | Derived handoff summary |
| ParentChildCorrelation | Orphan / gap detection |
| ReconstructabilityReport | R1–R12 evidence checks |
| Observability corpus | Deterministic offline fixtures (15 cases) |
| `metrics` / `metrics-corpus` CLI | Read-only owner presentation |

**M0–M4 delivered:** spike → contracts → corpus GO → CLI → freeze.  
**Frozen:** [acceptance](eval/fr017_agent_evaluation_observability.md).  
**Academy package:** [masterclass/FR017/](masterclass/FR017/).

---
