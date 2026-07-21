# Career Intelligence Copilot Roadmap



## Prioritisation Context



**Horizon 1 — Immediate:** Help the repository owner secure a suitable AI Engineering role sooner while reducing job-search effort.



**Horizon 2 — Long term:** Evolve into a reusable Career Intelligence Platform for ongoing career progression.



Horizon 1 takes priority whenever the two horizons compete.



Near-term work should satisfy at least one of:



- improve the likelihood of securing relevant interviews or job offers

- reduce the manual effort required to run an effective job search



---



## Current Phase



### Phase 1 — Product Definition



Current focus:



- Product vision and documentation alignment

- Phase 2 MVP scope definition

- Repository setup

- Initial architecture decision deferred until implementation

- Engineering knowledge capture



Status: Complete (Phase 2 MVP scope approved)



The first implementation decision is now recorded in
[ADR-001](adr/001_python_yaml_profile_foundation.md).



---



## Active and Planned Development



### Phase 2 — Job Intelligence (MVP)

**Status:** In progress. FR-001 Career Profile is implemented. FR-002 Job Analysis
is implemented (domain models, `JobAnalysisService`, `FixtureExtractor`,
`OpenAIJobExtractor`) and has completed its first real-world manual evaluation with
prompt v5 and offline regressions for live failure modes — see
[eval/fr002_openai_manual_eval.md](eval/fr002_openai_manual_eval.md). Remaining
decision-loop stages (FR-003+) are not yet implemented.



**Purpose:** Improve opportunity selection and reduce repetitive job-analysis work.



**Primary outcome:** Help the user prioritise which roles deserve effort — and how much — while reducing manual job-description analysis and tracking.



**In scope:**



- Career profile (FR-001)

- Job description analysis (FR-002)

- Opportunity assessment — Technical, Commercial, and Portfolio Fit (FR-003 scoped)

- Portfolio matching (FR-004)

- Application tiering — Platinum, Gold, Silver, Skip — with effort guidance (FR-005)

- Job opportunity pipeline and outcome logging (FR-013)

- Ranked comparison of open assessed opportunities



**Explicitly out of scope for Phase 2:**



- CV and cover letter generation

- Recruiter outreach generation

- Interview preparation

- Full career dashboard

- Market intelligence

- Cross-domain daily prioritisation

- Automated job discovery or external integrations

- Interview Probability and Recruiter Confidence scoring



Phase 2 is the first vertical slice. It must not expand into the entire job-search platform.



### Phase 2 Exit Criteria



Phase 2 is complete when the decision loop described in [06_domain_model.md](06_domain_model.md) is usable on real job postings during the owner's active search — not when individual FR acceptance criteria are checked in isolation.



**Engineering exit criteria:**



- Career profile available to every decision (FR-001)

- Job descriptions can be analysed with reduced manual extraction effort (FR-002)

- Assessments produce evidence-backed fit analysis across all three Phase 2 dimensions (FR-003)

- Portfolio projects can be ranked per opportunity with explanation (FR-004)

- Tier recommendations include effort guidance and cited rationale (FR-005)

- Outcomes can be recorded and retrieved against assessed opportunities (FR-013)

- Open assessed opportunities can be ranked for effort prioritisation



**Adoption criteria:**



- The owner uses the loop on real postings rather than bypassing it for manual analysis

- Outcome logging replaces ad-hoc tracking for assessed opportunities

- The system connects to the existing workflow in `applications/` — not a parallel unused tool



**Explicit non-criteria (Phase 2 completion does not require):**



- CV or cover letter generation

- Recruiter, interview, dashboard, or market intelligence capabilities

- Automated job discovery or external integrations

- Predictive scoring dimensions

- Production deployment or multi-user support



Phase 3 consideration begins only after Phase 2 exit criteria are met.



---



### Phase 3



Recruiter Intelligence



---



### Phase 4



Portfolio Intelligence



---



### Phase 5



Networking Intelligence



---



### Phase 6



Learning Intelligence



---



### Phase 7



Interview Intelligence



---



### Phase 8



Career Dashboard



---



## Future Ideas



Potential future enhancements (Horizon 2):



- Gmail integration



- Calendar integration



- LinkedIn integration



- Meetup integration



- GitHub integration



- Salary benchmarking



- Recruiter scoring



- Interview analytics



- Commercial SaaS version



Future ideas are deferred unless they directly support Horizon 1 during the active job search.



---



## Automated Job Acquisition



**Status:** Future work (not Phase 2 exit criteria). Manual copy/paste of job text into
`JobPosting` is an **MVP evaluation technique only** — sufficient to harden FR-002
extraction, not the intended long-term owner workflow.



**Intended production workflow:**



```
Job Discovery
      ↓
Job Acquisition
      ↓
Metadata Normalisation
      ↓
Duplicate Detection
      ↓
Job Extraction (FR-002)
      ↓
Candidate Fit Analysis (FR-003+)
```



**Potential acquisition mechanisms** (choose later by dual-value test):



- browser automation
- browser extension
- recruiter emails
- supported platform APIs
- platform alerts



**Architectural separation (non-negotiable):**



| Concern | Responsibility |
|---------|----------------|
| **Job Acquisition** | Obtain raw listing content and platform metadata (IDs, URLs, application status, UI noise stripped or segregated) |
| **Job Analysis** | Extract structured `JobAnalysis` from a trusted `JobPosting` — no discovery, scraping, or duplicate logic |



Acquisition must not be embedded inside extractors. Analysis must not scrape job boards.
Duplicate detection is specified as FR-014 in
[04_functional_specification.md](04_functional_specification.md). Related domain note:
[06_domain_model.md](06_domain_model.md) § Job Posting — Future Evolution.



---



## Parking Lot



Ideas that may be valuable but are intentionally deferred until later development.



Capabilities in the parking lot should be evaluated against the dual-value test before promotion to an active phase.


