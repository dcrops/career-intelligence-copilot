# Career Intelligence Copilot



## Overview



Career Intelligence Copilot is an AI-powered platform designed to help AI Engineers secure suitable roles sooner while reducing the manual effort of running an effective job search.



The **immediate priority** is to help the repository owner secure an appropriate AI Engineering role as quickly as reasonably possible — by improving opportunity decisions and reducing repetitive administrative work.



The **long-term direction** is a reusable Career Intelligence Platform that may continue supporting career progression after employment is secured, including networking, learning, role changes, and future opportunity evaluation.



The project also serves as a production-quality AI Engineering portfolio project and the practical project used to master modern AI engineering workflows with Cursor.



---



## Primary Goals



**Horizon 1 — Immediate (current priority):**



- Secure a suitable AI Engineering role sooner.

- Reduce manual effort, repetition, and administrative burden in the job search.

- Improve the quality of opportunity decisions and prioritisation.



**Horizon 2 — Long term:**



- Build an outstanding AI portfolio project.

- Learn professional AI Engineering workflows using Cursor.

- Evolve the platform to support ongoing career progression.



When Horizon 1 and Horizon 2 compete, Horizon 1 takes priority.



---



## Current Status



Phase: Phase 2 Job Intelligence implementation



Current focus:



- FR-001 Career Profile — complete

- FR-002 Job Analysis — complete

- FR-003 Opportunity Assessment — complete

- FR-004 Portfolio Matching — next

- Completing the Phase 2 decision loop without expanding scope



Completed pipeline so far:



```
FR-001 Career Profile
        ↓
FR-002 Job Analysis
        ↓
FR-003 Opportunity Assessment
```



See [docs/00_repository_guide.md](docs/00_repository_guide.md) for full orientation and [docs/10_roadmap.md](docs/10_roadmap.md) for phase status.



---



## Repository Structure



| Path | Purpose |
|------|---------|
| `docs/` | Product and engineering documentation |
| `docs/assets/` | Architecture and verification overview images |
| `src/` | Python implementation |
| `tests/` | Unit, functional, and golden journey tests |
| `data/` | Structured operational data, including the career profile |
| `applications/` | Live job search — applications, network contacts, company notes |
| `career-documents/` | Career artifacts (e.g. Master CV) |
| `templates/` | Message and document templates (placeholders) |
| `metrics/` | Review and analytics placeholders |
| `tools/` | Engineering evaluation harnesses (not product CLIs) |
| `images/` | Reserved — not yet populated |
| `career-log.md` | Dated career milestones and actions |
| `AGENTS.md` | Cursor agent bootstrap instructions |



---



## Documentation



Start with [docs/00_repository_guide.md](docs/00_repository_guide.md).



**Authoritative:**



- [docs/04_functional_specification.md](docs/04_functional_specification.md) — requirements

- [docs/10_roadmap.md](docs/10_roadmap.md) — delivery phasing

- [docs/03_product_vision.md](docs/03_product_vision.md) — product direction

- [docs/05_engineering_principles.md](docs/05_engineering_principles.md) — engineering tradeoffs

- [docs/06_domain_model.md](docs/06_domain_model.md) — domain concepts

- [docs/07_testing_strategy.md](docs/07_testing_strategy.md) — testing and regression strategy

- [AGENTS.md](AGENTS.md) — agent behaviour



**Supporting:**



- [docs/01_executive_summary.md](docs/01_executive_summary.md)

- [docs/02_problem_statement.md](docs/02_problem_statement.md)

- [docs/08_implementation_notes.md](docs/08_implementation_notes.md) — FR-001–FR-003 implementation notes

- [docs/eval/fr003_openai_manual_eval.md](docs/eval/fr003_openai_manual_eval.md) — FR-003 live eval (PARTIAL PASS)

- [docs/11_changelog.md](docs/11_changelog.md)



---



## Guiding Principles



- Help users spend less time managing their careers and more time advancing them

- Evidence-driven decisions

- Intelligence-first, with staged automation for repetitive administrative work

- Human review for important decisions and externally visible actions

- Production-quality engineering

- Modular architecture

- Optimise career outcomes rather than application volume



Near-term capabilities should improve the likelihood of securing relevant interviews or offers, or reduce the manual effort required to run an effective job search.



---



## Career Profile



FR-001 provides an evidence-based, typed career profile backed by
`data/career_profile.yaml`. Install the package and development tools:



```powershell
python -m pip install -e ".[dev]"
```



Use the thin CLI:



```powershell
cic profile validate
cic profile summary
cic profile show projects
cic profile init --path path/to/new_profile.yaml
```



Edit YAML directly for profile updates, then run `cic profile validate`. The CLI intentionally
does not provide partial update commands in this slice.



Run the complete test suite:



```powershell
python -m pytest
```


