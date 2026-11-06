import os
import subprocess
import pytest
from app.schemas.tools import TestRunRequest
from app.tools.test_tools import (
    ALLOWED_TEST_SUITES,
    build_test_classpath,
    get_cached_jars,
    get_safe_subprocess_env,
    parse_gradle_test_output,
    parse_junit_runner_output,
    run_tests,
)
from app.tools.workspace import InvalidInputError


@pytest.fixture(autouse=True)
def mock_temp_workspace_java_runner(monkeypatch):
    """
    Mocks subprocess.Popen for tests running against synthetic temp_workspace,
    returning deterministic DirectTestRunner output for approved test suites.
    """
    orig_popen = subprocess.Popen

    class MockDirectProcess:
        def __init__(self, suite: str):
            self.pid = 99881
            if suite == "checkout-service-unit-tests":
                self.returncode = 0
                self.stdout_data = (
                    "Starting IncidentOS Direct Test Runner for suite: checkout-service-unit-tests\n"
                    "  [RUN] testHealthEndpoint()\n"
                    "  [SUCCESSFUL] testHealthEndpoint()\n"
                    "\n--- JUnit Execution Summary ---\n"
                    "tests_found:     12\n"
                    "tests_succeeded: 12\n"
                    "tests_failed:    0\n"
                    "tests_skipped:   0\n"
                    "tests_aborted:   0\n"
                    "12 tests completed, 0 failed, 0 skipped\n"
                )
            elif suite == "checkout-service-regression-test":
                self.returncode = 1
                self.stdout_data = (
                    "Starting IncidentOS Direct Test Runner for suite: checkout-service-regression-test\n"
                    "  [RUN] testGuestCheckout_ShouldSucceed()\n"
                    "  [FAILED] testGuestCheckout_ShouldSucceed()\n"
                    "\n--- JUnit Execution Summary ---\n"
                    "tests_found:     1\n"
                    "tests_succeeded: 0\n"
                    "tests_failed:    1\n"
                    "tests_skipped:   0\n"
                    "tests_aborted:   0\n"
                    "1 test completed, 1 failed, 0 skipped\n"
                    "\nFailures (1):\n"
                    "FAIL: Guest checkout with null customer object should complete successfully -> "
                    "java.lang.NullPointerException: Cannot invoke Customer.getId() because customer is null\n"
                )
            elif suite == "payment-validator-tests":
                self.returncode = 0
                self.stdout_data = (
                    "Starting IncidentOS Direct Test Runner for suite: payment-validator-tests\n"
                    "  [RUN] testValidPaymentWithCustomer_ShouldPass()\n"
                    "  [SUCCESSFUL] testValidPaymentWithCustomer_ShouldPass()\n"
                    "\n--- JUnit Execution Summary ---\n"
                    "tests_found:     3\n"
                    "tests_succeeded: 3\n"
                    "tests_failed:    0\n"
                    "tests_skipped:   0\n"
                    "tests_aborted:   0\n"
                    "3 tests completed, 0 failed, 0 skipped\n"
                )
            else:
                self.returncode = 2
                self.stdout_data = f"[ERROR] Invalid or unapproved test suite: {suite}\n"

        def communicate(self, timeout=None):
            return (self.stdout_data, "")

        def kill(self):
            pass

    def mock_popen(args, *pargs, **kwargs):
        # Intercept Java DirectTestRunner invocations in unit test suites
        if isinstance(args, list) and len(args) >= 3 and "com.example.checkout.runner.DirectTestRunner" in args:
            suite = args[-1]
            return MockDirectProcess(suite)
        return orig_popen(args, *pargs, **kwargs)

    monkeypatch.setattr(subprocess, "Popen", mock_popen)


def test_safe_subprocess_env_strips_secrets():
    # Set a sensitive secret in host environment
    os.environ["SECRET_HOST_TOKEN"] = "super-secret-token-12345"
    safe_env = get_safe_subprocess_env()

    assert "SECRET_HOST_TOKEN" not in safe_env
    assert "INCIDENTOS_API_TOKEN" not in safe_env
    assert safe_env["TMPDIR"] == "/tmp"
    assert "GRADLE_USER_HOME" in safe_env
    assert "PATH" in safe_env


def test_no_gradle_command_execution():
    """Verify Gradle is completely removed from all approved test suite definitions."""
    for suite, config in ALLOWED_TEST_SUITES.items():
        if "command" in config:
            cmd = config["command"]
            for token in cmd:
                assert "gradle" not in token.lower()
                assert "gradlew" not in token.lower()


def test_build_test_classpath_deterministic_and_offline(temp_workspace):
    """Verify build_test_classpath generates deterministic local paths without network URLs."""
    cp = build_test_classpath(temp_workspace)
    assert str(temp_workspace / "build/classes/java/test") in cp
    assert str(temp_workspace / "build/classes/java/main") in cp
    assert str(temp_workspace / "src/main/resources") in cp
    # No HTTP/HTTPS remote repository URLs
    assert "http://" not in cp
    assert "https://" not in cp


def test_run_tests_unit_suite_passed(temp_workspace):
    req = TestRunRequest(test_suite="checkout-service-unit-tests", incident_id="INC-1")
    res = run_tests(request=req, demo_root=temp_workspace)
    assert res.status == "PASSED"
    assert res.exit_code == 0
    assert res.tests_run == 12
    assert res.tests_passed == 12
    assert res.tests_failed == 0
    assert res.tests_found == 12
    assert res.tests_skipped == 0
    assert res.audit.status == "SUCCESS"


def test_run_tests_regression_suite_failed(temp_workspace):
    req = TestRunRequest(test_suite="checkout-service-regression-test", incident_id="INC-1")
    res = run_tests(request=req, demo_root=temp_workspace)
    assert res.status == "FAILED"
    assert res.exit_code == 1
    assert res.tests_run == 1
    assert res.tests_failed == 1
    assert res.tests_passed == 0
    assert res.tests_found == 1
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
    assert data["tests_run"] == 12
    assert data["tests_passed"] == 12

    # Unapproved suite
    resp2 = client.post("/api/tools/tests/run", json={"test_suite": "unapproved-arbitrary-suite"})
    assert resp2.status_code == 400


def test_run_tests_payment_validator_suite(temp_workspace):
    req = TestRunRequest(test_suite="payment-validator-tests", incident_id="INC-1")
    res = run_tests(request=req, demo_root=temp_workspace)
    assert res.status == "PASSED"
    assert res.exit_code == 0
    assert res.tests_run == 3
    assert res.tests_passed == 3
    assert res.tests_failed == 0
    assert res.tests_found == 3
    assert res.audit.status == "SUCCESS"


def test_run_tests_invalid_workspace_root(tmp_path):
    nonexistent = tmp_path / "does-not-exist"
    req = TestRunRequest(test_suite="checkout-service-unit-tests")
    with pytest.raises(InvalidInputError) as exc_info:
        run_tests(request=req, demo_root=nonexistent)
    assert "does not exist or is invalid" in str(exc_info.value)


def test_run_tests_process_group_kills_orphaned_children(temp_workspace, monkeypatch):
    """
    Simulate a script that spawns a background child process and sleeps.
    Verify that timeout enforcement terminates the whole process group, not just the parent.
    """
    import app.tools.test_tools as test_mod

    # Custom suite that spawns a background child process
    mock_suites = dict(test_mod.ALLOWED_TEST_SUITES)
    mock_suites["child-spawner-timeout"] = {
        "command": [
            "python3",
            "-c",
            "import subprocess, time; subprocess.Popen(['sleep', '30']); time.sleep(10)",
        ],
        "description": "Spawns background child then hangs",
        "expected_tests_run": 1,
    }
    monkeypatch.setattr(test_mod, "ALLOWED_TEST_SUITES", mock_suites)

    req = TestRunRequest(test_suite="child-spawner-timeout")
    res = run_tests(request=req, demo_root=temp_workspace, timeout_override=1)
    assert res.status == "TIMEOUT"
    assert res.exit_code == 124
    assert res.audit.status == "ERROR"


def test_parse_gradle_daemon_connection_failure():
    """Case C: Gradle daemon connection failure returns ERROR, zero counts, and diagnostic error."""
    daemon_err = (
        "FAILURE: Build failed with an exception.\n"
        "* What went wrong:\n"
        "Could not connect to the Gradle daemon.\n"
        "Daemon daemon-77876.out.log contains trace."
    )
    status, run, passed, failed, skipped, err = parse_gradle_test_output(
        daemon_err, exit_code=1, execution_status="COMPLETED"
    )
    assert status == "ERROR"
    assert run == 0
    assert passed == 0
    assert failed == 0
    assert skipped == 0
    assert err is not None
    assert "Could not connect to the Gradle daemon" in err
    assert "exit code 1" in err


def test_parse_gradle_compilation_failure():
    """Case C: Compilation failure returns ERROR, zero counts, and diagnostic error."""
    compile_err = (
        "> Task :compileJava FAILED\n"
        "/demo/PaymentValidator.java:42: error: cannot find symbol\n"
        "  UUID customerId = customer.getId();\n"
        "1 error\n"
        "FAILURE: Build failed with an exception."
    )
    status, run, passed, failed, skipped, err = parse_gradle_test_output(
        compile_err, exit_code=1, execution_status="COMPLETED"
    )
    assert status == "ERROR"
    assert run == 0
    assert passed == 0
    assert failed == 0
    assert skipped == 0
    assert err is not None
    assert "exit code 1" in err


def test_parse_test_assertion_failure_with_execution_summary():
    """Case B: Assertion failure with actual execution summary returns FAILED with counts."""
    output = (
        "GuestCheckoutRegressionTest > testGuestCheckout_ShouldSucceed FAILED\n"
        "java.lang.NullPointerException: Cannot invoke Customer.getId()\n"
        "1 test completed, 1 failed\n"
    )
    status, run, passed, failed, skipped, err = parse_gradle_test_output(
        output, exit_code=1, execution_status="COMPLETED"
    )
    assert status == "FAILED"
    assert run == 1
    assert passed == 0
    assert failed == 1
    assert skipped == 0
    assert err is None


def test_parse_successful_unit_test_summary():
    """Case A: Successful unit test summary returns PASSED with counts."""
    output = (
        "Starting Test Suite: CheckoutServiceUnitTests\n"
        "12 tests completed\n"
        "BUILD SUCCESSFUL in 1s\n"
    )
    status, run, passed, failed, skipped, err = parse_gradle_test_output(
        output, exit_code=0, execution_status="COMPLETED"
    )
    assert status == "PASSED"
    assert run == 12
    assert passed == 12
    assert failed == 0
    assert skipped == 0
    assert err is None


def test_parse_successful_payment_validator_test_summary():
    """Case A: Successful PaymentValidator test summary returns PASSED with counts."""
    output = (
        "PaymentValidatorTest PASSED\n"
        "3 tests completed\n"
        "BUILD SUCCESSFUL in 800ms\n"
    )
    status, run, passed, failed, skipped, err = parse_gradle_test_output(
        output, exit_code=0, execution_status="COMPLETED"
    )
    assert status == "PASSED"
    assert run == 3
    assert passed == 3
    assert failed == 0
    assert skipped == 0
    assert err is None


def test_parse_timeout_status():
    """Timeout returns TIMEOUT, zero counts, never PASSED."""
    status, run, passed, failed, skipped, err = parse_gradle_test_output(
        "[ERROR] Execution timed out after 30 seconds.", exit_code=124, execution_status="TIMEOUT"
    )
    assert status == "TIMEOUT"
    assert run == 0
    assert passed == 0
    assert failed == 0
    assert skipped == 0
    assert err == "Test execution timed out."


def test_parse_missing_or_malformed_test_summary():
    """Case D: Missing or malformed test summary returns ERROR and zero counts."""
    output = "BUILD SUCCESSFUL in 2s but no test summary line was printed anywhere\n"
    status, run, passed, failed, skipped, err = parse_gradle_test_output(
        output, exit_code=0, execution_status="COMPLETED"
    )
    assert status == "ERROR"
    assert run == 0
    assert passed == 0
    assert failed == 0
    assert skipped == 0
    assert err is not None
    assert "Ambiguous test execution" in err


def test_parse_nonzero_exit_without_execution_evidence():
    """Case C: Non-zero exit code without execution evidence returns ERROR and zero counts."""
    output = "Unknown command-line option '--illegal-flag'.\n"
    status, run, passed, failed, skipped, err = parse_gradle_test_output(
        output, exit_code=2, execution_status="COMPLETED"
    )
    assert status == "ERROR"
    assert run == 0
    assert passed == 0
    assert failed == 0
    assert skipped == 0
    assert err is not None
    assert "exit code 2" in err


def test_parse_skipped_tests_handling():
    """Tests with skipped assertions correctly calculate passed counts."""
    output = "10 tests completed, 2 failed, 3 skipped\n"
    status, run, passed, failed, skipped, err = parse_gradle_test_output(
        output, exit_code=1, execution_status="COMPLETED"
    )
    assert status == "FAILED"
    assert run == 10
    assert failed == 2
    assert skipped == 3
    assert passed == 5  # 10 - 2 - 3
    assert err is None


def test_run_tests_end_to_end_infrastructure_failure(temp_workspace, monkeypatch):
    """End-to-end run_tests with daemon connection failure produces ERROR and audit ERROR."""
    import app.tools.test_tools as test_mod

    mock_suites = dict(test_mod.ALLOWED_TEST_SUITES)
    mock_suites["mock-daemon-failure"] = {
        "command": [
            "python3",
            "-c",
            "import sys; sys.stderr.write('FAILURE: Could not connect to the Gradle daemon.\\n'); sys.exit(1)",
        ],
        "description": "Simulates daemon connect failure",
        "expected_tests_run": 12,
    }
    monkeypatch.setattr(test_mod, "ALLOWED_TEST_SUITES", mock_suites)

    req = TestRunRequest(test_suite="mock-daemon-failure", incident_id="INC-FAIL")
    res = run_tests(request=req, demo_root=temp_workspace)

    assert res.status == "ERROR"
    assert res.exit_code == 1
    assert res.tests_run == 0
    assert res.tests_passed == 0
    assert res.tests_failed == 0
    assert res.tests_skipped == 0
    assert "Could not connect to the Gradle daemon" in res.output
    # Audit must be marked as ERROR, not SUCCESS
    assert res.audit.status == "ERROR"
    assert res.audit.error is not None
    assert "exit code 1" in res.audit.error


def test_run_tests_end_to_end_compilation_failure(temp_workspace, monkeypatch):
    """End-to-end run_tests with compilation failure produces ERROR and audit ERROR."""
    import app.tools.test_tools as test_mod

    mock_suites = dict(test_mod.ALLOWED_TEST_SUITES)
    mock_suites["mock-compile-failure"] = {
        "command": [
            "python3",
            "-c",
            "import sys; sys.stderr.write('> Task :compileJava FAILED\\nPaymentValidator.java: error\\n'); sys.exit(1)",
        ],
        "description": "Simulates compilation failure",
        "expected_tests_run": 3,
    }
    monkeypatch.setattr(test_mod, "ALLOWED_TEST_SUITES", mock_suites)

    req = TestRunRequest(test_suite="mock-compile-failure", incident_id="INC-FAIL")
    res = run_tests(request=req, demo_root=temp_workspace)

    assert res.status == "ERROR"
    assert res.exit_code == 1
    assert res.tests_run == 0
    assert res.tests_passed == 0
    assert res.tests_failed == 0
    assert res.tests_skipped == 0
    assert res.audit.status == "ERROR"
    assert res.audit.error is not None


def test_parse_junit_runner_structured_output():
    """Verify parse_junit_runner_output parses structured JUnit runner blocks."""
    output = (
        "Starting IncidentOS Direct Test Runner for suite: checkout-service-unit-tests\n"
        "  [RUN] testHealthEndpoint()\n"
        "  [SUCCESSFUL] testHealthEndpoint()\n"
        "\n--- JUnit Execution Summary ---\n"
        "tests_found:     12\n"
        "tests_succeeded: 12\n"
        "tests_failed:    0\n"
        "tests_skipped:   0\n"
        "tests_aborted:   0\n"
        "12 tests completed, 0 failed, 0 skipped\n"
    )
    status, run, passed, failed, skipped, found, aborted, err = parse_junit_runner_output(
        output, exit_code=0, execution_status="COMPLETED"
    )
    assert status == "PASSED"
    assert run == 12
    assert passed == 12
    assert failed == 0
    assert skipped == 0
    assert found == 12
    assert aborted == 0
    assert err is None


def test_zero_discovered_tests_yields_error():
    """Empty test discovery must be ERROR, not PASSED, with zero counts."""
    output = (
        "Starting IncidentOS Direct Test Runner for suite: empty-suite\n"
        "\n--- JUnit Execution Summary ---\n"
        "tests_found:     0\n"
        "tests_succeeded: 0\n"
        "tests_failed:    0\n"
        "tests_skipped:   0\n"
        "tests_aborted:   0\n"
        "0 tests completed, 0 failed, 0 skipped\n"
        "[ERROR] Zero tests discovered for suite: empty-suite\n"
    )
    status, run, passed, failed, skipped, found, aborted, err = parse_junit_runner_output(
        output, exit_code=2, execution_status="COMPLETED"
    )
    assert status == "ERROR"
    assert run == 0
    assert passed == 0
    assert failed == 0
    assert skipped == 0
    assert found == 0
    assert err is not None
    assert "No tests were executed" in err


def test_runner_startup_failure_yields_error():
    """Runner startup failure or unapproved suite returns ERROR and zero counts."""
    output = (
        "[ERROR] Invalid or unapproved test suite: arbitrary-unapproved-suite\n"
        "Allowed test suites: [checkout-service-unit-tests, checkout-service-regression-test, payment-validator-tests]\n"
    )
    status, run, passed, failed, skipped, found, aborted, err = parse_junit_runner_output(
        output, exit_code=2, execution_status="COMPLETED"
    )
    assert status == "ERROR"
    assert run == 0
    assert passed == 0
    assert failed == 0
    assert skipped == 0
    assert err is not None
    assert "exit code 2" in err


def test_parse_junit_runner_aborted_tests():
    """Verify tests aborted (e.g. assumeFalse) are tracked properly."""
    output = (
        "--- JUnit Execution Summary ---\n"
        "tests_found:     5\n"
        "tests_succeeded: 4\n"
        "tests_failed:    0\n"
        "tests_skipped:   0\n"
        "tests_aborted:   1\n"
        "4 tests completed, 0 failed, 0 skipped\n"
    )
    status, run, passed, failed, skipped, found, aborted, err = parse_junit_runner_output(
        output, exit_code=0, execution_status="COMPLETED"
    )
    assert status == "PASSED"
    assert run == 4
    assert passed == 4
    assert failed == 0
    assert aborted == 1
    assert found == 5
