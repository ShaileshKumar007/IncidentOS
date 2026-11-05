import os
import secrets
from typing import Optional
from fastapi import Header, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.schemas.common import ErrorResponse

# Read API token from environment variable. Never hardcode or commit tokens.
API_TOKEN_ENV_VAR = "INCIDENTOS_API_TOKEN"

bearer_scheme = HTTPBearer(auto_error=False)


def get_configured_token() -> Optional[str]:
    """Retrieves the configured API token from the environment."""
    token = os.environ.get(API_TOKEN_ENV_VAR)
    if token:
        token = token.strip()
    return token or None


async def verify_api_token(
    auth_header: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
) -> str:
    """
    Validates API authentication token for all protected /api/* endpoints.
    
    Supports:
    - Authorization: Bearer <token>
    - X-API-Key: <token>
    
    Security Guarantees:
    - Constant-time token comparison using secrets.compare_digest.
    - Never logs or exposes token values in error responses or logs.
    - Returns HTTP 401 for missing, malformed, or invalid tokens.
    """
    configured_token = get_configured_token()
    if not configured_token:
        # If no token is configured in environment, reject requests for safety
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ErrorResponse(
                error_code="UNAUTHORIZED",
                message="Authentication failed: server API token is not configured.",
            ).model_dump(),
        )

    provided_token: Optional[str] = None
    if auth_header and auth_header.credentials:
        provided_token = auth_header.credentials.strip()
    elif x_api_key:
        provided_token = x_api_key.strip()

    if not provided_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ErrorResponse(
                error_code="UNAUTHORIZED",
                message="Missing API token. Provide Authorization: Bearer <token> or X-API-Key.",
            ).model_dump(),
        )

    # Secure constant-time comparison
    if not secrets.compare_digest(provided_token, configured_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ErrorResponse(
                error_code="UNAUTHORIZED",
                message="Invalid API token.",
            ).model_dump(),
        )

    return provided_token
