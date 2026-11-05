def test_list_incidents(client):
    response = client.get("/api/incidents")
    assert response.status_code == 200
    incidents = response.json()
    assert isinstance(incidents, list)
    assert len(incidents) >= 1

    checkout_inc = next((i for i in incidents if i["incident_id"] == "INC-20261104-01"), None)
    assert checkout_inc is not None
    assert checkout_inc["severity"] == "SEV-1"
    assert checkout_inc["affected_service"] == "checkout-service"
    assert checkout_inc["status"] == "INVESTIGATING"
    assert len(checkout_inc["findings"]) >= 2

    # Verify findings distinguish OBSERVATION and HYPOTHESIS
    finding_types = [f["finding_type"] for f in checkout_inc["findings"]]
    assert "OBSERVATION" in finding_types
    assert "HYPOTHESIS" in finding_types


def test_get_incident_by_id(client):
    response = client.get("/api/incidents/INC-20261104-01")
    assert response.status_code == 200
    inc = response.json()
    assert inc["incident_id"] == "INC-20261104-01"
    assert inc["title"] == "Spike in HTTP 500 on /api/checkout"
    assert len(inc["timeline"]) >= 2


def test_get_incident_not_found(client):
    response = client.get("/api/incidents/NON_EXISTENT_INCIDENT")
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
