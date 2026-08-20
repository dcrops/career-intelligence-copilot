# Document Positioning M3 — Four-job CV positioning inspection

Offline inspection with `FixtureCvPositioningComposer`. Not live OpenAI. Not production `cic package prepare`. Not an M5 A/B evaluation. CSK live application package was not regenerated.

Shared candidate evidence: `data/career_profile.yaml` + `career-documents/cv/master_ai_engineer_cv.md`.

Project selection uses frozen golden `application_strategy.portfolio_emphasis` for E1/E3/E4. E2's tracked freeze is job analysis only, so emphasis falls back to live CareerProfile projects. Empty-emphasis wrappers were not used.

## Original Master summary

**Experienced engineer with 10+ years across testing, automation, data engineering and applied AI engineering.**

Applies software engineering discipline to build end-to-end AI applications with **Python, FastAPI, Docker, and OpenAI APIs**, with independent AI Engineering portfolio work across retrieval systems, operational intelligence, explainable AI, and enterprise decision support.

Applies a disciplined **AI Engineering methodology** — architecture-first design, evidence-based validation, and human-in-the-loop review — to build AI systems with traceable, reviewable outputs for operational decision-making.

---

# E1 — Allura AI Engineer

AI-lead. Python/REST/LLM DIRECT. GCP/MLOps/DevOps remain gaps. Methodology on.

## Positioned summary

AI Engineer building evidence-bounded applications, positioned for Allura Partners's ai engineering vacancy. Lead evidence is current AI Engineering work. Authorised capabilities include Python, REST APIs, LLM application development. Related platform evidence is Azure Data Factory; requested adjacent vendor services are not claimed as hands-on experience. Packed project evidence includes Governance-Aware Document Intelligence RAG, Career Intelligence Copilot.

## Selected highlights

- Designed and delivered a **portfolio of AI applications** combining deterministic logic with AI reasoning across RAG, operational intelligence, diagnostics, entitlements, and career decision support.
- Built modular service architectures with **FastAPI**, containerised services with **Docker**, and unit/regression suites in **PyTest**.
- Designed explainable, evidence-backed recommendation flows with traceable outputs rather than opaque model responses.
- Published architecture notes, testing approach, and working demonstrations through a public portfolio and GitHub repositories.

## Selected projects

- Governance-Aware Document Intelligence RAG (`governance-document-rag`)
- Career Intelligence Copilot (`career-intelligence-copilot`)

## Project relevance lines

- **Governance-Aware Document Intelligence RAG:** demonstrates Python delivery from packed independent portfolio evidence, not from unsupported employer tools.
- **Career Intelligence Copilot:** demonstrates Python delivery from packed independent portfolio evidence, not from unsupported employer tools.

## Methodology

- **include_methodology:** `True`
- Structured employer needs include evaluation, orchestration, governance, reliability, or equivalent methodology signals.
- Section present in Markdown: `True`

### Classifications used

- **Python** → DIRECT
- **Google Cloud** → UNSUPPORTED
- **REST APIs** → DIRECT
- **LLM** → DIRECT
- **MLOps** → UNSUPPORTED
- **DevOps** → UNSUPPORTED
- **data pipelines** → RELATED (promote Azure Data Factory; may_claim_requested=False)

## Evidence refs used

- `master_summary` (master_summary)
- `skill:Python` (skill)
- `experience:chase-risk-compliance-ai-engineer` (experience)
- `experience:nbn-data-engineer-2020` (experience)
- `skill:REST APIs` (skill)
- `project:public-holiday-entitlements` (project)
- `skill:LLM application development` (skill)
- `experience:ai-engineering-development-2025` (experience)
- `skill:Azure Data Factory` (skill)
- `experience:data-engineering-development-2023` (experience)

## Validation

Composer output passed M3 deterministic validators (fail-closed).
FR-014 was **not** run; this is not package Truth PASS.

---

# E2 — CSK mixed-fit specialist

RAG DIRECT. AWS RELATED for Bedrock; Bedrock not claimed. Chatbot gap. Methodology on.

## Positioned summary

AI Engineer building evidence-bounded applications, positioned for CSK Nexus Pty Ltd's ai engineering vacancy. Lead evidence is current AI Engineering work. Authorised capabilities include Python, Retrieval-Augmented Generation. Related platform evidence is AWS; requested adjacent vendor services are not claimed as hands-on experience. Packed project evidence includes Governance-Aware Document Intelligence RAG, Career Intelligence Copilot.

## Selected highlights

- Designed and delivered a **portfolio of AI applications** combining deterministic logic with AI reasoning across RAG, operational intelligence, diagnostics, entitlements, and career decision support.
- Built modular service architectures with **FastAPI**, containerised services with **Docker**, and unit/regression suites in **PyTest**.
- Designed explainable, evidence-backed recommendation flows with traceable outputs rather than opaque model responses.
- Published architecture notes, testing approach, and working demonstrations through a public portfolio and GitHub repositories.

## Selected projects

- Governance-Aware Document Intelligence RAG (`governance-document-rag`)
- Career Intelligence Copilot (`career-intelligence-copilot`)
- Operational Intelligence Copilot (`operational-intelligence-copilot`)

## Project relevance lines

- **Governance-Aware Document Intelligence RAG:** demonstrates Python delivery from packed independent portfolio evidence, not from unsupported employer tools.
- **Career Intelligence Copilot:** demonstrates Python delivery from packed independent portfolio evidence, not from unsupported employer tools.

## Methodology

- **include_methodology:** `True`
- Structured employer needs include evaluation, orchestration, governance, reliability, or equivalent methodology signals.
- Section present in Markdown: `True`

### Classifications used

- **AWS Bedrock** → RELATED (promote AWS; may_claim_requested=False)
- **Python** → DIRECT
- **RAG** → DIRECT
- **conversational ai** → UNSUPPORTED

## Evidence refs used

- `master_summary` (master_summary)
- `skill:AWS` (skill)
- `experience:nbn-data-engineer-2020` (experience)
- `certification:aws-certified-developer-associate` (certification)
- `skill:Python` (skill)
- `experience:chase-risk-compliance-ai-engineer` (experience)
- `skill:Retrieval-Augmented Generation` (skill)
- `project:governance-document-rag` (project)

## Validation

Composer output passed M3 deterministic validators (fail-closed).
FR-014 was **not** run; this is not package Truth PASS.

---

# E3 — Maincode AI Infrastructure

GPU/Linux/HPC stay gaps. Methodology off. Watch for over-positioning.

## Positioned summary

AI Engineer building evidence-bounded applications, positioned for Maincode's ai engineering vacancy. Lead evidence is current AI Engineering work. Authorised capabilities include AI Engineering. Packed project evidence includes Governance-Aware Document Intelligence RAG, Operational Intelligence Copilot.

## Selected highlights

- Designed and delivered a **portfolio of AI applications** combining deterministic logic with AI reasoning across RAG, operational intelligence, diagnostics, entitlements, and career decision support.
- Built modular service architectures with **FastAPI**, containerised services with **Docker**, and unit/regression suites in **PyTest**.
- Designed explainable, evidence-backed recommendation flows with traceable outputs rather than opaque model responses.
- Published architecture notes, testing approach, and working demonstrations through a public portfolio and GitHub repositories.

## Selected projects

- Governance-Aware Document Intelligence RAG (`governance-document-rag`)
- Operational Intelligence Copilot (`operational-intelligence-copilot`)
- Career Intelligence Copilot (`career-intelligence-copilot`)

## Project relevance lines

- **Governance-Aware Document Intelligence RAG:** demonstrates Python delivery from packed independent portfolio evidence, not from unsupported employer tools.
- **Operational Intelligence Copilot:** demonstrates Python delivery from packed independent portfolio evidence, not from unsupported employer tools.

## Methodology

- **include_methodology:** `False`
- Structured employer needs do not invoke evaluation, orchestration, governance, or equivalent methodology signals.
- Section present in Markdown: `False`

### Classifications used

- **GPU** → UNSUPPORTED
- **Linux** → UNSUPPORTED
- **HPC** → UNSUPPORTED

## Evidence refs used

- `master_summary` (master_summary)

## Validation

Composer output passed M3 deterministic validators (fail-closed).
FR-014 was **not** run; this is not package Truth PASS.

---

# E4 — Repurpose AI Adoption Specialist

full_chapters trajectory. Copilot/Claude unclaimed. Methodology on.

## Positioned summary

Software tester turned data engineer now building independent AI Engineering systems, applying for Repurpose It's ai adjacent vacancy. The hiring argument is the QA → data engineering → AI Engineering progression: commercial testing discipline, production data-platform work, then independent AI delivery. Authorised capabilities include AI Engineering. Packed project evidence includes Governance-Aware Document Intelligence RAG, Career Intelligence Copilot.

## Selected highlights

- Designed and delivered a **portfolio of AI applications** combining deterministic logic with AI reasoning across RAG, operational intelligence, diagnostics, entitlements, and career decision support.
- Designed explainable, evidence-backed recommendation flows with traceable outputs rather than opaque model responses.
- Built modular service architectures with **FastAPI**, containerised services with **Docker**, and unit/regression suites in **PyTest**.
- Published architecture notes, testing approach, and working demonstrations through a public portfolio and GitHub repositories.

## Selected projects

- Governance-Aware Document Intelligence RAG (`governance-document-rag`)
- Career Intelligence Copilot (`career-intelligence-copilot`)

## Project relevance lines

- **Governance-Aware Document Intelligence RAG:** demonstrates Python delivery from packed independent portfolio evidence, not from unsupported employer tools.
- **Career Intelligence Copilot:** demonstrates Python delivery from packed independent portfolio evidence, not from unsupported employer tools.

## Methodology

- **include_methodology:** `True`
- Structured employer needs include evaluation, orchestration, governance, reliability, or equivalent methodology signals.
- Section present in Markdown: `True`

### Classifications used

- **AI tools** → UNSUPPORTED
- **Copilot** → UNSUPPORTED
- **Claude** → UNSUPPORTED

## Evidence refs used

- `master_summary` (master_summary)

## Validation

Composer output passed M3 deterministic validators (fail-closed).
FR-014 was **not** run; this is not package Truth PASS.

---

# Quality notes (fixture inspection, not M5)

- The fixture writer is pack-faithful and explicit (`Authorised capabilities include …`). That is useful for validating policy and commercially weak. Live OpenAI composition exists as `OpenAICvPositioningComposer` but is **not wired** into package prepare in M3. Do not treat fixture wording as M5 recruiter preference.
- Fixture project relevance currently collapses to `demonstrates Python delivery…` even on RAG-heavy jobs. Policy-safe, repetitive, and under-positioned. A live writer must use packed project technologies without inventing employer tools.
- Highlight selection currently reorders existing Master bullets rather than inventing achievements. Across AI-family jobs the same four Master bullets often remain; that is bounded, not richly job-specific.
- E1 does not invent GCP/MLOps/DevOps. LLM is positioned from `LLM application development`, not as a RAG shortcut. ADF appears as RELATED evidence for data pipelines; that is catalogue-correct, not a GCP claim.
- E2 names AWS as related evidence and does not claim Bedrock experience. Chatbot/conversational AI is not claimed. RAG is DIRECT.
- E3 correctly omits methodology and does not name GPU/Linux/HPC. It still surfaces truthful AI/Python portfolio projects because those are the authorised CareerProfile evidence. That is not invented infrastructure employment, but the scan layer can still look stronger than the stretch role warrants. Watch this at M5.
- E4 leads with QA → DE → AI. Portfolio project *names* include the word Copilot (Career Intelligence Copilot); that is not a GitHub Copilot or Claude product claim. DIRECT claimable labels are thin because Copilot/Claude/AI tools are unsupported, so the pack leans on trajectory + Master summary.
- Project relevance lines are optional one-liners above locked project bodies. They were implemented, not deferred.
