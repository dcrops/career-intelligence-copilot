# Career Intelligence Copilot

## Overview

Career Intelligence Copilot is an AI-powered **decision-support** system for job
search — helping AI Engineers secure suitable roles sooner while reducing repetitive
analysis and tracking work.

It is **not** an unsupervised application-automation bot. Recommendations require
human review; the system must never silently submit applications or send outreach.

**Horizon 1 (current priority):** Help the owner identify and submit strong,
reviewed applications as quickly and reliably as possible.

- **Horizon 1A (complete):** Job application workflow — acquire → assess → prepare →
  review → submit → track (FR-008–FR-017 frozen)
- **Horizon 1B (current):** Scaled acquisition and market engagement —
  **FR-018 complete**; **FR-019 Core Loop Operationalisation** current (M0 GO;
  M1 ready); after FR-019: Submission Automation investigation, then Recruiter
  Intelligence (**FR-020+**, deferred); Horizon 1B range FR-018–FR-026;
  application loop usable; **not** gated on FR-017

**Principle:** Job acquisition first. Recruiter outreach second. After 1A, scale
lawful opportunity inflow (**FR-018 frozen**) and operationalise the daily apply
loop (**FR-019**) before recruiter CRM.

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
| Engineering Learning Academy source | [docs/masterclass/README.md](docs/masterclass/README.md) · [FR-016](docs/masterclass/FR016/) · [FR-017](docs/masterclass/FR017/) · [Interview Brief](docs/masterclass/INTERVIEW_BRIEF_STANDARD.md) · [Interview Deck](docs/masterclass/INTERVIEW_DECK_STANDARD.md) |

---

## Current Status

**Phase 2 Job Intelligence — Complete** (M5 GO —
[docs/eval/phase2_release_report.md](docs/eval/phase2_release_report.md)).

**Complete (owner-sequenced):** FR-006 CV Generation (incl. FR-006b/c);
FR-007 Cover Letter ([eval](docs/eval/fr007_cover_letter.md)).

**Horizon 1A progress:** **FR-008 complete** and frozen
([eval](docs/eval/fr008_workflow_orchestration.md);
[ADR-003](docs/adr/003_application_workflow_orchestration.md)).
**FR-009 Opportunity Review Queue & Ranking — complete** and frozen
([acceptance](docs/eval/fr009_opportunity_review_queue.md);
[ADR-004](docs/adr/004_opportunity_review_boundary.md); milestones
[M0](docs/eval/fr009_m0_domain_contracts.md),
[M1](docs/eval/fr009_m1_persistence_boundary.md),
[M2](docs/eval/fr009_m2_owner_review_actions.md),
[M3](docs/eval/fr009_m3_duplicate_detection.md),
[M4](docs/eval/fr009_m4_recommendations.md)).
Every analysed job persists before owner review, duplicates are **linked, never merged**,
and recommendations are **derived, deterministic, and advisory** — the owner always
decides.
**FR-010 Application Package Preparation — complete** and frozen
([acceptance](docs/eval/fr010_application_package.md); milestones
[M0](docs/eval/fr010_m0_application_package.md),
[M1](docs/eval/fr010_m1_package_durability.md),
[M2](docs/eval/fr010_m2_owner_cli.md)).

**FR-011 Application Preparation Orchestration — complete** and frozen
([acceptance](docs/eval/fr011_application_preparation.md); milestones
[M0](docs/eval/fr011_m0_application_preparation.md),
[M1](docs/eval/fr011_m1_executable_preparation.md)).

**FR-012 Submission Assistance — complete** and frozen
([acceptance](docs/eval/fr012_submission_assistance.md); milestones
[M0](docs/eval/fr012_m0_submission_contracts.md),
[M1](docs/eval/fr012_m1_submission_orchestration.md),
[M2](docs/eval/fr012_m2_owner_workflow.md)).

**FR-013 Application Pipeline Tracking — complete** and frozen
([acceptance](docs/eval/fr013_application_pipeline_tracking.md);
[ADR-005](docs/adr/005_application_pipeline_lifecycle.md); milestones
[M0](docs/eval/fr013_m0_engineering_spike.md)–[M4](docs/eval/fr013_m4_reporting_acceptance.md)).

**FR-014 Recruiter Document Truth Validation — complete** and frozen
([acceptance](docs/eval/fr014_recruiter_document_truth_validation.md);
[ADR-006](docs/adr/006_recruiter_document_truth_validation.md)).

**FR-015 Bounded Agentic Workflow — complete** and frozen
([acceptance](docs/eval/fr015_bounded_agentic_workflow.md);
[ADR-007](docs/adr/007_bounded_agentic_workflow.md); milestones
[M0](docs/eval/fr015_m0_engineering_spike.md)–[M4](docs/eval/fr015_m4_evaluation.md)).

**FR-016 Multi-Agent Orchestration — complete** and frozen (learning proof only —
**GO AS LEARNING PROOF ONLY**; prefer `cic agent run` for ordinary prep;
Engineering Learning Academy ready)
([acceptance](docs/eval/fr016_multi_agent_orchestration.md);
[educational package](docs/masterclass/FR016/);
[ADR-008](docs/adr/008_multi_agent_orchestration.md); milestones
[M0](docs/eval/fr016_m0_engineering_spike.md)–[M4](docs/eval/fr016_m4_evaluation.md)).

**FR-017** Agent Evaluation & Observability is **complete and frozen** (derive-only;
Horizon 1B **not** blocked) —
[acceptance](docs/eval/fr017_agent_evaluation_observability.md);
[package](docs/masterclass/FR017/);
[ADR-009](docs/adr/009_orchestration_evaluation_substrate.md).

**FR-018** Opportunity Discovery & Acquisition is **complete and frozen** —
[acceptance](docs/eval/fr018_opportunity_discovery_acquisition.md);
[package](docs/masterclass/FR018/);
[ADR-010](docs/adr/010_opportunity_discovery_ingress.md).

**Document Quality Remediation:** **COMPLETE**
([docs/eval/document_quality_remediation.md](docs/eval/document_quality_remediation.md)).

**Next engineering work:** **Application Assistance**, resuming from AAS-0
([docs/spikes/application_assistance_aas0.md](docs/spikes/application_assistance_aas0.md)).
Do not restart Playwright from scratch. Do not prioritise Indeed ingestion
ahead of AAS.

**FR-019 Core Loop Operationalisation** remains in progress (M0 Accepted / GO;
M1 ready —
[docs/eval/fr019_core_loop_operationalisation.md](docs/eval/fr019_core_loop_operationalisation.md)).
Horizon 1A and FR-018 frozen. Details: [docs/10_roadmap.md](docs/10_roadmap.md).
Changelog § 1.136.

Acquisition today: paste or local export file via
`scripts/run_fr008_workflow_manual.py` (`--source paste|export`), owner SEEK
URLs via `cic opportunity discover`, and job-alert `.eml` via
`cic opportunity discover-email` (email discovers; URL enrich supplies full ads
when alerts are card-only). Automatic Yahoo mailbox intake is **FR-019 M1**.
Playwright deferred to later FRs.

**Thereafter — after FR-019:** Submission Automation investigation → Recruiter /
meetup / LinkedIn engagement (**FR-020–FR-026**). AAS-0 is the existing spike
toward assisted application filling and is the immediate next engineering work.

### Phase 2 + document generation (baseline — frozen)

- FR-001 Career Profile
- FR-002 Job Analysis
- FR-003 Opportunity Assessment (Technical / Commercial / Portfolio Fit)
- FR-004 Portfolio Matching
- FR-005 Application Strategy (pursuit posture + effort tiers)
- FR-006 CV Generation (deterministic plan + optional OpenAI summary rewrite)
- FR-007 Cover Letter Generation
- Render-only HTML/PDF refresh from edited Markdown (`scripts/render_document.py`)
- M1 Opportunity persistence (`OpportunityService`, `opp_<ULID>`, immutable artefacts)
- M2 Owner decision & outcome logging (Phase 2; historically FR-013 subset; foundation for FR-013)
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

# FR-010 application packages (after apply)
cic package prepare <opp_id> --approve [--override-material-benefit]
cic package show <opp_id>
cic package verify <opp_id>

# FR-011 preparation orchestration (after apply)
cic preparation run <opp_id> --approve [--override-material-benefit]
cic preparation show <run_id>

# FR-015 BOPA (post-acquisition readiness; does not submit or advance pipeline)
cic agent run <opp_id> --approve [--override-material-benefit]
cic agent show <run_id>
cic agent history <run_id>
cic agent resume <run_id> --approve [--override-material-benefit]
# status=awaiting_owner → resume; status=failed → start a new run (not resume)
# material_benefit_required → add --override-material-benefit when appropriate

# FR-016 multi-agent learning proof (optional; not preferred daily prep)
cic agent orchestrate run <opp_id> --goal brief|prepare|prepare_then_brief --approve
cic agent orchestrate show <orchestration_run_id>
cic agent orchestrate resume <orchestration_run_id> --approve
cic agent orchestrate history <orchestration_run_id>
cic agent orchestrate list
cic agent orchestrate check-delegation <opp_id> --goal brief --target bopa

# FR-012 assisted submission (after package ready)
cic submission check <opp_id>
cic submission run <opp_id> --channel manual_assisted --approve-submit --destination URL
cic submission run <opp_id> --channel fake --approve-submit --destination URL
cic submission record-manual <opp_id> --approve-submit --attestation "…" --destination URL
cic submission show <attempt_id>
cic submission list

# FR-006 CV (see docs/eval/fr006_manual_validation.md)
python scripts/run_cv_generation_manual.py --job-file path/to/real_job.txt

# FR-009 review queue, duplicates, recommendations (read-only against the live store)
python scripts/run_fr009_review_queue_manual.py queue
python scripts/run_fr009_duplicate_review_manual.py candidates --opportunities data/opportunities
python scripts/run_fr009_recommendations_manual.py recommend --opportunities data/opportunities

# FR-010 manual validation
python scripts/run_fr010_application_package_manual.py cli --workspace data/_fr010_m2_manual

# FR-011 preparation orchestration manual validation
python scripts/run_fr011_preparation_manual.py cli --workspace data/_fr011_m1_manual

# FR-012 submission manual validation
python scripts/run_fr012_submission_manual.py cli --workspace data/_fr012_m2_manual

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
| `scripts/` | Owner / developer manual validation runners; `render_document.py` is render-only |
| `data/` | Career profile and opportunities store (SoT) |
| `applications/` | Live job search — applications, network, company notes |
| `career-documents/` | Career artefacts (Master CV, generated CVs / cover letters) |
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
