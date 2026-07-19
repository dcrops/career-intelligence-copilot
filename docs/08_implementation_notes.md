# Implementation Notes

Durable engineering notes for the implemented system. This document records data
provenance, intentional deviations from approved plans, and a backlog of known
improvements. It complements — and does not override — the authoritative documents in
[00_repository_guide.md](00_repository_guide.md).

---

## FR-001 Career Profile — Data Provenance

Every value in `data/career_profile.yaml` falls into one of three categories. Values that are
assumed/inferred are marked `OWNER-CONFIRM` in the profile until the owner confirms or corrects
them, because they influence real assessments (notably FR-003 Commercial Fit).

**Status: all flagged values were confirmed by the owner on 2026-07-19.** The Chase R&D start
date was corrected from the inferred 2023-11 to the owner-provided **2025-12**; goals,
locations, full-time employment, flexible remote arrangement, AUD currency with no salary
minimum, and the must-haves were confirmed as recorded.

### Confirmed from the Master CV

- Identity: full name, target role (AI Engineer), professional summary.
- Experience: nbn Australia — Data Engineer, Mar 2020 to Oct 2023 (organisation, title, dates,
  highlights, technologies). Classified `kind: employment`.
- Experience: Chase Risk & Compliance — AI Engineer, Independent Research & Development
  (organisation, title, highlights, technologies). Start date is inferred — see below.
  Classified `kind: independent_engineering`: an independent AI Engineering R&D and portfolio
  brand, not paid employment, consulting, or commercial delivery.
- Projects: Operational Intelligence Copilot, Governance-Aware Document Intelligence RAG,
  Payroll Diagnostics Engine, Public Holiday Entitlements Application — names, summaries,
  demonstrated capabilities, technologies, outcomes.
- Technical, domain, and soft skills, each traceable to a CV experience, project, or listed
  professional-development item.
- Certification: AWS Certified Developer - Associate.
- Location: Melbourne, VIC.

### Confirmed from project documentation

- Goals (`primary`, `secondary`, `horizon_notes`) are drawn from the product vision and
  roadmap (Horizon 1). They are consistent with the CV's direction but are the owner's
  objectives and still require owner endorsement.

### Assumed / inferred (owner-confirmed 2026-07-19)

| Value | Original inference | Outcome |
|-------|--------------------|---------|
| Chase R&D `start_date` | The CV states no date; inferred as 2023-11 (month after the nbn role ended). | **Corrected by owner to 2025-12.** |
| `preferences.locations` includes `Remote Australia` | Only Melbourne is on the CV; remote-Australia added as a plausible search scope. | Confirmed. |
| `preferences.employment_types: [full_time]` | Not stated on the CV. | Confirmed — full-time only. |
| `preferences.remote: flexible` | Not stated on the CV. | Confirmed. |
| `preferences.salary_currency: AUD` | Inferred from Australian location. `salary_min` left null. | Confirmed — no salary minimum. |
| `preferences.must_haves` | Inferred from the CV's stated career direction, not an explicit preference. | Confirmed; no deal-breakers added. |

Skill categorisation (technical / domain / soft) and the decision to record "professional
development" items (LangChain/LLM, Microsoft Fabric, Databricks, Snowflake, dbt, Azure Data
Factory) as skills rather than certifications are implementer judgments consistent with the
CV's own labelling; they are not value inventions.

### Career-history refinement (owner-directed, 2026-07-19)

The experience facet was refined so entries are typed by
`kind: employment | independent_engineering | professional_development` and the employer-only
field `company` was renamed `organisation`. Owner-provided timeline:

- **nbn Australia** (Mar 2020 – Oct 2023) — `employment`.
- **Data Engineering Professional Development and Career Transition**
  (Oct 2023 – Jun 2025) — `professional_development`; began with a personal break, then
  structured upskilling across Microsoft Fabric, Databricks, Snowflake, dbt, and Azure Data
  Factory.
- **AI Engineering Professional Development and Portfolio Development**
  (Jul 2025 – Nov 2025) — `professional_development`; deliberate pivot to AI Engineering.
- **Chase Risk & Compliance** (Dec 2025 – present) — `independent_engineering`; independent
  AI Engineering R&D and portfolio brand. Not employment, clients, revenue, consulting, or
  commercial delivery.

Skill evidence previously recorded under the informal `professional-development:master-cv`
namespace now cites the relevant professional-development experience IDs. No new top-level
career-phase ontology, separate collections, or project attribution links were introduced.

Deliberately not modelled (present on the CV, out of scope for decision support): contact
details, citizenship, and portfolio/GitHub URLs. These become relevant only for the deferred
CV-generation requirements.

### Accuracy and provenance refinement (owner-supplied, 2026-07-19)

The Master CV starts the professional history at nbn Australia and understated total
commercial technology experience. The pre-nbn history below is **not on the Master CV**; it
was supplied directly by the owner in an interactive confirmation session on 2026-07-19:

- **Bakers Delight** — Test Analyst (Mar 2009 – Jun 2012), `employment`. Role-level
  responsibilities were not provided; highlights are intentionally empty (flagged
  `OWNER-CONFIRM` in the profile) rather than invented.
- **Console** — Test Analyst (Jun 2012 – Dec 2014), `employment`. Ruby on Rails automation
  scripts, Agile ceremonies, Gherkin/Cucumber user-story tests.
- **Bakers Delight** — Test Analyst (Jan 2015 – Oct 2018), `employment`. POS replacement
  across 750 bakeries in 4 countries; automation framework; Selenium WebDriver with Java;
  Maven and Jenkins; test environments.
- **AccessHQ** — Test Analyst (Oct 2018 – Jun 2019), `employment`. Consultant to Public
  Transport Victoria (PTV): Selenium and API test suites for Myki/PTV systems, mobile and
  functional testing with Jira. Recorded under the employer AccessHQ, not the client PTV.
- **Bakers Delight** — Test Analyst (Aug 2019 – Sep 2019), `employment`. Short return
  engagement; title assumed to match the earlier role (flagged `OWNER-CONFIRM`).
- **General Assembly** — Data Science Immersive (Sep 2019 – Dec 2019),
  `professional_development`. Course projects (job-listing web scraping with NLP/predictive
  modelling; real-estate price analysis) are attributed here, not to Bakers Delight.

The professional summary now distinguishes total commercial technology experience (since
2009), the 3.5 years of commercial Data Engineering experience, and independent AI
Engineering/portfolio development. It does not claim commercial AI Engineering employment.

**Certifications.** `Certification` gained a required `status: active | expired` and an
optional `expiry_date` (`YYYY-MM`) so credentials are represented truthfully. Owner-supplied
statuses (2026-07-19): Databricks Certified Data Engineer Associate — **expired** Jul 2026;
Databricks Certified Data Engineer Professional — active until Aug 2026; AWS Certified
Developer - Associate — active until Sep 2026. The two Databricks credential names are
owner-supplied; the CV lists Databricks only as professional development. Note: an earlier
owner instruction described both AWS and Databricks certifications as expired; the owner
superseded this during the confirmation session by choosing the recorded expiry dates, under
which only the Databricks Associate credential has expired as of Jul 2026.

**PyTest at nbn** is owner-confirmed genuine usage during nbn employment and is retained as
nbn evidence.

---

## Deviations from the Approved FR-001 Plan

Both deviations are intentional and preserve the plan's intent; neither changes an
architectural decision, so ADR-001 is unchanged.

1. **Preference validation.** The plan listed a model validator: "preferences must include at
   least one location or an explicit remote preference." This was implemented structurally
   instead — `Preferences.remote` is a required field with no default, so an explicit remote
   preference is always present. The standalone validator was therefore removed as redundant.

2. **Inferred employment date placement.** The plan did not specify where to record inferred
   values. The Chase R&D start-date inference was initially written as an experience
   `highlight`; it has been moved to a YAML `OWNER-CONFIRM` comment so that `highlights`
   contains only genuine achievements and does not feed a meta-note into downstream portfolio
   or fit analysis.

---

## Future Improvements (Backlog)

Known, accepted technical debt from the FR-001 engineering review. These are intentionally
deferred, not defects. Evaluate against the dual-value test before promoting any item.

- **De-duplicate validation translation.** The `pydantic.ValidationError` to
  `ProfileValidationError` conversion exists in both `storage/yaml_store.py` and
  `profile/service.py`. Extract a single shared helper.
- **De-duplicate date parsing.** The `YYYY-MM` `parse_month` validator is repeated in
  `ExperienceEntry` and `Certification`. Extract a shared reusable validator or annotated type.
- **Install-safe default profile path.** `DEFAULT_PROFILE_PATH` assumes the editable repo
  layout (`parents[3]/data/...`) and the `data/` directory is not packaged. Resolve via
  packaged resources or require `CIC_PROFILE_PATH` before any non-editable install.
- **Evidence resolution.** Skill/`demonstrates` `evidence` strings are free text and are not
  checked against real experience/project IDs. (The informal
  `professional-development:master-cv` namespace was retired in the career-history refinement;
  all skill evidence now cites `experience:` or `project:` IDs.) FR-003/FR-004 — the first real
  consumers of evidence — may need referential validation.
- **Project attribution links.** Projects are not linked to the independent-engineering
  context that produced them. A `context_id` reference to an experience entry may aid
  explainability in FR-003/FR-004; deliberately excluded from the career-history refinement.
- **Profile load caching.** `get_section` and `summary` each re-read and re-parse the file.
  Acceptable for occasional interactive use; revisit if a downstream flow reads many sections
  per operation.
- **Typed section access.** `CareerProfileService.get_section` returns `Any`. Downstream
  consumers should prefer `load()` for full typing; consider typed accessors or overloads if a
  dynamic section API proves necessary.
