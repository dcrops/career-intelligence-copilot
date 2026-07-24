# Career Intelligence Copilot

## Overview

Career Intelligence Copilot is an AI-powered **decision-support** system for job
search — helping AI Engineers secure suitable roles sooner while reducing repetitive
analysis and tracking work.

It is **not** an application-automation bot. Recommendations require human review;
the system does not send outreach or apply on the owner's behalf.

**Horizon 1 (current priority):** Improve opportunity decisions and reduce job-search
effort for the repository owner.

**Horizon 2 (long term):** Evolve into a reusable Career Intelligence Platform for
ongoing career progression after employment is secured.

The project is also a production-quality portfolio artefact and a practical lab for
modern AI engineering workflows with Cursor. When those goals conflict with Horizon 1,
**Horizon 1 wins**.

---

## Where to start

| Audience | Start here |
|----------|------------|
| New engineer / contributor | [docs/00_repository_guide.md](docs/00_repository_guide.md) |
| Cursor agents | [AGENTS.md](AGENTS.md) |
| What was delivered in Phase 2 | [docs/eval/phase2_release_report.md](docs/eval/phase2_release_report.md) · [docs/12_phase_history.md](docs/12_phase_history.md) |
| What is next | [docs/10_roadmap.md](docs/10_roadmap.md) |

---

## Current Status

**Phase 2 Job Intelligence — Complete** (M5 GO —
[docs/eval/phase2_release_report.md](docs/eval/phase2_release_report.md)).

**Next milestone:** **FR-006b — CV Quality Improvement**

**Thereafter (Horizon 1):** FR-007 Cover Letter → automated job acquisition

### Phase 2 capabilities (baseline — frozen)

- FR-001 Career Profile
- FR-002 Job Analysis
- FR-003 Opportunity Assessment (Technical / Commercial / Portfolio Fit)
- FR-004 Portfolio Matching
- FR-005 Application Strategy (pursuit posture + effort tiers)
- FR-006 CV Generation (deterministic plan + optional OpenAI summary rewrite)
- M1 Opportunity persistence (`OpportunityService`, `opp_<ULID>`, immutable artefacts)
- M2 Owner decision & outcome logging (FR-013 Phase 2 subset)
- M3 CSV operational bridge (export + one-time legacy import; structured store = SoT)
- M4 Ranked comparison of open opportunities
- M4a Grounded title/company identity
- M5 Close-out validation

### Decision loop

```
FR-001 Career Profile
        ↓
FR-002 Job Analysis
        ↓
        ├─→ FR-003 Opportunity Assessment
        └─→ FR-004 Portfolio Matching
                  ↓
        FR-005 Application Strategy
                  ↓
        FR-006 CV Generation (optional)
                  ↓
        M1 Persist opportunity (--persist)
                  ↓
        M2 Owner decision / outcome
                  ↓
        M4 Ranked comparison (open opportunities)
```

---

## Quick start

```powershell
python -m pip install -e ".[dev]"
```

Set `OPENAI_API_KEY` for live Job Analysis and Opportunity Assessment.

```powershell
# Profile
cic profile validate
cic profile summary

# FR-001→FR-005 (+ optional --persist)
python scripts/run_application_strategy_manual.py --job-file path/to/real_job.txt --persist

# Decisions, ranking, CSV
cic opportunity list
cic opportunity decide <opp_id> apply|skip|defer
cic opportunity compare
cic opportunity export-csv

# FR-006 CV (see docs/eval/fr006_manual_validation.md)
python scripts/run_cv_generation_manual.py --job-file path/to/real_job.txt

# Tests
python -m pytest
```

Details: [docs/08_implementation_notes.md](docs/08_implementation_notes.md).

---

## Repository Structure

| Path | Purpose |
|------|---------|
| `docs/` | Product and engineering documentation |
| `docs/assets/` | Architecture and verification overview images |
| `docs/adr/` | Architecture decision records |
| `docs/eval/` | Manual eval and release reports |
| `src/` | Python implementation |
| `tests/` | Unit, functional, and golden journey tests |
| `scripts/` | Owner / developer manual validation runners |
| `data/` | Career profile and opportunities store (SoT) |
| `applications/` | Live job search — applications, network, company notes |
| `career-documents/` | Career artefacts (e.g. Master CV, generated CVs) |
| `templates/` | Message and document templates (placeholders) |
| `metrics/` | Review and analytics placeholders |
| `tools/` | Engineering evaluation harnesses (not product CLIs) |
| `manual_validation/` | Real job texts, outputs, and owner notes |
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
- [docs/07_testing_strategy.md](docs/07_testing_strategy.md) — testing strategy
- [AGENTS.md](AGENTS.md) — agent behaviour

**Supporting:**

- [docs/01_executive_summary.md](docs/01_executive_summary.md)
- [docs/02_problem_statement.md](docs/02_problem_statement.md)
- [docs/08_implementation_notes.md](docs/08_implementation_notes.md)
- [docs/12_phase_history.md](docs/12_phase_history.md) — completed phase narratives
- [docs/eval/phase2_release_report.md](docs/eval/phase2_release_report.md) — Phase 2 GO
- [docs/11_changelog.md](docs/11_changelog.md)

---

## Guiding Principles

- Intelligence before automation; human review for consequential outputs
- Evidence-driven decisions; no invented precision
- Dual-value: improve interview/offer odds **or** reduce search effort
- Operational continuity with `applications/` (structured store + CSV bridge)
- Production-quality engineering; modular public service boundaries

Full invariants: [docs/05_engineering_principles.md](docs/05_engineering_principles.md).
