import logging
import re
import time
import uuid
from fastapi import Depends, FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.auth import verify_api_token
from app.api.health import router as health_router
from app.api.incidents import router as incidents_router
from app.api.tools import router as tools_router
from app.logging_config import logger, sanitize_paths, setup_logging
from app.schemas.common import ErrorResponse
from app.tools.workspace import (
    FileSizeLimitExceededError,
    InvalidInputError,
    PathTraversalError,
    RestrictedPathError,
    SymlinkEscapeError,
    WorkspaceSecurityError,
)

# Initialize structured logging on startup
setup_logging()

app = FastAPI(
    title="IncidentOS Controlled Tools API",
    version="0.1.0",
    description="Sandboxed backend providing verified, least-privilege tools for IncidentOS agents.",
)

# Restrict CORS to localhost
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://127.0.0.1", "http://localhost:3000", "http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


# Structured Logging and Request Correlation Middleware
@app.middleware("http")
async def structured_logging_middleware(request: Request, call_next):
    # Extract or generate correlation request ID
    raw_req_id = request.headers.get("X-Request-ID")
    if raw_req_id and raw_req_id.strip():
        # Sanitize incoming request ID to prevent header/log injection
        request_id = re.sub(r"[^a-zA-Z0-9_\-\.]", "", raw_req_id.strip())[:64]
        if not request_id:
            request_id = str(uuid.uuid4())
    else:
        request_id = str(uuid.uuid4())

    request.state.request_id = request_id
    start_time = time.perf_counter()

    try:
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
        response.headers["X-Request-ID"] = request_id

        # Determine log level based on response status
        if response.status_code >= 500:
            log_level = logging.ERROR
        elif response.status_code >= 400:
            log_level = logging.WARNING
        else:
            log_level = logging.INFO

        # Security: Never log Authorization, X-API-Key, or request bodies
        logger.log(
            log_level,
            f"{request.method} {request.url.path} {response.status_code} ({duration_ms}ms)",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "client_ip": request.client.host if request.client else "unknown",
            },
        )
        return response

    except Exception as exc:
        duration_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
        sanitized_err = sanitize_paths(str(exc))
        logger.error(
            f"Unhandled server error on {request.method} {request.url.path}: {sanitized_err}",
            exc_info=True,
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": 500,
                "duration_ms": duration_ms,
                "client_ip": request.client.host if request.client else "unknown",
                "error_type": type(exc).__name__,
                "sanitized_error": sanitized_err,
            },
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(
                error_code="INTERNAL_SERVER_ERROR",
                message="An unexpected internal server error occurred.",
                detail=None,
            ).model_dump(),
            headers={"X-Request-ID": request_id},
        )


# Include Routers:
# Public health endpoint (for health checks and monitoring)
app.include_router(health_router)

# Protected API endpoints (require valid API token)
app.include_router(incidents_router, dependencies=[Depends(verify_api_token)])
app.include_router(tools_router, dependencies=[Depends(verify_api_token)])


# Global Security Exception Handlers
@app.exception_handler(PathTraversalError)
@app.exception_handler(SymlinkEscapeError)
@app.exception_handler(RestrictedPathError)
async def security_violation_handler(request: Request, exc: WorkspaceSecurityError):
    request_id = getattr(request.state, "request_id", None) or "unknown"
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content=ErrorResponse(
            error_code="SECURITY_VIOLATION",
            message="Workspace access security policy violation.",
            detail=sanitize_paths(str(exc)),
        ).model_dump(),
        headers={"X-Request-ID": request_id} if request_id != "unknown" else {},
    )


@app.exception_handler(InvalidInputError)
@app.exception_handler(FileSizeLimitExceededError)
async def invalid_input_handler(request: Request, exc: WorkspaceSecurityError):
    request_id = getattr(request.state, "request_id", None) or "unknown"
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=ErrorResponse(
            error_code="INVALID_WORKSPACE_INPUT",
            message="Invalid input or resource limit exceeded.",
            detail=sanitize_paths(str(exc)),
        ).model_dump(),
        headers={"X-Request-ID": request_id} if request_id != "unknown" else {},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", None) or request.headers.get("X-Request-ID") or "unknown"
    sanitized_err = sanitize_paths(str(exc))
    logger.error(
        f"Unhandled exception on {request.method} {request.url.path}: {sanitized_err}",
        exc_info=True,
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": 500,
            "error_type": type(exc).__name__,
            "sanitized_error": sanitized_err,
        },
    )
    headers = {"X-Request-ID": request_id} if request_id != "unknown" else {}
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error_code="INTERNAL_SERVER_ERROR",
            message="An unexpected internal server error occurred.",
            detail=None,
        ).model_dump(),
        headers=headers,
    )


@app.get("/")
def get_root():
    return {
        "service": "IncidentOS Controlled Tools Backend",
        "status": "operational",
        "docs_url": "/docs",
    }
