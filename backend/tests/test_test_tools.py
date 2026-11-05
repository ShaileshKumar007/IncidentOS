import os
import pytest
from app.schemas.tools import TestRunRequest
from app.tools.test_tools import get_safe_subprocess_env, run_tests
from app.tools.workspace import InvalidInputError


def test_safe_subprocess_env_strips_secrets():
    # Set a sensitive secret in host environment
    os.environ["SECRET_HOST_TOKEN"] = "super-secret-token-12345"
    safe_env = get_safe_subprocess_env()

    assert "SECRET_HOST_TOKEN" not in safe_env
    assert "INCIDENTOS_API_TOKEN" not in safe_env
    assert safe_env["TMPDIR"] == "/tmp"
    assert "GRADLE_USER_HOME" in safe_env
    assert "PATH" in safe_env


def test_run_tests_unit_suite_passed(temp_workspace):
    req = TestRunRequest(test_suite="checkout-service-unit-tests", incident_id="INC-1")
    res = run_tests(request=req, demo_root=temp_workspace)
    assert res.status == "PASSED"
    assert res.exit_code == 0
    assert res.tests_run == 12
    assert res.tests_passed == 12
    assert res.tests_failed == 0
    assert "CheckoutServiceUnitTests" in res.output
    assert res.audit.status == "SUCCESS"


def test_run_tests_regression_suite_failed(temp_workspace):
    req = TestRunRequest(test_suite="checkout-service-regression-test", incident_id="INC-1")
    res = run_tests(request=req, demo_root=temp_workspace)
    assert res.status == "FAILED"
    assert res.exit_code == 1
    assert res.tests_failed == 1
    assert "NullPointerException" in res.output
    assert res.audit.status == "SUCCESS"


def test_run_tests_reject_unapproved_suite(temp_workspace):
    req = TestRunRequest(test_suite="malicious-command; rm -rf /")
    with pytest.raises(InvalidInputError):
        run_tests(request=req, demo_root=temp_workspace)


def test_run_tests_timeout_enforcement(temp_workspace):
    req = TestRunRequest(test_suite="mock-timeout-test")
    res = run_tests(request=req, demo_root=temp_workspace, timeout_override=1)
    assert res.status == "TIMEOUT"
    assert res.exit_code == 124
    assert "timed out" in res.output.lower()
    assert res.audit.status == "ERROR"


def test_api_run_tests_endpoint(client, temp_workspace, monkeypatch):
    import app.tools.test_tools as test_mod
    monkeypatch.setattr(test_mod, "DEMO_WORKSPACE_ROOT", temp_workspace)

    # Valid run
    resp = client.post("/api/tools/tests/run", json={"test_suite": "checkout-service-unit-tests"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "PASSED"
    assert data["exit_code"] == 0

    # Unapproved suite
    resp2 = client.post("/api/tools/tests/run", json={"test_suite": "unapproved-arbitrary-suite"})
    assert resp2.status_code == 400
