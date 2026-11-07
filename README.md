# IncidentOS

> **A Multi-Agent AI Incident Response Platform**  
> Built for real-world collaborative incident investigation, empirical evidence verification, regression-tested diagnostics, and human-in-the-loop remediation through Switch, FastMCP, and Mattermost.

[![Python 3.12](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Java 21](https://img.shields.io/badge/java-21%20LTS-orange.svg)](https://openjdk.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com)
[![FastMCP](https://img.shields.io/badge/FastMCP-stdio-purple.svg)](https://github.com/modelcontextprotocol)
[![Tests Passing](https://img.shields.io/badge/tests-99%20passed-brightgreen.svg)](#test-results-summary)
[![Switch Console](https://img.shields.io/badge/switch-0.31.0-blueviolet.svg)](https://switch.local)
[![Mattermost](https://img.shields.io/badge/mattermost-11.9.0-blue.svg)](https://mattermost.com)

---

## Table of Contents

1. [Overview & Value Proposition](#1-overview--value-proposition)
2. [Problem Statement & Solution Overview](#2-problem-statement--solution-overview)
3. [Architecture & Demonstrated Operational Workflow](#3-architecture--demonstrated-operational-workflow)
4. [Implementation Status (Engineering Audit)](#4-implementation-status-engineering-audit)
5. [The Five Specialized Agents & Operational Boundaries](#5-the-five-specialized-agents--operational-boundaries)
6. [Demo Scenario: E-Commerce Guest Checkout Outage](#6-demo-scenario-e-commerce-guest-checkout-outage)
7. [Technology Stack](#7-technology-stack)
8. [Setup & Verification Guide for Hackathon Judges](#8-setup--verification-guide-for-hackathon-judges)
   - [Part A: Quick Verification (Local Repo & Dependencies Only)](#part-a-quick-verification-local-repo--dependencies-only)
   - [Part B: Full Multi-Agent Demonstration (External Infrastructure Requirements)](#part-b-full-multi-agent-demonstration-external-infrastructure-requirements)
9. [Test Results Summary](#9-test-results-summary)
10. [Security Model & Architectural Guardrails](#10-security-model--architectural-guardrails)
11. [Demonstration Video](#11-demonstration-video)
12. [Repository Structure](#12-repository-structure)

---

## 1. Overview & Value Proposition

During production software outages, engineering teams face cognitive overload, manual log trawling across fragmented dashboards, disparate chat threads, and hallucinated or ungrounded AI suggestions.

**IncidentOS** is an incident response platform designed to eliminate AI hallucination and unsafe autonomous actions by enforcing an **empirical, evidence-backed workflow**:
- Every diagnostic finding is tied directly to verified log lines, timestamps, or Git commit hashes.
- Every tool action runs through a sandboxed, token-authenticated backend with canonical path-traversal guards and secret-stripped subprocesses.
- Test suites execute via a direct, in-process JUnit 5 runner that does not require network daemons or open sockets.
- The human engineer remains the ultimate decision maker: **no code modification or postmortem is approved or applied without explicit human authorization**.

IncidentOS integrates human engineers in **Mattermost** with AI agents collaborating in **Switch** via the **Model Context Protocol (MCP)**.

---

## 2. Problem Statement & Solution Overview

### The Problem
1. **Cognitive Overload & MTTR Lag**: Engineers waste critical minutes correlating logs, recent commits, and deployments across disconnected tools.
2. **AI Hallucination & Phantom Fixes**: Off-the-shelf LLMs frequently generate plausible-sounding root causes and ungrounded code suggestions that can worsen an outage.
3. **Unsafe Autonomous Actions**: Unconstrained autonomous agents executing shell commands or committing directly to production branches create severe operational risk.
4. **Postmortem Neglect**: Documenting an outage after the fact is tedious, leading to sparse or inaccurate incident postmortems.

### The IncidentOS Solution
- **Separation of Collaboration Surfaces**: Human engineers communicate in Mattermost (`#incidents`), while agents collaborate over structured Switch channels (`incident-ops-bridge`).
- **Controlled FastMCP Tool Gateway**: Seven strongly-typed MCP tools allow agents to query logs, deployment history, Git commits, unified diffs, and pre-approved test suites without shell access.
- **In-Process Direct JUnit Test Runner**: A custom programmatic JUnit Platform Launcher executes real Java test classes inside isolated environments without Gradle daemons or loopback sockets.
- **Immutable Human Approval Gate**: Remediation proposals require explicit human sign-off before downstream closure actions.

---

## 3. Architecture & Demonstrated Operational Workflow

### System Architecture

```mermaid
flowchart TD
    subgraph HumanLayer["Human Collaboration Layer (Mattermost)"]
        Human["Lead Engineer / On-Call SRE"]
        MMChannel["Mattermost Channel: #incidents"]
        Human <-->|Alerts, Directives, Approvals| MMChannel
    end

    subgraph AgentFabric["Agent Collaboration Layer (Switch Console 0.31.0)"]
        IC["Incident Commander\n(Bridged to Mattermost)"]
        SwitchBridge["Switch Room: incidents\n(Mattermost Bridge)"]
        SwitchOps["Switch Room: incident-ops-bridge\n(Internal Agent Mesh)"]

        LI["Log Investigator"]
        CI["Code Investigator"]
        QA["QA & Validation Agent"]
        Doc["Documentation Agent"]

        MMChannel <-->|Webhook / WebSocket| SwitchBridge
        SwitchBridge <--> IC
        IC <--> SwitchOps
        LI <--> SwitchOps
        CI <--> SwitchOps
        QA <--> SwitchOps
        Doc <--> SwitchOps
    end

    subgraph FastMCPGateway["Tool Gateway Layer (Model Context Protocol)"]
        MCPServer["IncidentOS FastMCP Server\n(JSON-RPC over stdio)"]
        BackendClient["Authenticated Backend Client\n(Bearer Token Auth)"]
        
        IC -.->|MCP Tool Calls| MCPServer
        MCPServer --> BackendClient
    end

    subgraph ControlledBackend["Controlled Backend Service (FastAPI / Python 3.12)"]
        FastAPIApp["FastAPI Backend\n(127.0.0.1:8000)"]
        AuthGuard["Token Auth Guard & Path Sanitizer"]
        LogService["Log Search & Tail Engine"]
        GitService["Git History & Diff Service"]
        DeployService["Deployment History Service"]
        TestService["Direct JUnit Test Runner"]

        BackendClient -->|HTTP REST| FastAPIApp
        FastAPIApp --> AuthGuard
        AuthGuard --> LogService
        AuthGuard --> GitService
        AuthGuard --> DeployService
        AuthGuard --> TestService
    end

    subgraph TargetSystem["Target Demo Environment (Fictional E-Commerce Service)"]
        DemoApp["Java 21 / Spring Boot 3.3.0\n(checkout-service)"]
        AppLogs["application.log\n(JSON Structured Logs)"]
        GitRepo["Git Repository\n(Intentional Regression Commit)"]
        TestSuites["DirectTestRunner\n(JUnit 5 Platform Launcher)"]

        DemoApp --> AppLogs
        LogService -.->|Read-Only Inspection| AppLogs
        GitService -.->|Read-Only Inspection| GitRepo
        TestService -.->|In-Process Execution| TestSuites
    end
```

### Actual Demonstrated Workflow vs. Target Vision

To provide judges with complete transparency, IncidentOS distinguishes between the demonstrated workflow and the target multi-agent vision:

```
[Target Vision]
Human Alert (MM) ──► Commander (Switch) ──► Delegates to Specialists (Switch)
                                                    │
                                          ┌─────────┴─────────┐
                                          ▼                   ▼
                                    Log Specialist      Code Specialist
                                          │                   │
                                          └─────────┬─────────┘
                                                    ▼
                                          QA Specialist (Tests)
                                                    ▼
                                          Commander Reviews & Presents
                                                    ▼
                                          Human Approves (MM)
                                                    ▼
                                          Doc Agent Generates Postmortem

[Actual Demonstrated Workflow]
Human Alert (MM) ──► Commander (Switch) ──► Direct FastMCP Tool Invocations
                                                    │
                             ┌──────────────────────┼──────────────────────┐
                             ▼                      ▼                      ▼
                     incidentos_search_logs  incidentos_get_git_diff  incidentos_run_tests
                             │                      │                      │
                             └──────────────────────┼──────────────────────┘
                                                    ▼
                                    Commander Correlates & Synthesizes
                                                    ▼
                                    Presents RCA & Proposed Fix to Human (MM)
                                                    ▼
                                        Mandatory Human Approval Gate
```

1. **Alert Ingestion**: A human engineer submits an incident report or alert via Mattermost `#incidents` (e.g. `@incident-commander investigate INC-20261104-01`).
2. **Triage & Strategy**: The Incident Commander receives the alert through the Switch-Mattermost bridge, assigns severity (`SEV-1`), and formulates an investigation plan.
3. **Evidence Retrieval via MCP**: The Commander invokes IncidentOS FastMCP tools directly (`incidentos_search_logs`, `incidentos_get_log`, `incidentos_get_git_history`, `incidentos_get_git_diff`) to isolate the `NullPointerException` stack trace and identify the culprit commit.
4. **Root Cause Analysis & Remediation Formulation**: The Commander correlates the guest checkout null customer payload with line 42 of `PaymentValidator.java` and drafts a null-safe remediation proposal.
5. **Interactive Human Approval Gate**: The Commander presents the root cause diagnosis, culprit commit, and proposed code diff to the human engineer in Mattermost and requests explicit approval.
6. **Subsequent Lifecycle**: Post-approval remediation, patch compilation, test validation, and postmortem generation require developer orchestration in the current release.

> [!NOTE]
> **Operational Note on Specialist ACP Sessions**:
> In the latest live simulation, the Incident Commander completed the investigation directly using the IncidentOS FastMCP tools. The specialized ACP agents (`log-investigator`, `code-investigator`, `qa-validator`) were provisioned in Switch, but encountered headless interactive tool approval prompts (`request.opened`) inside unbridged Switch rooms where no human approval UI exists. Per [ADR-011](docs/DESIGN_DECISIONS.md#adr-011-do-not-automate-switch-approvals-without-structured-tool-provenance), automated approval based on title-string parsing was rejected for security reasons, so the Commander executed the investigation directly.

---

## 4. Implementation Status (Engineering Audit)

The following matrix documents the exact status of each capability verified against the codebase and test suites:

### Implemented and Verified
- **FastAPI Controlled Backend**: Complete Python 3.12 / FastAPI service with constant-time token verification (`INCIDENTOS_API_TOKEN`), canonical path sanitization (`DEMO_WORKSPACE_ROOT`), subprocess isolation with environment secret stripping (`PATH`, `HOME=/tmp`), and process-group timeout enforcement.
- **FastMCP Tool Server (7 Tools)**: Fully functional FastMCP server communicating over stdio JSON-RPC with stderr-only logging:
  - `incidentos_health`: Backend readiness and uptime check.
  - `incidentos_search_logs`: Search application logs by service, severity, keyword, or time range.
  - `incidentos_get_log`: Retrieve specific log records and full stack traces by log ID or trace ID.
  - `incidentos_list_deployments`: Inspect deployment events by service and version.
  - `incidentos_get_git_history`: Query commit log with path, branch, and count limits.
  - `incidentos_get_git_diff`: Inspect unified diffs between commits or working tree.
  - `incidentos_run_approved_tests`: Execute pre-approved test suites with strict command allowlisting.
- **Direct JUnit Test Runner**: Programmatic JUnit Platform Launcher (`DirectTestRunner.java`) that executes real Java test classes in-process without Gradle daemons, TestWorker processes, or loopback sockets, fully compliant with strict sandbox network boundaries.
- **Reproducible E-Commerce Demo Outage**: Fictional Java 21 / Spring Boot 3.3.0 checkout service (`demo-environment`) with an intentional regression in `PaymentValidator.java:42` (guest checkout `NullPointerException`), backed by real log files, deployment history, and Git commits.
- **Automated Test Coverage**: 99 automated tests passing:
  - 79 backend tests (`backend/tests/`): auth, path traversal, log queries, Git blame/diff, test runner isolation, and error handling.
  - 20 FastMCP server tests (`mcp-server/tests/`): auth header validation, tool registrations, protocol conformance, and FastAPI integration.
- **Switch & Mattermost Integration**: Model B dual-surface topology with bridged `#incidents` room and unbridged `incident-ops-bridge` room, tested with Switch Console 0.31.0 and Mattermost Team Edition 11.9.0.
- **Specialized Agent Definitions**: Prompt specifications and operational boundaries for all five agents documented in `agents/` and `AGENTS.md`.
- **Mandatory Human Approval Boundary**: Human authorization is strictly required before any remediation or closure action; `auto_approve: false` is maintained across all agent configurations.

### Partially Implemented or Operationally Limited
- **Headless Specialist Tool Approvals**: Specialist ACP agent sessions in unbridged Switch rooms trigger interactive tool approval events (`request.opened`) that lack a human UI to answer them, causing specialists to deadlock rather than complete autonomous investigation turns.
- **Incident Commander Single-Agent Execution**: During live Mattermost demonstrations, the Commander successfully completed the investigation by invoking FastMCP tools directly rather than coordinating with autonomous specialist agents in Switch.
- **Automated Switch Approval Gateway (Rejected via ADR-011)**: Audited in Milestones 4E.4.2 and 4E.4.3; rejected because Switch 0.31.0 wire events omit structured tool/server/agent provenance. Relying on title-string matching would create shell-spoofing security vulnerabilities.
- **Baseline Test Execution vs. Unapplied Patch Validation**: The direct JUnit runner executes existing compiled test classes (confirming standard unit tests pass and regression tests fail on flawed code). Applying patches to temporary worktrees, dynamically recompiling, and executing tests on unapplied patches is not yet automated into an agent pipeline.
- **Post-Approval Remediation and Postmortem Pipeline**: Postmortem generation logic and approval tracking exist in specifications, but the automated execution trigger from human approval in Mattermost to autonomous patch application and postmortem publication requires manual orchestration in the current build.

### Planned or Not Implemented
- **Fully Automated Isolated Remediation Execution**: Autonomous creation of temporary Git worktrees, synthetic patch application, and automatic compilation without human developer intervention.
- **End-to-End Autonomous Patch Validation**: Fully automated post-approval pipeline where the QA agent receives an applied patch, recompiles, validates regression resolution, and signs off autonomously.
- **Automated Evidence-Backed Postmortem Archival**: Autonomous push of Markdown postmortems directly to repository archives and Mattermost upon human approval event.
- **Production Deployment and Rollback Integrations**: Automated CI/CD webhooks, canary deployments, or rollback triggers.

---

## 5. The Five Specialized Agents & Operational Boundaries

| Agent Identifier | Surface | Primary Role | Operational Boundaries & Restrictions |
| :--- | :--- | :--- | :--- |
| **`incident-commander`** | Mattermost (`#incidents`) & Switch (`incident-ops-bridge`) | Lead incident orchestrator, severity triage, investigation planning, human liaison, and RCA presentation. | Cannot approve remediation proposals; cannot merge code or run destructive commands. |
| **`log-investigator`** | Switch (`incident-ops-bridge`) | Queries application logs, filters 5xx spikes, and extracts verbatim stack traces. | Read-only access to log paths only; prohibited from reading source code or running tests. |
| **`code-investigator`** | Switch (`incident-ops-bridge`) | Inspects Git commits, history, and diffs; isolates flawed code and drafts remediation patch. | Read-only access during investigation; write access strictly restricted to isolated Git branches. Prohibited from committing to `main`. |
| **`qa-validator`** | Switch (`incident-ops-bridge`) | Reviews fix diffs and executes automated tests via the sandboxed test runner. | Restricted strictly to approved test suites; cannot modify production application code. |
| **`documentation-agent`** | Switch & Mattermost | Compiles timeline and publishes standardized postmortem. **Strictly dormant until human approval.** | Cannot activate prior to verified human approval; prohibited from fabricating missing evidence. |

For detailed contracts, see [AGENTS.md](AGENTS.md).

---

## 6. Demo Scenario: E-Commerce Guest Checkout Outage

IncidentOS is demonstrated against a realistic enterprise e-commerce checkout service (`checkout-service`) located in `demo-environment/`:

- **Stack**: Java 21, Spring Boot 3.3.0, Gradle 9.8.2.
- **The Bug**: Commit `7f2a1b94c3d2` refactored `PaymentValidator.java` and removed the null-check on the customer session:
  ```java
  // PaymentValidator.java:42
  // Flawed line (throws NullPointerException when customer is null):
  UUID customerId = customer.getId();
  ```
- **The Impact**: Authenticated checkouts continue to pass, but all guest checkout requests (`POST /api/checkout` with `customer = null`) crash with `HTTP 500` and `java.lang.NullPointerException`.
- **Reproducible Test Fixture**:
  - `checkout-service-unit-tests` (12 tests): **PASSED** (verifies that authenticated orders, totals, and health endpoints work).
  - `payment-validator-tests` (3 tests): **PASSED** (verifies standard payment validation rules).
  - `checkout-service-regression-test` (1 test): **FAILED** (`NullPointerException: Cannot invoke CustomerDto.getId() because customer is null` at `PaymentValidator.java:42`).

> [!IMPORTANT]
> The failure of `checkout-service-regression-test` on the unmodified baseline is the **expected and verified behavior** that reproduces the production incident. It is not a test suite defect.

---

## 7. Technology Stack

- **Backend Service**: Python 3.12, FastAPI, Pydantic v2, Uvicorn, Pytest, HTTPX.
- **Tool Protocol Layer**: FastMCP (Model Context Protocol), JSON-RPC 2.0 over stdio transport.
- **Agent Coordination**: Switch Console 0.31.0, Antigravity ACP (v1.1.1), Agent Client Protocol.
- **Human Collaboration**: Mattermost Team Edition 11.9.0 (Docker Compose), Mattermost Bot API & WebSockets.
- **Target Demo Environment**: Java 21 (OpenJDK 21), Spring Boot 3.3.0, JUnit 5 Jupiter & Platform Launcher, Gradle 9.8.2.

---

## 8. Setup & Verification Guide for Hackathon Judges

### Part A: Quick Verification (Local Repo & Dependencies Only)

Judges can verify the entire backend, FastMCP server, security controls, and Java test runner directly using only the cloned repository and local dependencies.

#### 1. Prerequisites
- **Python**: `>=3.12`
- **Java**: Java 21 (e.g. `brew install openjdk@21` on macOS)
- **Git**: Installed and available on `PATH`

#### 2. Virtual Environment & Dependency Installation
```bash
# Clone the repository
git clone https://github.com/ShaileshKumar007/IncidentOS.git
cd IncidentOS

# Create and activate Python 3.12 virtual environment
python3.12 -m venv backend/.venv
source backend/.venv/bin/activate

# Install backend dependencies in editable mode
pip install -e "./backend[dev]"

# Install FastMCP server dependencies in editable mode
pip install -e "./mcp-server[dev]"
```

#### 3. Environment Configuration
Create the local `.env` file from the provided template:
```bash
cp .env.example backend/.env
```
Ensure `backend/.env` has `INCIDENTOS_API_TOKEN` set (default: `incidentos-dev-token-local`).

#### 4. Run the 99 Automated Pytest Suites
Execute the automated test suites:
```bash
# Execute backend tool & security test suite (79 passed in ~6.0s)
backend/.venv/bin/pytest backend/tests

# Execute FastMCP tool & protocol test suite (20 passed in ~0.6s)
backend/.venv/bin/pytest mcp-server/tests
```

#### 5. Start the Controlled Backend Tools Service
Start the FastAPI server:
```bash
PYTHONPATH=backend backend/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --env-file backend/.env
```
In a separate terminal, verify the endpoints:
```bash
# Unauthenticated health check
curl -s http://127.0.0.1:8000/health

# Authenticated log search (using INCIDENTOS_API_TOKEN)
curl -s -H "Authorization: Bearer incidentos-dev-token-local" \
  "http://127.0.0.1:8000/api/tools/logs/search?service=checkout-service&severity=ERROR"

# Authenticated Git diff inspection
curl -s -H "Authorization: Bearer incidentos-dev-token-local" \
  "http://127.0.0.1:8000/api/tools/git/diff?target_commit=HEAD"
```

#### 6. Execute the Direct JUnit Test Runner & Reproduce the Outage
Verify the programmatic JUnit runner and observe the intentional incident reproduction:

```bash
# 1. Execute the standard unit test suite (12 passing tests)
backend/.venv/bin/python -c "
import sys; sys.path.insert(0, 'backend')
from app.tools.test_tools import run_tests
from app.schemas.tools import TestRunRequest
res = run_tests(TestRunRequest(test_suite='checkout-service-unit-tests'))
print(f'Status: {res.status} | Tests Run: {res.tests_run} | Passed: {res.tests_passed} | Failed: {res.tests_failed}')
"

# 2. Execute the intentional regression reproduction test (1 expected failure reproducing the incident)
backend/.venv/bin/python -c "
import sys; sys.path.insert(0, 'backend')
from app.tools.test_tools import run_tests
from app.schemas.tools import TestRunRequest
res = run_tests(TestRunRequest(test_suite='checkout-service-regression-test'))
print(f'Status: {res.status} | Tests Run: {res.tests_run} | Failed: {res.tests_failed}')
print('Failure excerpt:', res.output.split('Failures (1):')[-1].strip().split('\n')[0])
"
```

Expected output:
- Suite `checkout-service-unit-tests`: `Status: PASSED | Tests Run: 12 | Passed: 12 | Failed: 0`
- Suite `checkout-service-regression-test`: `Status: FAILED | Tests Run: 1 | Failed: 1`
  - `FAIL: Guest checkout with null customer object should complete successfully -> java.lang.NullPointerException: Cannot invoke "com.example.checkout.dto.CustomerDto.getId()" because "customer" is null`

---

### Part B: Full Multi-Agent Demonstration (External Infrastructure Requirements)

To experience the full live multi-agent workflow across Switch and Mattermost, additional external services and runtime configurations are required. Cloning the repository alone does not provision these external environments.

#### External Prerequisites
1. **Switch Console 0.31.0**: Running locally on `http://127.0.0.1:60463` with Gateway on port `60462` and local PostgreSQL on port `60465`.
2. **Antigravity ACP Provider**: Installed (`antigravity-acp` v1.1.1) and authenticated in Switch Console.
3. **Mattermost Team Edition (v11.9.0)**: Running on `http://localhost:60464` via Docker Compose, configured with the Switch Mattermost bridge.
4. **Agent Provisioning**: All five agents registered in Switch using the parameters defined in `switch/README.md`.
5. **FastMCP Server Registration**: `incidentos-tools` registered in `~/.switch/mcp.json` pointing to `backend/.venv/bin/python -m incidentos_mcp.server`.

For the complete step-by-step presentation script and live execution instructions, refer to:
- [docs/DEMO_GUIDE.md](docs/DEMO_GUIDE.md): Step-by-step presentation script.
- [switch/README.md](switch/README.md): Switch runtime configuration and agent provisioning templates.

---

## 9. Test Results Summary

| Test Suite | Test Type | Tests Run | Passed | Failed | Duration | Execution Mode |
| :--- | :--- | :---: | :---: | :---: | :---: | :--- |
| **Backend Unit & Security** (`backend/tests`) | Pytest | 79 | 79 | 0 | ~6.0s | Sandboxed In-Process |
| **FastMCP Tools & Protocol** (`mcp-server/tests`) | Pytest | 20 | 20 | 0 | ~0.6s | Sandboxed In-Process |
| **Total Automated Tests** | Pytest | **99** | **99** | **0** | **~6.6s** | **All Passing** |
| `checkout-service-unit-tests` | JUnit 5 | 12 | 12 | 0 | ~1.8s | Direct JUnit Runner |
| `payment-validator-tests` | JUnit 5 | 3 | 3 | 0 | ~1.6s | Direct JUnit Runner |
| `checkout-service-regression-test` | JUnit 5 | 1 | 0 | **1\*** | ~1.7s | Direct JUnit Runner |

*\* Expected failure: Reproduces the intentional guest checkout `NullPointerException` at `PaymentValidator.java:42`.*

---

## 10. Security Model & Architectural Guardrails

IncidentOS implements defense-in-depth security to ensure autonomous agents cannot damage production systems or escape confinement:

1. **Zero Hallucination Guarantee**: Agents cannot report stack traces, commit hashes, or test results without citing exact tool execution outputs.
2. **Read-Only Default Investigation**: Log inspection and Git blame tools are strictly non-destructive.
3. **Canonical Workspace Jailing**: All file and directory arguments are resolved using canonical paths and verified to reside strictly within `DEMO_WORKSPACE_ROOT`. Escapes (`../../`) are blocked deterministically.
4. **Subprocess Isolation & Secret Stripping**: Test commands and Git subprocesses execute with stripped environments (`PATH`, `HOME=/tmp`). API tokens, bot tokens, and user credentials are removed.
5. **Rejection of Unsafe Approval Gateways ([ADR-011](docs/DESIGN_DECISIONS.md#adr-011-do-not-automate-switch-approvals-without-structured-tool-provenance))**:
   - Switch 0.31.0 wire events omit structured tool and server provenance, exposing only UI display strings.
   - An automated gateway based on regex matching display titles was audited and rejected because shell commands could spoof allowed tool titles.
   - `auto_approve: false` remains strictly enforced across all agents.
6. **Mandatory Human-in-the-Loop Gate**: Remediation proposals require physical human approval in Mattermost before downstream actions are authorized.

For complete architectural details, see [docs/SECURITY.md](docs/SECURITY.md) and [docs/DESIGN_DECISIONS.md](docs/DESIGN_DECISIONS.md).

---

## 11. Demonstration Video

<!-- Demonstration video recording placeholder -->
- **Video Walkthrough**: *[IncidentOS Demo Video](https://youtu.be/placeholder)* *(Link to hackathon demo recording)*
- **Demo Script**: Follow along with the exact step-by-step script in [docs/DEMO_GUIDE.md](docs/DEMO_GUIDE.md).

---

## 12. Repository Structure

```
.
├── AGENTS.md                  # Comprehensive operational contracts for all 5 agents
├── README.md                  # Project overview, architecture, status, and judge quickstart (this file)
├── .gitignore                 # VCS ignore rules (excludes .env, caches, build artifacts)
├── .env.example               # Environment variable configuration template
├── docs/
│   ├── PRD.md                 # Product Requirements Document
│   ├── ARCHITECTURE.md        # Technical architecture, protocols, and data flows
│   ├── REQUIREMENTS.md        # Detailed functional & non-functional requirements
│   ├── SECURITY.md            # Security, sandboxing, and least-privilege policies
│   ├── IMPLEMENTATION_PLAN.md # 9-milestone implementation plan
│   ├── DEMO_GUIDE.md          # Step-by-step presentation script & live verification guide
│   └── DESIGN_DECISIONS.md    # Architectural Decision Records (ADRs 001 through 011)
├── agents/                    # Agent-specific definitions & prompt configurations
│   ├── commander/             # Incident Commander agent specification
│   ├── log-investigator/      # Log Investigator agent specification
│   ├── code-investigator/     # Code Investigator agent specification
│   ├── qa-validator/          # QA & Validation agent specification
│   └── documentation/         # Documentation agent specification
├── backend/                   # IncidentOS Python/FastAPI backend & controlled tools
│   ├── app/
│   │   ├── api/               # Protected REST API routes (auth, health, incidents, tools)
│   │   ├── tools/             # Controlled tools (logs, git, deployments, direct test runner)
│   │   ├── schemas/           # Pydantic v2 data schemas
│   │   ├── services/          # Incident state & management services
│   │   └── main.py            # FastAPI application entry point
│   ├── tests/                 # Backend automated test suite (79 tests)
│   └── pyproject.toml         # Backend package & dependency specifications
├── mcp-server/                # FastMCP stdio server exposing IncidentOS tools to agents
│   ├── incidentos_mcp/
│   │   ├── server.py          # FastMCP server entry point (stdio transport)
│   │   ├── client.py          # HTTP client communicating with FastAPI backend
│   │   └── tools/             # 7 registered FastMCP tools
│   ├── tests/                 # MCP server automated test suite (20 tests)
│   └── pyproject.toml         # FastMCP package & dependency specifications
├── demo-environment/          # Fictional Java 21 / Spring Boot checkout service
│   ├── src/main/java/         # Checkout service source (includes intentional regression)
│   ├── src/test/java/         # Unit and regression test suites (includes DirectTestRunner)
│   ├── logs/                  # Simulated production application logs (JSON structured)
│   ├── deployments/           # Historical deployment event records
│   └── build.gradle           # Gradle 9.8.2 build configuration
└── switch/                    # Switch agent collaboration configuration & bindings
    └── README.md              # Switch runtime integration, room bindings & bridge details
```
