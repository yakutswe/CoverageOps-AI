# CoverageOps AI

### Evidence-first insurance intelligence · Multi-agent workflows · Human-in-the-loop review

CoverageOps AI is a full-stack insurance operations platform prototype that evaluates structured policy information against contractual coverage requirements, identifies coverage gaps, and coordinates human review.

The project demonstrates how agent-oriented architecture, deterministic validation, workflow orchestration, and persistent audit records can work together in a high-stakes domain where accuracy, traceability, and human oversight matter.

**Status:** Working local prototype using synthetic insurance data.

## Product Preview

CoverageOps AI includes an operational dashboard with:

- **Operations Overview** — workflow status, agent activity, pending reviews, and customer follow-ups.
- **AI Agent Performance** — visibility into policy analysis, coverage comparison, and evaluation stages.
- **Human Reviews** — workflow handoffs and recorded specialist decisions.
- **Coverage Findings** — structured policy discrepancies and supporting workflow evidence.
- **Live / Demo Mode** — distinguishes PostgreSQL-backed workflow information from illustrative sample data.
- **Customer Onboarding** — creates workflows through the FastAPI backend.

The dashboard is designed to surface actionable findings rather than treating AI-generated output as a final insurance determination.

## Example: Detecting a Coverage Gap

A synthetic logistics customer submits structured General Liability insurance information.

| Coverage attribute | Value |
|---|---|
| Policy limit | $1,000,000 |
| Contractual requirement | $2,000,000 |
| Identified shortfall | $1,000,000 |
| Result | Below requirement |
| Specialist decision | Request changes |
| Workflow status | Awaiting customer |

The coverage comparison identifies the deficiency, records its finding, and routes the case through the human-review workflow.

The reviewer decision and associated workflow events remain available for traceability.

## Architecture

```text
Next.js Dashboard
       |
       v
Next.js API Proxy
       |
       v
FastAPI Backend
       |
       v
Workflow Orchestration
       |
       +-- Policy Agent
       |
       +-- Coverage Comparison
       |
       +-- Policy Evaluation
       |
       v
Human Review / Decision
       |
       v
PostgreSQL
       |
       +-- Customer Workflows
       +-- Agent Results
       +-- Coverage Findings
       +-- Review Handoffs
       +-- Workflow Events
```

## Technology Stack

| Layer | Technologies |
|---|---|
| Frontend | Next.js, React, TypeScript |
| Backend | Python, FastAPI |
| Database | PostgreSQL, SQLAlchemy |
| Schema migrations | Alembic |
| Testing | Pytest |
| Infrastructure | Docker Compose |
| Local AI experimentation | Ollama integration |
| Version control | Git, GitHub |

The repository also contains experimental agent and memory components. Their presence should not be interpreted as proof that every insurance evaluation uses a live language-model inference.

## Engineering Principles

**Accuracy before automation.** Structured numerical comparisons establish coverage shortfalls without relying on an LLM to perform basic arithmetic.

**Human oversight.** Cases requiring judgment support review handoffs and recorded decisions.

**Traceability.** Workflow events, agent outputs, and findings are persisted so results can be investigated after execution.

**Transparent presentation.** Demo data is explicitly distinguished from live backend data.

**Separation of concerns.** Frontend presentation, API routing, business logic, persistence, and tests are organized into separate components.

## Repository Structure

```text
CoverageOps-AI/
├── app/
│   ├── agents/
│   ├── core/
│   ├── coverage/
│   │   ├── agents/
│   │   ├── services/
│   │   └── dashboard_router.py
│   ├── db/
│   └── main.py
├── coverageops-dashboard/
│   └── src/app/
├── alembic/
├── tests/
├── docker-compose.yml
├── requirements.txt
└── alembic.ini
```

## Local Development

### Requirements

- Python with a compatible environment
- Node.js and npm
- PostgreSQL
- Docker and Docker Compose

### Backend

From the repository root, create a Python virtual environment and install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Configure the database environment variables expected by the backend, start PostgreSQL, and apply the Alembic migrations according to your local configuration.

Start FastAPI:

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8002
```

API documentation:

`http://127.0.0.1:8002/docs`

Health endpoint:

`http://127.0.0.1:8002/health`

### Frontend

```powershell
cd coverageops-dashboard
npm ci
npm run dev
```

The dashboard uses port **3001** in the current development configuration.

The Next.js proxy expects the FastAPI backend at `http://127.0.0.1:8002` by default, configurable through `BACKEND_URL`.

### Tests

Run from the repository root:

```powershell
python -m pytest -q
```

**Latest verified local result:** 54 passed, 1 dependency deprecation warning.

Build the frontend:

```powershell
cd coverageops-dashboard
npm run build
```

The production build completed successfully during local verification.

## Security and Responsible Use

CoverageOps AI is a development prototype built for educational, research, and portfolio demonstration purposes.

- Use synthetic or properly de-identified data only.
- Do not expose development API endpoints directly to the public internet.
- Authentication, authorization, role-based access control, and deployment hardening require further implementation and testing.
- Insurance coverage findings are not legally binding determinations.
- Human review does not substitute for licensed professional judgment.
- Automated test success does not constitute a security audit or production certification.

## Future Improvements

- Versioned policy correction and resubmission
- Expanded reviewer case-management workflows
- Document ingestion and source-level evidence references
- Role-based authentication and authorization
- Automated frontend and end-to-end testing
- CI/CD and additional security testing
- Deployment architecture and observability improvements

## Project Status

**Implemented and locally verified:** Core workflow orchestration, structured insurance coverage comparison, human review persistence, PostgreSQL-backed dashboard data, and frontend production compilation.

**In development:** Broader end-to-end case management, secure production deployment, and expanded automated validation.

---

Built as a software engineering portfolio project focused on trustworthy AI-assisted enterprise workflows.
