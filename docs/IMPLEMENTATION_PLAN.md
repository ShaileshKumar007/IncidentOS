# Milestone-Based Implementation Plan

## Project: IncidentOS
**Document**: Roadmap, Milestones & Execution Strategy  
**Status**: Initial Architecture / Approved for Initialization  

---

## 1. Execution Strategy & Prioritization

To maximize hackathon success and de-risk core platform integrations early, the implementation follows a 9-milestone pipeline. This strictly prioritizes:
1. Verifying communication plumbing (Switch & Mattermost).
2. Spawning independent agent sessions.
3. Building a reproducible target demo.
4. Equipping agents with safe, controlled tools.
5. Executing evidence-driven investigation and QA.
6. Locking in the human approval gate.
7. Automating postmortem generation.

---

## 2. Detailed Implementation Milestones

### Milestone 1: Multi-Agent Collaboration Foundation (Switch & Mattermost)
- **Objective**: Establish and verify the baseline communication paths: Mattermost for human interaction and Switch for agent collaboration.
- **Prerequisites**:
  - Running Mattermost instance or test bot webhook/token.
  - Switch agent coordination room initialized (`incident-ops-bridge`).
- **Deliverables**:
  - Verification script confirming outgoing/incoming Mattermost message delivery.
  - Switch room verification showing broadcast and direct messaging between two test agent handles.
- **Validation Criteria**:
  - A test message sent from a terminal script appears in the Mattermost incident channel.
  - A test agent message published to Switch is received by an active listener session.
- **Risks & Unknowns**: Switch environment configuration specifics must be validated against host setup (see `DESIGN_DECISIONS.md`).

---

### Milestone 2: Establishing the Five Independent Agent Sessions
- **Objective**: Configure and spawn the 5 distinct agent sessions with defined identities, system instructions, and boundaries.
- **Prerequisites**: Milestone 1 complete.
- **Deliverables**:
  - Agent configurations and prompt definitions in `agents/commander/`, `agents/log-investigator/`, `agents/code-investigator/`, `agents/qa-validator/`, and `agents/documentation/`.
  - Registration / leasing of each agent session in the Switch collaboration room.
- **Validation Criteria**:
  - All 5 agents exist as independent actors in Switch (`incident-commander`, `log-investigator`, `code-investigator`, `qa-validator`, `documentation-agent`).
  - Commander sends a test ping to each agent; each agent responds according to its persona.
- **Risks**: Ensuring agents stay within their personas and do not answer questions outside their domain.

---

### Milestone 3: Spring Boot Demo Application & Reproducible Incident
- **Objective**: Create the fictional e-commerce checkout service with a reproducible regression bug and unit/regression tests.
- **Prerequisites**: Java 21 and Gradle / Maven installed.
- **Deliverables**:
  - Standalone Spring Boot project in `demo-environment/`.
  - Domain models: `Customer`, `Order`, `PaymentRequest`, `PaymentResponse`.
  - Services: `CheckoutController`, `CheckoutService`, `PaymentValidator`.
  - Regression bug: Missing null check on `customer` object in `PaymentValidator.validate()`.
  - Git repository initialization with commit history showing a recent commit that removed the null check.
  - Test suite with JUnit 5: standard unit tests (passing) and `testGuestCheckout_ShouldSucceed()` (fails on `main`).
  - Generated realistic log file (`logs/application.log`) containing the `NullPointerException` stack trace.
- **Validation Criteria**:
  - Running tests on `main` fails specifically on `testGuestCheckout_ShouldSucceed()` with `NullPointerException` at `PaymentValidator.validate()`.
  - Log file contains matching stack trace and timestamps.
- **Risks**: Keeping the demo lightweight so builds and tests execute in under 5 seconds.

---

### Milestone 4: Controlled Backend Investigation Tools (FastAPI)
- **Objective**: Implement the sandboxed, validated FastAPI backend service to supply safe tools to agents.
- **Prerequisites**: Python 3.12+ installed.
- **Deliverables**:
  - FastAPI application in `backend/` with endpoints:
    - `/api/tools/logs/tail` & `/api/tools/logs/search`
    - `/api/tools/git/commits`, `/api/tools/git/blame`, `/api/tools/git/create-remediation-branch`
    - `/api/tools/test/execute`
    - `/api/incident/approval/*`
  - Canonical path validator ensuring all file operations remain inside the workspace jail.
  - Pydantic models for all request and response payloads.
  - Pytest suite testing all tool endpoints and security guards.
- **Validation Criteria**:
  - 100% test pass on path traversal prevention (e.g. attempting to read `../../.env` raises 403).
  - Test runner endpoint executes Gradle/Maven and returns parsed JSON results.
- **Risks**: Handling subprocess execution timeouts cleanly without hanging the backend.

---

### Milestone 5: Evidence-Backed Root Cause Analysis Workflow
- **Objective**: Wire Log Investigator and Code Investigator to analyze the incident and produce empirical findings.
- **Prerequisites**: Milestones 2, 3, and 4 complete.
- **Deliverables**:
  - Incident Commander ingests alert and issues investigation tasks to Switch.
  - Log Investigator uses `/api/tools/logs/search` to retrieve the NPE stack trace and posts raw log evidence to Switch.
  - Code Investigator inspects `PaymentValidator.java`, runs `git blame` via `/api/tools/git/blame`, identifies culprit commit, and posts code evidence to Switch.
  - Commander synthesizes findings into a unified RCA.
- **Validation Criteria**:
  - Both agents provide verifiable citations (log timestamps, file lines, commit hash `7f2a1b...`).
  - Commander identifies the root cause without hallucination.
- **Risks**: Model prompt drift; mitigated by strict JSON schema enforcement in agent outputs.

---

### Milestone 6: Proposed Remediation & Regression Testing Workflow
- **Objective**: Code Investigator authors an isolated fix, and QA Validator tests the fix against the regression suite.
- **Prerequisites**: Milestone 5 complete.
- **Deliverables**:
  - Code Investigator writes patch restoring null check and creates branch `remediation/issue-checkout-npe`.
  - QA Validator checks out branch, executes `/api/tools/test/execute`, and captures output.
  - All tests pass (including `testGuestCheckout_ShouldSucceed()`).
  - QA Validator posts test verification payload to Switch.
- **Validation Criteria**:
  - Fix branch exists in Git with exactly one clean commit.
  - Test runner output proves 100% test pass on the fix branch.
  - `main` branch remains untouched.
- **Risks**: Flaky test executions; eliminated by using deterministic local unit tests without external network dependencies.

---

### Milestone 7: Interactive Human Approval Gate
- **Objective**: Implement the mandatory human review and approval mechanism in Mattermost.
- **Prerequisites**: Milestone 6 complete.
- **Deliverables**:
  - Incident Commander formats and publishes an interactive approval message in Mattermost:
    - Root cause summary.
    - Code diff (`git diff`).
    - Empirical test execution evidence.
    - [Approve Fix] and [Reject Fix] buttons.
  - Backend webhook handler to process approval/rejection events.
  - Cryptographic / signed `HumanApprovalRecord` stored in backend incident state.
- **Validation Criteria**:
  - Clicking "Approve" records the human engineer's username and timestamp.
  - Downstream workflows cannot proceed without this record.
- **Risks**: Mattermost interactive message callback configuration; fallback to slash command `/incident approve` supported.

---

### Milestone 8: Post-Approval Postmortem Generation
- **Objective**: Activate the Documentation Agent to generate a high-fidelity, audit-ready postmortem and share it in Mattermost.
- **Prerequisites**: Milestone 7 complete with recorded human approval.
- **Deliverables**:
  - Documentation Agent wakes up upon receiving approval event.
  - Ingests all timeline events, log citations, git hashes, test outputs, and approval records.
  - Generates comprehensive Markdown postmortem.
  - Writes postmortem to `docs/postmortems/INCIDENT-<id>.md`.
  - Posts formatted postmortem to the Mattermost incident channel.
- **Validation Criteria**:
  - Postmortem contains zero fabricated information.
  - Clearly states lifecycle state: Approved, Tested, Pending Merge / Deployment.
- **Risks**: Overly verbose LLM responses; mitigated with a structured postmortem template.

---

### Milestone 9: End-to-End Rehearsal & Live Demonstration
- **Objective**: Polish the end-to-end incident response flow into a seamless, high-impact hackathon presentation.
- **Prerequisites**: All milestones complete.
- **Deliverables**:
  - One-touch demo initialization script (`scripts/start_demo.sh` or `Makefile`).
  - Clean state reset script (`scripts/reset_demo.sh`).
  - Speaker notes and demo walkthrough guide in `docs/DEMO_GUIDE.md`.
- **Validation Criteria**:
  - Full end-to-end incident lifecycle executes cleanly from alert to postmortem in under 3 minutes.
