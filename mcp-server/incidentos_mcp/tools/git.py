from typing import Optional
from mcp.server.fastmcp import FastMCP
from incidentos_mcp.client import BackendClient


def register_git_tools(mcp: FastMCP, client: BackendClient) -> None:
    """Registers sandboxed Git history and diff inspection tools."""

    @mcp.tool(
        name="incidentos_get_git_history",
        description="Inspects Git commit history for the demo workspace with optional path, branch, and count filters.",
    )
    async def incidentos_get_git_history(
        count: int = 10,
        path: Optional[str] = None,
        branch: Optional[str] = None,
        incident_id: Optional[str] = None,
    ) -> dict:
        return await client.get_git_history(
            count=count,
            path=path,
            branch=branch,
            incident_id=incident_id,
        )

    @mcp.tool(
        name="incidentos_get_git_diff",
        description="Inspects unified Git diffs between commits or working tree in the demo workspace.",
    )
    async def incidentos_get_git_diff(
        target_commit: Optional[str] = None,
        base_commit: Optional[str] = None,
        path: Optional[str] = None,
        incident_id: Optional[str] = None,
    ) -> dict:
        return await client.get_git_diff(
            target_commit=target_commit,
            base_commit=base_commit,
            path=path,
            incident_id=incident_id,
        )
