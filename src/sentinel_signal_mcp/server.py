from __future__ import annotations

import argparse
from typing import Any

from mcp.server.fastmcp import FastMCP

from . import client
from .config import load_settings
from .credentials import CredentialResolutionError, remove_cached_credentials


mcp = FastMCP("Sentinel Signal MCP")


def _coerce_success_result(result: Any) -> dict[str, Any]:
    if isinstance(result, dict):
        if "ok" in result:
            return result
        return {"ok": True, **result}
    return {"ok": True, "result": result}


def _tool_error_result(exc: Exception) -> dict[str, Any]:
    if isinstance(exc, client.SentinelAPIError):
        error: dict[str, Any] = {
            "code": exc.code or "api_error",
            "message": str(exc),
        }
        if exc.action:
            error["action"] = exc.action
        if exc.status_code is not None:
            error["status_code"] = exc.status_code
        if exc.retry_after_seconds is not None:
            error["retry_after_seconds"] = exc.retry_after_seconds
        if exc.upgrade_url:
            error["upgrade_url"] = exc.upgrade_url
        return {"ok": False, "error": error}

    if isinstance(exc, CredentialResolutionError):
        return {
            "ok": False,
            "error": {
                "code": "credential_resolution_failed",
                "message": str(exc),
                "action": "configure_credentials",
            },
        }

    return {"ok": False, "error": {"code": "unexpected_error", "message": str(exc)}}


@mcp.tool()
async def score_workflow(
    workflow: str,
    payload: dict[str, Any],
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Call Sentinel Signal unified workflow scoring (POST /v1/score)."""
    try:
        result = await client.score_workflow(workflow=workflow, payload=payload, options=options)
    except Exception as exc:
        return _tool_error_result(exc)
    return _coerce_success_result(result)


@mcp.tool()
async def get_limits() -> dict[str, Any]:
    """Return plan limits for the current API key (GET /v1/limits)."""
    try:
        result = await client.get_limits()
    except Exception as exc:
        return _tool_error_result(exc)
    return _coerce_success_result(result)


@mcp.tool()
async def get_usage(month: str | None = None) -> dict[str, Any]:
    """Return usage for the current API key (GET /v1/usage). Optional month format: YYYY-MM."""
    try:
        result = await client.get_usage(month=month)
    except Exception as exc:
        return _tool_error_result(exc)
    return _coerce_success_result(result)


@mcp.tool()
async def submit_feedback(feedback: dict[str, Any]) -> dict[str, Any]:
    """Submit structured feedback for a prior scoring request (POST /v1/feedback)."""
    try:
        result = await client.submit_feedback(feedback=feedback)
    except Exception as exc:
        return _tool_error_result(exc)
    return _coerce_success_result(result)


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sentinel-signal-mcp")
    parser.add_argument(
        "--reset-credentials",
        action="store_true",
        help="Remove the cached trial credentials file and exit.",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    args = _build_arg_parser().parse_args(argv)
    if args.reset_credentials:
        settings = load_settings()
        removed = remove_cached_credentials(settings.credentials_path)
        if removed:
            print(f"Removed cached credentials: {settings.credentials_path}")
        else:
            print(f"No cached credentials found: {settings.credentials_path}")
        return
    mcp.run()


if __name__ == "__main__":
    main()
