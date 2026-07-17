# Functional Specification

## Purpose

The Career Intelligence Copilot shall provide intelligent decision support throughout the complete career lifecycle.

The immediate objective is to help the repository owner secure a suitable AI Engineering role sooner by improving opportunity selection and reducing repetitive job-search work.

The long-term objective is to evolve into a reusable Career Intelligence Platform supporting ongoing career progression.

Requirements are prioritised against two success horizons. Horizon 1 takes priority whenever horizons compete. Near-term capabilities should improve the likelihood of securing relevant interviews or offers, or reduce the manual effort required to run an effective job search.

The product is intelligence-first. Automation is in scope where it safely reduces repetitive administrative work. Important career decisions and externally visible actions must remain reviewable by the user.

The product does not guarantee employment, interviews, or recruiter engagement.

---

## Scope and Phasing

This specification describes the full platform capability set. Delivery is phased by roadmap.

**Phase 2 (Job Intelligence MVP)** is the first vertical slice. Its purpose is to improve opportunity selection and reduce repetitive job-analysis work. Phase 2 must not expand into the entire job-search platform.

### Phase 2 — In Scope

- FR-001 Career Profile
- FR-002 Job Analysis
- FR-003 Opportunity Assessment (scoped — see below)
- FR-004 Portfolio Matching
- FR-005 Application Strategy
- Job opportunity pipeline tracking
- Outcome logging for assessed opportunities
- Ranked comparison of open assessed opportunities

### Phase 2 — Out of Scope

- FR-006 CV Generation (deferred; tailor-yes/no guidance may be added as decision support)
- FR-007 Cover Letter
- FR-008 Recruiter Intelligence
- FR-009 Interview Preparation
- FR-010 Career Dashboard (full)
- FR-011 Market Intelligence
- FR-012 Daily Prioritisation (cross-domain)
- Automated job discovery or external platform integration
- Interview Probability and Recruiter Confidence scoring (insufficient data at launch)

### Post–Phase 2

Remaining functional requirements are scheduled per roadmap phases 3–8.

---

# Functional Requirements

## FR-001 Career Profile

**Phase:** 2

The system shall maintain a structured representation of the user's:

- experience
- skills
- projects
- certifications
- goals
- preferences

Acceptance Criteria

✓ User profile can be updated.

✓ Profile is available to every decision.

---

## FR-002 Job Analysis

**Phase:** 2

The system shall analyse job descriptions.

Extract:

- technologies
- responsibilities
- seniority
- location
- salary
- employment type
- required experience

Acceptance Criteria

✓ Technologies identified.

✓ Role classified.

✓ Salary extracted where available.

✓ Analysis reduces manual extraction effort compared to unassisted review.

---

## FR-003 Opportunity Assessment

**Phase:** 2 (scoped)

The system shall assess each opportunity and produce evidence-backed fit analysis.

### Phase 2 dimensions

- Technical Fit
- Commercial Fit
- Portfolio Fit

### Phase 2 synthesis output

- Assessment summary with explainable recommendation rationale

### Post–Phase 2 dimensions (deferred)

- Recruiter Confidence
- Interview Probability
- Strategic Value

Acceptance Criteria (Phase 2)

✓ All three Phase 2 fit dimensions assessed.

✓ Explanation generated with cited evidence from the job description and user profile.

✓ Assessment supports tier recommendation (FR-005).

---

## FR-004 Portfolio Matching

**Phase:** 2

The system shall identify the portfolio projects that best align with each opportunity.

Acceptance Criteria

✓ Projects ranked.

✓ Ranking explained.

---

## FR-005 Application Strategy

**Phase:** 2

The system shall recommend an application tier and effort investment.

Tiers:

- Platinum
- Gold
- Silver
- Skip

Acceptance Criteria

✓ Tier assigned.

✓ Time investment recommended.

✓ Rationale explains why the tier was assigned.

---

## FR-006 CV Generation

**Phase:** Post–Phase 2

The system shall generate tailored CVs when tailoring is materially beneficial and approved by the user.

Acceptance Criteria

✓ Summary rewritten.

✓ Skills reordered.

✓ Projects prioritised.

✓ Truthfulness maintained.

✓ Output requires user review before use.

---

## FR-007 Cover Letter

**Phase:** Post–Phase 2

Generate company-specific cover letters.

Acceptance Criteria

✓ References company.

✓ References role.

✓ References portfolio.

✓ Output requires user review before use.

---

## FR-008 Recruiter Intelligence

**Phase:** 3

Generate recruiter outreach.

Track recruiter history.

Recommend follow-ups.

All externally visible outreach must require user review before sending.

---

## FR-009 Interview Preparation

**Phase:** 7

Generate:

Recruiter interview.

Technical interview.

Behavioural interview.

Project walkthrough.

Questions to ask.

---

## FR-010 Career Dashboard

**Phase:** 8

Provide a live dashboard showing:

Applications.

Recruiters.

Visibility.

Portfolio.

Market trends.

Priority actions.

Phase 2 may provide a simple job opportunity list only; the full dashboard is out of scope for Phase 2.

---

## FR-011 Market Intelligence

**Phase:** 6

Track recurring technologies.

Recommend learning priorities.

Monitor salary trends.

---

## FR-012 Daily Prioritisation

**Phase:** 8 (full); partial in Phase 2

Recommend the highest-value activities for the day based on:

Career goals.

Outstanding tasks.

Interview opportunities.

Expected ROI.

Phase 2 supports ranked comparison of open assessed job opportunities only. Cross-domain daily prioritisation is deferred.

---

## FR-013 Outcome Logging

**Phase:** 2

The system shall allow the user to record outcomes for assessed and pursued opportunities.

Capture:

- user decision (apply / skip / defer)
- application status
- interview stage
- outcome (where known)

Acceptance Criteria

✓ Outcomes can be recorded against assessed opportunities.

✓ Outcome history is available to inform future assessments.

---

## Prioritisation Guidance

When scoping or implementing requirements, apply the dual-value test:

1. Does this capability improve the likelihood of securing relevant interviews or job offers?
2. Does this capability reduce the manual effort required to run an effective job search?

If neither applies, defer unless it is required infrastructure for a Phase 2 in-scope requirement.
