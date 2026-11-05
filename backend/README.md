# IncidentOS Backend & Controlled Tooling Service

The IncidentOS Backend is a lightweight, sandboxed Python 3.12+ / FastAPI service that exposes verified, least-privilege investigation and diagnostic tools to the specialized AI agents.

---

## 1. Core Responsibilities & Security Model

- **Python 3.12+ Runtime**: Enforces modern Python runtime typing and standard library capabilities.
- **API Token Authentication**: Protects all `/api/*` endpoints with constant-time token verification (`INCIDENTOS_API_TOKEN`). Rejects missing or invalid tokens with HTTP 401. Health checks (`/health`) remain accessible without credentials.
- **Workspace Jail**: All file operations resolve strictly against `DEMO_WORKSPACE_ROOT`. Directory traversals (`..`), absolute paths, and symlinks escaping the demo environment are rejected with HTTP 403.
- **Controlled Git Operations**: Read-only Git history and diff inspection on the demo repository. Completely suppresses Git hooks (`core.hooksPath=/dev/null`) and disables external diff drivers (`diff.external=`).
- **Subprocess Environment Isolation**: Subprocess executions for tests and Git operate with a minimal, sanitized environment (`PATH`, `HOME=/tmp`). Host secrets and API tokens are never inherited by child processes.
- **Process Group Termination on Timeout**: Test executions run in isolated process groups (`start_new_session=True`). On execution timeout, the entire process group is terminated cleanly via `os.killpg`.
- **Pre-Approved Test Runner**: Executes only allowlisted test suite definitions with strict timeout enforcement (`TOOL_EXECUTION_TIMEOUT_SECONDS`) and output size capping (50 KB). Arbitrary shell commands are strictly prohibited.
- **Structured Auditability**: Every tool response embeds a `ToolExecutionResult` capturing timing, tool name, agent identity, incident ID, execution status, and result summary.

---

## 2. Directory Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                     # FastAPI entrypoint, middleware, exception handlers, auth wiring
│   ├── config.py                   # Configuration and sandbox constants
│   ├── api/
│   │   ├── __init__.py
│   │   ├── auth.py                 # API token verification dependency (constant-time, secret-safe)
│   │   ├── health.py               # GET /health (public)
│   │   ├── incidents.py            # GET /api/incidents, GET /api/incidents/{id} (protected)
│   │   └── tools.py                # Protected log, deployment, git, and test runner endpoints
│   ├── models/
│   │   └── __init__.py             # Model exports
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── common.py               # ToolExecutionResult, ErrorResponse
│   │   ├── incident.py             # Incident, FindingType, EvidenceReference, Severity
│   │   └── tools.py                # Pydantic schemas for all investigation tools
│   ├── services/
│   │   ├── __init__.py
│   │   └── incident_service.py     # Incident state and finding storage
│   └── tools/
│       ├── __init__.py
│       ├── workspace.py            # Strict sandbox validator (traversal/symlink guards)
│       ├── log_tools.py            # Log search and retrieval
│       ├── deployment_tools.py     # Deployment history query
│       ├── git_tools.py            # Sandboxed Git log and diff inspector (hooks suppressed)
│       └── test_tools.py           # Pre-approved test suite runner (isolated environment)
├── tests/
│   ├── __init__.py
│   ├── conftest.py                 # Isolated temp workspace fixtures & TestClient
│   ├── test_auth.py                # API token authentication tests
│   ├── test_health.py              # Health check tests
│   ├── test_incidents.py           # Incident API tests
│   ├── test_workspace_sandbox.py   # Path traversal, symlink escape, and jail tests
│   ├── test_log_tools.py           # Log search, filters, and detail tests
│   ├── test_deployment_tools.py    # Deployment history tests
│   ├── test_git_tools.py           # Git history, diff, hook suppression & safe env tests
│   └── test_test_tools.py          # Allowlist, timeout enforcement & secret stripping tests
├── requirements.txt
├── pyproject.toml
├── Dockerfile
└── README.md
```

---

## 3. Quickstart & Local Setup

### Prerequisites
- Python 3.12+ (installed via Homebrew or system packaging)
- Git CLI

### Installation
From the project root:

```bash
# 1. Create a virtual environment using Python 3.12
python3.12 -m venv backend/.venv

# 2. Activate virtual environment
source backend/.venv/bin/activate

# 3. Install dependencies
pip install -r backend/requirements.txt
```

### Running Tests
Run the automated test suite with pytest:

```bash
backend/.venv/bin/pytest backend/tests -v
```

### Starting the Server
Start the FastAPI server on localhost (127.0.0.1:8000):

```bash
# Set a local API token for authentication
export INCIDENTOS_API_TOKEN="my-local-dev-token"

# Start the uvicorn development server
PYTHONPATH=backend backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

---

## 4. API Endpoints & Verification Examples

### Health Check (Public)
```bash
curl -s http://127.0.0.1:8000/health
```

### Protected Endpoints (Requires `Authorization: Bearer <token>` or `X-API-Key: <token>`)

```bash
TOKEN="my-local-dev-token"

# 1. List Incidents
curl -s http://127.0.0.1:8000/api/incidents \
  -H "Authorization: Bearer $TOKEN"

# 2. Search Application Logs for NullPointerException
curl -s "http://127.0.0.1:8000/api/tools/logs/search?severity=ERROR&keyword=NullPointerException" \
  -H "Authorization: Bearer $TOKEN"

# 3. Retrieve Specific Log by ID
curl -s "http://127.0.0.1:8000/api/tools/logs/err-log-001" \
  -H "Authorization: Bearer $TOKEN"

# 4. Query Deployment History
curl -s "http://127.0.0.1:8000/api/tools/deployments?service=checkout-service" \
  -H "Authorization: Bearer $TOKEN"

# 5. Inspect Git History & Diff
curl -s "http://127.0.0.1:8000/api/tools/git/history?count=2" \
  -H "Authorization: Bearer $TOKEN"

curl -s "http://127.0.0.1:8000/api/tools/git/diff?target_commit=6014328" \
  -H "Authorization: Bearer $TOKEN"

# 6. Run Pre-Approved Tests
curl -s -X POST http://127.0.0.1:8000/api/tools/tests/run \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"test_suite": "checkout-service-unit-tests"}'

curl -s -X POST http://127.0.0.1:8000/api/tools/tests/run \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"test_suite": "checkout-service-regression-test"}'
```

---

## 5. Agent Token Delivery & Switch Integration

In Milestone 4, Switch agents invoke backend tools via HTTP requests or MCP tool wrappers.
- The `INCIDENTOS_API_TOKEN` is passed to the agent runtime via the local environment or sidecar process configuration.
- Agents inject the token into HTTP headers as `Authorization: Bearer <token>`.
- The token is never echoed back by the backend in error responses or logs.
