# Career Profile Enrichment Report

**Status:** Complete  
**Date:** 2026-07-23  
**Scope:** Owner-confirmed data quality enrichment only — no FR-001 redesign, no FR-006 / planner changes.

---

## 1. Files modified

| File | Change |
|------|--------|
| `data/career_profile.yaml` | Added GA course technologies |
| `tests/fixtures/golden/career_profile.yaml` | Mirrored GA technologies |
| `tests/golden/test_profile_user_journey.py` | Assert GA techs present; historical techs not in Skills |
| `docs/08_implementation_notes.md` | Provenance note for enrichment sprint |
| `docs/11_changelog.md` | Version 1.18 |
| `docs/eval/career_profile_enrichment_report.md` | This report |

**Unchanged by design:** profile models/schema, FR-006 planner and ContactDetails code, certification URLs, project URLs, global Skills.

---

## 2. Factual additions made

On experience `general-assembly-data-science-2019` only:

```yaml
technologies:
  - Python
  - NLP
  - Web Scraping
```

Comment in YAML records that these are course techniques and must not be treated as current professional Skills.

---

## 3. Owner-confirmed data incorporated

| Item | How used |
|------|----------|
| General Assembly: NLP, Web Scraping | Added to that experience `technologies` list |
| Do not promote NLP / Web Scraping to Skills | Enforced by not editing `skills`; covered by golden test |
| Leave Java / Ruby on Rails / Gherkin experience-local | No Skills additions |
| Retain nbn AWS technologies | Left as already recorded (AWS, S3, Athena, Glue, Cloudwatch, DynamoDB, …) |
| Do not populate certification URLs | Left `url: null` |
| Personal links stay off Career Profile | Not written into YAML; documented for FR-006 `ContactDetails` |

Owner-confirmed personal links (for **CV contact overlay**, not profile storage):

- GitHub: `https://github.com/dcrops`
- Portfolio: `https://journey.chaseriskandcompliance.com.au/`
- LinkedIn: `https://www.linkedin.com/in/david-cropper/`

---

## 4. Data intentionally left unchanged

| Item | Reason |
|------|--------|
| `Project.url` (all four projects) | No per-project canonical URL was owner-confirmed in this sprint; schema keeps a single optional URL and was not redesigned |
| `Certification.url` / `date_obtained` | Owner deferred certification URLs |
| Global Skills | No promotions of historical or course-only technologies |
| Preferences, goals, identity | Out of scope |
| Bakers Delight 2009/2019 `OWNER-CONFIRM` flags | Still open |
| Schema / experience kinds / evidence_refs migration | Not required for this sprint |
| FR-006 planner / render behaviour | Explicitly out of scope |

**Project.url decision:** `Project.url` remains a single optional canonical link. Without owner-confirmed per-project destinations, filling it with the portfolio hub or inventing GitHub repo paths would be unsupported. Values stay `null`.

**Personal links decision:** FR-001 deliberately excludes contact/portfolio/GitHub from the Career Profile. No compelling reason to break that separation for MVP — FR-006 already accepts `ContactDetails`.

---

## 5. Test results

```text
597 passed
```

Full suite run after enrichment. Golden profile journey asserts:

- GA technologies == `Python`, `NLP`, `Web Scraping`
- `NLP`, `Web Scraping`, `Java`, `Ruby on Rails`, `Gherkin` absent from technical Skills

Backwards compatibility: schema_version `"1"` unchanged; no new fields; consumers that ignore experience-local technologies behave as before. FR-006 capability matching continues to use skills + project technologies only (experience-line techs excluded), so GA additions do not change CV emphasis ranking.

---

## 6. Documentation updates

- Changelog 1.18
- Implementation notes FR-001 provenance paragraph for this sprint
- This enrichment report

---

## 7. Remaining owner-confirmation items

1. Bakers Delight 2019 title (`OWNER-CONFIRM` still in YAML).
2. Bakers Delight 2009 highlights / technologies (intentionally empty).
3. Per-project canonical URLs (repo and/or live demo) for each of the four portfolio projects.
4. Whether any project should use the portfolio hub as its single `Project.url`.
5. Certification `date_obtained` values (urls deferred).
6. Preferences: salary_min vs tracker “expected” figures; company_stages; deal_breakers.
7. Optional `Skill.evidence_refs` migration from legacy evidence strings.
8. Optional project→experience `context_id` attribution (existing backlog).

---

## 8. Deferred until after MVP

- Multi-URL project model (repo + demo + portfolio on one entity)
- Moving GitHub / portfolio / LinkedIn onto the Career Profile
- Coursework as a top-level section
- Leadership / community experience entities
- Structured engineering-practices schema
- Promoting historical QA technologies into global Skills
- FR-006 behaviour changes driven by profile enrichment
- Phase C (LLM summary rewrite)
