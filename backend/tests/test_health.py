def test_health_check_public_unauthenticated(unauthenticated_client):
    """Verify that /health is public and responds 200 OK without requiring authentication."""
    response = unauthenticated_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "incidentos-backend"
    assert data["version"] == "0.1.0"
    assert "timestamp" in data


def test_health_check_authenticated(client):
    """Verify that /health responds 200 OK when authenticated."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_root_endpoint(unauthenticated_client):
    """Verify that root endpoint / is public and operational."""
    response = unauthenticated_client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "operational"
    assert "/docs" in data["docs_url"]


def test_no_duplicate_api_health_endpoint(client, unauthenticated_client):
    """
    Verify that there is no duplicate /api/health endpoint.
    The canonical health endpoint is strictly /health.
    """
    # Authenticated client requesting /api/health must get 404 Not Found
    resp_auth = client.get("/api/health")
    assert resp_auth.status_code == 404

    # Unauthenticated client requesting /api/health cannot access a public health check
    resp_unauth = unauthenticated_client.get("/api/health")
    assert resp_unauth.status_code in (401, 404)


def test_protected_api_endpoints_require_authentication(unauthenticated_client):
    """Verify that protected /api/* endpoints strictly reject unauthenticated requests."""
    protected_paths = [
        ("GET", "/api/incidents"),
        ("GET", "/api/tools/git/history"),
        ("GET", "/api/tools/git/diff"),
        ("GET", "/api/tools/logs/search"),
        ("GET", "/api/tools/deployments"),
        ("POST", "/api/tools/tests/run"),
    ]
    for method, path in protected_paths:
        if method == "GET":
            resp = unauthenticated_client.get(path)
        else:
            resp = unauthenticated_client.post(path, json={})
        assert resp.status_code == 401, f"Expected 401 for unauthenticated {method} {path}, got {resp.status_code}"
