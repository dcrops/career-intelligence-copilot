# Testing Strategy

## Purpose

This document is the authoritative testing reference for implementation work in the Career
Intelligence Copilot. It defines which behaviours each test layer protects and how the suite
grows as the product evolves (Phase 2 baseline is complete; further suites track
Horizon 1A workflow, acquisition adapters, and orchestration learning).

Requirements remain authoritative in [04_functional_specification.md](04_functional_specification.md).
Engineering tradeoffs remain authoritative in
[05_engineering_principles.md](05_engineering_principles.md).

---

## Principles

- Protect decision quality before pursuing coverage targets.
- Test public product behaviour independently from implementation details.
- Ground important journeys in real-shaped career and opportunity data.
- Keep fixtures deterministic, reviewable, and free of secrets or recruiter personal data.
- Add regression coverage when a defect could change a recommendation or interrupt the
  owner's workflow.

Coverage is diagnostic information, not a completion criterion. A high percentage cannot
compensate for an untested decision path.

---

## Unit Tests

Unit tests protect implementation correctness within a module or stage boundary.

Examples include domain validation, serialization, error translation, and persistence
round-trips. Unit tests may import internal modules. They may be revised during refactoring
when public behaviour is preserved.

Unit tests live under `tests/unit/`, grouped by capability
(including `tests/unit/opportunities/` for M1–M3 persistence, decisions, and CSV
bridge, and `tests/unit/opportunity_comparison/` for M4 ranking).

---

## Functional Tests

Functional tests protect product behaviour and map directly to functional requirements and
acceptance criteria. They exercise only the public interface of the capability under test.

A functional test should fail when the requirement regresses, even if all underlying units
still work independently. Internal refactoring should not require changing a functional test
when public behaviour is unchanged.

Functional tests live under `tests/functional/` and follow the naming convention
`test_fr00N_acceptance.py`.

---

## Golden User Journeys

Golden user journeys protect complete, owner-facing workflows using stable, real-shaped
fixtures. They validate that individually correct components still work together in a useful
sequence.

Golden fixtures are derived from real career artifacts or job postings, then made deterministic
and stripped of unnecessary sensitive information. They are reviewed inputs, not snapshots of
opaque model output.

Golden journeys live under `tests/golden/`; their shared fixtures live under
`tests/fixtures/golden/`.

---

## Regression Philosophy

The suite prioritises decision regression over code coverage. Golden cases should grow from
roles and workflows that matter during the active search. A visibly wrong assessment on a
cared-about role is a product failure even if isolated code coverage is high.

When fixing a defect:

1. Add the narrowest unit test that identifies the implementation fault.
2. Add or strengthen a functional or golden regression when the fault affected observable
   product behaviour.
3. Keep the evidence and expected behaviour explicit so future changes can be reviewed.

Tests must be deterministic and run without network access.

---

## Extending the Suite for Future Requirements

Each future functional requirement adds:

- focused unit tests under `tests/unit/`;
- `tests/functional/test_fr00N_acceptance.py` for its public acceptance criteria; and
- a golden journey when it introduces or materially changes an owner-facing workflow.

Future requirements reuse `tests/fixtures/golden/career_profile.yaml` as the shared candidate
profile. Additional candidate profiles are created only to isolate a specific edge case.
Opportunity fixtures should come from real postings where practical and must omit unnecessary
personal data.

Tests spanning FR-002 and later must obtain the career profile through
`career_intelligence.profile`, never through the YAML storage adapter. This preserves the public
service boundary and keeps regression tests valid if storage changes.

---

## FR-003 Opportunity Assessment coverage

FR-003 adds:

- unit tests under `tests/unit/opportunity_assessment/` (models, service, fixtures,
  OpenAI assessor with fake client);
- `tests/functional/test_fr003_acceptance.py` for the public service contract; and
- `tests/golden/test_opportunity_assessment_user_journey.py` for the offline
  CareerProfile → JobAnalysis → OpportunityAssessment journey.

Shared fixture markers in `job_analysis` link deterministic extraction to deterministic
assessment. Live OpenAI evaluation is manual only
([eval/fr003_openai_manual_eval.md](eval/fr003_openai_manual_eval.md)) and must not run in CI.

---

## FR-004 Portfolio Matching coverage

FR-004 adds:

- unit tests under `tests/unit/portfolio_matching/` (models, service, refs,
  DeterministicMatcher, FixtureMatcher, golden-profile scenarios);
- `tests/functional/test_fr004_acceptance.py` for the public service contract; and
- `tests/golden/test_portfolio_matching_user_journey.py` for the offline
  CareerProfile → JobAnalysis → PortfolioMatch journey.

Product-behaviour assertions prefer `DeterministicMatcher`. `FixtureMatcher` is used for
service-composition isolation (including an explicit tie-contract marker). Shared FR-002
fixture markers link extraction to fixture matching. FR-004 does not require
OpportunityAssessment and must not emit Apply/Skip, tiers, CV strategy, or
`portfolio_fit` fields.

---

## FR-005 Application Strategy coverage

FR-005 adds:

- unit tests under `tests/unit/application_strategy/` (models, context, refs, service,
  DeterministicStrategyPlanner, FixtureStrategyPlanner);
- `tests/functional/test_fr005_acceptance.py` for the public service contract and
  production policy acceptance scenarios; and
- `tests/golden/test_application_strategy_user_journey.py` for offline
  CareerProfile → JobAnalysis → OpportunityAssessment → PortfolioMatch →
  ApplicationStrategy journeys.

Product-behaviour assertions prefer `DeterministicStrategyPlanner`.
`FixtureStrategyPlanner` is used for service-composition isolation and predictable
contract output, keyed to shared FR-002 markers (plus a small set of strategy-only
markers). FR-005 does not require OpenAI, must not emit CV/cover-letter content or
autonomous apply decisions, and must keep `owner_review_required=True`.

Seniority-aware stretch policy is covered in
`tests/unit/application_strategy/test_seniority_mismatch.py` (cap vs unlock, salary-only
mixed, unknown seniority, independent engineering vs employment, non-AI senior roles).

---

## FR-006 CV Generation coverage

FR-006 is **complete**. Coverage includes:

- unit tests under `tests/unit/cv_generation/` (planner, generation service, fidelity,
  Phase C rewriter/validation/runtime prep, corpus regression);
- golden profile journey assertions for experience and skill boundaries; and
- owner manual validation via `scripts/run_cv_generation_manual.py`
  ([eval/fr006_manual_validation.md](eval/fr006_manual_validation.md)).

Phase C OpenAI calls are opt-in (`--rewrite-summary`) and fail-soft. Automated tests
use `FixtureSummaryRewriter` and fake OpenAI clients — no network in CI.

---

## FR-006b CV Quality — Golden Validation Suite

FR-006b improves **submit preference** against the Master CV. Automated tests still
guard contracts and fidelity; qualitative regressions use a fixed job set:

- Suite definition: [eval/fr006b_cv_quality_golden_suite.md](eval/fr006b_cv_quality_golden_suite.md)
- Quality findings (pre-implementation): [eval/fr006b_cv_quality_findings.md](eval/fr006b_cv_quality_findings.md)
- P0 validation report: [eval/fr006b_cv_quality_validation.md](eval/fr006b_cv_quality_validation.md)

Do **not** freeze full CV prose as exact snapshots. Re-run G1–G5 via
`scripts/run_fr006b_golden_suite.py` and score human preference when changing
planner emphasis, summary rewrite, Markdown render, or Career Profile
methodology/highlights content.

---

## FR-007 Cover Letter coverage

FR-007 is **complete** (owner manual validation passed). Coverage includes:

- unit tests under `tests/unit/cover_letter/` (gates, evidence-based selection,
  composition / AI-boilerplate refusal, signature, draft writer Markdown+HTML,
  determinism);
- fidelity checks that company, role, and planned portfolio projects appear; and
- owner manual validation via `scripts/run_cover_letter_manual.py`
  ([eval/fr007_cover_letter.md](eval/fr007_cover_letter.md)).

Default path is fully deterministic (no OpenAI). Owner review remains mandatory.

---

## FR-008 Orchestration coverage (complete — frozen)

FR-008 is **complete**. Acceptance:
[docs/eval/fr008_workflow_orchestration.md](eval/fr008_workflow_orchestration.md).
ADR-003 accepted. FR-009 coverage is likewise complete and frozen. **FR-010**
package preparation coverage is complete and frozen — see below. FR-008 suites were
updated where FR-009 M1 deliberately changed behaviour — skip and defer now retain a
durable Opportunity, and `persist` completes before owner review.

### What FR-008 validates

#### Unit tests (`tests/unit/orchestration/`)

| Area | Coverage |
|------|----------|
| Runner | start → owner review; cancel; invalid resume fail-closed |
| Routing | deterministic node order; completed-node skip |
| Checkpoint store | in-memory + JSON round-trip; corrupt/missing fail-closed |
| Persistence | one Opportunity per run; planned-id reclaim |
| Decision recording | owner decision via boundary translation |
| Resume | terminal idempotent reload; mid-decision recovery |
| Skip / defer | complete with the decision recorded on the existing record (FR-009 M1) |
| Retries | classification; policy; exhaustion; cross-process budget |
| Acquisition | paste + local-export adapters; source-agnostic node order |

#### Functional tests (`tests/functional/test_fr008_*.py`)

| Suite | Validates |
|-------|-----------|
| Job acquisition | Paste + export provenance; shared graph |
| Workflow execution | End-to-end to owner review |
| Checkpoint resume | Pre-review persist + decision; repeated resume; skip retained; invalid resume |
| Failure recovery | Retry / exhaustion / unrecoverable / M2 regression |

#### Manual validation (`scripts/run_fr008_workflow_manual.py`)

| Check | Result |
|-------|--------|
| Acquire (paste / export) | ✓ |
| Analyse → Assess → Match → Strategy | ✓ |
| Pause at owner review | ✓ |
| Resume apply | ✓ |
| Persist Opportunity + record decision | ✓ |
| Terminal complete | ✓ |
| Skip / defer paths | ✓ (automated + manual) |

Milestone file map (historical): M0 contracts; M1 runner; M2 persist; M3 retries;
acquisition foundation. See changelog 1.48–1.53.

Playwright / URL / API adapters remain deferred.

---

## FR-009 coverage (complete — frozen)

FR-009 is **complete** and its documentation is frozen. M0–M4 are delivered: contracts,
pre-review persistence with a derived projection, owner review actions, duplicate
detection and confirmation, and quality-first ranking calibration with explainable
recommendations. Full suite at freeze: **1019 passed**. Acceptance:
[eval/fr009_opportunity_review_queue.md](eval/fr009_opportunity_review_queue.md);
milestone records
[eval/fr009_m0_domain_contracts.md](eval/fr009_m0_domain_contracts.md),
[eval/fr009_m1_persistence_boundary.md](eval/fr009_m1_persistence_boundary.md),
[eval/fr009_m2_owner_review_actions.md](eval/fr009_m2_owner_review_actions.md),
[eval/fr009_m3_duplicate_detection.md](eval/fr009_m3_duplicate_detection.md),
[eval/fr009_m4_recommendations.md](eval/fr009_m4_recommendations.md);
architecture [ADR-004](adr/004_opportunity_review_boundary.md).

### M0 contract tests (`tests/unit/opportunities/test_m0_review_contracts.py`)

| Area | Coverage |
|------|----------|
| Pre-decision persistence | An Opportunity is durable and reloadable with `decision=None` |
| Deterministic defaults | New records get `reviewed_at=None`, `pinned=False`, `defer_until=None`, `archived_at=None`, `duplicate=None` |
| Backward compatibility | Apply-only index rows without review keys still deserialise |
| Round-trip | Review metadata and duplicate relation survive a YAML store round-trip |
| Invalid combinations | Self-referencing duplicate rejected; archived record cannot stay pinned |
| Orthogonality | Review updates leave identity, `strategy_summary`, artefacts, decision, and status untouched |
| Frozen M4 baseline | Review metadata does not change M4 order, ranks, or reasons |
| Duplicate safety | Identical content fingerprints remain independent records with no duplicate relation |

### M1 persistence-boundary tests (`tests/unit/orchestration/test_m1_pre_review_persistence.py`)

| Area | Coverage |
|------|----------|
| Pre-review durability | A reloadable Opportunity with `decision=None` exists when the run pauses |
| Checkpoint contract | State carries `opportunity_id`; no Opportunity object is serialised into the run file |
| Persistence failure | A store failure pauses the run as resumable and never reaches the interrupt or creates a record |
| Replay before interrupt | Re-executing `persist` reuses the same record and leaves artefacts unchanged |
| Crash after checkpoint | A run resumed from the checkpoint re-enters owner review with the record already present |
| Decision integration | `apply`, `skip`, and `defer` each update the same record (parametrised) |
| Decision-update failure | A failing `record_decision` prevents completion and stays resumable |
| Decision conflict | An accepted decision is never silently overwritten |
| Decision idempotency | Repeating the same decision is safe and leaves one record |

### M1 projection tests (`tests/unit/review_queue/`)

| Area | Coverage |
|------|----------|
| Eligibility policy | Undecided → awaiting; applied → active only; skipped, archived, confirmed-duplicate, and terminal-status records excluded |
| Reference date | Explicit `reference_date` decides whether a deferred record returns; undated defer holds |
| Reason stability | Multiple exclusion reasons are reported in a fixed order |
| Purity | Evaluating eligibility mutates nothing; querying the queue writes nothing |
| Ordering | Matches the frozen M4 baseline; equal signals fall back to stable id order |
| Backward compatibility | Records written before review metadata still project |

### M1 functional journeys (`tests/functional/test_fr009_review_queue.py`)

| Journey | Coverage |
|---------|----------|
| Apply | Record exists before review; resume updates it; exactly one record |
| Skip | Record retained with the skip decision and excluded from the default queue |
| Defer | Record retained with the defer decision and excluded from the default queue |
| Lost checkpoint | Re-running after the run file is discarded creates no duplicate record |
| Deterministic order | Several analysed jobs queue in a stable, explainable order |

These run against the real YAML/JSON stores in `tmp_path`, not mocks.

#### Manual validation (`scripts/run_fr009_review_queue_manual.py`)

| Check | Result |
|-------|--------|
| Several analysed jobs persist before any decision | ✓ |
| Deterministic review order with readable reasons | ✓ |
| Apply / skip / defer update the existing record | ✓ |
| Skip and defer leave the queue without deleting data | ✓ |
| Replaying a completed run creates no duplicate | ✓ |
| Live `data/opportunities/` projects read-only, unmigrated | ✓ |

### M2 owner-action tests (`tests/unit/opportunities/test_m2_review_actions.py`)

| Area | Coverage |
|------|----------|
| Mark reviewed | Sets `reviewed_at` without creating a decision; repeat preserves original |
| Pin / unpin | Reversible; pin rejected while archived; archive auto-clears pin |
| Timed defer | Past dates rejected; same-day expires; clear_defer → undecided |
| Archive / reopen | Reversible; reopen leaves skip/decision/reviewed intact |
| Aggregate integrity | Actions preserve decision, status, outcome, artefacts, ranking inputs |
| Audit history | Appends on mutate; empty default for legacy rows; YAML round-trip |
| Pin projection | Weak pinned record sorts first with `"Pinned by owner"`; unpin restores M4 |

### M2 functional journeys (`tests/functional/test_fr009_owner_review_actions.py`)

| Journey | Coverage |
|---------|----------|
| Mark reviewed | Stays awaiting; artefacts unchanged on disk |
| Pin / unpin | Presentation order override then M4 restore |
| Defer / clear / expiry | Hide, return on date to active, clear → awaiting |
| Archive / reopen | Visibility only; skip still excludes after reopen |
| Mixed state | Reviewed undecided + pinned coexist in awaiting |

#### Manual validation (`scripts/run_fr009_owner_review_manual.py`)

| Check | Result |
|-------|--------|
| Reviewed undecided stays awaiting | ✓ |
| Pin raises then unpin restores M4 order | ✓ |
| Timed defer hides; expiry returns to active; clear_defer restores awaiting | ✓ |
| Archive hides; reopen restores | ✓ |
| Idempotent repeats; no second Opportunity; status unchanged | ✓ |

### M3 duplicate detection tests (`tests/unit/duplicates/`)

| Area | Coverage |
|------|----------|
| Confidence tiers | Platform + job id and canonical/source URL → `definite`; company + title + corroboration → `probable`; single cluster → `possible` |
| Fingerprint safety | Identical description text alone never exceeds `possible` |
| Unknown vs match | Facets absent on either side are `unknown`; `manual` / `import` source kinds are not platform evidence |
| Normalisation | Legal-entity suffixes and bracketed title asides collapse; genuinely different names do not |
| Determinism | Scan order does not change candidates, pair order, or confidence order |
| Resolved pairs | Confirmed links, same-group members, and rejected pairs are never re-suggested |
| Canonical policy | Artefacts → non-recruiter → platform rank → completeness → earliest discovery → id |
| Group projection | Groups derive from `duplicate_of` only; a lone record forms no group |
| Read-only | Candidate and group queries leave `index.yaml` byte-identical |
| Backward compatibility | Rows written before `duplicate_rejections` existed still project |

### M3 owner-action tests (`tests/unit/opportunities/test_m3_duplicate_actions.py`)

| Area | Coverage |
|------|----------|
| Confirm | Links without deleting either record; canonical untouched; idempotent with original `confirmed_at` |
| Invalid links | Self-reference, chains, and re-pointing an existing canonical raise typed errors |
| Reject | Symmetric on both records; idempotent; cannot contradict a confirmed link, and vice versa |
| Canonical change | Whole group re-points; chosen record's relation cleared; all records survive |
| Aggregate integrity | Decision, status, outcome, artefacts, identity, and review metadata preserved |
| Audit | One `ReviewActionRecord` per real change; no entry on a no-op |
| Projection | Confirmed member excluded as `confirmed_duplicate`; canonical stays in the queue |

### M3 functional journeys (`tests/functional/test_fr009_duplicate_review.py`)

| Journey | Coverage |
|---------|----------|
| Cross-platform duplicate | Suggested with evidence, confirmed, group formed, both artefact sets intact on disk |
| Rejection | Repeated scans never re-suggest; both records stay independently reviewable |
| Unresolved | Stable across scans; neither record leaves the decision queue |
| Canonical change | Owner picks a different canonical; nothing deleted; recommendation then matches |
| Interrupted re-point | A partial star converges to one consistent group when the action is replayed |
| Idempotency | Repeating every action leaves state, timestamps, and audit trail unchanged |
| Reload | Duplicate state and artefacts survive a fresh service instance |

#### Manual validation (`scripts/run_fr009_duplicate_review_manual.py`)

| Check | Result |
|-------|--------|
| Same vacancy acquired twice is suggested as `probable` with matching/differing evidence | ✓ |
| Unrelated vacancy is not suggested | ✓ |
| Unresolved candidates repeat identically and hide nothing | ✓ |
| Confirmation links records; 3 of 3 records preserved with artefacts | ✓ |
| Canonical recommendation is advisory; owner confirms a different canonical | ✓ |
| Rejected pair never returns | ✓ |
| Repeated actions change nothing; audit trail readable | ✓ |
| Live `data/opportunities/` scan is read-only and surfaces only `possible` fingerprint collisions | ✓ |

### M4 recommendation tests (`tests/unit/recommendations/`, comparison calibration)

| Area | Coverage |
|------|----------|
| Calibrated order | Posture → fit → practical value → id; effort tier cannot outrank value |
| Unknown fit | Contributes 0; does not inflate strength |
| Wording | Applied + assessed does not claim awaiting owner action |
| Recommendations | Quality order, replay, pin, duplicates, next actions, urgency from follow-up |
| Read-only | Index unchanged; review state unchanged |
| Missing data | Absent identity fields reported; no invented salary/deadline urgency |

### M4 functional journeys (`tests/functional/test_fr009_recommendations.py`)

| Journey | Coverage |
|---------|----------|
| Deterministic explained order on real artefacts | ✓ |
| Pin + duplicate interaction with recommendations | ✓ |
| Apply updates next action without mutating ranking inputs | ✓ |
| Reload idempotency | ✓ |

#### Manual validation (`scripts/run_fr009_recommendations_manual.py`)

| Check | Result |
|-------|--------|
| Quality order with structured explanations | ✓ |
| Stable replay | ✓ |
| Pin raises without changing fit | ✓ |
| Apply wording + next action | ✓ |
| Live store recommend is read-only | ✓ |

---

## M4 Ranked comparison coverage

M4 is **complete** for Phase 2 job opportunities (historically labelled “FR-012
partial”; foundation for Horizon 1A **FR-009**). Coverage includes:

- unit tests under `tests/unit/opportunity_comparison/` (sort key, open filter, reasons,
  CLI `opportunity compare`, regression-stable ordering);
- functional acceptance in `tests/functional/test_fr012_acceptance.py` (public
  `OpportunityComparisonService` boundary); and
- golden journey `tests/golden/test_opportunity_comparison_user_journey.py`
  (persist trusted FR-002–FR-005 artifacts → list → compare; excludes terminal/skip).

Ranking is offline and deterministic — no OpenAI in this capability.

---

## M4a Identity metadata coverage

M4a is **complete**. Coverage includes:

- extraction schema / service enrichment unit tests (`posting_identity`, grounded bind,
  no overwrite of caller provenance, drop ungrounded inventions);
- persistence / CLI / backfill tests under `tests/unit/opportunities/test_identity_backfill.py`;
- prompt version **v8** assertions in FR-002 extractor tests.

---

## M5 Phase 2 close-out

M5 is validation-only (no new product tests required). Evidence:
[eval/phase2_release_report.md](eval/phase2_release_report.md). Full suite must
remain green before declaring Phase 2 complete.

---

## FR-010 Application Package coverage (complete — frozen)

FR-010 is **complete**. Acceptance:
[docs/eval/fr010_application_package.md](eval/fr010_application_package.md).
It delivers a standalone composition service that prepares one current
Application Package for an Opportunity with owner decision ``apply``.

- M0: [docs/eval/fr010_m0_application_package.md](eval/fr010_m0_application_package.md)
- M1: [docs/eval/fr010_m1_package_durability.md](eval/fr010_m1_package_durability.md)
- M2: [docs/eval/fr010_m2_owner_cli.md](eval/fr010_m2_owner_cli.md)

### What M0 validates

| Area | Coverage |
|------|----------|
| Eligibility | ``apply`` succeeds; skip / defer / undecided fail closed |
| Manifest | CV + cover-letter draft refs; evidence artefact paths; acquisition provenance |
| Traceability | Package → Opportunity id → immutable FR-002–FR-005 snapshots |
| Regeneration | Replace-on-regenerate; same draft stems; upstream bytes unchanged |
| Gates | Existing FR-006 / FR-007 owner-approval gates still enforced |
| Public loader | ``OpportunityService.load_artifacts`` rehydrates strategy without YAML imports |

### What M1 validates

| Area | Coverage |
|------|----------|
| Reload / exists | Current package loads; missing package fails closed |
| Relative persistence | Manifest stores filenames; service resolves absolute paths |
| Idempotency | Same inputs + same ``prepared_at`` → identical manifest and draft bytes |
| Repeated regeneration | ``prepared_at`` updates; paths and evidence stable |
| Failure safety | Failed draft write leaves prior manifest current |
| Integrity | ``get(verify=True)`` refuses missing draft files; M0 absolute paths still load |

### What M2 validates

| Area | Coverage |
|------|----------|
| CLI prepare | Requires ``--approve``; prepare/show/verify against temp stores |
| CLI show / verify | Human summary, YAML, integrity fail-closed |
| Invalid inputs | Non-apply refused; missing package; missing draft on verify |
| Thin adapter | No duplicated FR-006/007 business logic in the CLI |

**Unit:** `tests/unit/application_package/` (incl. `test_cli.py`)  
**Functional:** `tests/functional/test_fr010_application_package.py`  
**Manual:** `scripts/run_fr010_application_package_manual.py` (`demo`, `cli`)

Does **not** cover: orchestration nodes, PipelineStatus writes, submission, versioning,
PDF/DOCX.

---

## FR-011 Application Preparation Orchestration coverage (complete — frozen)

FR-011 is **complete**. Acceptance:
[docs/eval/fr011_application_preparation.md](eval/fr011_application_preparation.md).

**Status:** M0–M1 delivered —
[M0](eval/fr011_m0_application_preparation.md),
[M1](eval/fr011_m1_executable_preparation.md).

FR-011 coordinates package preparation via a dedicated orchestrator. Tests assert
precondition fail-closed behaviour and that package rules remain in FR-010.

### What M0 validates

| Area | Coverage |
|------|----------|
| Happy path | ``validate_preconditions`` → ``prepare_package``; completed run + verifiable package |
| Non-apply | Fails closed at ``validate_preconditions`` |
| Missing artefacts / opportunity | Fails closed at validate |
| Gate failure | FR-006/007 refusal fails at ``prepare_package`` without inventing success |
| Run persistence | JSON reload of ``PreparationRunState`` |
| Boundaries | FR-008 runner and FR-010 package business rules unchanged |

### What M1 validates

| Area | Coverage |
|------|----------|
| CLI run | Requires ``--approve``; invoke orchestrator only |
| CLI show | Reload run by id; YAML optional |
| Failed run | Non-apply surfaces failed status; non-zero exit |
| Package integrity | Orchestrated package still verifiable via FR-010 |

**Unit:** `tests/unit/application_preparation/` (incl. `test_cli.py`)  
**Functional:** `tests/functional/test_fr011_application_preparation.py`  
**Manual:** `scripts/run_fr011_preparation_manual.py` (`demo`, `cli`)

Does **not** cover: submission behaviour (FR-012 M1+), PipelineStatus writes, FR-008
``prepare_package`` node wiring, resume/branching ``routing.py``, package versioning,
PDF/DOCX.

---

## FR-012 Submission Assistance coverage (complete — frozen)

FR-012 is **complete**. Acceptance:
[docs/eval/fr012_submission_assistance.md](eval/fr012_submission_assistance.md).

Milestone records:
[M0](eval/fr012_m0_submission_contracts.md),
[M1](eval/fr012_m1_submission_orchestration.md),
[M2](eval/fr012_m2_owner_workflow.md).

FR-012 delivers owner-assisted submission: contracts, deterministic orchestration,
offline adapters, and a thin owner CLI. Tests assert:

| Area | Coverage |
|------|----------|
| Models / transitions / store | Append-only identity; illegal transitions fail |
| Orchestrator gates & policy | Owner Approval; package verify; duplicate / idempotency |
| Adapters | Fake outcomes; ManualAssisted never claims submitted |
| Manual Completion | Attestation path; no adapter success claim |
| CLI | `check` / `run` / `record-manual` / `show` / `list`; exit codes |

**Unit:** `tests/unit/submission/` (incl. `test_cli.py`)
**Functional:** `tests/functional/test_fr012_submission.py`
**Manual:** `scripts/run_fr012_submission_manual.py` (`demo`, `cli`)

Does **not** cover: live boards, Playwright, PipelineStatus, FR-008 ``submit`` node,
credentials, CAPTCHA, multi-agent submit.

---

## FR-013 Application Pipeline Tracking coverage (complete — frozen)

FR-013 is **complete**. Acceptance:
[docs/eval/fr013_application_pipeline_tracking.md](eval/fr013_application_pipeline_tracking.md).

[ADR-005](adr/005_application_pipeline_lifecycle.md);
[M0](eval/fr013_m0_engineering_spike.md);
[M1](eval/fr013_m1_pipeline_contracts.md);
[M2](eval/fr013_m2_pipeline_tracking.md);
[M3](eval/fr013_m3_owner_workflow.md);
[M4](eval/fr013_m4_reporting_acceptance.md).

| Area | Coverage |
|------|----------|
| Models / store | Append-only events; transitions; evidence |
| Tracking service | Event-first dual-write; partial failure; divergence/reconcile |
| Owner CLI | `cic pipeline` natural commands; history; corrections |
| Reporting | Summary rates/counts/ageing; due; CSV export |
| Manual | `scripts/run_fr013_pipeline_manual.py demo|journey|accept` |

**Unit:** `tests/unit/pipeline/`  
**Functional:** `tests/functional/test_fr013_*.py`

Does **not** cover: FR-012 auto-advance (forbidden), dashboards, adaptive scoring.

---

## Horizon 1A — Planned test coverage (remaining)

When FR-014–FR-017 are built, prefer behaviour over implementation detail:

| Area | Expected coverage |
|------|-------------------|
| FR-008 acquisition adapters (**delivered**) | Unit tests per adapter; provenance fields; extraction warnings; no assumption that every job is browser-sourced |
| FR-008 workflow (**delivered**) | Golden workflow on a saved/manual job; conditional routing from real strategy outputs; checkpoint + resume after owner approval; recoverable node failure; node execution traces |
| FR-009 queue / duplicates (**delivered** — see FR-009 coverage above) | Deterministic ranking inputs; explainable reasons; no mutate-on-rank; derived queue position (never persisted); eligibility excludes archived / skipped / currently deferred / confirmed duplicates; pinning changes order without altering fit signals; persistence-boundary move creates exactly one Opportunity across resume and replay; platform ID / URL / fingerprint matching with owner confirmation |
| FR-010 packages (**delivered** — see FR-010 coverage above) | Composition, durability, owner CLI |
| FR-011 preparation (**delivered** — see FR-011 coverage above) | Preconditions; package coordination; fail-closed; run audit; owner CLI |
| FR-012 submission (**delivered** — see FR-012 coverage above) | Readiness; Assisted Submission; Manual Completion; append-only audit; owner CLI |
| FR-013 tracking (**delivered** — frozen) | Dual-write + owner CLI + reporting; see FR-013 coverage |
| FR-014 truth validation | Fail-closed findings for unsupported candidate claims; JD evidence ≠ candidate evidence; Redwolf-style regression |
| FR-015 agents | Max iterations, stop conditions, restricted tools, validation before state update |
| FR-016 / FR-017 | Loop prevention; fault injection; token/cost/latency where LLM-backed; browser journey evidence when Playwright is used |

**Spike rule:** First FR-008 tests use fixture/saved jobs only — not live acquisition
or real submission. Deterministic replay where possible; owner manual validation for
approval interrupts.
