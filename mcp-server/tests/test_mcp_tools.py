import json
import pytest
import httpx

from incidentos_mcp.client import BackendClient
from incidentos_mcp.config import Settings
from incidentos_mcp.server import create_server
from incidentos_mcp.tools.tests import APPROVED_TEST_SUITES


@pytest.fixture
def mock_backend_client():
    settings = Settings(token="test-token-fixed", auto_load_env=False)
    client = BackendClient(settings=settings)
    return client


def test_tool_discovery_and_schemas(mock_backend_client):
    """Verify that all seven tools are registered with schemas and non-empty descriptions."""
    server = create_server(client=mock_backend_client)
    tools = server._tool_manager.list_tools()

    expected_tool_names = {
        "incidentos_health",
        "incidentos_search_logs",
        "incidentos_get_log",
        "incidentos_list_deployments",
        "incidentos_get_git_history",
        "incidentos_get_git_diff",
        "incidentos_run_approved_tests",
    }
    actual_tool_names = {t.name for t in tools}
    assert actual_tool_names == expected_tool_names

    for tool in tools:
        assert tool.description and len(tool.description.strip()) > 10
        assert tool.parameters is not None
        assert "properties" in tool.parameters


@pytest.mark.asyncio
async def test_incidentos_health_tool(mock_backend_client):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/health"
        return httpx.Response(200, json={"status": "healthy", "service": "incidentos-backend"})

    mock_backend_client._client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="http://testserver"
    )
    server = create_server(client=mock_backend_client)

    result = await server.call_tool("incidentos_health", {})
    assert len(result) == 1
    content = json.loads(result[0].text)
    assert content["status"] == "healthy"
    assert content["service"] == "incidentos-backend"


@pytest.mark.asyncio
async def test_incidentos_search_logs_tool(mock_backend_client):
    captured_params = {}

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/tools/logs/search"
        captured_params.update(dict(request.url.params))
        return httpx.Response(200, json={"total_matches": 1, "returned_count": 1, "records": []})

    mock_backend_client._client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="http://testserver"
    )
    server = create_server(client=mock_backend_client)

    call_args = {
        "service": "checkout-service",
        "severity": "ERROR",
        "keyword": "NullPointerException",
        "limit": 25,
        "incident_id": "INC-101",
    }
    result = await server.call_tool("incidentos_search_logs", call_args)
    content = json.loads(result[0].text)
    assert content["total_matches"] == 1
    assert captured_params["service"] == "checkout-service"
    assert captured_params["severity"] == "ERROR"
    assert captured_params["keyword"] == "NullPointerException"
    assert captured_params["limit"] == "25"
    assert captured_params["incident_id"] == "INC-101"


@pytest.mark.asyncio
async def test_incidentos_get_log_tool(mock_backend_client):
    def handler(request: httpx.Request) -> httpx.Response:
        if "err-001" in request.url.path:
            return httpx.Response(200, json={"log_id": "err-001", "level": "ERROR", "message": "Failed"})
        return httpx.Response(404, json={"detail": "Log entry 'unknown' not found."})

    mock_backend_client._client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="http://testserver"
    )
    server = create_server(client=mock_backend_client)

    # Found
    res1 = await server.call_tool("incidentos_get_log", {"log_id": "err-001"})
    data1 = json.loads(res1[0].text)
    assert data1["log_id"] == "err-001"

    # Not found
    res2 = await server.call_tool("incidentos_get_log", {"log_id": "unknown"})
    data2 = json.loads(res2[0].text)
    assert data2["status_code"] == 404
    assert "not found" in data2["error"].lower()


@pytest.mark.asyncio
async def test_incidentos_list_deployments_tool(mock_backend_client):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/tools/deployments"
        return httpx.Response(200, json={"total_deployments": 2, "deployments": []})

    mock_backend_client._client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="http://testserver"
    )
    server = create_server(client=mock_backend_client)

    res = await server.call_tool("incidentos_list_deployments", {"service": "checkout-service"})
    data = json.loads(res[0].text)
    assert data["total_deployments"] == 2


@pytest.mark.asyncio
async def test_incidentos_get_git_history_tool(mock_backend_client):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/tools/git/history"
        return httpx.Response(200, json={"repo_path": "/workspace", "commits": []})

    mock_backend_client._client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="http://testserver"
    )
    server = create_server(client=mock_backend_client)

    res = await server.call_tool("incidentos_get_git_history", {"count": 5, "path": "src/Main.java"})
    data = json.loads(res[0].text)
    assert "commits" in data


@pytest.mark.asyncio
async def test_incidentos_get_git_diff_tool(mock_backend_client):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/tools/git/diff"
        return httpx.Response(200, json={"repo_path": "/workspace", "diff_content": "diff --git a/file b/file"})

    mock_backend_client._client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="http://testserver"
    )
    server = create_server(client=mock_backend_client)

    res = await server.call_tool("incidentos_get_git_diff", {"target_commit": "6014328"})
    data = json.loads(res[0].text)
    assert "diff_content" in data


@pytest.mark.asyncio
async def test_incidentos_run_approved_tests_accepts_approved_suites(mock_backend_client):
    """Verify that all actual approved test suites in backend/app/tools/test_tools.py are accepted."""
    called_suites = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/tools/tests/run"
        body = json.loads(request.content)
        called_suites.append(body["test_suite"])
        return httpx.Response(200, json={"test_suite": body["test_suite"], "status": "PASSED", "exit_code": 0})

    mock_backend_client._client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="http://testserver"
    )
    server = create_server(client=mock_backend_client)

    for suite in APPROVED_TEST_SUITES:
        res = await server.call_tool("incidentos_run_approved_tests", {"test_suite": suite})
        data = json.loads(res[0].text)
        assert data["status"] == "PASSED"
        assert data["test_suite"] == suite

    assert called_suites == APPROVED_TEST_SUITES


@pytest.mark.asyncio
async def test_incidentos_run_approved_tests_rejects_unapproved_suites(mock_backend_client):
    """Verify that arbitrary or unapproved test suites are rejected immediately."""
    server = create_server(client=mock_backend_client)

    unapproved = "rm -rf /; malicious-command"
    res = await server.call_tool("incidentos_run_approved_tests", {"test_suite": unapproved})
    data = json.loads(res[0].text)

    assert data["status"] == "ERROR"
    assert data["status_code"] == 400
    assert "not permitted" in data["error"]


@pytest.mark.asyncio
async def test_incidentos_run_approved_tests_rejects_mock_timeout_test(mock_backend_client):
    """Verify that mock-timeout-test is rejected by the MCP tool as an unapproved agent suite."""
    server = create_server(client=mock_backend_client)

    res = await server.call_tool("incidentos_run_approved_tests", {"test_suite": "mock-timeout-test"})
    data = json.loads(res[0].text)

    assert data["status"] == "ERROR"
    assert data["status_code"] == 400
    assert "not permitted" in data["error"]
    assert "mock-timeout-test" not in APPROVED_TEST_SUITES


@pytest.mark.asyncio
async def test_backend_errors_sanitized(mock_backend_client):
    """Verify that 4xx and 5xx errors from the backend return structured errors without leaking tracebacks."""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error_code": "INTERNAL_SERVER_ERROR", "message": "An unexpected error occurred."})

    mock_backend_client._client = httpx.AsyncClient(
        transport=httpx.MockTransport(handler), base_url="http://testserver"
    )
    server = create_server(client=mock_backend_client)

    res = await server.call_tool("incidentos_health", {})
    data = json.loads(res[0].text)
    assert data["status_code"] == 500
    assert "error" in data
