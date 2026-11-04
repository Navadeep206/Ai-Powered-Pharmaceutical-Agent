# RootIQ: AI-Powered Root Cause Analysis & CAPA Platform
### Next-Generation Quality Intelligence for Pharmaceutical API Manufacturing

---

## 1. Overview & Product Purpose

**RootIQ** is an enterprise AI-augmented Root Cause Analysis (RCA) and Corrective and Preventive Action (CAPA) intelligence platform engineered specifically for **Active Pharmaceutical Ingredient (API)** manufacturing facilities.

In modern pharmaceutical manufacturing, deviations, Out-of-Specification (OOS) analytical results, and Out-of-Trend (OOT) process anomalies represent critical quality risks. RootIQ automates the labor-intensive stages of deviation triage, evidence cross-examination, and causal reasoning while enforcing strict compliance with **FDA 21 CFR Part 11**, **EU Annex 11**, **ICH Q9 (Quality Risk Management)**, and **ICH Q10 (Pharmaceutical Quality System)** regulations.

### Key Capabilities
- **Multi-Modal Evidence Corroboration:** Ingests and links Batch Manufacturing Records (BMR), SCADA/DCS sensor time-series, HPLC/GC chromatography data, and operator shift notes.
- **AI-Guided 6M Ishikawa & 5-Whys:** Orchestrates a multi-agent graph powered by **LangGraph** and **Groq** to construct structured causal trees categorized across Machine, Method, Material, Man, Measurement, and Milieu.
- **Closed-Loop S.M.A.R.T. CAPA:** Generates evidence-backed Corrective and Preventive Actions with automated effectiveness review metrics.
- **ALCOA+ GxP Data Integrity:** Built-in append-only audit trail and dual-authentication electronic signature verification.

---

## 2. System Architecture

RootIQ is organized as a decoupled, multi-tiered architecture:

```
[ Frontend: React 18 + Redux Toolkit + Tailwind CSS + Axios ]
                            │
                      REST / JSON API
                            ▼
[ Backend: Python FastAPI + Pydantic v2 + SQLAlchemy 2.0 Async ]
            │                                     │
            ▼                                     ▼
[ PostgreSQL 16 Persistence ]         [ LangGraph + Groq LLM Inference ]
  - Deviations & Investigations         - Multi-Agent StateGraph
  - 6M Causal Trees & CAPA Tasks        - 5-Whys Reasoning Chains
  - 21 CFR Part 11 Audit Trail          - GxP Quality Rule Validation
```

Detailed architectural diagrams, agent state graph flows, and data flow models are documented in [docs/architecture.md](docs/architecture.md).

---

## 3. Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Frontend** | React, Redux Toolkit, Tailwind CSS, Axios |
| **Backend API** | Python 3.11+, FastAPI, Pydantic v2 |
| **Database & ORM** | PostgreSQL 16, SQLAlchemy 2.0 (Async), Alembic |
| **AI Orchestration & LLM** | LangGraph, LangChain, Groq LPU (LLaMA 3.3 70B) |
| **Compliance & Security** | Python-JOSE (JWT), Passlib (Bcrypt), 21 CFR Part 11 E-Signatures |

---

## 4. Repository Structure & Module Responsibilities

```
AI-powered pharmaceutical RCA product/
├── .env.example             # Template for environment configurations and secrets
├── .gitignore               # Comprehensive Git ignore rules (OS, Node, Python, GxP)
├── README.md                # Project overview, purpose, and module guide
├── docs/
│   └── architecture.md      # Detailed system architecture and compliance specification
├── backend/
│   ├── requirements.txt     # Python dependency specifications
│   ├── app/
│   │   ├── __init__.py      # Backend package marker
│   │   ├── main.py          # FastAPI application entrypoint scaffold
│   │   ├── agents/          # LangGraph multi-agent RCA orchestration definitions
│   │   ├── api/
│   │   │   ├── __init__.py  # API routing package
│   │   │   └── routes/      # Sub-routers (auth, investigations, evidence, rca, capa, audit)
│   │   ├── core/            # Config, security policies, and application settings
│   │   ├── database/        # Database engine, sessionmaker, and base declarative models
│   │   ├── models/          # SQLAlchemy ORM domain entities (Deviation, CAPA, AuditLog)
│   │   ├── schemas/         # Pydantic request and response schemas
│   │   ├── services/        # Decoupled business logic services
│   │   └── utils/           # Analytical report parsers and cryptographic helpers
│   └── tests/               # Pytest suite and shared fixtures
└── frontend/
    └── src/
        ├── assets/          # Static brand assets, icons, and diagrams
        ├── components/
        │   ├── common/      # Reusable UI primitives (Buttons, Modals, Form inputs)
        │   ├── layout/      # Shell components (Header, Sidebar, Navigation)
        │   ├── dashboard/   # Executive summary widgets, KPI metrics, charts
        │   └── investigation/# Domain widgets (Ishikawa 6M diagram, 5-Whys tree)
        ├── pages/
        │   ├── Dashboard/          # Plant-level executive overview page
        │   ├── Investigations/    # Deviation triage and investigation list page
        │   ├── RCAWorkspace/       # Interactive root cause analysis workspace page
        │   ├── EvidenceAnalysis/   # Laboratory chromatography & sensor telemetry page
        │   └── CAPAManagement/     # Action item tracking & effectiveness review page
        ├── redux/
        │   └── slices/      # Redux Toolkit state slices (auth, investigation, rca, capa)
        ├── services/        # Axios API client instances and request interceptors
        ├── hooks/           # Custom React hooks encapsulating UI and domain logic
        └── utils/           # Frontend formatting, validation, and export helpers
```

### Module Responsibilities Breakdown

#### Frontend Modules (`frontend/src/`)
- **`components/common`**: Accessible, consistent UI building blocks adhering to pharma design standards.
- **`components/layout`**: Application scaffolding, responsive side navigation, and Part 11 active session indicators.
- **`components/dashboard`**: Visualization of plant deviation frequencies, cycle times, and open CAPA countdowns.
- **`components/investigation`**: Interactive canvas components for Ishikawa (Fishbone) diagrams and 5-Whys causal chains.
- **`pages/Dashboard`**: Executive level view of plant deviations, active investigations, and compliance status.
- **`pages/Investigations`**: Filterable list of open deviations, OOS alerts, batch lookups, and triage controls.
- **`pages/RCAWorkspace`**: Central investigative workspace integrating evidence previews, hypothesis generation, and agent reasoning.
- **`pages/EvidenceAnalysis`**: Deep-dive analytical view for comparing batch profiles, chromatography peaks, and SCADA process logs.
- **`pages/CAPAManagement`**: Corrective and Preventive Action planner with S.M.A.R.T. criteria validation and approval workflows.
- **`redux/slices`**: Centralized, predictable application state slices managing user auth, active investigations, causal trees, and audit state.
- **`services`**: Axios client layer configured with automatic bearer token attachment, error interceptors, and typed API calls.
- **`hooks`**: Reusable React hooks abstracting Redux dispatches, API polling, and digital signature modal workflows.
- **`utils`**: Date/time conversions (UTC/Local), input sanitization, and compliance formatting tools.

#### Backend Modules (`backend/app/`)
- **`agents`**: LangGraph graph definitions and agent roles (EvidenceExtractor, CausalHypothesis, RootCauseReasoner, CAPAPlanner, GxPCompliance).
- **`api/routes`**: RESTful endpoint routers mapping HTTP operations to backend services.
- **`core`**: Global configuration via Pydantic `BaseSettings`, token signing algorithms, and security constants.
- **`database`**: SQLAlchemy asynchronous session manager and engine pool configuration.
- **`models`**: Relational database entities representing the complete pharmaceutical manufacturing investigation domain.
- **`schemas`**: Request validation and response serialization schemas guaranteeing strict type safety.
- **`services`**: Pure business logic layer executing workflows independently of the web framework.
- **`utils`**: File parsers (HPLC report extractors, CSV readers) and cryptographic hashing utilities.
- **`tests`**: Integration and unit testing suite verifying business logic, agents, and compliance rules.

---

## 5. Configuration & Environment Variables

A template configuration file is provided at `.env.example`. 

Key configuration areas include:
- **Application**: Port, host, debug mode, and application secret keys.
- **Database**: PostgreSQL server, port, credentials, and asyncpg connection string.
- **Groq & LLM**: Groq API key, model selection (`llama-3.3-70b-versatile`), and generation parameters.
- **LangGraph**: LangSmith tracing endpoints and project configuration.
- **GxP Compliance**: Audit log switches, UTC enforcement, and signature validity windows.
- **Frontend**: Vite API base URL and runtime environment configuration.

---

## 6. Implementation Status & Next Steps

This project is currently at **Phase 1: Architectural Foundation**. 

Per the architectural specification:
- Directory trees and placeholder scaffolding are established.
- Dependencies, documentation, and environment templates are fully configured.
- No third-party packages have been installed and no live services have been started.

Phase 2 will proceed with database entity modeling, Alembic migrations, and Pydantic schema implementations upon instruction.

