# CoverageOps AI — Agent Control Center

Functional Next.js 16 + TypeScript frontend for the **independent synthetic insurance engineering demo**.

## Requirements

- Node.js 20.9+ recommended and npm
- Existing FastAPI backend at `http://127.0.0.1:8002`
- Existing PostgreSQL and CoverageOps routes

## Windows PowerShell quick start

1. Extract the `coverageops-dashboard` folder under `C:\Users\yakut\Desktop\agent-lab\coverageops-dashboard`.
2. From `agent-lab\coverageops-dashboard`, run:

   ```powershell
   Copy-Item .env.local.example .env.local
   npm install
   npm run dev
   ```

3. Open http://localhost:3001

In a separate PowerShell window, activate the backend virtual environment and run:

```powershell
cd C:\Users\yakut\Desktop\agent-lab
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload --port 8002
```

## What works now

- **Demo** mode with clearly labeled *illustrative synthetic* workflow data.
- **Live** mode: load a workflow UUID from `GET /coverage/workflows/{workflow_id}`.
- Create an onboarding workflow using `POST /coverage/onboarding`.
- Execute onboarding for a pending workflow using `POST /coverage/workflows/{workflow_id}/execute`.
- Review a handoff when it has a persisted `handoff_id` in workflow events using `POST /coverage/handoffs/{handoff_id}/review`.
- View workflow audit activity and insurance-agent events (when those events have been persisted).
- Server-side API proxy; the browser does not need FastAPI CORS changes.

## Limitations / next backend milestone

The current FastAPI router has **no HTTP endpoint to run the insurance policy agent pipeline**. Therefore the dashboard does not claim to execute policy agents in Live mode. It can display `insurance_agent_completed` events when they already exist. Building `/coverage/workflows/{workflow_id}/policy-review` and insurance results endpoints, with race-condition-safe execution, is a subsequent backend task.

The screenshot-like counts and policy discrepancy shown in **Demo** mode are illustrative, not pulled from your database. Never enter real insurance or patient data into the demo.
