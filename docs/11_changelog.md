# Changelog

Records product strategy and engineering knowledge changes. Routine typo fixes and minor edits are not recorded here.

---

## Version 1.28

### Phase 2 documentation freeze (pre–FR-006b)

- Restructured [10_roadmap.md](10_roadmap.md) into Completed / Current Focus / Future.
- Added [12_phase_history.md](12_phase_history.md) for Phase 1–2 outcomes and lessons
  (does not replace this changelog).
- README and repository guide clarified for new contributors; next work = FR-006b.
- Deliberately did **not** add `docs/01_product_vision.md` — vision remains
  [03_product_vision.md](03_product_vision.md).

---

## Version 1.27

### M5 Phase 2 close-out validation — GO

**Phase 2 Job Intelligence MVP is complete.**

Close-out rollup (M1–M5):

- **M1** Opportunity persistence (structured SoT, `opp_<ULID>`, immutable artefacts)
- **M2** Decision and outcome logging (FR-013 Phase 2 subset)
- **M3** CSV operational bridge (export + one-time import)
- **M4** Ranked comparison of open opportunities
- **M4a** Opportunity identity (grounded title/company)
- **M5** Release validation with formal **GO**
  ([eval/phase2_release_report.md](eval/phase2_release_report.md))

Also delivered in Phase 2 / owner-sequenced alongside: FR-001–FR-006.

- Live E2E on Maincode (012) and pay.com.au (013): analysis → assessment →
  portfolio → strategy → CV → persist → decide → compare.
- Full suite: 719 passed. No release-blocking defects.
- Next milestone: **FR-006b CV Quality Improvement**.

---

## Version 1.26

### M4a Opportunity identity metadata completion

- Root cause: `JobPosting.title` / `company` were caller-provenance only
  (`--title` / `--company`). `JobAnalysisExtraction` did not extract identity from
  the job description, so runs without CLI flags persisted blank identity through
  list/compare.
- Fix: extraction prompt **v8** + `posting_identity` on `JobAnalysisExtraction`;
  `JobAnalysisService` fills missing title/company only when grounded in raw text
  (never overwrites caller-supplied values; drops ungrounded inventions).
- Manual pipeline uses the analysis-bound posting for report and `--persist`.
- `cic opportunity backfill-identity` copies title/company from trusted
  `posting.json` when the index is blank but the artifact has values. Records whose
  `posting.json` is also blank must be **re-persisted** (no silent OpenAI re-run).
- Phase 2 remains **in progress**. M5 close-out not started.

---

## Version 1.25

### M4 Ranked comparison of open opportunities

- Added `OpportunityComparisonService` (`career_intelligence.opportunity_comparison`)
  for deterministic ranking of open Opportunity records.
- Sort key: pursuit posture → fit strength → application tier → `opportunity_id`.
- Open filter excludes terminal statuses and `decision=skip`. Each item includes
  explainable `reasons`. No OpenAI, re-analysis, or mutation of opportunities.
- CLI: `cic opportunity compare` (optional `--yaml`).
- Ranking lives outside `OpportunityService` (dedicated public comparison boundary).
- Phase 2 remains **in progress**. M5 close-out validation is not implemented.
  Cross-domain ranking (recruiters / networking / meetups) is explicitly out of scope.

---

## Version 1.24

### M3 CSV operational bridge

- Added `OpportunityCsvBridge` with deterministic UTF-8-SIG export
  (`cic opportunity export-csv`) and one-time legacy tracker import
  (`cic opportunity import-legacy-csv`, with `--dry-run`).
- Structured store under `data/opportunities/` remains the sole system of record.
  CSV is a derived view / migration utility — **no bidirectional sync**.
- Legacy imports create incomplete opportunities (`strategy_summary=None`, empty
  artifacts) with `LegacyImportProvenance` and fingerprint-based duplicate skip.
- Phase 2 remains **in progress**. M4 ranked comparison and M5 close-out are not
  implemented.

---

## Version 1.23

### M2 Owner decision and outcome logging (FR-013 Phase 2 subset)

- Extended `OpportunityService` with `record_decision` and `update_outcome`.
- Separates owner **decision** (apply/skip/defer), pipeline **status**, and historical
  **outcome** (pending/offer/accepted/rejected/withdrawn/unknown).
- Simple status transition validation (e.g. no interviewing before submitted; terminal
  states cannot reopen). Immutable M1 artifacts are never modified.
- CLI: `cic opportunity decide` / `cic opportunity outcome`.
- Phase 2 remains **in progress**. M3 CSV export and M4 ranked comparison are not
  implemented. Full FR-013 “inform future assessments” is deferred.

---

## Version 1.22

### M1 Opportunity persistence

- Added `career_intelligence.opportunities` with public `OpportunityService`, typed
  `Opportunity` / `OpportunityIdentity` models, replaceable `OpportunityStore`, and
  YAML-directory adapter under `data/opportunities/`.
- Permanent ids use `opp_<ULID>`. Identity facets (platform id, canonical URL, fingerprint)
  are stored for future FR-014 only — no duplicate detection in M1.
- `--persist` on `scripts/run_application_strategy_manual.py` writes five immutable
  artifact snapshots (posting, job analysis, assessment, portfolio match, strategy).
- CLI: `cic opportunity list|show`.
- ADR: [adr/002_opportunity_persistence.md](adr/002_opportunity_persistence.md).
- Phase 2 remains **in progress**. M2 outcome logging, M3 CSV export, and M4 ranked
  comparison are not implemented. FR-013 is not complete.

---

## Version 1.21

### FR-006 CV Generation formally closed

- **Status: Completed.** Deterministic Tailoring Plan + CV render + optional OpenAI
  summary rewrite (prompt **v2**) are implemented and owner-validated (Bluefin:
  `summary_source=openai_rewrite`, no unsupported technologies, planning unchanged).
- Documentation updated across AGENTS, README, repository guide, functional
  specification, roadmap, implementation notes, and FR-006 eval guides.
- Presentation-only ideas discussed as informal “Phase D” (dynamic layouts, adaptive
  section ordering, richer document presentation) are **out of scope for FR-006**.
  If needed later, raise a **new** FR — do not extend FR-006.
- Next planned functional requirement: **FR-007 Cover Letter**. Remaining Phase 2
  exit criteria (pipeline tracking, FR-013, ranked comparison) unchanged.

---

## Version 1.20

### FR-006 Phase C prompt v2 (quality only)

- Summary rewrite instructions moved to `prompts/cv_summary_v2.md`.
- Guides employer-relevant lead, capabilities over chronology, capabilities
  before project names, and recruiter-scan readability — without changing
  deterministic planning, validation, or fail-soft behaviour.
- `cv_summary_v1.md` retained for history.

---

## Version 1.19

### FR-006 Phase C — opt-in OpenAI summary rewrite

- Added plan-driven Professional Summary rewrite behind `rewrite_summary=False`
  (opt-in). Deterministic Tailoring Plan remains authoritative.
- Prompt loaded from versioned file
  `src/career_intelligence/cv_generation/prompts/cv_summary_v1.md` (not embedded;
  superseded by v2 for quality guidance — see Version 1.20).
- Fail-soft: OpenAI / validation failures copy the profile summary and set
  `summary_source=fallback_profile_copy`.
- Manual runner: `--rewrite-summary`. Design:
  [docs/eval/fr006_phase_c_design.md](eval/fr006_phase_c_design.md).
- Connection fix: Phase C runner now applies the same `truststore.inject_into_ssl()`
  path as FR-002/003 live manuals before constructing `OpenAISummaryRewriter`
  (corpus runs reuse saved JSON and previously skipped that branch). Provider
  failures are classified (Connection / Auth / RateLimit / Timeout / APIStatus).

---

## Version 1.18

### Career Profile enrichment sprint (owner-confirmed)

- General Assembly experience technologies now include `NLP` and `Web Scraping`
  (course techniques only; not promoted to global Skills).
- Historical technologies (Java, Ruby on Rails, Gherkin) remain experience-local only.
- Project and certification `url` fields left null: no per-project canonical URLs were
  owner-confirmed in this sprint; certification URLs deferred by owner.
- Personal links (GitHub, portfolio, LinkedIn) remain outside the Career Profile per
  FR-001 separation; use FR-006 `ContactDetails` when generating CVs.
- Report:
  [docs/eval/career_profile_enrichment_report.md](eval/career_profile_enrichment_report.md).

---

## Version 1.17

### Career Profile evidence-strength model

- Skills remain truthful capability claims; optional `SkillEvidenceRef` records *how*
  a capability is demonstrated (employment, independent engineering, portfolio project,
  certification, professional development, coursework).
- Legacy `Skill.evidence` strings (`experience:id; project:id`) resolve against the
  profile for backwards compatibility; explicit `evidence_refs` take precedence.
- FR-006 deterministic planner ranks promoted skills and summary themes by evidence
  strength so PD-only capabilities (e.g. Snowflake from upskilling) stay recognised
  but are not over-prioritised versus employment/portfolio demonstration.
- Report:
  [docs/eval/career_profile_evidence_model_refinement.md](eval/career_profile_evidence_model_refinement.md).
- Phase C (LLM summary rewrite) not started.

---

## Version 1.16

### FR-005 formally closed after owner manual validation

- Owner manual validation of the FR-001→FR-005 pipeline against real SEEK/LinkedIn roles is
  **complete** (jobs 001–013). Record:
  [manual_validation/jobs/manual_validation_notes.md](../manual_validation/jobs/manual_validation_notes.md).
- Material upstream finding (Job 009 Forever New) was an **FR-003** commercial calibration /
  grounding defect (`commercial_fit=strong` despite a material production AI gap; independent
  engineering over-read as commercial production; mis-grounded retail alignment via nbn) —
  not an FR-005 threshold defect. FR-005 posture/tier policy was intentionally left unchanged.
- Supporting FR-003 hardening retained: commercial vs independent engineering distinction,
  industry evidence grounding, strong judgment incompatible with material gaps, exact catalogue
  evidence refs, trailing-punctuation rejection, portfolio alignment dual-evidence contract,
  fail-closed validation (no silent repair).
- One FR-005 implementation bug during the phase: leadership-token matching uses word
  boundaries so `cto` does not match inside `Victoria`.
- Next planned functional requirement: **FR-006** CV Generation. Remaining Phase 2 items
  (pipeline tracking, FR-013 Outcome Logging, ranked comparison) stay in Phase 2 scope and
  are required for Phase 2 exit, sequenced per owner priority after FR-005 closure.

---

## Version 1.15

### FR-003 portfolio alignment dual-evidence prompt hardening

- Live Job 012 failure: `portfolio_fit.findings.0` alignment with empty `job_evidence`.
- Prompt **v11**: explicit portfolio alignment example with both job and profile evidence;
  invalid empty-`job_evidence` example; hard rule restated for all dimensions.
- `<FindingFieldGuide>` restates that alignment-style findings may not use `job_evidence=[]`.
- Validation unchanged (fail closed; no silent repair). No FR-005 policy changes.

---

## Version 1.14

### FR-003 exact profile evidence catalogue tokens

- Live Job 010 failure: assessor emitted `experience:chase-risk-compliance-ai-engineer.`
  (trailing period). The ID exists in the bound profile; the corrupted token does not.
- Prompt **v10** + cite guide: copy catalogue refs character-for-character; no invented IDs;
  no trailing punctuation.
- `ProfileEvidenceRef` rejects trailing punctuation (fail closed; no silent strip/repair).
- Reference validation hint when a near-miss trailing-punctuated experience id is detected.

---

## Version 1.13

### FR-003 commercial judgment calibration + FR-005 token fix

- Opportunity Assessment prompt **v9**: material gap/conflict findings forbid
  `judgment=strong`; missing commercial production LLM/agent delivery cannot yield
  commercial `strong`; industry alignments require genuine industry-supporting evidence;
  independent engineering is not commercial production employment.
- Domain validation rejects strong judgments with material gaps (no silent repair).
- Service calibration rejects mis-grounded industry alignments (e.g. nbn as retail) and
  commercial production alignments that cite independent/portfolio evidence as employment.
- FR-005 leadership-token matching uses word boundaries so `cto` does not match inside
  `Victoria`. No FR-005 threshold or stretch-policy changes. No FR-004 changes.

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
