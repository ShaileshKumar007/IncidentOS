import os
import sys
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv

# Base paths: resolve explicitly relative to this file's location
PACKAGE_DIR = Path(__file__).resolve().parent
MCP_SERVER_ROOT = PACKAGE_DIR.parent
PROJECT_ROOT = MCP_SERVER_ROOT.parent
BACKEND_DIR = PROJECT_ROOT / "backend"

# Candidate paths for explicit .env resolution
ENV_FILE_CANDIDATES: List[Path] = [
    PROJECT_ROOT / ".env",
    BACKEND_DIR / ".env",
]


def resolve_env_file() -> Optional[Path]:
    """Finds the first existing .env file among explicit candidate paths."""
    for path in ENV_FILE_CANDIDATES:
        if path.is_file():
            return path
    return None


def load_environment() -> Optional[Path]:
    """Explicitly loads configuration from known candidate paths if present."""
    env_path = resolve_env_file()
    if env_path:
        load_dotenv(dotenv_path=env_path)
    return env_path


class Settings:
    """Configuration settings for IncidentOS FastMCP server."""

    def __init__(
        self,
        backend_url: Optional[str] = None,
        token: Optional[str] = None,
        auto_load_env: bool = True,
    ):
        if auto_load_env:
            self.loaded_env_path = load_environment()
        else:
            self.loaded_env_path = None

        self.backend_url: str = (
            backend_url or os.environ.get("BACKEND_URL", "http://127.0.0.1:8000")
        ).rstrip("/")
        self.token: Optional[str] = token or os.environ.get("INCIDENTOS_API_TOKEN")

    def validate(self) -> None:
        """
        Validates configuration and fails closed if INCIDENTOS_API_TOKEN is missing.
        Emits diagnostic only to sys.stderr to protect stdout protocol integrity.
        """
        if not self.token or not self.token.strip():
            sys.stderr.write(
                "[FATAL] INCIDENTOS_API_TOKEN is not configured in environment or .env file.\n"
                "[FATAL] The MCP server requires a valid token to authenticate with the backend.\n"
                "[FATAL] Failing closed.\n"
            )
            sys.stderr.flush()
            raise RuntimeError(
                "INCIDENTOS_API_TOKEN is not configured. MCP server failing closed."
            )
