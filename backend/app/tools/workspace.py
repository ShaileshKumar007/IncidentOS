import os
from pathlib import Path
from typing import List, Optional

from app.config import (
    ALLOWED_DIRECTORIES,
    ALLOWED_EXTENSIONS,
    BLOCKED_FILES,
    DEMO_WORKSPACE_ROOT,
    MAX_FILE_READ_BYTES,
)


class WorkspaceSecurityError(Exception):
    """Base exception for workspace security violations."""
    pass


class PathTraversalError(WorkspaceSecurityError):
    """Raised when an attempt to traverse directories is detected."""
    pass


class SymlinkEscapeError(WorkspaceSecurityError):
    """Raised when a symlink points outside the permitted workspace."""
    pass


class RestrictedPathError(WorkspaceSecurityError):
    """Raised when access to a restricted or non-whitelisted path is requested."""
    pass


class FileSizeLimitExceededError(WorkspaceSecurityError):
    """Raised when a file exceeds permitted read thresholds."""
    pass


class InvalidInputError(WorkspaceSecurityError):
    """Raised when invalid path formatting is provided."""
    pass


def resolve_and_validate_path(
    relative_path: str,
    allowed_dirs: Optional[List[str]] = None,
    allow_repo_root: bool = False,
    demo_root: Optional[Path] = None,
    check_exists: bool = True,
) -> Path:
    """
    Validates and resolves a user/agent provided relative path against the sandboxed workspace.
    
    Guarantees:
    1. Rejects null bytes and malformed input.
    2. Rejects absolute paths.
    3. Rejects traversal markers ('..').
    4. Canonicalizes via resolve() and verifies containment within demo_root.
    5. Detects and rejects symlink escapes.
    6. Blocks hidden files (.git, .env, etc.) and explicitly blacklisted files.
    7. Enforces extension whitelists for files.
    8. Enforces max file size limits.
    9. Restricts paths to allowed subdirectories when provided.
    """
    if not isinstance(relative_path, str) or not relative_path.strip():
        raise InvalidInputError("Path must be a non-empty string.")

    if "\0" in relative_path:
        raise InvalidInputError("Null bytes in path are strictly forbidden.")

    # Reject absolute paths
    raw_path = Path(relative_path)
    if raw_path.is_absolute() or relative_path.startswith("/") or relative_path.startswith("\\"):
        raise PathTraversalError("Absolute paths are forbidden. Paths must be relative to the workspace.")

    # Reject directory traversal components
    if ".." in raw_path.parts:
        raise PathTraversalError("Directory traversal components ('..') are strictly forbidden.")

    root = (demo_root or DEMO_WORKSPACE_ROOT).resolve()

    # Pre-check target path before symlink resolution
    target = root / raw_path

    # Canonicalize
    try:
        resolved = target.resolve()
    except Exception as e:
        raise InvalidInputError(f"Failed to resolve path: {str(e)}")

    # Symlink / Traversal escape check
    try:
        resolved.relative_to(root)
    except ValueError:
        raise SymlinkEscapeError(f"Target path escapes workspace root: {relative_path}")

    # Check for forbidden hidden parts or blocked files
    rel_parts = resolved.relative_to(root).parts
    for part in rel_parts:
        if part.startswith(".") and part != ".":
            raise RestrictedPathError(f"Access to hidden file or directory '{part}' is forbidden.")

    if resolved.name in BLOCKED_FILES:
        raise RestrictedPathError(f"Access to sensitive file '{resolved.name}' is strictly forbidden.")

    # Restrict to allowed subdirectories if specified
    if allowed_dirs is not None and len(rel_parts) > 0:
        first_dir = rel_parts[0]
        is_root_file = len(rel_parts) == 1 and (not check_exists or resolved.is_file())
        if not (allow_repo_root and is_root_file) and first_dir not in allowed_dirs:
            raise RestrictedPathError(
                f"Directory '{first_dir}' is not permitted. Allowed: {allowed_dirs}"
            )

    # If the target exists, perform file-level checks
    if check_exists and resolved.exists():
        if resolved.is_file():
            # Check extension
            if ALLOWED_EXTENSIONS and resolved.suffix.lower() not in ALLOWED_EXTENSIONS:
                raise RestrictedPathError(
                    f"File extension '{resolved.suffix}' is not permitted. Allowed: {ALLOWED_EXTENSIONS}"
                )

            # Check size
            file_size = resolved.stat().st_size
            if file_size > MAX_FILE_READ_BYTES:
                raise FileSizeLimitExceededError(
                    f"File size ({file_size} bytes) exceeds maximum limit ({MAX_FILE_READ_BYTES} bytes)."
                )

    return resolved
