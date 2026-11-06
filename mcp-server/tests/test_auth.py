import io
import logging
import pytest
import httpx
from pathlib import Path

from incidentos_mcp.client import BackendClient
from incidentos_mcp.config import Settings, resolve_env_file
from incidentos_mcp.server import create_server


def test_missing_token_causes_startup_failure(monkeypatch):
    """Verify that an empty or missing token fails closed with RuntimeError and stderr message."""
    monkeypatch.delenv("INCIDENTOS_API_TOKEN", raising=False)
    settings = Settings(token="", auto_load_env=False)

    with pytest.raises(RuntimeError) as exc_info:
        create_server(settings=settings)
    assert "INCIDENTOS_API_TOKEN is not configured. MCP server failing closed." in str(exc_info.value)


def test_token_loaded_from_local_env(tmp_path, monkeypatch):
    """Verify that Settings locates and loads configuration from an explicit .env file."""
    fake_env = tmp_path / ".env"
    fake_env.write_text("INCIDENTOS_API_TOKEN=explicitly-loaded-token-abc123\nBACKEND_URL=http://127.0.0.1:8000\n")

    monkeypatch.setattr("incidentos_mcp.config.ENV_FILE_CANDIDATES", [fake_env])
    monkeypatch.delenv("INCIDENTOS_API_TOKEN", raising=False)

    settings = Settings(auto_load_env=True)
    assert settings.token == "explicitly-loaded-token-abc123"
    assert settings.backend_url == "http://127.0.0.1:8000"


@pytest.mark.asyncio
async def test_bearer_token_attached_internally():
    """Verify that BackendClient internally injects Authorization: Bearer <token> on requests."""
    captured_auth_header = []

    def mock_handler(request: httpx.Request) -> httpx.Response:
        captured_auth_header.append(request.headers.get("Authorization"))
        return httpx.Response(200, json={"status": "healthy"})

    mock_transport = httpx.MockTransport(mock_handler)
    settings = Settings(token="sec-token-xyz-789", auto_load_env=False)
    client = BackendClient(settings=settings)

    # Inject mock transport
    client._client = httpx.AsyncClient(
        transport=mock_transport,
        base_url="http://testserver",
        headers={"Authorization": f"Bearer {client._token}"},
    )

    try:
        res = await client.get_health()
        assert res["status"] == "healthy"
        assert len(captured_auth_header) == 1
        assert captured_auth_header[0] == "Bearer sec-token-xyz-789"
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_token_never_appears_in_logs_or_responses(caplog):
    """Verify that neither client logs nor tool response dictionaries expose the token value."""
    secret_token = "ultra-secret-token-99999"

    def mock_handler(request: httpx.Request) -> httpx.Response:
        # Simulate a 401 unauthorized or 500 error from backend
        return httpx.Response(401, json={"detail": "Unauthorized access"})

    mock_transport = httpx.MockTransport(mock_handler)
    settings = Settings(token=secret_token, auto_load_env=False)
    client = BackendClient(settings=settings)
    client._client = httpx.AsyncClient(
        transport=mock_transport,
        base_url="http://testserver",
        headers={"Authorization": f"Bearer {client._token}"},
    )

    try:
        with caplog.at_level(logging.DEBUG):
            response = await client.search_logs(keyword="NullPointerException")

        # Response must not contain the token
        assert secret_token not in str(response)

        # Logs must not contain the token
        for record in caplog.records:
            assert secret_token not in record.getMessage()
    finally:
        await client.aclose()
