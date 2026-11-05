import os
import re
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional

from app.config import DEMO_WORKSPACE_ROOT, TOOL_EXECUTION_TIMEOUT_SECONDS
from app.schemas.common import ToolExecutionResult
from app.schemas.tools import GitCommitRecord, GitDiffResponse, GitHistoryResponse
from app.tools.workspace import InvalidInputError, resolve_and_validate_path

# Strict hexadecimal commit hash validation (4-40 hex chars)
COMMIT_HASH_REGEX = re.compile(r"^[0-9a-fA-F]{4,40}$")

# Strict branch name validation (alphanumeric, underscores, hyphens, slashes)
BRANCH_NAME_REGEX = re.compile(r"^[a-zA-Z0-9_\-\./]+$")


def validate_commit_hash(commit_hash: Optional[str], field_name: str = "commit_hash") -> None:
    if commit_hash and not COMMIT_HASH_REGEX.match(commit_hash):
        raise InvalidInputError(f"Invalid {field_name} format: '{commit_hash}'. Must be 4-40 hex characters.")


def validate_branch_name(branch: Optional[str]) -> None:
    if branch:
        # Prevent flag injection or directory traversal in branch names
        if branch.startswith("-") or ".." in branch or not BRANCH_NAME_REGEX.match(branch):
            raise InvalidInputError(f"Invalid branch name: '{branch}'. Cannot start with '-' or contain '..'.")


def get_safe_git_env() -> Dict[str, str]:
    """
    Constructs a hardened, isolated environment for Git CLI executions.
    Disables interactive prompts, external diff drivers, pagers, and system configs.
    """
    return {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin:/usr/sbin:/sbin"),
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_PAGER": "cat",
        "GIT_EXTERNAL_DIFF": "",
        "HOME": "/tmp",
    }


def get_git_history(
    count: int = 10,
    path: Optional[str] = None,
    branch: Optional[str] = None,
    incident_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    demo_root: Optional[Path] = None,
) -> GitHistoryResponse:
    start_tick = time.perf_counter()
    root = (demo_root or DEMO_WORKSPACE_ROOT).resolve()

    count = min(max(1, count), 50)
    validate_branch_name(branch)

    # Base Git command with hooks explicitly disabled and external diff suppressed
    args = [
        "git",
        "-c", "core.hooksPath=/dev/null",
        "-c", "diff.external=",
        "log",
        f"-n{count}",
        "--pretty=format:%H%x1f%an%x1f%ad%x1f%s",
        "--date=iso-strict",
    ]

    if branch:
        args.append(branch)

    if path:
        validated_file = resolve_and_validate_path(path, demo_root=root, check_exists=False)
        rel_to_root = str(validated_file.relative_to(root))
        args.extend(["--", rel_to_root])

    commits: List[GitCommitRecord] = []
    error_msg = None
    try:
        proc = subprocess.run(
            args,
            cwd=str(root),
            env=get_safe_git_env(),
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=TOOL_EXECUTION_TIMEOUT_SECONDS,
        )
        if proc.returncode == 0 and proc.stdout:
            for line in proc.stdout.strip().split("\n"):
                if not line.strip():
                    continue
                parts = line.split("\x1f")
                if len(parts) >= 4:
                    c_hash, author, date, msg = parts[0], parts[1], parts[2], parts[3]
                    commits.append(
                        GitCommitRecord(
                            commit_hash=c_hash,
                            author=author,
                            date=date,
                            message=msg,
                        )
                    )
        elif proc.returncode != 0:
            error_msg = proc.stderr.strip()
    except subprocess.TimeoutExpired:
        error_msg = f"Git history timed out after {TOOL_EXECUTION_TIMEOUT_SECONDS}s"
    except Exception as e:
        error_msg = f"Failed to execute git: {str(e)}"

    duration_ms = (time.perf_counter() - start_tick) * 1000.0
    status = "SUCCESS" if not error_msg else "ERROR"
    summary = f"Retrieved {len(commits)} commits." if status == "SUCCESS" else f"Git error: {error_msg}"

    audit = ToolExecutionResult(
        tool_name="git.history",
        incident_id=incident_id,
        agent_id=agent_id,
        status=status,
        duration_ms=round(duration_ms, 2),
        result_summary=summary,
        error=error_msg,
    )

    return GitHistoryResponse(
        repo_path=str(root.name),
        commits=commits,
        audit=audit,
    )


def get_git_diff(
    target_commit: Optional[str] = None,
    base_commit: Optional[str] = None,
    path: Optional[str] = None,
    incident_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    demo_root: Optional[Path] = None,
) -> GitDiffResponse:
    start_tick = time.perf_counter()
    root = (demo_root or DEMO_WORKSPACE_ROOT).resolve()

    validate_commit_hash(target_commit, "target_commit")
    validate_commit_hash(base_commit, "base_commit")

    args = [
        "git",
        "-c", "core.hooksPath=/dev/null",
        "diff",
        "--no-ext-diff",
    ]

    if base_commit and target_commit:
        args.append(f"{base_commit}..{target_commit}")
    elif target_commit:
        args.append(f"{target_commit}^!")
    else:
        # Default: diff against HEAD
        args.append("HEAD")

    if path:
        validated_file = resolve_and_validate_path(path, demo_root=root, check_exists=False)
        rel_to_root = str(validated_file.relative_to(root))
        args.extend(["--", rel_to_root])

    diff_content = ""
    error_msg = None
    try:
        proc = subprocess.run(
            args,
            cwd=str(root),
            env=get_safe_git_env(),
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=TOOL_EXECUTION_TIMEOUT_SECONDS,
        )
        if proc.returncode == 0:
            diff_content = proc.stdout
        else:
            error_msg = proc.stderr.strip()
    except subprocess.TimeoutExpired:
        error_msg = f"Git diff timed out after {TOOL_EXECUTION_TIMEOUT_SECONDS}s"
    except Exception as e:
        error_msg = f"Failed to execute git diff: {str(e)}"

    duration_ms = (time.perf_counter() - start_tick) * 1000.0
    status = "SUCCESS" if not error_msg else "ERROR"
    summary = f"Diff generated ({len(diff_content)} chars)." if status == "SUCCESS" else f"Diff error: {error_msg}"

    audit = ToolExecutionResult(
        tool_name="git.diff",
        incident_id=incident_id,
        agent_id=agent_id,
        status=status,
        duration_ms=round(duration_ms, 2),
        result_summary=summary,
        error=error_msg,
    )

    return GitDiffResponse(
        repo_path=str(root.name),
        target_commit=target_commit,
        base_commit=base_commit,
        file_path=path,
        diff_content=diff_content,
        audit=audit,
    )
