# Testing Strategy

## Purpose

This document is the authoritative testing reference for implementation work in the Career
Intelligence Copilot. It defines which behaviours each test layer protects and how the suite
grows as Phase 2 progresses.

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
(including `tests/unit/opportunities/` for M1 persistence).

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
