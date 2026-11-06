from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.schemas.common import ToolExecutionResult


# ==============================================================================
# 1. Log Tool Schemas
# ==============================================================================
class LogRecord(BaseModel):
    log_id: Optional[str] = None
    timestamp: str
    level: str
    service: str
    logger: Optional[str] = None
    message: str
    trace_id: Optional[str] = None
    source_file: Optional[str] = None
    line_number: Optional[int] = None
    stack_trace: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class LogSearchResponse(BaseModel):
    total_matches: int
    returned_count: int
    records: List[LogRecord]
    audit: ToolExecutionResult


# ==============================================================================
# 2. Deployment Tool Schemas
# ==============================================================================
class DeploymentRecord(BaseModel):
    deployment_id: str
    service: str
    version: str
    environment: str
    deployed_at: str
    status: str
    commit_hash: str
    deployer: str
    release_notes: Optional[str] = None
    synthetic_marker: Optional[str] = None


class DeploymentSearchResponse(BaseModel):
    total_deployments: int
    deployments: List[DeploymentRecord]
    audit: ToolExecutionResult


# ==============================================================================
# 3. Git Tool Schemas
# ==============================================================================
class GitCommitRecord(BaseModel):
    commit_hash: str
    author: str
    date: str
    message: str
    files_changed: List[str] = Field(default_factory=list)


class GitHistoryResponse(BaseModel):
    repo_path: str
    commits: List[GitCommitRecord]
    audit: ToolExecutionResult


class GitDiffResponse(BaseModel):
    repo_path: str
    target_commit: Optional[str] = None
    base_commit: Optional[str] = None
    file_path: Optional[str] = None
    diff_content: str
    audit: ToolExecutionResult


# ==============================================================================
# 4. Test Tool Schemas
# ==============================================================================
class TestRunRequest(BaseModel):
    __test__ = False
    test_suite: str = Field(
        description="Name of the pre-approved test suite (e.g. 'checkout-service-unit-tests', 'payment-validator-tests')"
    )
    incident_id: Optional[str] = None
    agent_id: Optional[str] = None


class TestRunResponse(BaseModel):
    __test__ = False
    test_suite: str
    status: str = Field(description="PASSED, FAILED, TIMEOUT, or ERROR")
    exit_code: int
    duration_seconds: float
    tests_run: int
    tests_passed: int
    tests_failed: int
    tests_skipped: int = 0
    tests_found: Optional[int] = None
    tests_aborted: int = 0
    output: str
    audit: ToolExecutionResult
