# Career Intelligence Copilot

## Executive Summary

**Version:** 1.2 (Draft)

---

## Overview

Career Intelligence Copilot is an AI-powered career decision-support platform designed to help professionals make better career decisions through intelligent analysis, structured reasoning and evidence-based recommendations — while reducing the manual effort required to run an effective job search.

Unlike traditional career tools that focus on individual tasks such as CV generation or interview preparation, Career Intelligence Copilot provides an integrated workflow spanning opportunity assessment, application strategy, portfolio positioning, recruiter engagement and long-term career planning.

The platform treats career management as an ongoing decision-making process rather than a collection of disconnected activities.

---

## Immediate Objective

The current priority is to help the repository owner secure an appropriate AI Engineering role as quickly as reasonably possible.

Near-term work: Horizon 1A application loop is **complete**. Horizon 1B starts with
**FR-018 Opportunity Discovery & Acquisition** (scale lawful inflow into that loop),
then recruiter outreach and networking automation (FR-019+).

**Job acquisition first. Recruiter outreach second.** After 1A, scale opportunity
inflow before recruiter CRM.

The product should improve the likelihood of securing relevant interviews or offers and reduce repetitive administrative work. It does not guarantee employment, interviews, or recruiter engagement.

---

## Problem

Modern job searching is fragmented and administratively burdensome.

Professionals manage job boards, CVs, recruiter conversations, interview preparation, networking and career planning across multiple independent tools.

While AI has made it easier to generate content, it has done little to improve the quality of career decisions or reduce the repetition involved in assessing opportunities.

As a result, candidates often spend significant time applying for roles — and on repetitive analysis and tracking — without understanding which opportunities provide the greatest return on effort.

---

## Proposed Solution

Career Intelligence Copilot acts as an intelligent orchestration layer that combines career information from multiple sources into a unified decision-support system.

The platform evaluates opportunities, prioritises actions, explains recommendations and continuously adapts as career goals evolve. Where appropriate, it automates repetitive administrative work under human supervision — so users can spend less time managing their search and more time advancing their careers.

The objective is to improve career outcomes through structured reasoning and well-scoped automation, not unchecked automation of important decisions or externally visible actions.

---

## Key Capabilities

The platform will provide:

- Career profile management
- Intelligent job assessment
- Technical and commercial fit analysis
- Portfolio matching
- Tailored application generation (where it reduces effort and passes human review)
- Recruiter relationship management
- Interview preparation
- Career analytics and dashboards
- Market intelligence
- Daily prioritisation

Near-term delivery: Phase 2 Job Intelligence and document generation (FR-006/007) are
complete. Within Horizon 1A, job acquisition and workflow orchestration (FR-008), the
opportunity review queue, duplicate handling, and ranked recommendations (FR-009),
application package preparation (FR-010), application preparation orchestration
(FR-011), submission assistance (FR-012), application pipeline tracking (FR-013), and
**recruiter document truth validation (FR-014)** and **bounded agentic workflow
(FR-015)** are **complete and frozen**. **FR-016** Multi-Agent Orchestration is
**complete and frozen** as a learning proof only (**GO AS LEARNING PROOF ONLY** —
prefer `cic agent run` for ordinary prep; Engineering Learning Academy ready).
**FR-017** Agent Evaluation & Observability is **complete and frozen** (derive-only
orchestration evaluation; **Horizon 1B is not blocked on FR-017** —
[eval/fr017_agent_evaluation_observability.md](eval/fr017_agent_evaluation_observability.md)).
See [10_roadmap.md](10_roadmap.md).

---

## Expected Outcomes

Career Intelligence Copilot aims to help professionals:

- secure suitable roles sooner
- make better career decisions
- improve the likelihood of relevant interviews or offers
- reduce time spent on low-value and repetitive job-search activities
- increase professional visibility
- identify meaningful skill gaps
- focus effort where it has the greatest impact
- manage their career as an evolving long-term strategy

---

## Success Horizons

**Horizon 1 — Immediate:** Help the user secure a suitable AI Engineering role while reducing job-search effort.

- **1A (complete):** Job application workflow end to end (FR-008–FR-017 frozen)
- **1B (next, owner request):** Scaled acquisition and market engagement (FR-018–FR-025) —
  **FR-018 Opportunity Discovery & Acquisition** first; recruiter/network from FR-019

**Horizon 2 — Long term:** Evolve into a reusable Career Intelligence Platform supporting career progression, networking, learning, promotion, role changes, and future opportunity evaluation.

Horizon 1 takes priority whenever the two horizons compete. Within Horizon 1, 1A completes before 1B. Within 1B, opportunity discovery leads recruiter work.

---

## Design Philosophy

The platform follows a simple principle:

> **Optimise career outcomes, not career activity.**

Every recommendation should be evidence-based, commercially realistic and explainable.

Near-term capabilities should satisfy at least one of:

- improve the likelihood of securing relevant interviews or job offers
- reduce the manual effort required to run an effective job search

Capabilities that satisfy neither criterion should normally be deferred.
