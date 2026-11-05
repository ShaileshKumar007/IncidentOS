from app.tools.deployment_tools import get_deployment_history


def test_get_deployments_all(temp_workspace):
    res = get_deployment_history(demo_root=temp_workspace)
    assert res.total_deployments == 2
    assert res.audit.status == "SUCCESS"
    assert res.audit.tool_name == "deployments.get_history"


def test_get_deployments_filter_service(temp_workspace):
    res = get_deployment_history(service="checkout-service", demo_root=temp_workspace)
    assert res.total_deployments == 2
    for d in res.deployments:
        assert d.service == "checkout-service"


def test_get_deployments_filter_version(temp_workspace):
    res = get_deployment_history(version="1.4.2", demo_root=temp_workspace)
    assert res.total_deployments == 1
    assert res.deployments[0].version == "1.4.2"
    assert res.deployments[0].commit_hash == "7f2a1b94c3d2"


def test_get_deployments_filter_time(temp_workspace):
    res = get_deployment_history(start_time="2026-11-04T00:00:00Z", demo_root=temp_workspace)
    assert res.total_deployments == 1
    assert res.deployments[0].version == "1.4.2"


def test_api_deployment_endpoint(client, temp_workspace, monkeypatch):
    import app.tools.deployment_tools as dep_mod
    monkeypatch.setattr(dep_mod, "DEMO_WORKSPACE_ROOT", temp_workspace)

    resp = client.get("/api/tools/deployments?version=1.4.2")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_deployments"] == 1
    assert data["deployments"][0]["version"] == "1.4.2"
    assert "audit" in data
