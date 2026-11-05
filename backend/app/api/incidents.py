from typing import List
from fastapi import APIRouter, HTTPException, status

from app.schemas.incident import Incident
from app.services.incident_service import incident_service

router = APIRouter(prefix="/api/incidents", tags=["Incidents"])


@router.get("", response_model=List[Incident])
def list_incidents() -> List[Incident]:
    """Retrieve all current and archived incidents."""
    return incident_service.list_incidents()


@router.get("/{incident_id}", response_model=Incident)
def get_incident(incident_id: str) -> Incident:
    """Retrieve a specific incident by ID, including its timeline and findings."""
    inc = incident_service.get_incident(incident_id)
    if not inc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident '{incident_id}' not found.",
        )
    return inc
