from typing import Optional
from mcp.server.fastmcp import FastMCP
from incidentos_mcp.client import BackendClient


def register_log_tools(mcp: FastMCP, client: BackendClient) -> None:
    """Registers application and error log search and retrieval tools."""

    @mcp.tool(
        name="incidentos_search_logs",
        description="Searches application and error logs in the sandboxed workspace by service, severity, keyword, or ISO-8601 time range.",
    )
    async def incidentos_search_logs(
        service: Optional[str] = None,
        severity: Optional[str] = None,
        keyword: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        limit: int = 50,
        incident_id: Optional[str] = None,
    ) -> dict:
        return await client.search_logs(
            service=service,
            severity=severity,
            keyword=keyword,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            incident_id=incident_id,
        )

    @mcp.tool(
        name="incidentos_get_log",
        description="Retrieves a specific log record and full stack trace by unique log ID or trace ID.",
    )
    async def incidentos_get_log(
        log_id: str,
        incident_id: Optional[str] = None,
    ) -> dict:
        return await client.get_log(log_id=log_id, incident_id=incident_id)
