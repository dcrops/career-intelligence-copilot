# Document Positioning M4 — Four-job cover-letter positioning inspection

Offline inspection with `FixtureCoverLetterPositioningComposer`. Not live OpenAI. Not production `cic package prepare`. Not an M5 A/B evaluation. CSK live application package was not regenerated.

Shared candidate evidence: `data/career_profile.yaml`.

PortfolioMatch ranks use frozen golden `application_strategy.portfolio_emphasis` for E1/E3/E4. E2's tracked freeze is job analysis only, so emphasis falls back to live CareerProfile project order.

---

# E1 — Allura AI Engineer

AI-lead opening. Python/REST/LLM DIRECT. GCP/MLOps/DevOps unclaimed. Testing history only if useful.

## Employer needs

### DIRECT / RELATED / UNSUPPORTED

- **Python** → DIRECT
- **Google Cloud** → UNSUPPORTED
- **REST APIs** → DIRECT
- **LLM** → DIRECT
- **MLOps** → UNSUPPORTED
- **DevOps** → UNSUPPORTED
- **data pipelines** → RELATED (promote Azure Data Factory; may_claim_requested=False)

## Selected evidence sources

- **Governance-Aware Document Intelligence RAG** (`project:governance-document-rag`, project)
  - Why selected: Selected because this project covers Python (direct), REST APIs (direct), LLM (direct). PortfolioMatch rank 2.
  - Employer need(s) covered: Python, REST APIs, LLM
  - PortfolioMatch rank 2
  - Override: PortfolioMatch rank 1 project 'Public Holiday Entitlements Application' was not selected. PositioningPlan need coverage preferred Governance-Aware Document Intelligence RAG (Python, REST APIs, LLM), Operational Intelligence Copilot (Python, REST APIs, LLM) over this project's overlap (Python, REST APIs).
- **Operational Intelligence Copilot** (`project:operational-intelligence-copilot`, project)
  - Why selected: Selected because this project covers Python (direct), REST APIs (direct), LLM (direct). PortfolioMatch rank 3.
  - Employer need(s) covered: Python, REST APIs, LLM
  - PortfolioMatch rank 3
  - Override: PortfolioMatch rank 1 project 'Public Holiday Entitlements Application' was not selected. PositioningPlan need coverage preferred Governance-Aware Document Intelligence RAG (Python, REST APIs, LLM), Operational Intelligence Copilot (Python, REST APIs, LLM) over this project's overlap (Python, REST APIs).

## PortfolioMatch overrides

- Rank 1 `public-holiday-entitlements` (Public Holiday Entitlements Application): PortfolioMatch rank 1 project 'Public Holiday Entitlements Application' was not selected. PositioningPlan need coverage preferred Governance-Aware Document Intelligence RAG (Python, REST APIs, LLM), Operational Intelligence Copilot (Python, REST APIs, LLM) over this project's overlap (Python, REST APIs).

## Trajectory / forbidden claims

- **trajectory_mode:** `ai_lead`
- Role family is ai_engineering, so positioning leads with AI evidence and does not use the QA→DE→AI chapter walk as the primary argument.
- **Forbidden claims:**
  - Google Cloud (unsupported)
  - MLOps (unsupported)
  - DevOps (unsupported)
  - data pipelines (related_unclaimable)
  - data pipeline (related_unclaimable)
  - etl (related_unclaimable)

## Generated fixture cover letter

Allura Partners's AI Engineer role is relevant because it asks for Python, REST APIs, LLM application development, which the packed evidence can support. The strongest truthful anchors are Governance-Aware Document Intelligence RAG and Operational Intelligence Copilot. Related platform grounding is Azure Data Factory; requested adjacent vendor services are not claimed as hands-on experience.

I developed Governance-Aware Document Intelligence RAG as independent portfolio work. Allows organisations to answer questions from their own documents with responses that stay grounded in source material. Built for teams that need trustworthy AI answers over policies, procedures, and knowledge bases — with evaluation and explainability controls. Packed technical evidence includes Python, FastAPI, Docker,…

I developed Operational Intelligence Copilot as independent portfolio work. Demonstrates operational intelligence capability for understanding business data. Combines reliable analytics with AI reasoning to surface anomalies and produce clear, evidence-backed executive insights that can be checked and trusted. Packed technical evidence includes Python, FastAPI, OpenAI APIs, PyTest. This answers employer need(s)…

This packed evidence is useful to Allura Partners's AI Engineer work because it answers the selected employer needs without overclaim.

## Validation

Composer output passed M4 deterministic validators (fail-closed).
FR-014 was **not** run; this is not package Truth PASS.

---

# E2 — CSK mixed-fit specialist

RAG / AI application lead. AWS RELATED for Bedrock; Bedrock and chatbot unclaimed.

## Employer needs

### DIRECT / RELATED / UNSUPPORTED

- **AWS Bedrock** → RELATED (promote AWS; may_claim_requested=False)
- **Python** → DIRECT
- **RAG** → DIRECT
- **conversational ai** → UNSUPPORTED

## Selected evidence sources

- **Governance-Aware Document Intelligence RAG** (`project:governance-document-rag`, project)
  - Why selected: Selected because this project covers Python (direct), RAG (direct). PortfolioMatch rank 3.
  - Employer need(s) covered: Python, RAG
  - PortfolioMatch rank 3
  - Override: PortfolioMatch rank 1 project 'Career Intelligence Copilot' was not selected. PositioningPlan need coverage preferred Governance-Aware Document Intelligence RAG (Python, RAG), Data Engineer — nbn Australia (AWS Bedrock, Python) over this project's overlap (Python).; PortfolioMatch rank 2 project 'Operational Intelligence Copilot' was not selected. PositioningPlan need coverage preferred Governance-Aware Document Intelligence RAG (Python, RAG), Data Engineer — nbn Australia (AWS Bedrock, Python) over this project's overlap (Python).
- **Data Engineer — nbn Australia** (`experience:nbn-data-engineer-2020`, employment)
  - Why selected: Selected because this employment covers AWS Bedrock (related).
  - Employer need(s) covered: AWS Bedrock, Python
  - no PortfolioMatch rank
  - Override: PortfolioMatch rank 1 project 'Career Intelligence Copilot' was not selected. PositioningPlan need coverage preferred Governance-Aware Document Intelligence RAG (Python, RAG), Data Engineer — nbn Australia (AWS Bedrock, Python) over this project's overlap (Python).; PortfolioMatch rank 2 project 'Operational Intelligence Copilot' was not selected. PositioningPlan need coverage preferred Governance-Aware Document Intelligence RAG (Python, RAG), Data Engineer — nbn Australia (AWS Bedrock, Python) over this project's overlap (Python).

## PortfolioMatch overrides

- Rank 1 `career-intelligence-copilot` (Career Intelligence Copilot): PortfolioMatch rank 1 project 'Career Intelligence Copilot' was not selected. PositioningPlan need coverage preferred Governance-Aware Document Intelligence RAG (Python, RAG), Data Engineer — nbn Australia (AWS Bedrock, Python) over this project's overlap (Python).
- Rank 2 `operational-intelligence-copilot` (Operational Intelligence Copilot): PortfolioMatch rank 2 project 'Operational Intelligence Copilot' was not selected. PositioningPlan need coverage preferred Governance-Aware Document Intelligence RAG (Python, RAG), Data Engineer — nbn Australia (AWS Bedrock, Python) over this project's overlap (Python).

## Trajectory / forbidden claims

- **trajectory_mode:** `ai_lead`
- Role family is ai_engineering, so positioning leads with AI evidence and does not use the QA→DE→AI chapter walk as the primary argument.
- **Forbidden claims:**
  - AWS Bedrock (related_unclaimable)
  - amazon bedrock (related_unclaimable)
  - bedrock (related_unclaimable)
  - conversational ai (unsupported)
  - customer support automation (unsupported)
  - customer support agents (unsupported)
  - conversational interfaces (unsupported)
  - virtual agents (unsupported)
  - chatbots (unsupported)
  - chatbot (unsupported)

## Generated fixture cover letter

CSK Nexus Pty Ltd's ai engineering role is relevant because it asks for Python, Retrieval-Augmented Generation, which the packed evidence can support. The strongest truthful anchors are Governance-Aware Document Intelligence RAG and Data Engineer — nbn Australia. Related platform grounding is AWS; requested adjacent vendor services are not claimed as hands-on experience.

I developed Governance-Aware Document Intelligence RAG as independent portfolio work. Allows organisations to answer questions from their own documents with responses that stay grounded in source material. Built for teams that need trustworthy AI answers over policies, procedures, and knowledge bases — with evaluation and explainability controls. Packed technical evidence includes Python, FastAPI, Docker,…

Commercial evidence from Data Engineer — nbn Australia: Data Engineer at nbn Australia. Packed technical evidence includes Python, SQL, AWS, S3. This is RELATED transfer evidence: the packed profile capability is promoted and the requested vendor identity is not claimed.

This packed evidence is useful to CSK Nexus Pty Ltd's ai engineering work because it answers the selected employer needs without overclaim.

## Validation

Composer output passed M4 deterministic validators (fail-closed).
FR-014 was **not** run; this is not package Truth PASS.

---

# E3 — Maincode AI Infrastructure

Stretch-control. GPU/Linux/HPC stay gaps. Do not present as an infrastructure engineer.

## Employer needs

### DIRECT / RELATED / UNSUPPORTED

- **GPU** → UNSUPPORTED
- **Linux** → UNSUPPORTED
- **HPC** → UNSUPPORTED

## Selected evidence sources

- **Operational Intelligence Copilot** (`project:operational-intelligence-copilot`, project)
  - Why selected: Selected as truthful project evidence when remaining employer needs were unsupported or already covered.
  - Employer need(s) covered: none listed
  - PortfolioMatch rank 1
- **Governance-Aware Document Intelligence RAG** (`project:governance-document-rag`, project)
  - Why selected: Selected as truthful project evidence when remaining employer needs were unsupported or already covered.
  - Employer need(s) covered: none listed
  - PortfolioMatch rank 2

## PortfolioMatch overrides

- None for this job.

## Trajectory / forbidden claims

- **trajectory_mode:** `ai_lead`
- Role family is ai_engineering, so positioning leads with AI evidence and does not use the QA→DE→AI chapter walk as the primary argument.
- **Forbidden claims:**
  - GPU (unsupported)
  - Linux (unsupported)
  - HPC (unsupported)

## Generated fixture cover letter

Maincode's AI Infrastructure Engineer role is relevant because it asks for packed AI Engineering work, which the packed evidence can support. The strongest truthful anchors are Operational Intelligence Copilot and Governance-Aware Document Intelligence RAG.

I developed Operational Intelligence Copilot as independent portfolio work. Demonstrates operational intelligence capability for understanding business data. Combines reliable analytics with AI reasoning to surface anomalies and produce clear, evidence-backed executive insights that can be checked and trusted. Packed technical evidence includes Python, FastAPI, OpenAI APIs, PyTest. This is packed supporting…

I developed Governance-Aware Document Intelligence RAG as independent portfolio work. Allows organisations to answer questions from their own documents with responses that stay grounded in source material. Built for teams that need trustworthy AI answers over policies, procedures, and knowledge bases — with evaluation and explainability controls. Packed technical evidence includes Python, FastAPI, Docker,…

This packed evidence is useful to Maincode's AI Infrastructure Engineer work because it answers the selected employer needs without overclaim. I do not claim GPU, Linux, or HPC employment; the packed case is applied AI and Python delivery only.

## Validation

Composer output passed M4 deterministic validators (fail-closed).
FR-014 was **not** run; this is not package Truth PASS.

---

# E4 — Repurpose AI Adoption Specialist

full_chapters. QA → DE → AI useful. Copilot/Claude unclaimed.

## Employer needs

### DIRECT / RELATED / UNSUPPORTED

- **AI tools** → UNSUPPORTED
- **Copilot** → UNSUPPORTED
- **Claude** → UNSUPPORTED

## Selected evidence sources

- **QA → data engineering → AI Engineering trajectory** (`trajectory:career-chapters`, trajectory)
  - Why selected: Career trajectory is the hiring argument (full_chapters); portfolio evidence supports it rather than replacing it.
  - Employer need(s) covered: none listed
  - no PortfolioMatch rank
  - Override: PortfolioMatch rank 2 project 'Operational Intelligence Copilot' was not selected because it does not cover remaining high-priority employer needs. Selected instead: QA → data engineering → AI Engineering trajectory (no remaining need overlap), Governance-Aware Document Intelligence RAG (no remaining need overlap).
- **Governance-Aware Document Intelligence RAG** (`project:governance-document-rag`, project)
  - Why selected: Selected as truthful project evidence when remaining employer needs were unsupported or already covered.
  - Employer need(s) covered: none listed
  - PortfolioMatch rank 1

## PortfolioMatch overrides

- Rank 2 `operational-intelligence-copilot` (Operational Intelligence Copilot): PortfolioMatch rank 2 project 'Operational Intelligence Copilot' was not selected because it does not cover remaining high-priority employer needs. Selected instead: QA → data engineering → AI Engineering trajectory (no remaining need overlap), Governance-Aware Document Intelligence RAG (no remaining need overlap).

## Trajectory / forbidden claims

- **trajectory_mode:** `full_chapters`
- Role family is AI-adjacent and the profile has testing, data-engineering, and independent AI chapters, so the career trajectory is the hiring argument.
- **Forbidden claims:**
  - AI tools (unsupported)
  - Copilot (unsupported)
  - Claude (unsupported)

## Generated fixture cover letter

Repurpose It's AI Adoption Specialist role is a fit for a tester-to-data-engineer-to-AI-engineer path, not a generic application. The strongest truthful anchors are QA → data engineering → AI Engineering trajectory and Governance-Aware Document Intelligence RAG.

Commercial software testing/automation as Test Analyst at Bakers Delight. Commercial data engineering as Data Engineer at nbn Australia. Current independent AI Engineering as AI Engineer - Independent Research & Development at Chase Risk & Compliance. Testing discipline and human review remain relevant to adoption and reliability work.

I developed Governance-Aware Document Intelligence RAG as independent portfolio work. Allows organisations to answer questions from their own documents with responses that stay grounded in source material. Built for teams that need trustworthy AI answers over policies, procedures, and knowledge bases — with evaluation and explainability controls. Packed technical evidence includes Python, FastAPI, Docker,…

This packed evidence is useful to Repurpose It's AI Adoption Specialist work because it answers the selected employer needs without overclaim.

## Validation

Composer output passed M4 deterministic validators (fail-closed).
FR-014 was **not** run; this is not package Truth PASS.

---

# Quality notes (fixture inspection, not M5)

- The fixture writer is pack-faithful and explicit. That is useful for validating policy and commercially weak. Do not treat fixture wording as recruiter-quality or as M5 preference evidence.
- Openings name the employer/role family and packed DIRECT capabilities. They avoid 'I am excited to apply'. They are still formulaic.
- E1 leads with AI evidence rather than a QA → DE → AI biography. GCP/MLOps/DevOps are not claimed. Related ADF/data-pipeline evidence is not forced into the letter when it is a late RELATED need. Rank-1 Public Holiday Entitlements is overridden because RAG/OIC cover more DIRECT needs. CIC is not the second source because it lacks FastAPI/REST overlap; that is inspectable coverage, not a ranking accident.
- E2 selects Governance RAG for DIRECT RAG/Python and nbn AWS employment for RELATED Bedrock coverage. Bedrock and chatbot are not claimed. The raw posting title (which lists Bedrock and Chatbots) is not pasted into prose; `prose_role_title` falls back to the role family.
- E3 does not claim GPU/Linux/HPC. It still surfaces truthful AI/Python portfolio evidence because those are authorised CareerProfile sources. That is not invented infrastructure employment, but the letter can still look stronger than a stretch role warrants. Watch this at M5.
- E4 uses `full_chapters`. Copilot/Claude are not claimed. Portfolio evidence supports the trajectory rather than replacing it.
- Evidence-source count is two by default; a third source appears only when a remaining high-priority DIRECT/RELATED need is uncovered.
- Production `cic package prepare` still uses the pre-M4 bounded cover-letter path (`BoundedCoverLetterService` + tag/concern project selection). M4 is implemented and unwired. M6 owns production integration.
