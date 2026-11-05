# System & Technical Requirements Specification

## Project: IncidentOS
**Document**: Requirements & Tool Interfaces  
**Status**: Initial Architecture / Approved for Initialization  

---

## 1. System Requirements & Prerequisites

### 1.1 Host Environment
- **Operating System**: macOS (Darwin 24+) or Linux (Ubuntu 22.04+).
- **Python**: Version 3.12 or higher.
- **Java**: Java Development Kit (JDK) 21 (Temurin or OpenJDK recommended).
- **Build Tools**: Gradle 8.x or Maven 3.9+ (bundled wrapper preferred).
- **Git**: Git 2.38+ with working tree support.
- **Messaging Platforms**:
  - Mattermost Server or Mattermost Cloud workspace with incoming/outgoing webhook or bot account access.
  - Switch Agent Runtime environment.

---

## 2. Controlled Tooling Specifications (FastAPI Backend)

To prevent hallucinations and guarantee safety, agents interact through strictly validated REST endpoints provided by the IncidentOS Backend.

### 2.1 Log Tool Interface (`/api/tools/logs`)

#### Endpoint: `POST /api/tools/logs/tail`
- **Purpose**: Tail the recent lines of a service log.
- **Input Schema**:
  ```json
  {
    "service_name": "checkout-service",
    "lines": 100,
    "log_file": "application.log"
  }
  ```
- **Validation**:
  - `lines`: Integer, between 1 and 1000.
  - `log_file`: Relative file path within the configured log directory. Absolute paths or paths with `..` are rejected.
- **Output Schema**:
  ```json
  {
    "service_name": "checkout-service",
    "total_lines_returned": 100,
    "log_lines": ["..."],
    "retrieved_at": "2026-11-04T23:10:00Z"
  }
  ```

#### Endpoint: `POST /api/tools/logs/search`
- **Purpose**: Query log entries by keyword or regex within a specific time boundary.
- **Input Schema**:
  ```json
  {
    "service_name": "checkout-service",
    "query": "NullPointerException",
    "level": "ERROR",
    "max_results": 50
  }
  ```
- **Output Schema**:
  ```json
  {
    "matches_count": 12,
    "matched_entries": [
      {
        "timestamp": "2026-11-04T23:02:15.120Z",
        "level": "ERROR",
        "logger": "c.e.checkout.service.PaymentValidator",
        "message": "Validation failed due to unexpected exception",
        "stack_trace": "java.lang.NullPointerException: Cannot invoke \"Customer.getId()\" because \"customer\" is null\n\tat com.example.checkout.service.PaymentValidator.validate(PaymentValidator.java:42)..."
      }
    ]
  }
  ```

---

### 2.2 Git Tool Interface (`/api/tools/git`)

#### Endpoint: `POST /api/tools/git/commits`
- **Purpose**: Inspect recent commits on the repository.
- **Input Schema**:
  ```json
  {
    "repo_path": "demo-environment",
    "branch": "main",
    "count": 5
  }
  ```
- **Output Schema**:
  ```json
  {
    "commits": [
      {
        "commit_hash": "7f2a1b94c3d2",
        "author": "dev@fictional-store.internal",
        "timestamp": "2026-11-04T22:30:00Z",
        "message": "feat: simplify customer session validation in checkout",
        "files_changed": ["src/main/java/com/example/checkout/service/PaymentValidator.java"]
      }
    ]
  }
  ```

#### Endpoint: `POST /api/tools/git/blame`
- **Purpose**: Retrieve line-by-line blame for a specific file.
- **Input Schema**:
  ```json
  {
    "repo_path": "demo-environment",
    "file_path": "src/main/java/com/example/checkout/service/PaymentValidator.java",
    "start_line": 35,
    "end_line": 50
  }
  ```
- **Output Schema**:
  ```json
  {
    "file_path": "src/main/java/com/example/checkout/service/PaymentValidator.java",
    "lines": [
      {
        "line_number": 42,
        "commit_hash": "7f2a1b94c3d2",
        "author": "dev@fictional-store.internal",
        "code": "UUID customerId = customer.getId();"
      }
    ]
  }
  ```

#### Endpoint: `POST /api/tools/git/create-remediation-branch`
- **Purpose**: Create an isolated Git branch and apply the proposed patch.
- **Input Schema**:
  ```json
  {
    "repo_path": "demo-environment",
    "base_branch": "main",
    "new_branch": "remediation/issue-checkout-npe",
    "patch_content": "diff --git a/src/main/java/... b/src/main/java/...\n..."
  }
  ```
- **Validation**:
  - `new_branch`: Must match regex `^remediation/[a-zA-Z0-9_-]+$`.
  - Target branch must not already exist on remote.
- **Output Schema**:
  ```json
  {
    "status": "SUCCESS",
    "branch_created": "remediation/issue-checkout-npe",
    "applied_commit_hash": "a1b2c3d4e5f6",
    "files_modified": ["src/main/java/com/example/checkout/service/PaymentValidator.java"]
  }
  ```

---

### 2.3 Test Runner Interface (`/api/tools/test`)

#### Endpoint: `POST /api/tools/test/execute`
- **Purpose**: Run automated tests on an isolated branch.
- **Input Schema**:
  ```json
  {
    "repo_path": "demo-environment",
    "branch": "remediation/issue-checkout-npe",
    "test_filter": "com.example.checkout.service.PaymentValidatorTest"
  }
  ```
- **Validation**:
  - `test_filter`: Sanitized package and class names only; no shell metacharacters.
- **Output Schema**:
  ```json
  {
    "status": "PASSED",
    "exit_code": 0,
    "duration_seconds": 3.42,
    "tests_run": 5,
    "tests_passed": 5,
    "tests_failed": 0,
    "tests_skipped": 0,
    "raw_output": "BUILD SUCCESSFUL in 3s\n5 actionable tasks: 1 executed, 4 up-to-date\n..."
  }
  ```

---

### 2.4 Human Approval Interface (`/api/incident/approval`)

#### Endpoint: `POST /api/incident/approval/request`
- **Purpose**: Registers an interactive approval request waiting for human review.
- **Input Schema**:
  ```json
  {
    "incident_id": "INC-20261104-01",
    "root_cause_summary": "Null customer object in guest checkout causes NPE in PaymentValidator.validate() line 42.",
    "remediation_branch": "remediation/issue-checkout-npe",
    "remediation_diff": "...",
    "test_results_summary": "5/5 tests passed (including regression test)."
  }
  ```

#### Endpoint: `POST /api/incident/approval/respond`
- **Purpose**: Ingests the human engineer's decision from Mattermost interactive action button.
- **Input Schema**:
  ```json
  {
    "incident_id": "INC-20261104-01",
    "decision": "APPROVED",
    "engineer_id": "@alex",
    "timestamp": "2026-11-04T23:15:30Z",
    "feedback": "Patch verified, guest checkout null check looks good."
  }
  ```
- **Output Schema**:
  ```json
  {
    "status": "RECORDED",
    "approval_token": "appr_tok_991823120abc",
    "next_phase": "POSTMORTEM_GENERATION"
  }
  ```

---

## 3. Incident State Data Contract

All agents and backend services maintain state consistency via the following shared data model:

```python
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum

class IncidentSeverity(str, Enum):
    SEV1 = "SEV-1"
    SEV2 = "SEV-2"
    SEV3 = "SEV-3"
    SEV4 = "SEV-4"

class IncidentState(str, Enum):
    REPORTED = "REPORTED"
    TRIAGED = "TRIAGED"
    INVESTIGATING = "INVESTIGATING"
    ROOT_CAUSE_IDENTIFIED = "ROOT_CAUSE_IDENTIFIED"
    REMEDIATION_PROPOSED = "REMEDIATION_PROPOSED"
    QA_VALIDATED = "QA_VALIDATED"
    PENDING_HUMAN_APPROVAL = "PENDING_HUMAN_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    DOCUMENTED = "DOCUMENTED"
    CLOSED = "CLOSED"

class LogEvidence(BaseModel):
    timestamp: str
    service: str
    level: str
    culprit_class: str
    culprit_method: str
    culprit_line: int
    raw_stack_trace: str

class CodeEvidence(BaseModel):
    culprit_commit_hash: str
    commit_author: str
    commit_message: str
    affected_file: str
    diff_snippet: str

class QAValidationEvidence(BaseModel):
    test_suite: str
    branch: str
    tests_run: int
    tests_passed: int
    tests_failed: int
    raw_output: str
    passed: bool

class HumanApprovalRecord(BaseModel):
    decision: str  # APPROVED / REJECTED
    engineer_handle: str
    decided_at: datetime
    feedback_notes: Optional[str] = None
    approval_token: str
```
