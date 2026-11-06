import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.config import DEMO_WORKSPACE_ROOT, WORKSPACE_DIR


def sanitize_paths(text: str) -> str:
    """
    Sanitizes local absolute filesystem paths from strings, stack traces,
    and error messages to prevent leakage of host architecture, usernames,
    and filesystem layouts to clients or external logs.
    """
    if not text or not isinstance(text, str):
        return str(text) if text is not None else ""

    # Replace specific workspace roots first
    text = text.replace(str(DEMO_WORKSPACE_ROOT), "<demo-workspace>")
    text = text.replace(str(WORKSPACE_DIR), "<workspace>")

    # Replace user home directory
    home_dir = os.path.expanduser("~")
    if home_dir and home_dir != "/":
        text = text.replace(home_dir, "~")

    # Replace any leftover absolute user or system paths
    text = re.sub(
        r"/(?:Users|home|private/[a-z0-9_-]+)/[a-zA-Z0-9_\.\-]+(?:/[a-zA-Z0-9_\.\-]+)*",
        "<sanitized-path>",
        text,
    )

    return text


class StructuredJsonFormatter(logging.Formatter):
    """
    Structured JSON log formatter for IncidentOS backend.
    Produces single-line JSON log events compliant with production telemetry standards.
    Never serializes sensitive authentication headers or credentials.
    """

    def format(self, record: logging.LogRecord) -> str:
        log_obj: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": sanitize_paths(record.getMessage()),
        }

        # Include structured context attributes if set on the record
        for attr in (
            "request_id",
            "method",
            "path",
            "status_code",
            "duration_ms",
            "client_ip",
            "error_type",
            "sanitized_error",
        ):
            val = getattr(record, attr, None)
            if val is not None:
                log_obj[attr] = val

        # Handle exception tracebacks server-side
        if record.exc_info and record.exc_info[0] is not None:
            formatted_tb = self.formatException(record.exc_info)
            log_obj["traceback"] = sanitize_paths(formatted_tb)

        return json.dumps(log_obj)


def setup_logging(log_level: Optional[str] = None) -> logging.Logger:
    """
    Configures structured server-side logging for the application.
    Installs the StructuredJsonFormatter on the root and incidentos loggers.
    """
    level_name = log_level or os.environ.get("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    root_logger = logging.getLogger()
    # Avoid duplicate handlers if setup_logging is called multiple times
    has_json_handler = any(
        isinstance(h, logging.StreamHandler) and isinstance(h.formatter, StructuredJsonFormatter)
        for h in root_logger.handlers
    )
    if not has_json_handler:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(StructuredJsonFormatter())
        root_logger.addHandler(handler)

    root_logger.setLevel(level)

    app_logger = logging.getLogger("incidentos")
    app_logger.setLevel(level)
    return app_logger


logger = logging.getLogger("incidentos")
