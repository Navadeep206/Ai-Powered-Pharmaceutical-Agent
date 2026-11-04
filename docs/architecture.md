# RootIQ: AI-Powered Pharmaceutical Root Cause Analysis (RCA) & CAPA Platform
## Technical Architecture & Engineering Specification

---

### 1. Executive Summary & Product Purpose

#### 1.1 Problem Statement
Active Pharmaceutical Ingredient (API) manufacturing operates under rigorous regulatory oversight where deviations, Out-of-Specification (OOS) results, and Out-of-Trend (OOT) excursions can compromise drug safety, cause multimillion-dollar batch rejections, and incur severe regulatory scrutiny (e.g., FDA Form 483s or Warning Letters). 

Traditional Root Cause Analysis (RCA) and Corrective and Preventive Action (CAPA) processes suffer from:
- **Disparate Data Silos:** Critical Process Parameters (CPPs) from SCADA/DCS systems, Critical Quality Attributes (CQAs) from LIMS, chromatography reports (HPLC, GC-MS), and paper/electronic Batch Manufacturing Records (BMRs) are disconnected.
- **Cognitive Bias & Superficial Root Causes:** Investigations frequently conclude with generic "human error" or "operator retraining," failing to identify systemic failure modes across the 6M categories (Machine, Method, Material, Man, Measurement, Milieu).
- **Delayed Cycle Times:** Regulatory standards mandate deviation closure within 30 calendar days. Manual data aggregation and hypothesis testing consume 60-80% of this window.
- **Inadequate CAPA Effectiveness:** Preventive actions fail to address true latent causes, leading to recurring deviations and non-compliance.

#### 1.2 Product Purpose: RootIQ
**RootIQ** is an enterprise-grade, AI-augmented RCA and CAPA intelligence platform specifically tailored for pharmaceutical API manufacturing plants. RootIQ bridges the gap between raw plant telemetry, analytical lab reports, and regulatory compliance by orchestrating a specialized multi-agent graph (LangGraph + Groq) to:
1. Ingest, parse, and cross-correlate multi-modal batch records, analytical chromatography data, and environmental monitoring logs.
2. Construct deterministic Ishikawa (Fishbone) 6M models and dynamic 5-Whys causal graphs supported by verifiable empirical evidence.
3. Formulate robust, S.M.A.R.T. CAPA plans with automated effectiveness tracking metrics.
4. Enforce strict **FDA 21 CFR Part 11**, **EU GMP Annex 11**, and **ICH Q9 (Quality Risk Management)** / **ICH Q10 (Pharmaceutical Quality System)** compliance with immutable audit trails and electronic signatures.

---

### 2. High-Level System Architecture

RootIQ utilizes a modern decoupled micro-service / modular-monolith architecture designed for high availability, low latency, and uncompromising data integrity.

```
+---------------------------------------------------------------------------------------+
|                                    PRESENTATION TIER                                  |
|  React 18 SPA | Redux Toolkit | Tailwind CSS | Axios | Responsive Enterprise UI       |
|  - Executive Dashboard           - Evidence Analysis (HPLC/GC/SCADA)                  |
|  - Deviation & OOS Triage       - Interactive RCA Workspace (Ishikawa / 5-Whys)      |
|  - CAPA Lifecycle Management     - 21 CFR Part 11 Digital Sign-off Modal              |
+-------------------------------------------+-------------------------------------------+
                                            | JSON / REST via HTTPS
                                            v
+---------------------------------------------------------------------------------------+
|                                  API GATEWAY & SECURITY                               |
|  FastAPI Gateway (Uvicorn / ASGI)                                                     |
|  - JWT Bearer Authentication & Role-Based Access Control (RBAC)                       |
|  - 21 CFR Part 11 E-Signature Verification & ALCOA+ Audit Interceptor                 |
|  - Pydantic v2 Request/Response Validation & Sanitization                             |
+-------------------------------------------+-------------------------------------------+
                                            |
                    +-----------------------+-----------------------+
                    |                                               |
                    v                                               v
+---------------------------------------+   +---------------------------------------+
|           APPLICATION SERVICES        |   |      LANGGRAPH MULTI-AGENT ENGINE     |
|  Python 3.11 Business Logic Layer     |   |  StateGraph Orchestrator (Groq LPUs)  |
|  - Investigation Workflow Service     |   |                                       |
|  - Evidence Parsing & Indexing        |<->|  [ EvidenceExtractorAgent ]           |
|  - RCA Graph State Management         |   |            |                          |
|  - CAPA Tracking & Verification       |   |  [ CausalHypothesisAgent (6M) ]       |
|  - GxP Audit Trail Log Service        |   |            |                          |
+-------------------+-------------------+   |  [ RootCauseReasonerAgent (5-Whys) ]  |
                    |                       |            |                          |
                    | SQLAlchemy 2.0 Async  |  [ CAPAPlannerAgent (S.M.A.R.T.) ]    |
                    v                       |            |                          |
+---------------------------------------+   |  [ GxPComplianceAgent (ICH Q9/Q10) ]  |
|            PERSISTENCE TIER           |   +---------------------------------------+
|  PostgreSQL 16 Enterprise             |
|  - Deviations, Batches, & OOS Records |
|  - Causal Nodes & 6M Relationship JSON|
|  - CAPA Actions & Effectiveness Logs  |
|  - Append-Only Cryptographic Audit Log|
+---------------------------------------+
```

---

### 3. Technology Stack & Architectural Justification

| Layer | Technology | Version | Technical Justification |
| :--- | :--- | :--- | :--- |
| **Frontend Framework** | **React** | `^18.3.0` | Declarative component model, virtual DOM for high-frequency interactive canvas rendering (Fishbone diagrams, node trees). |
| **State Management** | **Redux Toolkit** | `^2.2.0` | Deterministic centralized state store, immutable updates via Immer, ideal for multi-step GxP deviation workflows and undo/redo capabilities. |
| **Styling & Design** | **Tailwind CSS** | `^3.4.0` | Utility-first CSS providing accessible, consistent, design-system-driven styling for high-density pharmaceutical data displays. |
| **HTTP Client** | **Axios** | `^1.7.0` | Robust request/response interceptors for automatic JWT renewal, request tracing, and standardized error handling. |
| **Backend Framework** | **FastAPI** | `^0.115.0` | High-performance asynchronous Python web framework with native OpenAPI schema generation and tight Pydantic integration. |
| **Data Validation** | **Pydantic** | `^2.8.0` | Strict data parsing, type coercion, and schema validation ensuring zero malformed payloads enter GxP workflows. |
| **ORM / Data Access** | **SQLAlchemy** | `^2.0.32` | Asynchronous ORM utilizing `asyncpg` for non-blocking I/O, complex relational mapping, and unit-of-work patterns. |
| **Agentic Framework** | **LangGraph** | `^0.2.20` | Graph-based cyclic agent orchestration enabling multi-actor state machines, human-in-the-loop checkpoints, and branching reasoning paths. |
| **LLM Inference** | **Groq LPU** | `^0.11.0` | Ultra-low latency inference engine powering LLaMA 3.3 70B models, enabling near real-time interactive causal graph generation. |
| **Primary Database** | **PostgreSQL** | `16+` | Enterprise ACID compliance, robust indexing, native JSONB support for complex graph representations, and strict audit logging. |

---

### 4. Module Responsibilities & Directory Layout

#### 4.1 Frontend Architecture (`frontend/src`)

- **`assets/`**: Static media assets, pharmaceutical equipment iconography, certified SVG emblems, and company branding.
- **`components/common/`**: Reusable design system primitives: buttons, input fields, modals, table controls, GxP warning badges, and loading skeletons.
- **`components/layout/`**: Structural shell components: top navigation bar with user session details, sidebar navigation, breadcrumbs, and 21 CFR Part 11 status banners.
- **`components/dashboard/`**: High-level manufacturing analytics widgets: deviation distribution charts, active OOS counters, CAPA overdue warning widgets, and batch risk matrices.
- **`components/investigation/`**: Domain-specific interactive UI elements:
  - *IshikawaDiagram*: SVG/Canvas interactive 6M fishbone diagram.
  - *FiveWhysTree*: Recursive node editor displaying causal depth.
  - *EvidenceDrawer*: File viewer for HPLC chromatograms, SCADA time-series, and operator statements.
- **`pages/Dashboard/`**: Executive cockpit monitoring manufacturing plants, active investigations, and regulatory metrics.
- **`pages/Investigations/`**: Master deviation log, triage list, filtering by severity (Critical, Major, Minor), and investigation creation wizard.
- **`pages/RCAWorkspace/`**: Core investigation workbench combining evidence panels, agent-assisted causal brainstorming, and hypothesis validation.
- **`pages/EvidenceAnalysis/`**: Analytical laboratory data correlation screen, comparing deviation batches against historical golden batches.
- **`pages/CAPAManagement/`**: Action tracker enforcing RACI assignments, verification schedules, and post-implementation effectiveness evaluation.
- **`redux/slices/`**: Redux state slices partitioned by domain:
  - `authSlice`: User credentials, token lifetimes, permissions.
  - `investigationSlice`: Active investigation state, stage progress, metadata.
  - `rcaSlice`: Ishikawa nodes, 5-Whys causal hierarchy, hypothesis scores.
  - `capaSlice`: Action items, milestones, effectiveness metrics.
  - `auditSlice`: Session actions, digital signature prompts, audit logs.
- **`services/`**: Axios client configuration, API endpoints abstraction, interceptors injecting bearer tokens and audit metadata.
- **`hooks/`**: Custom React hooks (`useAuth`, `useRCA`, `useEvidence`, `useAuditSign`) encapsulating business logic and Redux selectors.
- **`utils/`**: Helper utilities for UTC date formatting, GxP string validation, CSV/PDF export generation, and mathematical calculations.

#### 4.2 Backend Architecture (`backend/app`)

- **`main.py`**: ASGI application factory, lifespan management, middleware registration (CORS, Request ID, Audit Interceptor), and API router aggregation.
- **`api/routes/`**: Route controllers organized by resource domain:
  - `auth.py`: Authentication, MFA challenge, and 21 CFR Part 11 signing token generation.
  - `investigations.py`: CRUD operations, status state transitions, and deviation triage.
  - `evidence.py`: Evidence artifact upload, multi-modal file ingestion, and parsing endpoints.
  - `rca.py`: Causal graph persistence, Ishikawa category assignment, and 5-Whys updates.
  - `capa.py`: CAPA creation, assignment, verification checklists, and effectiveness reviews.
  - `audit.py`: Querying immutable audit records and generating regulatory inspection exports.
- **`agents/`**: LangGraph agent definitions, graph state schemas, prompt templates, and reasoning chains.
- **`core/`**: Central application configurations (`config.py`), cryptographic utilities, JWT token encoding, and custom exception handlers.
- **`database/`**: Async engine initialization, connection pooling configurations, session dependency providers, and Base declarative model classes.
- **`models/`**: SQLAlchemy declarative ORM models defining database schema:
  - `User`, `Role`, `Permission`: Identity and authorization.
  - `Deviation`, `BatchRecord`: Deviation events, batch numbers, API product identifiers.
  - `Investigation`: The primary investigation lifecycle entity.
  - `EvidenceArtifact`: Attached chromatography files, sensor logs, and lab notes.
  - `RCANode`, `CausalEdge`: Graph structures for Ishikawa 6M and 5-Whys.
  - `CAPAAction`, `EffectivenessReview`: Remediation tracking entities.
  - `AuditLog`: Immutable, append-only GxP audit trail table.
- **`schemas/`**: Pydantic models for incoming request validation and outgoing JSON responses.
- **`services/`**: Pure business logic layer decoupled from HTTP transport.
- **`utils/`**: Reusable backend utilities: analytical document extractors, datetime converters, cryptographic hashers.

---

### 5. LangGraph Multi-Agent RCA & CAPA Workflow

The intelligence engine employs a coordinated multi-agent workflow defined via LangGraph and powered by Groq LPU inference.

```
                  +-------------------------------+
                  |  Investigation Triggered      |
                  |  (Deviation / OOS Ingested)   |
                  +---------------+---------------+
                                  |
                                  v
                  +-------------------------------+
                  |    EvidenceExtractorAgent     |
                  |  Parses BMR, HPLC, SCADA logs |
                  +---------------+---------------+
                                  |
                                  v
                  +-------------------------------+
                  |    CausalHypothesisAgent      |
                  |  Classifies into Ishikawa 6M  |
                  +---------------+---------------+
                                  |
                                  v
                  +-------------------------------+
                  |    RootCauseReasonerAgent     |
                  |  Recursive 5-Whys Drilldown   |
                  |  Calculates Evidence Support  |
                  +---------------+---------------+
                                  |
                                  v
                  +-------------------------------+
                  |    Human-in-the-Loop Review   |
                  |  Subject Matter Expert Valid. |
                  +---------------+---------------+
                                  |
                                  v
                  +-------------------------------+
                  |       CAPAPlannerAgent        |
                  |  Generates S.M.A.R.T. Actions |
                  +---------------+---------------+
                                  |
                                  v
                  +-------------------------------+
                  |      GxPComplianceAgent       |
                  |  Verifies ICH Q9/Q10 Standards|
                  |  Prepares 21 CFR 11 E-Sign    |
                  +-------------------------------+
```

#### Agent Roles & Responsibilities:
1. **EvidenceExtractorAgent**:
   - Parses unstructured operator shift logs, structured batch records, and analytical outputs (e.g., peak area discrepancies in HPLC chromatograms).
   - Extracts key parameters: Temperature, Agitation Speed, pH, Solvent Addition Rates, Impurity Profiles.
2. **CausalHypothesisAgent**:
   - Projects potential failure modes onto the standard pharmaceutical **6M Ishikawa Framework**:
     - *Machine*: Reactor seal degradation, sensor drift, impeller wear.
     - *Method*: Inadequate stir time, incorrect ramp rate, ambiguous SOP wording.
     - *Material*: Raw material lot variation, solvent water content, reagent purity.
     - *Man*: Shift handover omission, manual charging timing variation.
     - *Measurement*: HPLC column fouling, uncalibrated pH probe, sample prep error.
     - *Milieu (Environment)*: Cleanroom humidity spike, HVAC differential pressure drop.
3. **RootCauseReasonerAgent**:
   - Performs iterative 5-Whys traversal on the most plausible causal pathways.
   - Cross-references hypothesis against plant telemetry to assign an empirical confidence score ($0.0 - 1.0$).
4. **CAPAPlannerAgent**:
   - Converts confirmed root causes into actionable CAPA pairs:
     - *Corrective Action*: Immediate containment and remediation of affected batches.
     - *Preventive Action*: Long-term engineering controls, SOP revisions, or automated interlocks.
   - Enforces S.M.A.R.T. criteria (Specific, Measurable, Achievable, Relevant, Time-bound).
5. **GxPComplianceAgent**:
   - Verifies completeness against ICH Q9 Quality Risk Management principles.
   - Flags regulatory risks and generates pre-signature verification summaries for Quality Assurance review.

---

### 6. Regulatory Compliance & Data Integrity (ALCOA+ & 21 CFR Part 11)

RootIQ is built from the foundation up to satisfy the stringent requirements of pharmaceutical GxP environments:

1. **Attributable**:
   - Every system interaction is cryptographically tied to a verified user identity.
   - No generic or shared accounts.
2. **Legible**:
   - Audit logs are stored in standardized, human-readable formats with deterministic timestamps.
3. **Contemporaneous**:
   - System records actions immediately at the time of execution via automated server-side interceptors.
4. **Original**:
   - Primary evidence documents (e.g., raw chromatography files) are fingerprinted with SHA-256 hashes upon upload.
5. **Accurate**:
   - Input boundaries are strictly validated via Pydantic schemas; all modifications require explicit justification reasons.
6. **21 CFR Part 11 Electronic Signatures**:
   - Digital sign-off requires dual authentication (username/password re-entry or MFA token).
   - Signatures capture: Signer Identity, Timestamp (UTC), and Meaning of Signature (e.g., "Review", "Approval", "Authorship").
   - Signed records are sealed and rendered immutable.

---

### 7. Phased Implementation Roadmap

- **Phase 1: Architectural Foundation & Project Scaffolding** *(Current)*
  - Establish complete repository structure, module boundaries, documentation, and configuration templates.
- **Phase 2: Core Data Layer & Entity Modeling**
  - Implement SQLAlchemy ORM models, Alembic migration scripts, and Pydantic schemas.
- **Phase 3: Backend API & Service Layer**
  - Implement FastAPI routing, 21 CFR Part 11 audit interceptors, and authentication services.
- **Phase 4: LangGraph Multi-Agent Reasoning Engine**
  - Construct LangGraph StateGraph, integrate Groq LPU API, and implement agent prompt chains.
- **Phase 5: Frontend State & UI Workspace**
  - Build React components, Redux Toolkit slices, interactive Ishikawa canvas, and CAPA management screens.
- **Phase 6: Integration, GxP Validation & Verification**
  - End-to-end integration tests, 21 CFR Part 11 validation scripts, and performance benchmarking.

