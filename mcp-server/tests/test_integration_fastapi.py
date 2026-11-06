import json
import os
import pytest
import httpx
from pathlib import Path

from app.main import app
from incidentos_mcp.client import BackendClient
from incidentos_mcp.config import Settings
from incidentos_mcp.server import create_server


@pytest.mark.asyncio
async def test_fastapi_integration_health_and_auth(monkeypatch):
    """
    Integration test mounting the actual FastAPI backend into BackendClient via ASGITransport.
    Verifies full end-to-end flow with real FastAPI middleware, authentication, and error handlers.
    """
    valid_token = "integration-test-token-valid-12345"
    monkeypatch.setenv("INCIDENTOS_API_TOKEN", valid_token)

    settings = Settings(token=valid_token, auto_load_env=False)
    client = BackendClient(settings=settings)

    # Use ASGITransport to route requests directly into the FastAPI app
    transport = httpx.ASGITransport(app=app)
    client._client = httpx.AsyncClient(
        transport=transport,
        base_url="http://127.0.0.1:8000",
        headers={"Authorization": f"Bearer {valid_token}"},
    )

    server = create_server(client=client)

    try:
        # 1. Health check through MCP
        health_res = await server.call_tool("incidentos_health", {})
        health_data = json.loads(health_res[0].text)
        assert health_data["status"] == "healthy"
        assert health_data["service"] == "incidentos-backend"

        # 2. Search logs through MCP
        logs_res = await server.call_tool("incidentos_search_logs", {"limit": 10})
        logs_data = json.loads(logs_res[0].text)
        assert "total_matches" in logs_data
        assert "records" in logs_data
        assert "audit" in logs_data

        # 3. Deployments list through MCP
        dep_res = await server.call_tool("incidentos_list_deployments", {})
        dep_data = json.loads(dep_res[0].text)
        assert "total_deployments" in dep_data

        # 4. Rejection of unapproved test suite through MCP
        test_res = await server.call_tool(
            "incidentos_run_approved_tests",
            {"test_suite": "unauthorized-malicious-test"},
        )
        test_data = json.loads(test_res[0].text)
        assert test_data["status"] == "ERROR"
        assert test_data["status_code"] == 400

    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_fastapi_integration_invalid_token(monkeypatch):
    """Verify that an invalid token causes FastAPI to return 401, sanitized through MCP."""
    monkeypatch.setenv("INCIDENTOS_API_TOKEN", "actual-server-token")

    # Client configured with wrong token
    bad_settings = Settings(token="wrong-token-55555", auto_load_env=False)
    client = BackendClient(settings=bad_settings)
    transport = httpx.ASGITransport(app=app)
    client._client = httpx.AsyncClient(
        transport=transport,
        base_url="http://127.0.0.1:8000",
        headers={"Authorization": "Bearer wrong-token-55555"},
    )

    server = create_server(client=client)

    try:
        res = await server.call_tool("incidentos_search_logs", {})
        data = json.loads(res[0].text)
        assert data["status_code"] == 401
        assert "error" in data
        assert "wrong-token-55555" not in str(data)
    finally:
        await client.aclose()
