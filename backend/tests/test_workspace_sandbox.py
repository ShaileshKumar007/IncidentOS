import pytest
from app.tools.workspace import (
    FileSizeLimitExceededError,
    InvalidInputError,
    PathTraversalError,
    RestrictedPathError,
    SymlinkEscapeError,
    resolve_and_validate_path,
)


def test_valid_path_resolution(temp_workspace):
    path = resolve_and_validate_path(
        "logs/application.jsonl",
        allowed_dirs=["logs"],
        demo_root=temp_workspace,
    )
    assert path.exists()
    assert path.name == "application.jsonl"


def test_reject_null_bytes(temp_workspace):
    with pytest.raises(InvalidInputError):
        resolve_and_validate_path("logs/app\0lication.jsonl", demo_root=temp_workspace)


def test_reject_empty_path(temp_workspace):
    with pytest.raises(InvalidInputError):
        resolve_and_validate_path("   ", demo_root=temp_workspace)


def test_reject_absolute_paths(temp_workspace):
    with pytest.raises(PathTraversalError):
        resolve_and_validate_path("/etc/passwd", demo_root=temp_workspace)

    with pytest.raises(PathTraversalError):
        resolve_and_validate_path(str(temp_workspace / "logs/application.jsonl"), demo_root=temp_workspace)


def test_reject_directory_traversal(temp_workspace):
    with pytest.raises(PathTraversalError):
        resolve_and_validate_path("../../etc/passwd", demo_root=temp_workspace)

    with pytest.raises(PathTraversalError):
        resolve_and_validate_path("logs/../../etc/passwd", demo_root=temp_workspace)

    with pytest.raises(PathTraversalError):
        resolve_and_validate_path("logs/../deployments/../.env", demo_root=temp_workspace)


def test_reject_symlink_escape(temp_workspace):
    # escape_symlink.jsonl points to outside-target/host_secret.txt
    with pytest.raises(SymlinkEscapeError):
        resolve_and_validate_path("logs/escape_symlink.jsonl", demo_root=temp_workspace)


def test_reject_sensitive_files(temp_workspace):
    with pytest.raises(RestrictedPathError):
        resolve_and_validate_path(".env", demo_root=temp_workspace)

    with pytest.raises(RestrictedPathError):
        resolve_and_validate_path("id_rsa", demo_root=temp_workspace)


def test_reject_hidden_directories(temp_workspace):
    with pytest.raises(RestrictedPathError):
        resolve_and_validate_path(".git/HEAD", demo_root=temp_workspace, check_exists=False)


def test_reject_unwhitelisted_extension(temp_workspace):
    bad_file = temp_workspace / "src" / "script.bin"
    bad_file.write_bytes(b"\x00\x01\x02")
    with pytest.raises(RestrictedPathError):
        resolve_and_validate_path("src/script.bin", demo_root=temp_workspace)


def test_reject_unauthorized_directory(temp_workspace):
    # Requesting src file with allowed_dirs=['logs']
    with pytest.raises(RestrictedPathError):
        resolve_and_validate_path("src/PaymentValidator.java", allowed_dirs=["logs"], demo_root=temp_workspace)


def test_reject_oversized_file(temp_workspace, monkeypatch):
    large_file = temp_workspace / "logs" / "large.log"
    # Write 100 bytes but set MAX_FILE_READ_BYTES to 50
    large_file.write_text("A" * 100)
    import app.tools.workspace as ws_module
    monkeypatch.setattr(ws_module, "MAX_FILE_READ_BYTES", 50)

    with pytest.raises(FileSizeLimitExceededError):
        resolve_and_validate_path("logs/large.log", demo_root=temp_workspace)
