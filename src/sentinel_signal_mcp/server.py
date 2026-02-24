from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from . import client


mcp = FastMCP("Sentinel Signal MCP")


@mcp.tool()
async def score_workflow(
    workflow: str,
    payload: dict[str, Any],
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Call Sentinel Signal unified workflow scoring (POST /v1/score)."""
    result = await client.score_workflow(workflow=workflow, payload=payload, options=options)
    if not isinstance(result, dict):
        return {"result": result}
    return result


@mcp.tool()
async def get_limits() -> dict[str, Any]:
    """Return plan limits for the current API key (GET /v1/limits)."""
    result = await client.get_limits()
    if not isinstance(result, dict):
        return {"result": result}
    return result


@mcp.tool()
async def get_usage(month: str | None = None) -> dict[str, Any]:
    """Return usage for the current API key (GET /v1/usage). Optional month format: YYYY-MM."""
    result = await client.get_usage(month=month)
    if not isinstance(result, dict):
        return {"result": result}
    return result


@mcp.tool()
async def submit_feedback(feedback: dict[str, Any]) -> dict[str, Any]:
    """Submit structured feedback for a prior scoring request (POST /v1/feedback)."""
    result = await client.submit_feedback(feedback=feedback)
    if not isinstance(result, dict):
        return {"result": result}
    return result


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()

