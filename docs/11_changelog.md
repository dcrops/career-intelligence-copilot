# Changelog

Records product strategy and engineering knowledge changes. Routine typo fixes and minor edits are not recorded here.

---

## Version 1.12

### FR-005 seniority-aware application strategy policy

- Deterministic planner caps AI-target senior roles at `consider` / Silver /
  `acceptable_opportunity` when material senior commercial / leadership gaps are
  present, commercial fit is not strong, and the profile lacks direct senior commercial
  AI **employment** evidence (`experience.kind=employment` with AI + ownership markers).
- Independent engineering remains distinguishable from commercial employment.
- Salary-only commercial uncertainty does not trigger the cap; findings (not only the
  commercial fit label) drive the seniority mismatch.
- Credible stretch with strong technical + portfolio fit may use Silver + **targeted**
  effort (narrow exception to the usual Silver→minimal mapping); not a blanket
  “senior = silver” rule.
- No FR-002 / FR-003 / FR-004 policy changes. FR-013 not started.

---

## Version 1.11

### FR-003 assumption field-contract hardening

- Opportunity Assessment prompt **v8**: select finding kind first; `assumption` text is
  allowed only when `kind="assumption"`; non-assumption kinds must set `assumption=null`
  and put commentary in `summary`/`detail`.
- Assessor input adds `<FindingFieldGuide>` (per-kind allowed/forbidden fields).
- Schema invariant retained — no post-parse cleanup, no discriminated-union redesign.
- Regression tests for invalid assumption side-channels on gap/partial/transferable findings.
- No FR-004/FR-005 policy changes. FR-013 not started.

---

## Version 1.10

### FR-003 evidence-contract hardening

- Opportunity Assessment prompt **v7**: per-finding-kind evidence requirements for
  `alignment`, `partial_alignment`, `transferable_alignment`, `gap`, `conflict`,
  `uncertainty`, and `assumption`; explicit ban on empty required evidence arrays;
  hybrid AI Product Manager conceptual examples.
- Assessor input now includes `<ProfileEvidenceCiteGuide>` cite-as JSON for every
  catalogue profile ref (mirrors JobEvidenceIndexes discipline).
- Validation invariants retained (`partial_alignment` / `transferable_alignment` still
  require profile evidence). No fabricated refs; no retry loop.
- Richer `OpportunityAssessmentValidationError` messages for manual-runner diagnostics.
- No FR-004/FR-005 policy or threshold changes. FR-013 not started.

---

## Version 1.9

### Hybrid role-family extraction (FR-002)

- Extended role-family taxonomy with `network_engineering` (narrowest addition for
  network-primary hybrid Automation & AI roles).
- Extraction prompt **v7**: classify hybrid roles by dominant profession; AI/automation
  capabilities do not redefine family; known families (including `other`) still require
  evidence — empty-evidence `other` remains invalid.
- Manual runner prints concise validation diagnostics (component, field, reason) without
  dumping full request payloads.
- Added hybrid-role regression fixtures/tests. No FR-003/004/005 policy changes.
  FR-013 not started.

---

## Version 1.8

### Manual-validation quality pass (FR-002 extraction + FR-005 location/wording)

- Fixed FR-005 soft location matching: normalize punctuation, whitespace, parenthetical
  arrangement suffixes, and common Australian state aliases so values such as
  `Melbourne, VIC` and `Melbourne VIC (Hybrid)` no longer false-conflict.
- Hardened FR-002 OpenAI extraction prompt to **v6**: de-prioritise SEEK/job-board
  chrome (“How you match”, profile-match tags, volume labels, employer questions),
  split grouped technologies, and extract multiple employer-authored responsibilities.
- Corrected FR-005 explanation wording so only true AI-target families are labelled
  “AI-aligned”; software/data engineering reasons use the actual role family.
- Fixed manual-runner evidence display so `preference:locations` is not rendered as
  `preference:preference:locations` (model refs unchanged).
- Added junior software/DevOps offline fixture and regression tests. No FR-003,
  FR-004, or FR-005 threshold/weight policy changes. FR-013 not started.

---

## Version 1.7

### FR-005 Application Strategy complete

- Implemented Application Strategy domain model with PursuitPosture as the primary
  recommendation and ApplicationTier as effort investment only (Platinum / Gold /
  Silver / **Bronze**). Bronze replaces the legacy Skip tier name and does **not** mean
  “never apply.”
- Added `ApplicationStrategyService` as the public trust boundary: planners return
  untrusted payloads; the service binds caller-owned `JobAnalysis`, validates schema and
  evidence references, and rejects mismatched OpportunityAssessment / PortfolioMatch
  posting identity.
- Added package-private `DeterministicStrategyPlanner` (production policy): rule-based
  posture/tier/effort, portfolio emphasis from Portfolio Match (no rerank), advisory
  `consider_*` next_actions, optional `SearchOperatingContext.volume_applications_enabled`
  (default false; no quotas).
- Added package-private `FixtureStrategyPlanner` and marker-keyed fixtures (shared FR-002
  markers plus strategy-only salary-conflict / weak-portfolio / volume markers).
- Documented the five-question acceptance standard answered by existing fields (reasons,
  risks, next_actions, evidence, manual_checks, assumptions/blockers).
- Added functional acceptance and golden journeys for
  CareerProfile → JobAnalysis → OpportunityAssessment → PortfolioMatch →
  ApplicationStrategy.
- Explicitly excluded: CV/cover-letter generation, outreach, submission, percentage
  scores, autonomous apply/skip, mandatory OpenAI narrative.

---

## Version 1.6

### FR-004 Portfolio Matching complete

- Implemented the portfolio-matching domain model (`PortfolioMatch`,
  `RankedPortfolioProject`, `RankingFactor`) with evidence-backed factors via local
  `JobEvidenceRef` / `ProfileEvidenceRef` shapes and stable `project:<id>` references.
- Added `PortfolioMatchingService` as the public trust boundary: matchers return
  untrusted payloads; the service binds caller-owned `JobAnalysis`, validates schema,
  enforces full project coverage, and rejects invalid evidence references.
- Added package-private `DeterministicMatcher` (production ranking path): technology
  phrase overlap and responsibility/demonstrates token overlap; ordered by required →
  preferred → demonstrates → responsibility → unspecified → stable `project_id`.
- Added package-private `FixtureMatcher` and shared FR-002 marker builders (plus
  `MARKER_PORTFOLIO_TIE`) for offline service-composition tests.
- Clarified sibling boundary with FR-003: Portfolio Fit answers whether the portfolio
  supports the role; Portfolio Match answers which projects should lead. Neither feeds
  or modifies the other; both consume CareerProfile + JobAnalysis only.
- Accepted honest Data Engineer ties when only shared Python evidence exists; do not
  invent SQL/Spark/dbt distinctions the profile does not claim.
- Added functional acceptance and golden journeys for CareerProfile → JobAnalysis →
  PortfolioMatch.
- Explicitly excluded from FR-004: Apply/Skip/Defer, tiers, effort, CV/outreach strategy,
  percentage scores, and any dependency on OpportunityAssessment.

## Version 1.5

### FR-003 Opportunity Assessment complete

- Implemented the opportunity-assessment domain model with three Phase 2 fit dimensions
  (Technical, Commercial, Portfolio), qualitative judgments only (no percentage scores),
  and evidence-backed findings via `JobEvidenceRef` / `ProfileEvidenceRef`.
- Added `OpportunityAssessmentService` as the public trust boundary: assessors return
  untrusted payloads; the service binds caller-owned `JobAnalysis`, validates schema, and
  rejects invalid evidence references.
- Added deterministic `FixtureAssessor` and shared FR-002 fixture markers (including
  no-technologies and working-rights) so offline journeys chain
  JobAnalysisService → OpportunityAssessmentService.
- Added package-private `OpenAIAssessor` (`responses.parse` →
  `OpportunityAssessmentExtraction`) with prompt versioning through **v6**.
- Hardened assessor input presentation after live bare-ref recurrence on
  `senior-ai-production`: `<ValidProfileReferences>` lists complete `namespace:id`
  tokens only; assessor-facing `<CareerProfile>` uses `ref=` pointers instead of bare
  entity ids / preference keys (service validation unchanged — no ref repair).
- Completed live manual evaluation across eight representative scenarios — verdict
  **PARTIAL PASS** (not full PASS). After prompt **v6** input-presentation hardening,
  owner-confirmed live structural passes for `applied-ai` and `senior-ai-production`
  with valid `namespace:id` profile refs. Record:
  [eval/fr003_openai_manual_eval.md](eval/fr003_openai_manual_eval.md).
- Added cross-stage golden journeys proving CareerProfile → JobAnalysis →
  OpportunityAssessment offline.
- Documented architecture and verification overview in
  [08_implementation_notes.md](08_implementation_notes.md) § FR-003, with overview image at
  [assets/fr003_opportunity_assessment_architecture_overview.png](assets/fr003_opportunity_assessment_architecture_overview.png).
- Accepted known live semantic limitations at closeout (`salary_min=null` friction prose,
  sparse-spec variance, occasional scalar `item_index`, upstream JobAnalysis coupling,
  live nondeterminism). Offline architecture and CI remain authoritative.
- Explicitly excluded from FR-003: Apply/Skip/Defer, tiers, effort, JobSeeker quota,
  `SearchOperatingContext`, inferred working rights, and invented commercial AI employment
  from independent engineering / portfolio evidence.
- Phase H documentation closeout complete; next Phase 2 stage is FR-004.

## Version 1.4

### FR-002 manual evaluation completed

- Completed the first real-world manual evaluation of OpenAI job extraction (synthetic
  smoke + Principal AI Engineer + Software Engineer (AI)). Record:
  [eval/fr002_openai_manual_eval.md](eval/fr002_openai_manual_eval.md).
- Hardened the extraction prompt through live production-style advertisements:
  title-aware complete posting (v3), employment non-inference (v4), then a compact
  **global evidence** rule (v5) after v4’s employment wording caused empty `evidence`
  arrays on otherwise correct claims.
- Added offline regression coverage for live failure modes (title-only seniority,
  employment non-inference, known claims requiring evidence, empty-evidence rejection).
- Improved evidence discipline without weakening domain validators.
- Documented future **Automated Job Acquisition** (roadmap) and **Duplicate Application
  Detection** (FR-014), keeping acquisition separate from Job Analysis.

### FR-002 OpenAI job extraction

- Added `OpenAIJobExtractor` using the official OpenAI Python SDK Responses API
  (`responses.parse`) with structured output into internal `JobAnalysisExtraction`
  (all `JobAnalysis` fields except `posting`).
- Kept `JobAnalysisService` as the trust boundary: extractors return untrusted
  payloads; the service rejects embedded `posting`, binds the caller-supplied
  `JobPosting`, and validates trusted `JobAnalysis`.
- Configuration limited to API key (SDK `OPENAI_API_KEY` / optional override),
  model (default `gpt-4o-mini`), and timeout; client injection for offline tests.
- Automated tests remain fully offline via a tiny fake OpenAI client; added
  [eval/fr002_openai_manual_eval.md](eval/fr002_openai_manual_eval.md) for manual
  quality checks on real advertisements.
- `FixtureExtractor` remains deterministic offline scaffolding and is unchanged as
  a non-default test path.
- Prompt v3 formats the complete `JobPosting` as tagged sections (`JobTitle`,
  `Company`, `SourceURL`, `JobDescription`) so seniority can be taken from the title
  when the body never repeats it; title/body conflicts remain ambiguous with evidence.
- Prompt v4 requires evidence-backed employment only: do not infer full-time/permanent
  from office, hybrid, seniority, or recruiter wording.
- Prompt v5 adds a compact global evidence rule so known role-family, technology, and
  responsibility claims never emit empty evidence arrays (v4 employment wording
  regression).

### Phase 2 implementation begins — FR-001 Career Profile

- Implemented the evidence-based Career Profile domain model with Python 3.11+ and Pydantic.
- Added replaceable YAML persistence behind a public service boundary.
- Added the `validate`, `summary`, `show`, and `init` profile CLI commands.
- Manually structured the initial profile from the Master CV; runtime PDF parsing remains
  deferred.
- Added unit, functional, and golden user journey coverage for FR-001.
- Added [07_testing_strategy.md](07_testing_strategy.md) as the testing authority for future
  implementation work.
- Recorded the first implementation decision in
  [ADR-001](adr/001_python_yaml_profile_foundation.md).
- Advanced the roadmap from Product Definition to Phase 2 implementation.

### FR-001 product review

- Added [08_implementation_notes.md](08_implementation_notes.md) — career-profile data
  provenance, plan deviations, and the future-improvements backlog.
- Marked assumed/inferred career-profile values (goals, preferences, and the inferred Chase
  R&D start date) as `OWNER-CONFIRM` rather than presenting them as CV-sourced fact.
- Recorded two intentional FR-001 plan deviations: preference validation implemented via a
  required `remote` field instead of a standalone validator, and the inferred employment date
  moved from an experience highlight to a provenance comment. Neither changes ADR-001.
- Owner confirmed all flagged profile assumptions (2026-07-19): goals, locations, full-time
  employment, flexible remote arrangement, AUD with no salary minimum, and must-haves confirmed
  as recorded; the Chase R&D start date corrected from the inferred 2023-11 to 2025-12.
  FR-001 approved for merge.

### Career-history domain refinement (pre-merge)

- Experience entries are now explicitly typed by
  `kind: employment | independent_engineering | professional_development`; experience is a
  professional-history facet, not an employment list. `company` renamed to `organisation`.
- Chase Risk & Compliance reclassified as `independent_engineering` — an independent AI
  Engineering R&D and portfolio brand, not employment.
- Added two owner-directed professional-development periods: Data Engineering upskilling and
  career transition (Oct 2023 – Jun 2025) and AI Engineering study with portfolio development
  (Jul 2025 – Nov 2025), closing the previous timeline gap.
- Retired the informal `professional-development:master-cv` evidence namespace; skill evidence
  now cites experience or project IDs.
- No new top-level career-phase ontology, separate collections, or project attribution links
  were introduced. ADR-001 unchanged.

### Career-profile accuracy and provenance refinement (pre-merge)

- Added owner-supplied pre-nbn history absent from the Master CV: Bakers Delight (2009–2012,
  2015–2018, and Aug–Sep 2019), Console (2012–2014), and AccessHQ consulting to Public
  Transport Victoria (2018–2019) as `employment` Test Analyst roles, plus the General Assembly
  Data Science Immersive (Sep–Dec 2019) as `professional_development`.
- `Certification` now requires `status: active | expired` and supports an optional
  `expiry_date`, so lapsed credentials are represented truthfully. Recorded both Databricks
  Data Engineer certifications (Associate — expired Jul 2026; Professional — active until
  Aug 2026) alongside the active AWS Certified Developer - Associate (expires Sep 2026).
- Professional summary now distinguishes total commercial technology experience since 2009,
  3.5 years of commercial Data Engineering, and independent AI Engineering/portfolio
  development — without implying commercial AI Engineering employment.
- Added QA-era skills (Selenium WebDriver, Jenkins, Maven, Cucumber; software quality
  assurance and test automation domains) with evidence citing the new experience entries.
  ADR-001 unchanged.

---

## Version 1.3

### Engineering knowledge capture

- Added [00_repository_guide.md](00_repository_guide.md) — canonical repository entry point, documentation authority map, folder semantics, operational data conventions.
- Added [AGENTS.md](../AGENTS.md) — Cursor agent bootstrap, scope boundaries, engineering invariants.
- Added [05_engineering_principles.md](05_engineering_principles.md) — engineering decision framework for Phase 2.
- Added [06_domain_model.md](06_domain_model.md) — conceptual domain model and decision loop.
- Merged **assessment and tier semantics** into [04_functional_specification.md](04_functional_specification.md) — fit dimension definitions, tier effort guidance, legacy Tier 1 → Platinum mapping.
- Merged **Phase 2 exit criteria** into [10_roadmap.md](10_roadmap.md) — engineering, adoption, and non-criteria boundaries.
- Updated README, product vision, and cross-references across documentation.
- Clarified architecture status: intentionally undecided; no ADR infrastructure until first implementation decision.
- Open item: reconcile legacy "Tier 1" terminology in operational tracker data.

---

## Version 1.2

### Approved strategic clarification — success horizons and near-term priority

- Established **Horizon 1 (Immediate):** help the repository owner secure a suitable AI Engineering role sooner while reducing job-search effort.
- Established **Horizon 2 (Long term):** evolve into a reusable Career Intelligence Platform for ongoing career progression after employment is secured.
- Horizon 1 takes priority whenever the two horizons compete.
- Added **product mission:** help professionals spend less time managing their careers and more time advancing them.
- Added **dual-value prioritisation test:** near-term capabilities must improve the likelihood of relevant interviews or offers, or reduce manual job-search effort.
- Reframed **intelligence and automation:** intelligence-first, with staged human-supervised automation for repetitive administrative work; important decisions and externally visible actions remain user-reviewable.
- Clarified that the product does not guarantee employment, interviews, or recruiter engagement.
- Confirmed **Phase 2 MVP scope:** Job Intelligence vertical slice — opportunity assessment, tiering, portfolio matching, pipeline tracking; not the full job-search platform.
- Aligned application tier terminology to **Platinum, Gold, Silver, Skip** across product documentation.
- Scoped FR-003 to three Phase 2 fit dimensions (Technical, Commercial, Portfolio); deferred Recruiter Confidence, Interview Probability, and Strategic Value.
- Added FR-013 Outcome Logging as a Phase 2 requirement.

---

## Version 1.1

### Strategy refinement after live applications

- Master CV philosophy changed from "tailor every CV" to "maintain a single Master CV and tailor only when materially beneficial."
- Introduced application tiering (Platinum, Gold, Silver).
- Added emphasis on visibility as the primary career bottleneck.
- Added focus on return on time invested.
- Updated mission to prioritise converting portfolio capability into commercial opportunities.
