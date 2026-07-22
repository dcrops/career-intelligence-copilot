# FR-003 OpenAI Manual Evaluation

Engineering evaluation record for `OpenAIAssessor` — live OpenAI Responses API
assessments against trusted `JobAnalysis` inputs and the repository career profile.

This is not an automated evaluation framework. Offline tests remain authoritative for
regression; this document records what live evaluation taught the engineering design.

---

## Purpose

Validate that the FR-003 OpenAI path produces trusted `OpportunityAssessment` results on
production-style postings before relying on it for daily search decisions — and capture
prompt-hardening lessons that offline fixtures alone would miss. This record remains the
authoritative live-evaluation evidence for FR-003 closeout (**PARTIAL PASS**).

Pipeline under test:

```
JobPosting → JobAnalysisService(OpenAIJobExtractor)
CareerProfileService.load()
→ OpportunityAssessmentService(OpenAIAssessor)
→ OpportunityAssessment
```

Harness: `tools/manual_eval_openai_assessor.py`

---

## Environment and model

| Setting | Value |
|---------|-------|
| Model | `gpt-4o-mini` (OpenAIAssessor default) |
| Job extraction prompt | `EXTRACTION_PROMPT_VERSION` **v5** |
| Assessment prompt | `ASSESSMENT_PROMPT_VERSION` **v6** (current; v5 closed Phase F) |
| OpenAIAssessor | package-private; structured output via `responses.parse` |
| SDK | `openai>=1.66.0` |
| API key | `OPENAI_API_KEY` in environment (not recorded here) |

---

## Career profile used

`data/career_profile.yaml` via `CareerProfileService()` default path (overridable with
`CIC_PROFILE_PATH`). Golden test fixture at `tests/fixtures/golden/career_profile.yaml`
is structurally equivalent for offline tests.

---

## Evaluation methodology

1. Eight representative cases drawn from FR-002 fixture postings plus FR-002 real-advert
   families (LinkedIn production AI, SEEK Developer Programmer).
2. Each case runs live JobAnalysis extraction, then live OpportunityAssessment.
3. Twelve quality dimensions scored per posting (see table below).
4. Structural validation failures recorded exactly (`loc`, `type`, `msg`).
5. Semantic quality reviewed on assessments that pass validation.
6. Prompt changes made only when live evidence justified them; each change versioned.
7. Offline regression tests added for every failure that produced a code or prompt change.

### Quality dimensions

| # | Dimension |
|---|-----------|
| 1 | Technical judgment quality |
| 2 | Commercial judgment quality |
| 3 | Portfolio judgment quality |
| 4 | Evidence grounding |
| 5 | Profile reference validity |
| 6 | Job evidence index validity |
| 7 | Independent engineering honesty |
| 8 | Handling of missing information |
| 9 | Absence of invented facts |
| 10 | Absence of tier/apply/quota advice |
| 11 | Summary usefulness |
| 12 | Overall PASS / PARTIAL / FAIL |

---

## Evaluation summary (prompt v5 final run)

| Case | Category | Structural result | Overall quality |
|------|----------|-------------------|-----------------|
| applied-ai | Strong AI Engineering fit | **PASS** | **PASS** |
| senior-ai-production | Commercial production AI required | **PASS** | **PARTIAL** |
| data-engineer | Broad role, partial AI relevance | **PASS** | **PASS** |
| no-technologies | Sparse spec, no named technologies | **FAIL** (1st run) / **PASS** (re-run) | **PARTIAL** |
| linkedin-production-rights | Production AI + working rights + on-site | **PASS** | **PARTIAL** |
| developer-programmer | Broad stack, salary friction | **PASS** | **PASS** |
| contract-hybrid | Contract + Sydney hybrid | **PASS** | **PARTIAL** |
| missing-salary | Salary unstated | **PASS** | **PARTIAL** |

**Structural pass rate (v5 full run):** 7/8. **After no-technologies re-run:** 8/8.

Raw output: `tools/fr003_live_eval_output.txt`

---

## Posting-by-posting results

### 1. applied-ai — Applied AI Engineer (strong AI fit)

**Structural:** PASS

| Dimension | Judgment |
|-----------|----------|
| Technical | Strong — Python, FastAPI, applied AI responsibilities cited with valid indexes |
| Commercial | Moderate/mixed — hybrid Sydney vs preferences handled without invented deal-breakers |
| Portfolio | Strong — projects linked to production-service responsibilities |
| Evidence | Grounded — technology indexes and profile refs valid |
| Independent engineering | Honest — portfolio cited as capability, not paid commercial AI tenure |
| Missing info | Seniority left uncertain (unknown in extraction) |
| Tier leakage | None detected |
| **Overall** | **PASS** |

---

### 2. senior-ai-production — Senior AI Engineer (production AI required)

**Structural:** PASS

| Dimension | Judgment |
|-----------|----------|
| Technical | Strong — Python, LangChain, RAG/production requirements grounded |
| Commercial | Strong — employment and compensation aligned; salary_min=null respected |
| Portfolio | Moderate — partial_alignment on production LLM requirement with employment ref |
| Evidence | Mostly grounded; scalar sources sometimes include spurious `item_index` (passes schema) |
| Independent engineering | Acceptable — portfolio gap/limitation stated |
| Missing info | Seniority from title used correctly in extraction |
| Tier leakage | None |
| **Overall** | **PARTIAL** — occasional `item_index` on scalar job evidence (employment, compensation, work_arrangement) |

---

### 3. data-engineer — Data Engineer (broad / partial AI relevance)

**Structural:** PASS

| Dimension | Judgment |
|-----------|----------|
| Technical | Mixed — Python/SQL alignment; Spark/dbt gaps or partial alignment appropriate |
| Commercial | Moderate — role-family misalignment with AI Engineering target surfaced |
| Portfolio | Moderate — limited direct data-engineering portfolio narrative |
| Evidence | Grounded with valid indexes |
| Independent engineering | N/A |
| Missing info | Seniority unknown handled |
| Tier leakage | None |
| **Overall** | **PASS** |

---

### 4. no-technologies — AI Engineer sparse spec

**Structural:** FAIL on first v5 run (`commercial_fit` partial_alignment without profile_evidence); **PASS** on immediate re-run.

| Dimension | Judgment |
|-----------|----------|
| Technical | Mixed — production AI gap vs independent engineering; seniority uncertainty |
| Commercial | Mixed — **semantic issue:** gap finding invents salary conflict despite `salary_min: null` on re-run |
| Portfolio | Strong — responsibilities linked to portfolio projects |
| Evidence | Grounded when passing |
| Independent engineering | Honest on production-experience gap |
| Missing info | Sparse technologies handled via experience_requirement / responsibility refs |
| Tier leakage | None |
| **Overall** | **PARTIAL** — flaky structural pass; salary-floor inference still appears intermittently |

---

### 5. linkedin-production-rights — LinkedIn AI Engineer

**Structural:** PASS

| Dimension | Judgment |
|-----------|----------|
| Technical | Mixed — production systems emphasis; no invented technology matches |
| Commercial | Mixed — on-site Melbourne vs preferences; working-rights requirement surfaced as uncertainty/gap without inferring candidate eligibility |
| Portfolio | Moderate — project evidence linked to production responsibilities |
| Evidence | Grounded |
| Working rights | Job requirement cited; candidate eligibility not inferred (correct) |
| Tier leakage | None |
| **Overall** | **PARTIAL** — working-rights handling acceptable; some commercial judgments border on overstated alignment |

---

### 6. developer-programmer — SEEK Developer Programmer

**Structural:** PASS

| Dimension | Judgment |
|-----------|----------|
| Technical | Weak/misaligned — broad stack role vs AI Engineering target |
| Commercial | Weak — low salary band vs AI Engineering direction noted |
| Portfolio | Weak/moderate — limited relevance surfaced |
| Evidence | Grounded |
| Salary | Low band acknowledged without inventing candidate salary floor |
| Tier leakage | None |
| **Overall** | **PASS** |

---

### 7. contract-hybrid — Contract AI Engineer

**Structural:** PASS

| Dimension | Judgment |
|-----------|----------|
| Technical | Strong — Python, LangChain, retrieval responsibilities |
| Commercial | Mixed — contract engagement vs preferences; **semantic issue:** compensation gap wording implies conflict despite null salary_min |
| Portfolio | Strong — projects linked to responsibilities (earlier v4 run mis-used `work_arrangement` source; v5 improved) |
| Evidence | Grounded |
| Tier leakage | None |
| **Overall** | **PARTIAL** — salary_min=null rule still weak in commercial gap prose |

---

### 8. missing-salary — AI Engineer (compensation unstated)

**Structural:** PASS

| Dimension | Judgment |
|-----------|----------|
| Technical | Strong — Python, RAG responsibilities, experience gap noted |
| Commercial | Mixed — unstated compensation as uncertainty/assumption (appropriate) |
| Portfolio | Strong — RAG project linked to responsibility |
| Evidence | Grounded; assumption finding used correctly |
| Missing salary | Unstated compensation not invented into raw figures |
| Tier leakage | None |
| **Overall** | **PARTIAL** — acceptable handling of unstated pay; minor scalar `item_index` noise |

---

## Failures discovered (live)

| Failure type | Prompt version observed | Resolution |
|--------------|------------------------|------------|
| Bare profile refs (`operational-intelligence-copilot` without `project:` prefix) | v1 | v2 — mandatory `namespace:id` with examples |
| Empty `job_evidence` on alignment / partial_alignment (all dimensions) | v1–v3 | v4 — cite-as JSON in `<JobEvidenceIndexes>`, explicit job-evidence shape rules |
| `assumption` field populated on non-assumption findings | v2 | v3 — global assumption discipline |
| Empty `job_evidence` on `portfolio_fit` only | v4 | v5 — portfolio-specific job-evidence requirement |
| `partial_alignment` without `profile_evidence` (commercial, sparse specs) | v5 | Intermittent — passed on re-run; monitor |
| Scalar sources with `item_index` (employment, compensation, work_arrangement) | v4–v5 | Prompt rule added in v5; still appears occasionally (schema allows) |
| Salary conflict invented when `salary_min` is null | v4–v5 | Prompt rule present; intermittent semantic leakage |
| Wrong job evidence `source` for portfolio claims (`work_arrangement` carrying project text) | v4 | Reduced in v5; not fully eliminated |

---

## Prompt evolution

| Version | Change | Justifying failure |
|---------|--------|-------------------|
| **v1** | Initial assessment instructions | — |
| **v2** | Mandatory `namespace:id` profile refs with examples | Bare profile ref hallucination |
| **v3** | Global evidence rules at prompt top; assumption field discipline | Empty job_evidence; assumption misuse |
| **v4** | Cite-as JSON in `<JobEvidenceIndexes>`; job-evidence shape examples; schema-empty-array warning | Persistent empty job_evidence after v3 (0/8 → 3/8 pass) |
| **v5** | Portfolio-fit job-evidence requirement; explicit scalar `item_index` prohibition | Portfolio-only findings; scalar index noise |
| **v6** | Catalogue lists complete `namespace:id` tokens only; assessor-facing CareerProfile rewritten to `ref=` pointers (no bare `id` / preference keys); verbatim-copy instruction | Live `senior-ai-production` recurred bare refs (`Python`, project/experience ids, `salary_min`) despite v2–v5 prompt text — root cause was competing bare IDs in the CareerProfile JSON dump |

Current: `ASSESSMENT_PROMPT_VERSION = "v6"`.

---

## Regression tests added

| Test | File | Live case |
|------|------|-----------|
| `test_bare_profile_ref_without_namespace_fails_through_service` | `tests/unit/opportunity_assessment/test_openai_assessor.py` | v1 / recurred v5 senior-ai-production |
| `test_format_assessment_input_avoids_bare_profile_ids_for_copying` | same | v6 input-presentation fix |
| `test_alignment_with_empty_job_evidence_fails_through_service` | same | v2/v3 all cases |
| `test_non_assumption_with_assumption_text_fails_through_service` | same | v2 applied-ai family |
| `test_portfolio_alignment_without_job_evidence_fails_through_service` | same | v4 portfolio_fit cases |

All use injected fake clients — no live API calls in CI.

---

## Test execution

| Suite | Result |
|-------|--------|
| Golden journey | **8 passed** |
| FR-003 unit + functional + golden | **94 passed** |
| Full `tests/` | **260 passed** |

Verified at Phase H closeout (includes the v6 input-presentation regression).

---

## Phase H live confirmation (prompt v6)

Owner-confirmed structural live passes after the v6 catalogue / CareerProfile presentation
fix:

| Case | Result |
|------|--------|
| `applied-ai` | **PASS** — valid `namespace:id` profile refs |
| `senior-ai-production` | **PASS** — valid `namespace:id` profile refs; independent engineering honesty preserved |

These confirmations do **not** rewrite the eight-scenario Phase F verdict from PARTIAL PASS
to full PASS. Remaining semantic limitations below still apply.

---

## Final quality assessment

| Area | Verdict |
|------|---------|
| Structural trust boundary | **Good** — validators catch hallucinated refs and empty evidence; v6 reduces bare-ref copying |
| Technical fit judgments | **Good** — alignments, gaps, and uncertainties generally appropriate |
| Commercial fit judgments | **Mixed** — salary_min=null rule intermittently violated in prose |
| Portfolio fit judgments | **Good** after v5 — projects linked to job responsibilities |
| Independent engineering honesty | **Good** — production AI gaps stated without equating portfolio to employment |
| Working rights | **Good** — requirements surfaced without inferring candidate eligibility |
| Tier / apply leakage | **Good** — none detected in serialised output |
| Run-to-run stability | **Mixed** — sparse-spec and evidence-omission flakiness can still appear |

**Overall manual evaluation verdict: PARTIAL PASS**

Structural validation is reliable after prompt v6. Semantic limitations remain and are
accepted at FR-003 closeout. Offline architecture, fixtures, and golden journeys are
authoritative for CI. Do not rewrite this verdict as a full PASS.

---

## Remaining limitations

1. **`salary_min=null`** — commercial findings may occasionally imply salary friction when
   no candidate threshold exists.
2. **Sparse-specification variance** — thin adverts can produce run-to-run variation or
   incomplete evidence.
3. **Scalar `item_index`** — schema does not forbid `item_index` on scalar sources; the
   model sometimes emits it without failing validation.
4. **JobAnalysis dependency** — assessment quality partly tracks upstream FR-002 extraction
   stability (shared markers and FixtureExtractor cover offline cases).
5. **Live flakiness** — not suitable for CI; offline fake-client tests remain authoritative.

These limitations are caught or mitigated by validation where possible. They do not
invalidate the offline architecture. Revisit through observed production evidence rather
than speculative prompt tuning.

Raw live run transcript (regeneratable via the harness; no secrets):
`tools/fr003_live_eval_output.txt`.

---

## FR-003 completion recommendation

| Phase | Recommendation |
|-------|----------------|
| **Phase F (this evaluation)** | **Complete** — harness, live eval, prompt hardening, regressions, and this record delivered |
| **Phase G (golden journey)** | **Complete** — offline Profile → JobAnalysis → OpportunityAssessment journeys passed |
| **Phase H (closeout)** | **Complete** — documentation, roadmap, changelog, architecture overview image, and final verification; live verdict remains **PARTIAL PASS** |

FR-003 is **closed** for Phase 2 implementation with documented live semantic limitations.
Next stage: FR-004 Portfolio Matching.
