# Architecture Decision Records

| ADR | Title | Status |
|-----|-------|--------|
| [001](001_python_yaml_profile_foundation.md) | Python + YAML profile foundation | Accepted |
| [002](002_opportunity_persistence.md) | Opportunity persistence | Accepted |
| **003** | Application workflow orchestration architecture | **Pending** — required during/after the **FR-008** learning spike; evaluate LangGraph vs existing service orchestration before production commit |

Do not assume LangGraph (or any orchestrator) is the production choice until ADR-003 is written and accepted.

Related: [04_functional_specification.md](../04_functional_specification.md) § FR-008;
[10_roadmap.md](../10_roadmap.md) § Agent Orchestration Learning Spike.
