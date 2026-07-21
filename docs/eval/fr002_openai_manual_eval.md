# FR-002 OpenAI Manual Evaluation

Engineering evaluation record for `OpenAIJobExtractor` — live OpenAI Responses API
extractions against synthetic smoke fixtures and real job advertisements.

This is not an automated evaluation framework. Offline tests remain authoritative for
regression; this document records what live evaluation taught the engineering design.
See [08_implementation_notes.md](../08_implementation_notes.md) for prompt evolution and
architecture notes.

---

## Purpose

Validate that the FR-002 OpenAI path produces trusted `JobAnalysis` results on
production-style postings before relying on it for daily search decisions — and capture
architectural lessons that offline fixtures alone would miss.

---

## Preconditions

- `OPENAI_API_KEY` set in the environment (SDK default)
- Package installed (`python -m pip install -e ".[dev]"`)
- Prompt version under test recorded: `EXTRACTION_PROMPT_VERSION` in
  `src/career_intelligence/job_analysis/extraction_prompt.py` (current: **v5**)

---

## Evaluation summary

| Evaluation | Result | Findings | Outcome |
|------------|--------|----------|---------|
| Synthetic smoke test | **PASS** | End-to-end Responses API + structured output + trust boundary; candidate-fit fields absent; evidence grounded | Pipeline operational |
| Real Job #1 — Principal AI Engineer | **PASS** (after prompt/architecture hardening) | Employment inferred without evidence (validator correctly rejected); title-only seniority required complete-posting input | Title-aware extraction + employment non-inference; regressions added |
| Real Job #2 — Software Engineer (AI) | **PASS** (after prompt v5) | Employment inference fixed by v4, but v4 weakened global evidence discipline (`evidence=[]` on known claims) | Prompt v5 global evidence rule; regressions added |

Model used throughout: `gpt-4o-mini`. SDK floor: `openai>=1.66.0`.

---

## Synthetic smoke test

**Result:** PASS

Validated:

- OpenAI Responses API connectivity
- Structured Outputs into `JobAnalysisExtraction`
- Trust boundary (`JobAnalysisService` binds caller-owned `JobPosting`)
- JobPosting ownership (extractor payload excludes `posting`)
- Basic extraction (technologies, compensation unstated / seniority unknown where appropriate)
- Candidate-fit fields absent
- Evidence grounding on positive claims

**Conclusion:** The end-to-end FR-002 extraction pipeline is operational.

---

## Real Job Evaluation #1 — Principal AI Engineer

**Final result:** PASS

### Initial findings

- Extractor returned known employment (`full_time` and/or `permanent`) **without evidence**
- The advert never explicitly stated full-time, part-time, permanent, contract, or casual
- Domain validators correctly rejected the extraction

### Investigation

- Seniority appeared only in the **title** (“Principal”); the body never repeated it —
  body-only analysis under-classified seniority
- That drove tagged complete-posting input (`JobTitle`, `Company`, `SourceURL`,
  `JobDescription`) and title-aware prompt rules (prompt v3)
- Prompt **v4** then added strict employment non-inference rules after live failures

### Resolution

- Seniority extracted from job title when clearly stated (evidence section `"Job title"`)
- Employment remains `unspecified` unless explicitly stated, with evidence when known
- Offline regression tests added for title-only Principal and employment non-inference

### Final successful characteristics

- Title-based seniority working (`principal` with title evidence)
- Employment unspecified when not explicit
- Known claims carry evidence excerpts from the tagged posting

---

## Real Job Evaluation #2 — Software Engineer (AI)

**Final result:** PASS

### Initial findings

- After SEEK UI / profile-match / application-status noise was removed from the input,
  employment inference was no longer the primary failure
- Prompt **v4** introduced an **evidence regression**: known role family, technologies,
  and responsibilities returned with `evidence=[]`
- Validators correctly rejected all unsupported claims (~18 validation errors)

### Root cause

Prompt wording that strengthened employment (including “empty evidence” phrasing for
unspecified employment) unintentionally weakened the **global** evidence discipline.
Strict JSON Schema requires the `evidence` key but allows empty arrays (`minItems` absent);
only domain validators catch empty evidence on known claims.

### Resolution

Prompt **v5**:

- Hard global evidence rule near the top of the prompt
- Compact instructions overall
- Employment-specific non-inference retained

Offline regressions added for Software Engineer (AI)–shaped payloads (evidence on all
known claims; empty technology evidence still fails validation).

### Final successful characteristics

- Evidence present for all known role-family, technology, and responsibility claims
- Title-based seniority / ambiguity handling intact where applicable
- Location extracted when explicitly present in the posting
- Employment extracted only when explicitly stated; otherwise unspecified

---

## Architectural lessons (from live evaluation)

1. **Analyse the complete posting** — titles and other trusted metadata are first-class
   extraction inputs, not optional decoration.
2. **Validators are the safety net** — they correctly rejected invented employment and
   empty-evidence claims; do not weaken them to “make live runs pass.”
3. **Prompt sections interact** — strengthening one field (employment) can regress another
   (global evidence) unless a compact global rule stays prominent.
4. **Manual copy/paste is MVP evaluation only** — production ingestion should become
   automated **Job Acquisition**, kept separate from **Job Analysis**. See
   [10_roadmap.md](../10_roadmap.md) § Automated Job Acquisition.
5. **Platform noise is acquisition metadata** — UI chrome, personalised match text, and
   “Applied” status belong outside the employer job description (see FR-014 in
   [04_functional_specification.md](../04_functional_specification.md)).

---

## Complete posting metadata (evaluation checklist)

When constructing a live `JobPosting`:

- Always pass `title` (and `company` when known)
- Prefer clear title seniority when the body does not conflict; evidence section
  `"Job title"`
- Technologies and responsibilities primarily from the body
- Employment only when explicitly stated
- Every known claim must include at least one evidence excerpt

---

## Procedure (repeatable)

1. Construct a `JobPosting` (`raw_text` required; always pass `title` when known;
   `company` / `source_url` optional). Strip platform UI noise from `raw_text`.
2. Run:

```python
from career_intelligence.job_analysis import JobAnalysisService, JobPosting
from career_intelligence.job_analysis.openai_extractor import OpenAIJobExtractor

posting = JobPosting(title="...", company="...", raw_text="...")
analysis = JobAnalysisService(OpenAIJobExtractor()).analyse(posting)
print(analysis.model_dump(mode="json"))
```

3. Score dimensions as **pass**, **partial**, or **fail**, noting prompt version and date.

### Dimension guidance

- **Role family** — taxonomy match; `unknown` when unclear; evidence when known
- **Seniority** — full posting including title; ambiguous when title/body conflict
- **Required / preferred** — match posting language
- **Evidence grounding** — short real substrings; never empty on known claims
- **Compensation** — stated only when present; no invention
- **Employment** — explicit wording only; otherwise unspecified
- **Schema validation** — `analyse` succeeds without `JobAnalysisValidationError`

---

## Status

**First real-world manual evaluation complete.** FR-002 OpenAI extraction is usable for
personal search with prompt **v5**, offline regressions for live failure modes, and
documented follow-ons for acquisition automation and duplicate detection.
