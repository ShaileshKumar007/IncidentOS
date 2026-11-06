# Architectural Decision Records (ADRs) & Integration Log

## Project: IncidentOS
**Document**: Architectural Decisions & Unknown Integration Details  
**Status**: Initial Architecture / Approved for Initialization  

---

## 1. Architectural Decisions

### ADR-001: Separation of Collaboration Surfaces (Mattermost for Humans, Switch for Agents)
- **Context**: Incident response requires both clear, high-signal communication with human incident commanders and rapid, structured, multi-turn technical negotiation between autonomous agents.
- **Decision**: 
  - Use **Mattermost** strictly as the human-facing interface. Human engineers receive alerts, view condensed progress summaries, inspect verified diffs and test results, and click interactive approval buttons.
  - Use **Switch** as the inter-agent collaboration and coordination layer. Specialized agents converse, debate hypotheses, delegate subtasks, and publish structured tool evidence inside a shared Switch room.
- **Consequences**: Avoids flooding human engineering channels with hundreds of verbose tool execution logs and agent reasoning steps, while ensuring complete transparency within the Switch agent room.

---

### ADR-002: Controlled FastAPI Backend for Tool Execution
- **Context**: Granting LLM agents direct shell or unconstrained filesystem access creates significant risk of prompt injection, path traversal, accidental destructive commands (`rm -rf`), and uncontrolled resource consumption.
- **Decision**: Implement a dedicated, lightweight Python 3.12+ / FastAPI backend exposing strongly-typed, Pydantic-validated REST endpoints for all agent actions (log tailing, log search, git blame, isolated branch creation, test execution).
- **Consequences**: Guarantees canonical path traversal protection (`ALLOWED_WORKSPACE_ROOT`), strict argument sanitization, subprocess timeout enforcement, and easy unit/integration testing with pytest.

---

### ADR-003: Mandatory Human Approval Gate Prior to Postmortem & Closure
- **Context**: Autonomous agents that self-approve code fixes or self-publish incident closures undermine operational safety and create compliance vulnerabilities.
- **Decision**: Remediation diffs and test execution proofs must be submitted to the human engineer via an interactive Mattermost prompt. The transition from `PENDING_HUMAN_APPROVAL` to `APPROVED` requires a valid human-signed action. The Documentation Agent is physically prevented from activating until this approval event is recorded.
- **Consequences**: Zero risk of premature incident closure. Every postmortem carries an immutable human approval record.

---

### ADR-004: Explicit Deferral of Next.js Dashboard
- **Context**: A web dashboard was initially considered for visualizing incident metrics and agent graphs.
- **Decision**: Explicitly defer the Next.js dashboard for future iterations. It is NOT part of the hackathon MVP.
- **Rationale**: For a solo developer during a hackathon, maintaining a React/Next.js frontend, WebSocket synchronizer, and backend API alongside multi-agent orchestration adds excessive surface area. Mattermost and Switch already provide complete, interactive, and demonstrable user and agent interfaces.

---

### ADR-005: Fictional Java 21 / Spring Boot Demo Target
- **Context**: We need an enterprise-grade target application to demonstrate real log triage, Git blame, code diffing, and regression testing.
- **Decision**: Build a clean, minimal Java 21 / Spring Boot 3.x fictional checkout service (`checkout-service`).
- **Rationale**: Java/Spring Boot is the canonical enterprise stack where `NullPointerException` stack traces, Gradle/Maven build logs, and unit/regression test suites are universally recognized and realistic. All code, logs, and commit histories are fictional and contained inside the local repository.

---


---

### ADR-006: Agent Provisioning & Permission Baseline (Antigravity ACP, Auto-Mode, No-Bypass)
- **Context**: Five independent agents require distinct execution sessions, clear least-privilege permissions, and bounded execution environments.
- **Decision**:
  - Provision all five agents (`incident-commander`, `log-investigator`, `code-investigator`, `qa-validator`, `documentation-agent`) as independent Switch-managed agent sessions on the local host machine using provider `antigravity`.
  - Configure `auto_mode: true` to enable headless autonomous turn handling within room boundaries.
  - Set `auto_approve: false` across all agents to explicitly disable bypass mode (`yolo`), guaranteeing least-privilege tool execution and preventing unverified shell commands, arbitrary writes, or automatic deployment.
  - Assign each agent an isolated working directory under `~/.switch/agents/localhost-60463/<agent-name>`.
- **Consequences**: Every agent runs with safe execution defaults. Risky operations cannot run unattended without verification, and the human approval gate remains strictly enforced.

---

### ADR-007: Dual-Room Topology and Directed Linking (Model B)
- **Context**: Mixing human incident discussion with high-volume inter-agent diagnostic negotiation produces noise and risks notification fatigue.
- **Decision**:
  - Provision an internal-only Switch room `incident-ops-bridge` (`42033586-7bc2-4200-9414-e3cd60872462`) populated by all five specialized agents.
  - Provision a Mattermost-bridged Switch room `incidents` (`69f5fc19-ad5a-4d14-8315-ea834af5bc23`) linked to Mattermost channel `#incidents` (`88pcwkycoiywpgqqupx5zyzmse`), populated solely by `incident-commander` and authenticated human engineers.
  - Establish a directed link from `incident-ops-bridge` to `incidents` with relationship label `human-incident-channel`.
- **Consequences**: Strict segregation of chatter: human engineers see only high-level alerts, triage digests, and approval gates, while agents collaborate deeply in the internal ops bridge.

---

### ADR-008: API Token Authentication for Agent-to-Backend Tool Gateway
- **Context**: The FastAPI backend exposes sensitive investigation capabilities (file reading, log analysis, Git inspection, test execution). Without authentication, any local process could abuse these endpoints.
- **Decision**: Protect all `/api/*` routes with a constant-time token verification mechanism (`INCIDENTOS_API_TOKEN`). Support both `Authorization: Bearer <token>` and `X-API-Key: <token>`. Leave `/health` unauthenticated for health monitoring.
- **Consequences**: Guarantees that only authorized Switch agents with the token can query or execute tools. Tokens are never echoed in logs or error responses.

---

### ADR-009: Subprocess Isolation, Secret Stripping & Hook Suppression
- **Context**: Running test commands and Git operations via `subprocess` inherits the parent process's environment variables by default, risking leakage of `INCIDENTOS_API_TOKEN`, Mattermost tokens, or user secrets to test code. Furthermore, Git commands can execute local hooks (`.git/hooks`) or external diff programs.
- **Decision**:
  1. Pass an explicit, sanitized environment (`get_safe_subprocess_env()` and `get_safe_git_env()`) containing only essential OS variables (`PATH`, `HOME=/tmp`).
  2. Suppress Git hooks and external diff drivers with `-c core.hooksPath=/dev/null` and `-c diff.external=`.
  3. Run test subprocesses with `start_new_session=True` and kill the entire process group (`os.killpg`) if a timeout occurs.
- **Consequences**: Guarantees zero credential leakage and prevents test code or Git configs from escaping sandbox boundaries.

---

### ADR-010: Java 21 / Spring Boot 3.3.0 Demo Architecture with Tagged JUnit 5 Regression Suite
- **Context**: The target demo application must demonstrate realistic enterprise behavior, reproducible exceptions at exact code lines, structured logging, and automated verification without requiring external databases or third-party cloud infrastructure.
- **Decision**:
  1. Build a fictional e-commerce checkout service using Java 21 (Homebrew `openjdk@21`) and Spring Boot 3.3.0 managed via Gradle 9.8.2.
  2. Implement an in-memory layered architecture (`CheckoutController`, `CheckoutService`, `PaymentValidator`, DTOs, `GlobalExceptionHandler`).
  3. Introduce an intentional regression in `PaymentValidator.java:42` where a missing null-check on guest checkout triggers `java.lang.NullPointerException`.
  4. Separate test suites using JUnit 5 tags: standard unit tests (12 tests) exclude `@Tag("regression")`, allowing regular tests to pass; a dedicated regression test (`GuestCheckoutRegressionTest`, tagged `@Tag("regression")`) reproduces the failure.
  5. Provide pre-approved Gradle tasks (`unitTest`, `regressionTest`, `runApp`) allowlisted by the FastAPI backend test runner.
- **Consequences**: Enables fast, reliable, offline-capable test runs in under 3 seconds with empirical pass/fail reporting for the QA Agent, while strictly isolating the reproducible regression.

---

### ADR-011: Do Not Automate Switch Approvals Without Structured Tool Provenance
- **Status**: Accepted
- **Context**:
  In Milestone 4E.4.3, we investigated whether a separate local gateway service could listen to Switch Gateway WebSocket events (`request.opened`) on port `60462` and automatically submit `request.answer` frames for approved IncidentOS MCP tools. While Switch 0.31.0 exposes `request.opened` and accepts `request.answer` with revision protection, the wire event strips all structured provenance:
  - `toolName` is missing from the event schema.
  - `mcpServer` is missing from the event schema.
  - `agentId` is absent from the `request.opened` event payload (only `sessionId` is transmitted).
  - `arguments` are not provided as a structured JSON object; only `content.detail: string | null` is provided, which stringifies arguments and truncates them at 1,000 characters with `… (N more characters not shown)`, breaking JSON parseability for larger payloads.
  - Both MCP tool calls and arbitrary shell/command executions share the identical generic wire discriminator `content.kind === "approval"`.
- **Decision**:
  Do not implement an automated approval gateway or decision mechanism based on parsing unstructured display titles (`content.title`) or truncated detail strings.
- **Rationale**:
  Display strings are human-facing UI formatting artifacts, not trustworthy authorization metadata. A shell command execution (`run_command`) can accept a description or command argument that produces a display title mimicking an approved MCP tool call (e.g. `description: "incidentos wants to run incidentos_search_logs"`). Relying on regex or substring matching against display titles creates a severe vulnerability where an uncontained shell execution could be mistakenly auto-approved as a safe read-only MCP tool.
- **Security Requirements for Reconsideration**:
  Automated tool approval can only be reconsidered if upstream Switch / ACP provides an authenticated, tamper-proof event contract containing:
  1. Immutable structured provider identity.
  2. Structured MCP server identity.
  3. Structured tool name.
  4. Structured, un-truncated arguments.
  5. Reliable requesting agent and session identity.
  6. Approval request ID and revision.
  7. Explicit, structured distinction between MCP tool approvals and shell/command approvals.
  8. Replay and stale-request protection.
- **Consequences**:
  - `auto_approve: false` remains mandatory across all agent configurations to prevent unverified bypass mode (`yolo`).
  - Human approval remains the definitive authorization gate.
  - No gateway service will be implemented against the current Switch 0.31.0 contract. Headless specialist agents must either execute pre-authorized actions via native provider allowlists or coordinate findings without headless approval deadlocks.

## 2. Verified Integration Details & Environmental Findings

Following the Milestone 1 audit of the live Switch Console and Mattermost environment, all initial integration unknowns have been verified and resolved.

### UNK-001: Switch Agent Session Binding Protocol [RESOLVED]
- **Status**: Verified in Milestone 1 Audit.
- **Resolution**:
  - Switch Console 0.31.0 manages agents locally via the Agent Controller (`managed_agents`) on the configured host machine.
  - Provider `antigravity` executes via `antigravity-acp` (v1.1.1) using the Agent Client Protocol (ACP) over stdio.
  - Sessions run with `auto_session: true`, supervised automatically by Switch Console.
  - Switch provisions a local stdio MCP server named `switch` for each agent, exposing native tools: `connect_to_room`, `post_message`, `send_targeted_message`, `read_context`, `create_room`, etc.
  - Tool calls go through `call_mcp_tool(switch, <tool_name>)`.

### UNK-002: Switch Message Event Payload Format [RESOLVED]
- **Status**: Verified in Milestone 1 Audit.
- **Resolution**:
  - Outbound messaging: Agents call `post_message(body=...)` for channel-wide broadcast or `send_targeted_message(body=..., target_names=[...])` to directly invoke specific agents.
  - Inbound event delivery: Switch delivers messages into the agent's ACP turn with structured framing:
    `[Switch] <sender> addressed you in room <room> (message_id <id>[, thread_id <tid>]):`
    `BEGIN SWITCH MESSAGE <nonce>`
    `<content>`
    `END SWITCH MESSAGE <nonce>`
  - Ambient room history is retrieved on-demand via `read_context(room_id=...)`.

### UNK-003: Mattermost Interactive Button Callback Configuration [RESOLVED]
- **Status**: Verified in Milestone 1 Audit.
- **Resolution**:
  - Switch integrates with Mattermost (v11.9.0 running on `http://localhost:60464`) via default bridge `3c93642d-40a0-4a53-9acf-825eb9b38598` under team `switch`.
  - Every agent in a bridged room receives a dedicated Mattermost bot account. Outbound agent messages render full Markdown tables and formatting natively.
  - Inbound messages flow from Mattermost via WebSocket into Switch. Mentioning an agent or typing in an assigned channel dispatches an addressed event to that agent session.
  - **Approval Handling**: Because Antigravity runs headless via ACP, native prompt UI modals are skipped/denied. For MVP, human approval decisions are handled via in-channel text interaction (`@incident-commander approve` or `!approve`), which is simple, robust, and requires zero external webhook callback networking.

### UNK-004: Delivery of Backend API Token to Headless Antigravity / Switch Sessions
- **Status**: Open / Pending Implementation.
- **Description**: How the `INCIDENTOS_API_TOKEN` will be securely injected into headless Antigravity/Switch agent sessions without hardcoding it in repository files or exposing it in Switch chat rooms.
- **Current Recommendation**: Inject `INCIDENTOS_API_TOKEN` via environment variables in the agent launch harness or provide a local MCP tool wrapper that reads the token from the host environment.

## 3. Scope Boundaries & Constraints Summary

- **Single Developer Hackathon Feasibility**: Kept lean by relying on FastAPI, Pydantic, pytest, and local Gradle/Maven execution.
- **No Complex External Databases**: All incident state and timeline records are managed in-memory with optional JSON/SQLite backing by the FastAPI backend.
- **No Fabricated Evidence**: Zero mock data pipelines—agents will inspect real files generated by the Spring Boot test runs.
