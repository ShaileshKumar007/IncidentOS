from typing import Optional
from mcp.server.fastmcp import FastMCP
from incidentos_mcp.client import BackendClient


def register_deployment_tools(mcp: FastMCP, client: BackendClient) -> None:
    """Registers deployment history retrieval tools."""

    @mcp.tool(
        name="incidentos_list_deployments",
        description="Retrieves historical deployment events for services in the sandboxed demo environment.",
    )
    async def incidentos_list_deployments(
        service: Optional[str] = None,
        version: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        incident_id: Optional[str] = None,
    ) -> dict:
        return await client.list_deployments(
            service=service,
            version=version,
            start_time=start_time,
            end_time=end_time,
            incident_id=incident_id,
        )
