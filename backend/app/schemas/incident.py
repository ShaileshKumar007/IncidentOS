from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class IncidentSeverity(str, Enum):
    SEV1 = "SEV-1"
    SEV2 = "SEV-2"
    SEV3 = "SEV-3"
    SEV4 = "SEV-4"


class IncidentStatus(str, Enum):
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


class FindingType(str, Enum):
    OBSERVATION = "OBSERVATION"
    HYPOTHESIS = "HYPOTHESIS"
    CONFIRMED_ROOT_CAUSE = "CONFIRMED_ROOT_CAUSE"


class EvidenceReference(BaseModel):
    """Identifies concrete source, location and excerpt for factual validation."""
    evidence_id: str
    source: str = Field(description="e.g., 'logs', 'git', 'deployments', 'tests'")
    location: str = Field(description="e.g., 'logs/error-traces.jsonl:1' or 'commit:7f2a1b94c3d2'")
    excerpt: str = Field(description="Verbatim excerpt or diff segment")
    timestamp: Optional[str] = None


class InvestigationFinding(BaseModel):
    """Investigation finding categorized as OBSERVATION, HYPOTHESIS, or CONFIRMED_ROOT_CAUSE."""
    finding_id: str
    incident_id: str
    agent_id: str
    finding_type: FindingType
    claim: str
    evidence_references: List[EvidenceReference] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Incident(BaseModel):
    """Incident data model representing current operational state."""
    incident_id: str
    title: str
    severity: IncidentSeverity
    status: IncidentStatus
    affected_service: str
    description: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    lead_agent: Optional[str] = "incident-commander"
    findings: List[InvestigationFinding] = Field(default_factory=list)
    timeline: List[Dict[str, Any]] = Field(default_factory=list)
    human_approval: Optional[Dict[str, Any]] = None
