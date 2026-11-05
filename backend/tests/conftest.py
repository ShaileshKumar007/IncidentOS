import json
import os
import subprocess
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

# Set test environment variable for API authentication
TEST_API_TOKEN = "test-token-sec-991823"
os.environ["INCIDENTOS_API_TOKEN"] = TEST_API_TOKEN

from app.main import app


@pytest.fixture
def client():
    """Client configured with valid Bearer token for protected endpoints."""
    return TestClient(app, headers={"Authorization": f"Bearer {TEST_API_TOKEN}"})


@pytest.fixture
def unauthenticated_client():
    """Client with no authentication headers."""
    return TestClient(app)


@pytest.fixture
def temp_workspace(tmp_path: Path):
    """
    Creates an isolated temporary demo workspace with realistic synthetic fixtures,
    git commits, symlinks, and restricted files for exhaustive security and tool testing.
    """
    root = tmp_path / "demo-workspace"
    root.mkdir()

    # 1. Logs directory
    logs_dir = root / "logs"
    logs_dir.mkdir()
    app_log = logs_dir / "application.jsonl"
    app_log.write_text(
        json.dumps({
            "timestamp": "2026-11-04T22:00:00Z",
            "level": "INFO",
            "service": "checkout-service",
            "message": "Checkout started",
            "trace_id": "tr-001"
        }) + "\n" +
        json.dumps({
            "timestamp": "2026-11-04T22:05:00Z",
            "level": "ERROR",
            "service": "checkout-service",
            "message": "Validation failed: NullPointerException",
            "trace_id": "tr-002",
            "error_type": "java.lang.NullPointerException",
            "culprit_class": "com.example.checkout.service.PaymentValidator",
            "line_number": 42,
            "stack_trace": "java.lang.NullPointerException: Cannot invoke Customer.getId()"
        }) + "\n"
    )

    err_log = logs_dir / "error-traces.jsonl"
    err_log.write_text(
        json.dumps({
            "log_id": "err-001",
            "timestamp": "2026-11-04T22:05:00Z",
            "level": "ERROR",
            "service": "checkout-service",
            "message": "Payment validation failed",
            "trace_id": "tr-002",
            "stack_trace": "java.lang.NullPointerException at PaymentValidator.java:42"
        }) + "\n"
    )

    # 2. Deployments directory
    dep_dir = root / "deployments"
    dep_dir.mkdir()
    dep_file = dep_dir / "history.json"
    dep_file.write_text(
        json.dumps([
            {
                "deployment_id": "dep-101",
                "service": "checkout-service",
                "version": "1.4.1",
                "environment": "production",
                "deployed_at": "2026-11-03T12:00:00Z",
                "status": "SUCCESS",
                "commit_hash": "3e9b1a2f4c5d",
                "deployer": "ci-bot",
                "release_notes": "Initial release"
            },
            {
                "deployment_id": "dep-102",
                "service": "checkout-service",
                "version": "1.4.2",
                "environment": "production",
                "deployed_at": "2026-11-04T21:45:00Z",
                "status": "SUCCESS",
                "commit_hash": "7f2a1b94c3d2",
                "deployer": "ci-bot",
                "release_notes": "Regression release"
            }
        ])
    )

    # 3. Source directory
    src_dir = root / "src"
    src_dir.mkdir()
    source_file = src_dir / "PaymentValidator.java"
    source_file.write_text(
        "public class PaymentValidator {\n"
        "    public void validate() {\n"
        "        // Line 42 regression\n"
        "        UUID id = customer.getId();\n"
        "    }\n"
        "}\n"
    )

    # 4. Sensitive & Restricted files
    env_file = root / ".env"
    env_file.write_text("SECRET_KEY=supersecret\n")
    id_rsa = root / "id_rsa"
    id_rsa.write_text("PRIVATE KEY DATA\n")

    # 5. Outside target & Symlink pointing outside workspace
    outside_dir = tmp_path / "outside-target"
    outside_dir.mkdir()
    secret_outside = outside_dir / "host_secret.txt"
    secret_outside.write_text("EXFILTRATED DATA\n")

    symlink_escape = root / "logs" / "escape_symlink.jsonl"
    os.symlink(str(secret_outside), str(symlink_escape))

    # 6. Mock gradlew script for isolated backend unit tests
    gradlew_mock = root / "gradlew"
    gradlew_mock.write_text(
        "#!/bin/sh\n"
        "case \"$*\" in\n"
        "  *unitTest*)\n"
        "    echo 'Starting Test Suite: CheckoutServiceUnitTests'\n"
        "    echo '12 tests completed'\n"
        "    exit 0\n"
        "    ;;\n"
        "  *regressionTest*)\n"
        "    echo 'GuestCheckoutRegressionTest > testGuestCheckout_ShouldSucceed FAILED'\n"
        "    echo 'java.lang.NullPointerException: Cannot invoke Customer.getId() because customer is null'\n"
        "    echo '1 test completed, 1 failed'\n"
        "    exit 1\n"
        "    ;;\n"
        "  *PaymentValidatorTest*)\n"
        "    echo 'PaymentValidatorTest PASSED'\n"
        "    echo '3 tests completed'\n"
        "    exit 0\n"
        "    ;;\n"
        "  *)\n"
        "    echo '1 test completed'\n"
        "    exit 0\n"
        "    ;;\n"
        "esac\n"
    )
    gradlew_mock.chmod(0o755)

    # 7. Initialize git repo inside temp_workspace
    subprocess.run(["git", "init"], cwd=str(root), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=str(root), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["git", "config", "user.email", "test@test.local"], cwd=str(root), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["git", "add", "."], cwd=str(root), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["git", "commit", "-m", "Initial test commit"], cwd=str(root), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    return root
