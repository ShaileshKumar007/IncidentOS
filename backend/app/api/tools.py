from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status

from app.logging_config import sanitize_paths
from app.schemas.tools import (
    DeploymentSearchResponse,
    GitDiffResponse,
    GitHistoryResponse,
    LogRecord,
    LogSearchResponse,
    TestRunRequest,
    TestRunResponse,
)
from app.tools.deployment_tools import get_deployment_history
from app.tools.git_tools import get_git_diff, get_git_history
from app.tools.log_tools import get_log_by_id, search_logs
from app.tools.test_tools import run_tests
from app.tools.workspace import (
    FileSizeLimitExceededError,
    InvalidInputError,
    PathTraversalError,
    RestrictedPathError,
    SymlinkEscapeError,
)

router = APIRouter(prefix="/api/tools", tags=["Investigation Tools"])


# ==============================================================================
# 1. Log Tools
# ==============================================================================
@router.get("/logs/search", response_model=LogSearchResponse)
def api_search_logs(
    service: Optional[str] = Query(None, description="Service name filter (e.g. 'checkout-service')"),
    severity: Optional[str] = Query(None, description="Severity / level filter (e.g. 'ERROR', 'WARN', 'INFO')"),
    keyword: Optional[str] = Query(None, description="Search keyword or substring"),
    start_time: Optional[str] = Query(None, description="Start timestamp (ISO-8601)"),
    end_time: Optional[str] = Query(None, description="End timestamp (ISO-8601)"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of log records to return"),
    incident_id: Optional[str] = Query(None, description="Associated incident ID for audit tracking"),
    agent_id: Optional[str] = Query(None, description="Calling agent identity for audit tracking"),
) -> LogSearchResponse:
    """Search application and error logs within the sandboxed workspace."""
    try:
        return search_logs(
            service=service,
            severity=severity,
            keyword=keyword,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            incident_id=incident_id,
            agent_id=agent_id,
        )
    except (PathTraversalError, SymlinkEscapeError, RestrictedPathError) as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=sanitize_paths(str(e)))
    except (InvalidInputError, FileSizeLimitExceededError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=sanitize_paths(str(e)))


@router.get("/logs/{log_id}", response_model=LogRecord)
def api_get_log(
    log_id: str,
    incident_id: Optional[str] = Query(None, description="Associated incident ID for audit tracking"),
    agent_id: Optional[str] = Query(None, description="Calling agent identity for audit tracking"),
) -> LogRecord:
    """Retrieve detailed log record and stack trace by log_id or trace_id."""
    try:
        record, audit = get_log_by_id(
            log_id=log_id,
            incident_id=incident_id,
            agent_id=agent_id,
        )
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Log entry '{log_id}' not found.",
            )
        return record
    except (PathTraversalError, SymlinkEscapeError, RestrictedPathError) as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=sanitize_paths(str(e)))


# ==============================================================================
# 2. Deployment Tools
# ==============================================================================
@router.get("/deployments", response_model=DeploymentSearchResponse)
def api_get_deployments(
    service: Optional[str] = Query(None, description="Service name filter"),
    version: Optional[str] = Query(None, description="Release version filter"),
    start_time: Optional[str] = Query(None, description="Start timestamp (ISO-8601)"),
    end_time: Optional[str] = Query(None, description="End timestamp (ISO-8601)"),
    incident_id: Optional[str] = Query(None, description="Associated incident ID for audit tracking"),
    agent_id: Optional[str] = Query(None, description="Calling agent identity for audit tracking"),
) -> DeploymentSearchResponse:
    """Retrieve deployment records from the sandboxed environment."""
    return get_deployment_history(
        service=service,
        version=version,
        start_time=start_time,
        end_time=end_time,
        incident_id=incident_id,
        agent_id=agent_id,
    )


# ==============================================================================
# 3. Git Tools
# ==============================================================================
@router.get("/git/history", response_model=GitHistoryResponse)
def api_get_git_history(
    count: int = Query(10, ge=1, le=50, description="Number of commits to retrieve"),
    path: Optional[str] = Query(None, description="Filter history by relative file path"),
    branch: Optional[str] = Query(None, description="Branch name (default: HEAD)"),
    incident_id: Optional[str] = Query(None, description="Associated incident ID for audit tracking"),
    agent_id: Optional[str] = Query(None, description="Calling agent identity for audit tracking"),
) -> GitHistoryResponse:
    """Inspect Git commit history for the demo repository."""
    try:
        return get_git_history(
            count=count,
            path=path,
            branch=branch,
            incident_id=incident_id,
            agent_id=agent_id,
        )
    except (PathTraversalError, SymlinkEscapeError, RestrictedPathError) as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=sanitize_paths(str(e)))
    except InvalidInputError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=sanitize_paths(str(e)))


@router.get("/git/diff", response_model=GitDiffResponse)
def api_get_git_diff(
    target_commit: Optional[str] = Query(None, description="Target commit hash to diff"),
    base_commit: Optional[str] = Query(None, description="Base commit hash to diff against"),
    path: Optional[str] = Query(None, description="Filter diff by relative file path"),
    incident_id: Optional[str] = Query(None, description="Associated incident ID for audit tracking"),
    agent_id: Optional[str] = Query(None, description="Calling agent identity for audit tracking"),
) -> GitDiffResponse:
    """Inspect Git diffs for specific commits or files in the demo repository."""
    try:
        return get_git_diff(
            target_commit=target_commit,
            base_commit=base_commit,
            path=path,
            incident_id=incident_id,
            agent_id=agent_id,
        )
    except (PathTraversalError, SymlinkEscapeError, RestrictedPathError) as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=sanitize_paths(str(e)))
    except InvalidInputError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=sanitize_paths(str(e)))


# ==============================================================================
# 4. Test Tools
# ==============================================================================
@router.post("/tests/run", response_model=TestRunResponse)
def api_run_tests(request: TestRunRequest) -> TestRunResponse:
    """Execute pre-approved test suite in a sandboxed runner with timeout limits."""
    try:
        return run_tests(request=request)
    except InvalidInputError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=sanitize_paths(str(e)))
