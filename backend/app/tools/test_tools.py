import os
import re
import signal
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, Optional

from app.config import DEMO_WORKSPACE_ROOT, TOOL_EXECUTION_TIMEOUT_SECONDS
from app.schemas.common import ToolExecutionResult
from app.schemas.tools import TestRunRequest, TestRunResponse
from app.tools.workspace import InvalidInputError

# Explicit Predefined Test Command Allowlist
# Agents may only specify an approved suite name. Arbitrary commands are strictly rejected.
ALLOWED_TEST_SUITES: Dict[str, Dict[str, Any]] = {
    "checkout-service-unit-tests": {
        "command": [
            "./gradlew", "unitTest", "--offline", "--console=plain",
        ],
        "description": "Standard checkout service unit tests (excludes known regression)",
        "default_tests_run": 12,
        "default_passed": 12,
        "default_failed": 0,
    },
    "checkout-service-regression-test": {
        "command": [
            "./gradlew", "regressionTest", "--offline", "--console=plain",
        ],
        "description": "Guest checkout regression reproduction test (demonstrates failure on flawed code)",
        "default_tests_run": 1,
        "default_passed": 0,
        "default_failed": 1,
    },
    "payment-validator-tests": {
        "command": [
            "./gradlew", "test", "--tests", "com.example.checkout.service.PaymentValidatorTest", "--offline", "--console=plain",
        ],
        "description": "PaymentValidator unit test suite",
        "default_tests_run": 3,
        "default_passed": 3,
        "default_failed": 0,
    },
    "mock-timeout-test": {
        "command": ["python3", "-c", "import time; time.sleep(10)"],
        "description": "Mock long-running test to verify timeout enforcement",
        "default_tests_run": 1,
        "default_passed": 0,
        "default_failed": 1,
    },
}

MAX_TEST_OUTPUT_BYTES = 50_000  # 50 KB limit for test output logs


def get_safe_subprocess_env() -> Dict[str, str]:
    """
    Constructs an isolated, minimal environment for test subprocesses.
    Prevents the accidental leakage or inheritance of sensitive host environment
    variables, tokens, API keys, or cloud credentials.
    """
    return {
        "PATH": "/opt/homebrew/opt/openjdk@21/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin",
        "JAVA_HOME": "/opt/homebrew/opt/openjdk@21",
        "GRADLE_USER_HOME": os.path.expanduser("~/.gradle"),
        "HOME": os.path.expanduser("~"),
        "TMPDIR": "/tmp",
        "LANG": "en_US.UTF-8",
        "LC_ALL": "en_US.UTF-8",
        "PYTHONUNBUFFERED": "1",
    }


def run_tests(
    request: TestRunRequest,
    demo_root: Optional[Path] = None,
    timeout_override: Optional[int] = None,
) -> TestRunResponse:
    start_tick = time.perf_counter()
    root = (demo_root or DEMO_WORKSPACE_ROOT).resolve()

    suite_name = request.test_suite.strip()
    if suite_name not in ALLOWED_TEST_SUITES:
        allowed_list = list(ALLOWED_TEST_SUITES.keys())
        raise InvalidInputError(
            f"Test suite '{suite_name}' is not permitted. Allowed test suites: {allowed_list}"
        )

    suite_config = ALLOWED_TEST_SUITES[suite_name]
    command = suite_config["command"]
    timeout_seconds = timeout_override or TOOL_EXECUTION_TIMEOUT_SECONDS
    safe_env = get_safe_subprocess_env()

    status = "ERROR"
    exit_code = -1
    raw_output = ""
    error_msg = None

    proc = None
    try:
        # Spawn in a new process group so timeouts terminate child processes completely
        proc = subprocess.Popen(
            command,
            cwd=str(root),
            env=safe_env,
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            start_new_session=True,
        )
        stdout_data, _ = proc.communicate(timeout=timeout_seconds)
        exit_code = proc.returncode
        raw_output = stdout_data[:MAX_TEST_OUTPUT_BYTES] if stdout_data else ""
        status = "PASSED" if exit_code == 0 else "FAILED"
    except subprocess.TimeoutExpired:
        if proc:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
            proc.communicate()
        status = "TIMEOUT"
        exit_code = 124
        raw_output = f"[ERROR] Execution timed out after {timeout_seconds} seconds."
        error_msg = f"Test execution timed out after {timeout_seconds}s."
    except Exception as e:
        if proc:
            try:
                proc.kill()
            except Exception:
                pass
        status = "ERROR"
        exit_code = -1
        raw_output = f"[ERROR] Failed to execute test: {str(e)}"
        error_msg = str(e)

    duration_sec = time.perf_counter() - start_tick

    # Parse test counts dynamically from Gradle test report if present
    tests_run = suite_config.get("default_tests_run", 1)
    tests_failed = 0
    tests_passed = tests_run

    match = re.search(r"(\d+)\s+tests?\s+completed(?:,\s+(\d+)\s+failed)?", raw_output)
    if match:
        tests_run = int(match.group(1))
        tests_failed = int(match.group(2)) if match.group(2) else 0
        tests_passed = max(0, tests_run - tests_failed)
    elif status == "FAILED":
        tests_failed = suite_config.get("default_failed", 1)
        tests_passed = max(0, tests_run - tests_failed)
    elif status == "TIMEOUT" or status == "ERROR":
        tests_passed = 0
        tests_failed = tests_run

    summary = f"Test suite '{suite_name}' completed with status {status} (exit code {exit_code}) in {duration_sec:.2f}s."
    audit = ToolExecutionResult(
        tool_name="tests.run",
        incident_id=request.incident_id,
        agent_id=request.agent_id,
        status="SUCCESS" if status in ("PASSED", "FAILED") else "ERROR",
        duration_ms=round(duration_sec * 1000.0, 2),
        result_summary=summary,
        error=error_msg,
    )

    return TestRunResponse(
        test_suite=suite_name,
        status=status,
        exit_code=exit_code,
        duration_seconds=round(duration_sec, 3),
        tests_run=tests_run,
        tests_passed=tests_passed,
        tests_failed=tests_failed,
        output=raw_output,
        audit=audit,
    )
