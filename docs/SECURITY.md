# Security & Guardrail Architecture

## Project: IncidentOS
**Document**: Security Model, Sandboxing & Principle of Least Privilege  
**Status**: Initial Architecture / Approved for Initialization  

---

## 1. Security Tenets

Autonomous AI agents operating on software repositories represent a serious operational and security risk if unconstrained. IncidentOS adheres to five immutable security principles:

1. **Principle of Least Privilege**: Each agent is granted access only to the exact tools and directories needed to perform its specific role.
2. **Read-Only Default**: Triage and root cause investigation are strictly read-only. No write operations, environment mutations, or background process modifications are permitted during diagnosis.
3. **Workspace Jailing & Canonical Path Enforcement**: Tool operations are strictly bounded to the configured workspace root. Path traversal attacks (e.g., `../../etc/passwd`) are rejected deterministically before execution.
4. **Isolated Branching & Remediation Sandboxing**: All proposed patches are applied to temporary, isolated Git branches (`remediation/*`). Pushes or merges to protected branches (`main`, `master`, `release/*`) are blocked at the tool layer.
5. **Mandatory Human-in-the-Loop Governance**: No remediation may be finalized or merged without explicit, cryptographically traceable human engineer approval.
6. **Token-Authenticated Tool Gateway**: All `/api/*` backend endpoints require a valid API token verified using constant-time comparison (`secrets.compare_digest`). Tokens are never echoed in logs or error messages.
7. **Subprocess Secret Stripping**: Subprocesses for tests and Git execute with a stripped, controlled environment (`PATH`, `HOME=/tmp`) that completely removes host API keys, bot tokens, and credentials.
8. **Hook & External Program Suppression**: Git executions explicitly disable hooks (`-c core.hooksPath=/dev/null`) and external diff utilities (`-c diff.external=`) to prevent arbitrary code execution.

---

## 2. Threat Model & Mitigations

| Threat | Attack / Failure Scenario | Mitigation Mechanism |
| :--- | :--- | :--- |
| **Path Traversal** | Agent or malicious prompt injection supplies `../../../secrets.env` to a log or file tool. | Backend normalizes paths using `os.path.realpath` and verifies they are subpaths of `ALLOWED_WORKSPACE_ROOT`. Rejects violations with HTTP 403. |
| **Command Injection** | Agent passes malicious shell metacharacters (`; rm -rf /`) in test filter parameters. | Backend prohibits raw shell evaluation (`shell=False` in subprocess) and strictly validates arguments against rigid alphanumeric/regex patterns. |
| **Hallucinated Diagnostics** | LLM invents a stack trace, commit hash, or nonexistent bug cause. | Incident Commander rejects any finding not accompanied by a verified tool output payload. Log and code hashes are cross-checked. |
| **Unauthorized Code Mutation** | Agent attempts to overwrite production configuration or merge unverified code to `main`. | Git tool enforces branch naming rules (`remediation/*` only) and prohibits `git push` or `git checkout main` with modification flags. |
| **Autonomous Premature Deploy** | Agent assumes approval and triggers deployment scripts. | IncidentOS has zero autonomous deployment capabilities. Human approval is strictly recorded as a decision gate for postmortem documentation only. |
| **Credential Exfiltration** | Prompts attempt to dump environment variables or read `.env` / credentials. | `.gitignore` prevents tracking secrets; backend tool blocks reading `.env`, `.git/config`, or private keys. |

---

## 3. Sandboxing & Input Validation Rules

### 3.1 Workspace Canonicalization Guard
Every backend tool must route filesystem accesses through a path validator function:

```python
import os
from pathlib import Path

def resolve_and_validate_path(relative_path: str, base_dir: Path) -> Path:
    """
    Resolves relative path against base_dir and ensures the target 
    strictly resides within base_dir. Raises PermissionError otherwise.
    """
    resolved_base = base_dir.resolve()
    target_path = (resolved_base / relative_path).resolve()

    if not target_path.is_relative_to(resolved_base):
        raise PermissionError(f"Access Denied: Path {target_path} escapes workspace jail {resolved_base}")
    
    # Block sensitive system and secret files
    blocked_filenames = {".env", ".env.local", "id_rsa", "credentials.json"}
    if target_path.name in blocked_filenames or any(p.startswith(".git") for p in target_path.parts[len(resolved_base.parts):]):
        if target_path.name != ".git": # allow git tool to manage repo internally via git commands
            raise PermissionError(f"Access Denied: Target {target_path.name} is a restricted file.")
            
    return target_path
```

### 3.2 Test Runner Command Sandboxing
The QA Validation agent executes test suites exclusively via the backend test runner:
- Command is executed as `["./gradlew", "test", "--tests", sanitized_test_class]`.
- Standard output and error streams are captured into memory with strict buffer limits (max 1MB).
- Execution timeout is enforced (maximum 120 seconds) to prevent infinite loops or hung tests.
- Process runs with non-privileged user permissions.

---

## 4. Human Approval Gate & Audit Record

### 4.1 Approval Contract
- The Incident Commander can **request** approval, but cannot grant it.
- Approval requires a physical human action on Mattermost:
  - Button click on an interactive post, or
  - Explicit slash command `/incident approve <incident-id>`.
- The Mattermost interactive callback verifies the human's user ID, team ID, and role.
- Upon approval, the backend issues an immutable `HumanApprovalRecord`:
  ```json
  {
    "incident_id": "INC-20261104-01",
    "decision": "APPROVED",
    "approver_user_id": "user_alex_sre",
    "approver_username": "@alex",
    "timestamp_iso": "2026-11-04T23:15:30.412Z",
    "patch_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "approval_token": "appr_tok_991823120abc"
  }
  ```

### 4.2 Lifecycle State Integrity in Documentation
The Documentation Agent must explicitly document the state of the resolution:
- **Status: APPROVED**: Human engineer verified the diagnosis and fix.
- **Status: TESTED**: Automated regression suite ran and passed in isolation.
- **Status: MERGED**: False (Merges to `main` must be performed through the team's standard CI/CD and PR review outside the agent incident loop).
- **Status: DEPLOYED**: False (Production deployment is manual or governed by standard deployment pipelines).
