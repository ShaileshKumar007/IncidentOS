import logging
import sys
from typing import Optional
from mcp.server.fastmcp import FastMCP

from incidentos_mcp.client import BackendClient
from incidentos_mcp.config import Settings
from incidentos_mcp.tools import register_all_tools


def configure_logging() -> None:
    """
    Directs all logging exclusively to sys.stderr.
    Guarantees that sys.stdout is never polluted, preserving the integrity
    of MCP JSON-RPC protocol messages.
    """
    root_logger = logging.getLogger()
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    stderr_handler = logging.StreamHandler(sys.stderr)
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    stderr_handler.setFormatter(formatter)
    root_logger.addHandler(stderr_handler)
    root_logger.setLevel(logging.INFO)


def create_server(
    settings: Optional[Settings] = None,
    client: Optional[BackendClient] = None,
) -> FastMCP:
    """
    Instantiates and configures the FastMCP server with all seven controlled tools.
    Fails closed if the API token is not configured.
    """
    configure_logging()
    app_settings = settings or Settings()
    # Validate settings and fail closed if token is missing
    app_settings.validate()

    backend_client = client or BackendClient(settings=app_settings)

    mcp = FastMCP(
        name="IncidentOS Tools",
        instructions=(
            "Sandboxed investigation and diagnostic tools for IncidentOS. "
            "Provides controlled access to checkout-service logs, deployment history, "
            "Git commits and diffs, and approved test execution."
        ),
    )

    register_all_tools(mcp=mcp, client=backend_client)
    return mcp


def main() -> None:
    """Entry point for running the FastMCP server over stdio transport."""
    try:
        mcp = create_server()
        sys.stderr.write("[INFO] IncidentOS FastMCP server starting stdio transport...\n")
        sys.stderr.flush()
        mcp.run(transport="stdio")
    except Exception as exc:
        sys.stderr.write(f"[FATAL] Server startup failed: {exc}\n")
        sys.stderr.flush()
        sys.exit(1)


if __name__ == "__main__":
    main()
