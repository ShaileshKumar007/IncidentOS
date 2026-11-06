from mcp.server.fastmcp import FastMCP
from incidentos_mcp.client import BackendClient


def register_health_tools(mcp: FastMCP, client: BackendClient) -> None:
    """Registers health check tool."""

    @mcp.tool(
        name="incidentos_health",
        description="Checks the operational health, status, and readiness of the IncidentOS backend service.",
    )
    async def incidentos_health() -> dict:
        return await client.get_health()
