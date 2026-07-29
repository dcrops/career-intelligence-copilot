# FR-008 — Job Acquisition & Workflow Orchestration

**Status:** **Complete** — documentation frozen  
**Date:** 2026-07-29  
**ADR:** [ADR-003](../adr/003_application_workflow_orchestration.md) (Accepted)  
**Recommendation:** **GO** (engineering)

## Objectives

Coordinate job acquisition through FR-002–FR-005, mandatory owner review, and
controlled Opportunity persistence on apply — without unsupervised submission,
job-board scraping, or a framework commitment before evidence.

## Implementation summary

| Milestone | Delivered |
|-----------|-----------|
| M0 | Typed `WorkflowState`, node protocol, events, checkpoint store protocol |
| M1 | Thin `ApplicationWorkflowRunner`; paste acquire; owner interrupt; JSON resume |
| M2 | Apply → persist Opportunity + record decision; skip/defer without persist; idempotent reclaim |
| M3 | Recoverable vs unrecoverable failures; bounded retries; checkpointed attempt budget |
| Closure | `AcquisitionAdapter` abstraction; paste + local-export adapters |

Package: `career_intelligence.orchestration`.

## Architecture

- **Runtime:** thin in-repository runner ([ADR-003](../adr/003_application_workflow_orchestration.md))
- **Checkpoints:** `CheckpointStore` / JSON under `data/workflow_runs/` (not Opportunity SoT)
- **Opportunity SoT:** unchanged ([ADR-002](../adr/002_opportunity_persistence.md))
- **Acquisition:** `AcquisitionAdapter` → `AcquisitionResult` → `AcquireNode` → shared graph

### Final workflow

```
Acquire → Validate → Analyse → Assess → Match → Strategy → Owner Review
                                                              │
                         Apply → Persist → Record Decision → Complete
                         Skip / Defer → Complete
```

### Supported acquisition methods

| Adapter | `source_kind` | Notes |
|---------|---------------|--------|
| `PasteAcquisitionAdapter` / `PasteJobInput` | `paste` | Manual / pasted text |
| `LocalFileAcquisitionAdapter` | `export` | UTF-8 local job export file |

## Manual validation

Script: `scripts/run_fr008_workflow_manual.py`

### Validation performed

| Step | Result |
|------|--------|
| Acquire (paste) | ✓ |
| Acquire (local export) | ✓ |
| Validate / normalise | ✓ |
| Analyse (FR-002) | ✓ |
| Assess (FR-003) | ✓ |
| Portfolio Match (FR-004) | ✓ |
| Application Strategy (FR-005) | ✓ |
| Pause (owner review checkpoint) | ✓ |
| Resume (apply) | ✓ |
| Persist Opportunity | ✓ |
| Record decision | ✓ |
| Complete | ✓ |
| Skip / defer (no Opportunity) | ✓ |
| Bounded retry injection (engineering) | ✓ |

### Outcome

**PASS**

### Observations

- Completed nodes were not re-executed on resume
- Checkpoint resume preserved `run_id` and artefacts
- Owner approval gate behaved correctly (no default apply)
- Opportunity persisted exactly once under repeated resume
- Paste and export shared the same post-acquire graph; provenance differed only on
  `AcquisitionEnvelope`
- Workflow completed successfully to terminal `completed` after apply

### Repeatable commands

```bash
python scripts/run_fr008_workflow_manual.py start --source paste \
  --job-file path/to/job.txt --offline-fixtures
python scripts/run_fr008_workflow_manual.py start --source export \
  --job-file path/to/job.txt --offline-fixtures
python scripts/run_fr008_workflow_manual.py resume --run-id wfr_... \
  --decision apply --offline-fixtures
```

## Unit testing

Under `tests/unit/orchestration/`: runner, routing, checkpoint stores, persistence,
decision recording, resume/skip/defer, retries, acquisition adapters.

## Functional testing

- `test_fr008_job_acquisition.py` — paste + export provenance
- `test_fr008_workflow_execution.py` — golden path to owner review
- `test_fr008_checkpoint_resume.py` — apply/skip/idempotent resume
- `test_fr008_failure_recovery.py` — retry / exhaustion / M2 regression

Full repository suite green at freeze (886+ tests; no FR-008 regressions).

## Failure recovery, checkpoints, retries

- Recoverable failures on `analyse` / `assess` only (default max 3 attempts)
- Unknown / validation failures fail closed
- Attempt counts survive process restart via checkpoints
- Exhaustion → terminal `failed`; no Opportunity created

## Idempotency evidence

Pre-allocate `opportunity_id`, checkpoint, then `create_from_strategy(opportunity_id=…)`.
Repeated resume does not duplicate Opportunities.

## Limitations (by design)

- No live URL/API/email/Playwright adapters
- No FR-009 deduplication or ranking
- No FR-010/011 package generation or submission
- No FR-013+ agents
- Post-approval persist/record use M2 resumable pause (not M3 auto-retry policy)

## Engineering spike conclusions

### Successful

- Deterministic orchestration proved sufficient for FR-008 scope
- Checkpoint / resume works well for single-user interactive runs
- Orchestration stayed separated from FR-001–FR-007 business logic
- Human approval integrates naturally as a first-class interrupt
- Persistence isolated from analysis in dedicated nodes
- Idempotent Opportunity create closed crash windows without a second SoT
- Acquisition adapter boundary keeps the runner source-agnostic
- Thin in-repo runner justified deferring LangGraph ([ADR-003](../adr/003_application_workflow_orchestration.md))

### Deferred (until justified)

Do **not** treat the following as FR-008 follow-on by default:

| Deferred | Rationale |
|----------|-----------|
| LangGraph / external workflow engines | No evidence they are required yet (ADR-003) |
| Distributed / queue-based orchestration | Single-user phase; JSON checkpoints suffice |
| Playwright acquisition | Controlled fallback only; not needed to close FR-008 |
| URL / API / email adapters | Boundary exists; implement when a real source is chosen |
| Automated application submission | Horizon 1A later (FR-011); always requires owner approval |
| Broader retry frameworks | M3 bounded analyse/assess retries are enough for now |

## Lessons learned

1. Validate architecture with a thin runner before adding framework complexity
2. Isolate side effects (persist / decide) from analysis nodes
3. Make persistence idempotent before depending on resume
4. Separate orchestration from domain services (public APIs only)
5. Human approval is part of the workflow, not an exception
6. Deterministic orchestration can scale surprisingly far before specialised engines
7. Fail closed on unknown and validation errors; retry only what is explicitly recoverable
8. Keep Opportunity SoT separate from workflow-run checkpoints

## GO / NO-GO assessment

| Area | Result | Notes |
|------|--------|-------|
| Implementation | **PASS** | Adapter acquisition through terminal apply/skip/defer delivered |
| Testing | **PASS** | Unit + functional coverage for graph, resume, persist, retries |
| Manual validation | **PASS** | Full path exercised; Opportunity once; gate correct |
| Documentation | **PASS** | Spec, roadmap, changelog, notes, testing, ADR-003, this report |
| Architecture | **PASS** | Thin runner; clear boundaries; ADR-003 accepted |

### Recommendation

**GO**

FR-008 is complete and frozen. Proceed to **FR-009** (deduplication / review queue /
ranking) only on explicit owner request. Do not reopen FR-008 scope without cause.
