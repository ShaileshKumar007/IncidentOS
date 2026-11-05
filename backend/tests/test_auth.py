from tests.conftest import TEST_API_TOKEN


def test_public_endpoints_accessible_without_token(unauthenticated_client):
    # Health endpoint is public
    health_resp = unauthenticated_client.get("/health")
    assert health_resp.status_code == 200
    assert health_resp.json()["status"] == "healthy"

    # Root endpoint is public
    root_resp = unauthenticated_client.get("/")
    assert root_resp.status_code == 200
    assert root_resp.json()["status"] == "operational"


def test_protected_endpoints_reject_missing_token(unauthenticated_client):
    # Incidents API
    inc_resp = unauthenticated_client.get("/api/incidents")
    assert inc_resp.status_code == 401
    err = inc_resp.json()
    assert "detail" in err
    assert "error_code" in err["detail"]
    assert err["detail"]["error_code"] == "UNAUTHORIZED"
    # Never expose tokens
    assert TEST_API_TOKEN not in str(err)

    # Tools API
    tool_resp = unauthenticated_client.get("/api/tools/logs/search")
    assert tool_resp.status_code == 401


def test_protected_endpoints_reject_invalid_token(unauthenticated_client):
    headers = {"Authorization": "Bearer completely-invalid-fake-token"}
    resp = unauthenticated_client.get("/api/incidents", headers=headers)
    assert resp.status_code == 401
    err = resp.json()
    assert err["detail"]["error_code"] == "UNAUTHORIZED"
    assert "Invalid API token" in err["detail"]["message"]
    assert "completely-invalid-fake-token" not in str(err)


def test_protected_endpoints_accept_valid_bearer_token(unauthenticated_client):
    headers = {"Authorization": f"Bearer {TEST_API_TOKEN}"}
    resp = unauthenticated_client.get("/api/incidents", headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_protected_endpoints_accept_valid_x_api_key(unauthenticated_client):
    headers = {"X-API-Key": TEST_API_TOKEN}
    resp = unauthenticated_client.get("/api/incidents", headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
