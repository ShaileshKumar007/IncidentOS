import os
from pathlib import Path
from typing import List

# Base workspace paths
WORKSPACE_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_DEMO_WORKSPACE = WORKSPACE_DIR / "demo-environment"

DEMO_WORKSPACE_ROOT = Path(os.environ.get("DEMO_WORKSPACE_ROOT", str(DEFAULT_DEMO_WORKSPACE))).resolve()

# Network settings (strictly bind to localhost by default)
BACKEND_HOST = os.environ.get("BACKEND_HOST", "127.0.0.1")
BACKEND_PORT = int(os.environ.get("BACKEND_PORT", "8000"))

# Tool limits
MAX_LOG_RESULTS = int(os.environ.get("MAX_LOG_RESULTS", "100"))
MAX_FILE_READ_BYTES = int(os.environ.get("MAX_FILE_READ_BYTES", "500000"))  # 500 KB limit
TOOL_EXECUTION_TIMEOUT_SECONDS = int(os.environ.get("TOOL_EXECUTION_TIMEOUT_SECONDS", "30"))

# File and Directory Whitelists for Sandboxing
ALLOWED_EXTENSIONS: List[str] = [
    ".log",
    ".jsonl",
    ".json",
    ".java",
    ".xml",
    ".properties",
    ".md",
    ".txt",
    ".yml",
    ".yaml",
]

ALLOWED_DIRECTORIES: List[str] = [
    "logs",
    "deployments",
    "src",
    "docs",
]

BLOCKED_FILES: List[str] = [
    ".env",
    ".env.local",
    ".env.example",
    "id_rsa",
    "id_ed25519",
    "credentials.json",
    "secrets",
    ".git",
]
