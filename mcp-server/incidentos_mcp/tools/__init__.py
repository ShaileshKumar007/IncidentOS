from mcp.server.fastmcp import FastMCP
from incidentos_mcp.client import BackendClient
from incidentos_mcp.tools.deployments import register_deployment_tools
from incidentos_mcp.tools.git import register_git_tools
from incidentos_mcp.tools.health import register_health_tools
from incidentos_mcp.tools.logs import register_log_tools
from incidentos_mcp.tools.tests import register_test_tools


def register_all_tools(mcp: FastMCP, client: BackendClient) -> None:
    """Registers all 7 controlled IncidentOS tools onto the FastMCP instance."""
    register_health_tools(mcp, client)
    register_log_tools(mcp, client)
    register_deployment_tools(mcp, client)
    register_git_tools(mcp, client)
    register_test_tools(mcp, client)
