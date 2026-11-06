import json
import logging
import uuid
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.logging_config import StructuredJsonFormatter, sanitize_paths
from app.main import app
from tests.conftest import TEST_API_TOKEN


def test_request_id_generated_automatically(unauthenticated_client):
    """When X-Request-ID header is omitted, the backend generates a valid UUID."""
    response = unauthenticated_client.get("/health")
    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    req_id = response.headers["X-Request-ID"]
    # Verify it is a valid UUID
    parsed_uuid = uuid.UUID(req_id)
    assert str(parsed_uuid) == req_id


def test_request_id_propagated_from_caller(unauthenticated_client):
    """When a valid X-Request-ID is supplied, it is propagated in the response header."""
    custom_id = "trace-req-alpha-99"
    response = unauthenticated_client.get("/health", headers={"X-Request-ID": custom_id})
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == custom_id


def test_request_id_sanitized_against_injection(unauthenticated_client):
    """Dangerous characters in X-Request-ID header are stripped to prevent log/header injection."""
    injected_id = "safe-id-123\r\nInjected-Header: evil\x00<bad>"
    response = unauthenticated_client.get("/health", headers={"X-Request-ID": injected_id})
    assert response.status_code == 200
    req_id = response.headers.get("X-Request-ID")
    assert "\r" not in req_id
    assert "\n" not in req_id
    assert "\x00" not in req_id
    assert "<" not in req_id
    assert ">" not in req_id
    assert "safe-id-123" in req_id


def test_structured_json_formatter():
    """Verify that StructuredJsonFormatter outputs valid single-line JSON with standard fields."""
    formatter = StructuredJsonFormatter()
    record = logging.LogRecord(
        name="incidentos.test",
        level=logging.INFO,
        pathname="test.py",
        lineno=10,
        msg="Test event message",
        args=(),
        exc_info=None,
    )
    record.request_id = "req-test-123"
    record.method = "GET"
    record.path = "/health"
    record.status_code = 200
    record.duration_ms = 1.45

    formatted = formatter.format(record)
    data = json.loads(formatted)

    assert data["level"] == "INFO"
    assert data["logger"] == "incidentos.test"
    assert data["message"] == "Test event message"
    assert data["request_id"] == "req-test-123"
    assert data["method"] == "GET"
    assert data["path"] == "/health"
    assert data["status_code"] == 200
    assert data["duration_ms"] == 1.45
    assert "timestamp" in data


def test_no_auth_tokens_or_secrets_logged(caplog, client):
    """Verify that sensitive API tokens and Authorization headers are never logged."""
    with caplog.at_level(logging.INFO, logger="incidentos"):
        # Make authenticated request
        resp = client.get("/api/incidents")
        assert resp.status_code == 200

    # Ensure sensitive credentials are not in captured log records
    for record in caplog.records:
        message = record.getMessage()
        assert TEST_API_TOKEN not in message
        assert "Authorization" not in message
        assert "Bearer" not in message
        assert "X-API-Key" not in message


def test_unhandled_exception_returns_generic_500_without_stacktrace(monkeypatch, client):
    """
    Simulate an unhandled runtime error inside an endpoint.
    Verify:
    1. Returns HTTP 500 with generic ErrorResponse.
    2. Does NOT leak python tracebacks or exception class names in the HTTP response.
    3. Does NOT leak absolute host paths to the client.
    4. Includes X-Request-ID in response header.
    """
    import app.api.incidents as inc_mod

    def broken_list_incidents():
        raise RuntimeError("Unexpected failure: /Users/secret_user/sensitive/db.sqlite locked!")

    monkeypatch.setattr(inc_mod.incident_service, "list_incidents", broken_list_incidents)

    resp = client.get("/api/incidents")
    assert resp.status_code == 500
    data = resp.json()

    assert data["error_code"] == "INTERNAL_SERVER_ERROR"
    assert data["message"] == "An unexpected internal server error occurred."
    assert data["detail"] is None
    assert "X-Request-ID" in resp.headers

    # Response body must not contain stack trace or path
    resp_text = resp.text
    assert "RuntimeError" not in resp_text
    assert "Traceback" not in resp_text
    assert "/Users/" not in resp_text
    assert "secret_user" not in resp_text


def test_sanitize_paths_utility():
    """Verify sanitize_paths removes home directories, workspace paths, and usernames."""
    text_with_user_path = "Error reading /Users/shailesh/Desktop/Projects/IncidentOS/demo-environment/src/Main.java"
    sanitized = sanitize_paths(text_with_user_path)
    assert "/Users/shailesh" not in sanitized
    assert "<demo-workspace>" in sanitized or "<workspace>" in sanitized or "<sanitized-path>" in sanitized

    text_with_home_path = "File located at /home/deployer/project/secret.key"
    sanitized_home = sanitize_paths(text_with_home_path)
    assert "/home/deployer" not in sanitized_home
    assert "<sanitized-path>" in sanitized_home
