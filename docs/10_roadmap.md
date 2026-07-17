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

- Initial architecture (intentionally undecided — no stack or architecture document exists yet)

- Engineering knowledge capture



Status: In Progress (Phase 2 MVP scope approved; implementation not started)



Architecture and technology decisions will be recorded when the first irreversible implementation choice requires them. Until then, absence of an architecture document is expected.



---



## Planned Development



### Phase 2 — Job Intelligence (MVP)



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



## Parking Lot



Ideas that may be valuable but are intentionally deferred until later development.



Capabilities in the parking lot should be evaluated against the dual-value test before promotion to an active phase.


