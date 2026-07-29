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
ADR-003 accepted. Current coverage focus: **FR-009** (M0 contracts complete).

### What FR-008 validates

#### Unit tests (`tests/unit/orchestration/`)

| Area | Coverage |
|------|----------|
| Runner | start → owner review; cancel; invalid resume fail-closed |
| Routing | deterministic node order; completed-node skip |
| Checkpoint store | in-memory + JSON round-trip; corrupt/missing fail-closed |
| Persistence | apply creates one Opportunity; planned-id reclaim |
| Decision recording | apply decision via boundary translation |
| Resume | terminal idempotent reload; mid-apply recovery |
| Skip / defer | complete with no Opportunity |
| Retries | classification; policy; exhaustion; cross-process budget |
| Acquisition | paste + local-export adapters; source-agnostic node order |

#### Functional tests (`tests/functional/test_fr008_*.py`)

| Suite | Validates |
|-------|-----------|
| Job acquisition | Paste + export provenance; shared graph |
| Workflow execution | End-to-end to owner review |
| Checkpoint resume | Apply persist + decision; repeated resume; skip; invalid resume |
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

## FR-009 coverage (in progress — M0 contracts only)

FR-009 is **in progress**. M0 delivered domain contracts only; the queue, ranking
extensions, owner actions, and duplicate detection are not implemented, so there is no
queue behaviour to test yet. M0 acceptance:
[eval/fr009_m0_domain_contracts.md](eval/fr009_m0_domain_contracts.md);
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

Deliberately **not** covered yet (later milestones): queue eligibility and ordering (M1),
pin / defer / archive behaviour (M2), duplicate detection and confirmation (M3), manual
ranking calibration (M4).

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

## Horizon 1A — Planned test coverage (not yet implemented)

When FR-008–FR-015 are built, prefer behaviour over implementation detail:

| Area | Expected coverage |
|------|-------------------|
| FR-008 acquisition adapters | Unit tests per adapter; provenance fields; extraction warnings; no assumption that every job is browser-sourced |
| FR-008 workflow | Golden workflow on a saved/manual job; conditional routing from real strategy outputs; checkpoint + resume after owner approval; recoverable node failure; node execution traces |
| FR-009 queue / duplicates (M1–M4) | Deterministic ranking inputs; explainable reasons; no mutate-on-rank; derived queue position (never persisted); eligibility excludes archived / skipped / currently deferred / confirmed duplicates; pinning changes order without altering fit signals; persistence-boundary move creates exactly one Opportunity across resume and replay; platform ID / URL / fingerprint matching with owner confirmation |
| FR-010 packages | Artefacts grouped by application identity; trace to job evidence |
| FR-011 submission | Never silent submit; fail-closed on unknown answers; unsupported-form / CAPTCHA / auth paths escalate; duplicate-submission guards |
| FR-012 tracking | Status transitions with timestamps and audit history |
| FR-013 agents | Max iterations, stop conditions, restricted tools, validation before state update |
| FR-014 / FR-015 | Loop prevention; fault injection; token/cost/latency where LLM-backed; browser journey evidence when Playwright is used |

**Spike rule:** First FR-008 tests use fixture/saved jobs only — not live acquisition
or real submission. Deterministic replay where possible; owner manual validation for
approval interrupts.
