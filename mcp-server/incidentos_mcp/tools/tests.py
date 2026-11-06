from typing import List, Optional
from mcp.server.fastmcp import FastMCP
from incidentos_mcp.client import BackendClient

# Genuine checkout-service test suites permitted for agent invocation.
# Internal fixtures such as mock-timeout-test remain strictly backend-only.
APPROVED_TEST_SUITES: List[str] = [
    "checkout-service-unit-tests",
    "checkout-service-regression-test",
    "payment-validator-tests",
]


def register_test_tools(mcp: FastMCP, client: BackendClient) -> None:
    """Registers sandboxed test runner tool for pre-approved test suites."""

    @mcp.tool(
        name="incidentos_run_approved_tests",
        description=(
            "Executes a pre-approved test suite in the sandboxed demo environment. "
            "Permitted test_suite values: 'checkout-service-unit-tests', 'checkout-service-regression-test', "
            "'payment-validator-tests'. Arbitrary commands are strictly rejected."
        ),
    )
    async def incidentos_run_approved_tests(
        test_suite: str,
        incident_id: Optional[str] = None,
    ) -> dict:
        suite = test_suite.strip() if test_suite else ""
        if suite not in APPROVED_TEST_SUITES:
            return {
                "error": f"Test suite '{test_suite}' is not permitted. Allowed suites: {APPROVED_TEST_SUITES}",
                "status": "ERROR",
                "status_code": 400,
            }
        return await client.run_tests(test_suite=suite, incident_id=incident_id)
