import io
import json
import logging
import sys
import pytest
import httpx

from incidentos_mcp.client import BackendClient
from incidentos_mcp.config import Settings
from incidentos_mcp.server import configure_logging, create_server


def test_diagnostics_go_to_stderr_never_stdout(capsys):
    """
    Verify that configure_logging() routes all log events to sys.stderr
    and leaves sys.stdout pristine for MCP JSON-RPC protocol messages.
    """
    configure_logging()
    logger = logging.getLogger("incidentos_mcp.test")
    logger.info("Test diagnostic message to stderr")
    logger.warning("Test warning diagnostic to stderr")

    captured = capsys.readouterr()
    assert captured.out == "", "sys.stdout must remain completely empty to avoid corrupting MCP JSON-RPC protocol"
    assert "Test diagnostic message to stderr" in captured.err
    assert "Test warning diagnostic to stderr" in captured.err


@pytest.mark.asyncio
async def test_mcp_tool_execution_protocol_format():
    """Verify that FastMCP call_tool returns standard TextContent holding serialized JSON."""
    settings = Settings(token="sec-token-123", auto_load_env=False)
    client = BackendClient(settings=settings)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"status": "healthy"})

    client._client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="http://testserver"
    )
    server = create_server(client=client)

    result = await server.call_tool("incidentos_health", {})
    assert isinstance(result, list)
    assert len(result) == 1
    content_item = result[0]
    assert content_item.type == "text"
    # Ensure it deserializes cleanly from valid JSON
    parsed = json.loads(content_item.text)
    assert parsed["status"] == "healthy"


@pytest.mark.asyncio
async def test_graceful_shutdown_closes_resources():
    """Verify that BackendClient cleanly closes underlying httpx client sessions."""
    settings = Settings(token="test-token", auto_load_env=False)
    client = BackendClient(settings=settings)

    http_client = await client.get_client()
    assert not http_client.is_closed

    await client.aclose()
    assert client._client is None
