import os
import re
import signal
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.config import DEMO_WORKSPACE_ROOT, TOOL_EXECUTION_TIMEOUT_SECONDS
from app.logging_config import sanitize_paths
from app.schemas.common import ToolExecutionResult
from app.schemas.tools import TestRunRequest, TestRunResponse
from app.tools.workspace import InvalidInputError

# Explicit Predefined Test Command Allowlist
# Agents may only specify an approved suite name. Arbitrary commands are strictly rejected.
# Java test execution uses the programmatic DirectTestRunner with JUnit Platform Launcher.
ALLOWED_TEST_SUITES: Dict[str, Dict[str, Any]] = {
    "checkout-service-unit-tests": {
        "description": "Standard checkout service unit tests (excludes known regression)",
        "expected_tests_run": 12,
    },
    "checkout-service-regression-test": {
        "description": "Guest checkout regression reproduction test (demonstrates failure on flawed code)",
        "expected_tests_run": 1,
    },
    "payment-validator-tests": {
        "description": "PaymentValidator unit test suite",
        "expected_tests_run": 3,
    },
    "mock-timeout-test": {
        "command": ["python3", "-c", "import time; time.sleep(10)"],
        "description": "Mock long-running test to verify timeout enforcement",
        "expected_tests_run": 1,
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


_CACHED_JARS: Optional[List[str]] = None
_BYTE_BUDDY_AGENT_JAR: Optional[str] = None

EXCLUDED_PLUGIN_GROUPS = {"io.spring.gradle"}
EXCLUDED_PLUGIN_ARTIFACTS = {
    "spring-boot-gradle-plugin",
    "spring-boot-buildpack-platform",
    "spring-boot-loader-tools",
    "tomlj",
    "commons-compress",
    "httpclient5",
    "httpclient5-h2",
    "httpcore5",
    "httpcore5-h2",
    "jna",
    "jna-platform",
    "antlr4-runtime",
}


def _resolve_cached_dependencies() -> Tuple[List[str], Optional[str]]:
    """
    Scans ~/.gradle/caches/modules-2/files-2.1 and returns:
    1. A deduplicated list of dependency jars with conflicting versions disambiguated to latest.
    2. Path to the byte-buddy-agent jar if present (required for Mockito inline mock maker on Java 21).
    """
    cache_dir = Path(os.path.expanduser("~/.gradle/caches/modules-2/files-2.1"))
    if not cache_dir.exists():
        return [], None

    artifacts: Dict[Tuple[str, str], Dict[str, str]] = {}
    byte_buddy_agent: Optional[str] = None

    for root, _, files in os.walk(cache_dir):
        for f in files:
            if f.endswith(".jar") and not f.endswith("-sources.jar") and not f.endswith("-javadoc.jar"):
                p = Path(root) / f
                try:
                    rel_parts = p.relative_to(cache_dir).parts
                except ValueError:
                    continue
                if len(rel_parts) >= 3:
                    grp, art, ver = rel_parts[0], rel_parts[1], rel_parts[2]
                    if grp in EXCLUDED_PLUGIN_GROUPS or art in EXCLUDED_PLUGIN_ARTIFACTS:
                        continue
                    key = (grp, art)
                    if key not in artifacts:
                        artifacts[key] = {}
                    artifacts[key][ver] = str(p)
                    if art == "byte-buddy-agent":
                        byte_buddy_agent = str(p)

    selected: List[str] = []
    for key, ver_map in sorted(artifacts.items()):
        # Sort versions numerically where possible (e.g. 2.0.13 > 1.7.36)
        sorted_vers = sorted(
            ver_map.keys(),
            key=lambda v: [int(x) if x.isdigit() else x for x in v.replace(".Final", "").split(".")],
        )
        best_ver = sorted_vers[-1]
        selected.append(ver_map[best_ver])

    return selected, byte_buddy_agent


def get_cached_jars() -> List[str]:
    """Finds and resolves all pre-cached dependency jars in ~/.gradle/caches/modules-2/files-2.1."""
    global _CACHED_JARS, _BYTE_BUDDY_AGENT_JAR
    if _CACHED_JARS is not None:
        return _CACHED_JARS

    jars, agent = _resolve_cached_dependencies()
    _CACHED_JARS = jars
    _BYTE_BUDDY_AGENT_JAR = agent
    return _CACHED_JARS


def get_byte_buddy_agent_jar() -> Optional[str]:
    """Returns the path to the byte-buddy-agent jar if available."""
    global _BYTE_BUDDY_AGENT_JAR
    if _CACHED_JARS is None:
        get_cached_jars()
    return _BYTE_BUDDY_AGENT_JAR


def build_test_classpath(demo_root: Path) -> str:
    """
    Constructs the deterministic offline classpath for the direct JUnit Platform runner.
    Includes compiled test classes, compiled main classes, resources, and cached dependencies.
    """
    elements = [
        str((demo_root / "build/classes/java/test").resolve()),
        str((demo_root / "build/classes/java/main").resolve()),
        str((demo_root / "src/main/resources").resolve()),
    ]
    elements.extend(get_cached_jars())
    return ":".join(elements)


def ensure_direct_runner_compiled(demo_root: Path) -> None:
    """
    Ensures DirectTestRunner.class is compiled and available in build/classes/java/test.
    If missing or older than the source file, compiles it using javac without Gradle.
    """
    test_classes = (demo_root / "build/classes/java/test").resolve()
    runner_class = test_classes / "com/example/checkout/runner/DirectTestRunner.class"
    runner_src = (demo_root / "src/test/java/com/example/checkout/runner/DirectTestRunner.java").resolve()

    if runner_class.exists() and (not runner_src.exists() or runner_class.stat().st_mtime >= runner_src.stat().st_mtime):
        return

    if not runner_src.exists():
        return

    test_classes.mkdir(parents=True, exist_ok=True)
    cp = build_test_classpath(demo_root)
    javac_bin = "/opt/homebrew/opt/openjdk@21/bin/javac"
    if not os.path.exists(javac_bin):
        javac_bin = "javac"

    subprocess.run(
        [javac_bin, "-cp", cp, "-d", str(test_classes), str(runner_src)],
        check=True,
        capture_output=True,
        text=True,
    )


def parse_junit_runner_output(
    raw_output: str,
    exit_code: int,
    execution_status: str,
) -> Tuple[str, int, int, int, int, Optional[int], int, Optional[str]]:
    """
    Parses JUnit Platform runner output and strictly classifies execution outcome.

    Returns:
        (status, tests_run, tests_passed, tests_failed, tests_skipped, tests_found, tests_aborted, error_msg)

    Classification rules:
    - TIMEOUT: Process execution timed out. All counts are strictly 0.
    - ERROR: Infrastructure, startup, classloading, compilation, or 0 tests discovered. All counts 0.
    - PASSED: Tests demonstrably executed (tests_found > 0), tests_failed == 0, and exit_code == 0.
    - FAILED: Tests demonstrably executed (tests_found > 0) and tests_failed > 0.
    """
    if execution_status == "TIMEOUT":
        return ("TIMEOUT", 0, 0, 0, 0, 0, 0, "Test execution timed out.")

    if execution_status == "ERROR":
        sanitized_diag = sanitize_paths(raw_output.strip()[-500:]) if raw_output else "Process execution failed"
        return ("ERROR", 0, 0, 0, 0, 0, 0, sanitized_diag)

    # 1. Parse structured JUnit counts if present
    found_match = re.search(r"tests_found:\s*(\d+)", raw_output)
    succeeded_match = re.search(r"tests_succeeded:\s*(\d+)", raw_output)
    failed_match = re.search(r"tests_failed:\s*(\d+)", raw_output)
    skipped_match = re.search(r"tests_skipped:\s*(\d+)", raw_output)
    aborted_match = re.search(r"tests_aborted:\s*(\d+)", raw_output)

    # 2. Also match fallback completed line (e.g. "12 tests completed, 0 failed")
    completed_match = re.search(
        r"(\d+)\s+tests?\s+completed(?P<details>[^\n\r]*)",
        raw_output,
        re.IGNORECASE,
    )

    if not found_match and not completed_match:
        sanitized_diag = sanitize_paths(raw_output.strip()[-500:]) if raw_output else "No output produced"
        if exit_code != 0:
            error_msg = f"Runner or test execution failure (exit code {exit_code}): {sanitized_diag}"
        else:
            error_msg = f"Ambiguous test execution: process exited 0 but no test summary was found: {sanitized_diag}"
        return ("ERROR", 0, 0, 0, 0, 0, 0, error_msg)

    if found_match:
        tests_found = int(found_match.group(1))
        tests_passed = int(succeeded_match.group(1)) if succeeded_match else 0
        tests_failed = int(failed_match.group(1)) if failed_match else 0
        tests_skipped = int(skipped_match.group(1)) if skipped_match else 0
        tests_aborted = int(aborted_match.group(1)) if aborted_match else 0
        tests_run = tests_passed + tests_failed
    else:
        tests_run = int(completed_match.group(1))
        details = completed_match.group("details") or ""
        f_m = re.search(r"(\d+)\s+failed", details, re.IGNORECASE)
        s_m = re.search(r"(\d+)\s+skipped", details, re.IGNORECASE)
        tests_failed = int(f_m.group(1)) if f_m else 0
        tests_skipped = int(s_m.group(1)) if s_m else 0
        tests_aborted = 0
        tests_passed = max(0, tests_run - tests_failed - tests_skipped)
        tests_found = tests_run + tests_skipped

    # Rule: An empty test discovery must be ERROR, not PASSED
    if tests_found == 0 or tests_run == 0:
        sanitized_diag = sanitize_paths(raw_output.strip()[-500:]) if raw_output else "Zero tests discovered"
        return ("ERROR", 0, 0, 0, 0, 0, 0, f"No tests were executed (tests_found={tests_found}, tests_run={tests_run}): {sanitized_diag}")

    # Case A: Execution completed and all discovered tests succeeded (exit_code == 0)
    if tests_failed == 0 and exit_code == 0:
        return ("PASSED", tests_run, tests_passed, tests_failed, tests_skipped, tests_found, tests_aborted, None)

    # Case B: Tests actually executed and at least one test assertion failed (tests_failed > 0)
    if tests_failed > 0:
        return ("FAILED", tests_run, tests_passed, tests_failed, tests_skipped, tests_found, tests_aborted, None)

    # Case C / D: exit_code != 0 but tests_failed == 0 -> runner/JVM error during or after run
    sanitized_diag = sanitize_paths(raw_output.strip()[-500:]) if raw_output else "Process exited non-zero"
    return ("ERROR", 0, 0, 0, 0, 0, 0, f"Runner execution failure (exit code {exit_code}): {sanitized_diag}")


def parse_gradle_test_output(
    raw_output: str,
    exit_code: int,
    execution_status: str,
) -> Tuple[str, int, int, int, int, Optional[str]]:
    """Backward compatibility wrapper for parse_junit_runner_output."""
    status, run, passed, failed, skipped, _, _, err = parse_junit_runner_output(
        raw_output, exit_code, execution_status
    )
    return (status, run, passed, failed, skipped, err)


def run_tests(
    request: TestRunRequest,
    demo_root: Optional[Path] = None,
    timeout_override: Optional[int] = None,
) -> TestRunResponse:
    start_tick = time.perf_counter()
    root = (demo_root or DEMO_WORKSPACE_ROOT).resolve()

    if not root.exists() or not root.is_dir():
        raise InvalidInputError(f"Workspace directory '{root.name}' does not exist or is invalid.")

    suite_name = request.test_suite.strip()
    if suite_name not in ALLOWED_TEST_SUITES:
        allowed_list = list(ALLOWED_TEST_SUITES.keys())
        raise InvalidInputError(
            f"Test suite '{suite_name}' is not permitted. Allowed test suites: {allowed_list}"
        )

    suite_config = ALLOWED_TEST_SUITES[suite_name]
    timeout_seconds = timeout_override or TOOL_EXECUTION_TIMEOUT_SECONDS
    safe_env = get_safe_subprocess_env()

    if suite_name == "mock-timeout-test":
        command = suite_config.get("command", ["python3", "-c", "import time; time.sleep(10)"])
    elif "command" in suite_config:
        command = suite_config["command"]
    else:
        java_bin = "/opt/homebrew/opt/openjdk@21/bin/java"
        if not os.path.exists(java_bin):
            java_bin = "java"
        ensure_direct_runner_compiled(root)
        cp = build_test_classpath(root)
        agent_jar = get_byte_buddy_agent_jar()
        command = [java_bin]
        if agent_jar and os.path.exists(agent_jar):
            command.extend(["-XX:+EnableDynamicAgentLoading", f"-javaagent:{agent_jar}"])
        command.extend([
            "-cp",
            cp,
            "com.example.checkout.runner.DirectTestRunner",
            suite_name,
        ])

    raw_status = "ERROR"
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
        raw_status = "COMPLETED"
    except subprocess.TimeoutExpired:
        if proc:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
            try:
                proc.communicate(timeout=2)
            except Exception:
                pass
        raw_status = "TIMEOUT"
        exit_code = 124
        raw_output = f"[ERROR] Execution timed out after {timeout_seconds} seconds."
        error_msg = f"Test execution timed out after {timeout_seconds}s."
    except Exception as e:
        if proc:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
            try:
                proc.kill()
            except Exception:
                pass
        sanitized_err = sanitize_paths(str(e))
        raw_status = "ERROR"
        exit_code = -1
        raw_output = f"[ERROR] Failed to execute test: {sanitized_err}"
        error_msg = sanitized_err

    duration_sec = time.perf_counter() - start_tick

    # Parse and classify execution results strictly from verified output
    status, tests_run, tests_passed, tests_failed, tests_skipped, tests_found, tests_aborted, parse_error = (
        parse_junit_runner_output(raw_output, exit_code, raw_status)
    )
    if parse_error and not error_msg:
        error_msg = parse_error

    summary = f"Test suite '{suite_name}' finished with status {status} (exit code {exit_code}) in {duration_sec:.2f}s."
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
        tests_skipped=tests_skipped,
        tests_found=tests_found,
        tests_aborted=tests_aborted,
        output=raw_output,
        audit=audit,
    )
