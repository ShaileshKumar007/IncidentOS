from datetime import datetime, timezone
from typing import Dict, List, Optional

from app.schemas.incident import (
    EvidenceReference,
    FindingType,
    Incident,
    IncidentSeverity,
    IncidentStatus,
    InvestigationFinding,
)


class IncidentService:
    """Manages in-memory incident records and findings."""

    def __init__(self):
        self._incidents: Dict[str, Incident] = {}
        self._seed_default_incident()

    def _seed_default_incident(self) -> None:
        """Seed the fictional demo checkout incident."""
        inc_id = "INC-20261104-01"
        now = datetime.now(timezone.utc)

        sample_findings = [
            InvestigationFinding(
                finding_id="fnd-001",
                incident_id=inc_id,
                agent_id="log-investigator",
                finding_type=FindingType.OBSERVATION,
                claim="NullPointerException observed during checkout requests on /api/checkout.",
                evidence_references=[
                    EvidenceReference(
                        evidence_id="ev-log-01",
                        source="logs",
                        location="logs/error-traces.jsonl:1",
                        excerpt='Cannot invoke "Customer.getId()" because "customer" is null at PaymentValidator.java:42',
                        timestamp="2026-11-04T22:05:22.025Z",
                    )
                ],
                created_at=now,
            ),
            InvestigationFinding(
                finding_id="fnd-002",
                incident_id=inc_id,
                agent_id="code-investigator",
                finding_type=FindingType.HYPOTHESIS,
                claim="Recent commit 6014328 removed null-check on guest customer objects.",
                evidence_references=[
                    EvidenceReference(
                        evidence_id="ev-git-01",
                        source="git",
                        location="commit:6014328",
                        excerpt="- UUID customerId = (customer != null) ? customer.getId() : null;\n+ UUID customerId = customer.getId();",
                        timestamp="2026-11-04T21:45:00.000Z",
                    )
                ],
                created_at=now,
            ),
        ]

        timeline = [
            {
                "timestamp": "2026-11-04T22:05:22.000Z",
                "event": "Alert Triggered",
                "details": "15% spike in HTTP 500 responses on POST /api/checkout",
                "source": "monitoring",
            },
            {
                "timestamp": "2026-11-04T22:06:00.000Z",
                "event": "Incident Declared",
                "details": "Incident Commander declared SEV-1 and initiated triage",
                "source": "incident-commander",
            },
        ]

        self._incidents[inc_id] = Incident(
            incident_id=inc_id,
            title="Spike in HTTP 500 on /api/checkout",
            severity=IncidentSeverity.SEV1,
            status=IncidentStatus.INVESTIGATING,
            affected_service="checkout-service",
            description="Checkout endpoint returning HTTP 500 errors after deployment v1.4.2.",
            created_at=now,
            updated_at=now,
            lead_agent="incident-commander",
            findings=sample_findings,
            timeline=timeline,
        )

    def list_incidents(self) -> List[Incident]:
        return list(self._incidents.values())

    def get_incident(self, incident_id: str) -> Optional[Incident]:
        return self._incidents.get(incident_id)

    def add_finding(self, incident_id: str, finding: InvestigationFinding) -> Optional[Incident]:
        incident = self._incidents.get(incident_id)
        if not incident:
            return None
        incident.findings.append(finding)
        incident.updated_at = datetime.now(timezone.utc)
        return incident

    def update_status(self, incident_id: str, status: IncidentStatus) -> Optional[Incident]:
        incident = self._incidents.get(incident_id)
        if not incident:
            return None
        incident.status = status
        incident.updated_at = datetime.now(timezone.utc)
        return incident


# Singleton instance
incident_service = IncidentService()
