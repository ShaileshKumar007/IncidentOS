from fastapi import Depends, FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.auth import verify_api_token
from app.api.health import router as health_router
from app.api.incidents import router as incidents_router
from app.api.tools import router as tools_router
from app.schemas.common import ErrorResponse
from app.tools.workspace import (
    FileSizeLimitExceededError,
    InvalidInputError,
    PathTraversalError,
    RestrictedPathError,
    SymlinkEscapeError,
    WorkspaceSecurityError,
)

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
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content=ErrorResponse(
            error_code="SECURITY_VIOLATION",
            message="Workspace access security policy violation.",
            detail=str(exc),
        ).model_dump(),
    )


@app.exception_handler(InvalidInputError)
@app.exception_handler(FileSizeLimitExceededError)
async def invalid_input_handler(request: Request, exc: WorkspaceSecurityError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=ErrorResponse(
            error_code="INVALID_WORKSPACE_INPUT",
            message="Invalid input or resource limit exceeded.",
            detail=str(exc),
        ).model_dump(),
    )


@app.get("/")
def get_root():
    return {
        "service": "IncidentOS Controlled Tools Backend",
        "status": "operational",
        "docs_url": "/docs",
    }
