from datetime import datetime, timezone
from typing import Dict
from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/health")
def get_health() -> Dict[str, str]:
    """Health check endpoint confirming service status and readiness."""
    return {
        "status": "healthy",
        "service": "incidentos-backend",
        "version": "0.1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
