import logging
from typing import Any, Dict, Optional
import httpx

from incidentos_mcp.config import Settings

logger = logging.getLogger("incidentos_mcp.client")


class BackendClient:
    """
    Dedicated asynchronous HTTP client for calling the IncidentOS FastAPI backend.

    Security & Operational Guarantees:
    1. Injects Authorization: Bearer <token> internally.
    2. Never exposes tokens in exceptions, logs, or return values.
    3. Enforces explicit connection and total execution timeouts.
    4. Handles connection drops and server errors gracefully with structured responses.
    """

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or Settings()
        self.settings.validate()
        self.backend_url = self.settings.backend_url
        self._token = self.settings.token
        self._client: Optional[httpx.AsyncClient] = None

    async def get_client(self) -> httpx.AsyncClient:
        """Returns or lazily creates an authenticated httpx.AsyncClient."""
        if self._client is None or self._client.is_closed:
            headers = {
                "Authorization": f"Bearer {self._token}",
                "Accept": "application/json",
                "User-Agent": "incidentos-mcp/0.1.0",
            }
            # 5s connect timeout, 35s read timeout (compatible with 30s tool timeout)
            timeout = httpx.Timeout(35.0, connect=5.0)
            self._client = httpx.AsyncClient(
                base_url=self.backend_url,
                headers=headers,
                timeout=timeout,
            )
        return self._client

    async def aclose(self) -> None:
        """Closes the underlying HTTP client session."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Executes HTTP request against the backend and returns a structured dictionary.
        Catches transport errors and returns sanitized, structured error payloads.
        """
        client = await self.get_client()
        filtered_params = {k: v for k, v in (params or {}).items() if v is not None}

        try:
            response = await client.request(
                method=method,
                url=path,
                params=filtered_params or None,
                json=json_data,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.warning(f"Backend HTTP error {e.response.status_code} on {method} {path}")
            try:
                body = e.response.json()
                detail = body.get("detail") or body.get("message") or body
            except Exception:
                detail = e.response.text or "Backend request failed."
            return {
                "error": detail,
                "status_code": e.response.status_code,
            }
        except (httpx.ConnectError, httpx.ConnectTimeout):
            logger.error(f"Failed to connect to IncidentOS backend at {self.backend_url}")
            return {
                "error": f"Failed to connect to IncidentOS backend at {self.backend_url}. Verify backend service is running.",
                "status_code": 503,
            }
        except httpx.TimeoutException:
            logger.error(f"Backend request timed out on {method} {path}")
            return {
                "error": "Backend request timed out.",
                "status_code": 504,
            }
        except Exception:
            logger.error(f"Unexpected error communicating with backend on {method} {path}")
            return {
                "error": "An unexpected communication error occurred.",
                "status_code": 500,
            }

    async def get_health(self) -> Dict[str, Any]:
        """Queries backend public health status."""
        return await self._request("GET", "/health")

    async def search_logs(
        self,
        service: Optional[str] = None,
        severity: Optional[str] = None,
        keyword: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        limit: int = 50,
        incident_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Searches logs via backend GET /api/tools/logs/search."""
        params = {
            "service": service,
            "severity": severity,
            "keyword": keyword,
            "start_time": start_time,
            "end_time": end_time,
            "limit": limit,
            "incident_id": incident_id,
        }
        return await self._request("GET", "/api/tools/logs/search", params=params)

    async def get_log(
        self,
        log_id: str,
        incident_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Retrieves single log by ID via backend GET /api/tools/logs/{log_id}."""
        params = {"incident_id": incident_id}
        return await self._request("GET", f"/api/tools/logs/{log_id}", params=params)

    async def list_deployments(
        self,
        service: Optional[str] = None,
        version: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        incident_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Retrieves deployment history via backend GET /api/tools/deployments."""
        params = {
            "service": service,
            "version": version,
            "start_time": start_time,
            "end_time": end_time,
            "incident_id": incident_id,
        }
        return await self._request("GET", "/api/tools/deployments", params=params)

    async def get_git_history(
        self,
        count: int = 10,
        path: Optional[str] = None,
        branch: Optional[str] = None,
        incident_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Inspects Git history via backend GET /api/tools/git/history."""
        params = {
            "count": count,
            "path": path,
            "branch": branch,
            "incident_id": incident_id,
        }
        return await self._request("GET", "/api/tools/git/history", params=params)

    async def get_git_diff(
        self,
        target_commit: Optional[str] = None,
        base_commit: Optional[str] = None,
        path: Optional[str] = None,
        incident_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Inspects Git diff via backend GET /api/tools/git/diff."""
        params = {
            "target_commit": target_commit,
            "base_commit": base_commit,
            "path": path,
            "incident_id": incident_id,
        }
        return await self._request("GET", "/api/tools/git/diff", params=params)

    async def run_tests(
        self,
        test_suite: str,
        incident_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Executes approved test suite via backend POST /api/tools/tests/run."""
        body = {
            "test_suite": test_suite,
            "incident_id": incident_id,
        }
        return await self._request("POST", "/api/tools/tests/run", json_data=body)
