from __future__ import annotations

from typing import Any

import httpx

from .config import Settings, load_settings


class SentinelAPIError(RuntimeError):
    """Raised when the Sentinel Signal API returns an error."""


def _headers(settings: Settings) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.api_key}",
        "Accept": "application/json",
        "User-Agent": settings.user_agent,
    }


def _parse_response(response: httpx.Response) -> Any:
    content_type = (response.headers.get("content-type") or "").lower()
    if "application/json" in content_type:
        try:
            payload = response.json()
        except ValueError:
            payload = {"raw_text": response.text}
    else:
        payload = {"raw_text": response.text}

    if response.is_error:
        detail = payload if isinstance(payload, dict) else {"detail": payload}
        raise SentinelAPIError(f"Sentinel API error {response.status_code}: {detail}")
    return payload


async def _request(
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
) -> Any:
    settings = load_settings()
    try:
        async with httpx.AsyncClient(
            base_url=settings.api_base_url,
            timeout=settings.timeout_seconds,
            headers=_headers(settings),
        ) as client:
            response = await client.request(method, path, params=params, json=json_body)
    except httpx.HTTPError as exc:
        raise SentinelAPIError(f"HTTP request to Sentinel API failed: {exc}") from exc
    return _parse_response(response)


async def score_workflow(
    *,
    workflow: str,
    payload: dict[str, Any],
    options: dict[str, Any] | None = None,
) -> Any:
    body: dict[str, Any] = {
        "workflow": workflow,
        "payload": payload,
    }
    if options is not None:
        body["options"] = options
    return await _request("POST", "/v1/score", json_body=body)


async def get_limits() -> Any:
    return await _request("GET", "/v1/limits")


async def get_usage(*, month: str | None = None) -> Any:
    params: dict[str, Any] | None = None
    if month:
        params = {"month": month}
    return await _request("GET", "/v1/usage", params=params)


async def submit_feedback(*, feedback: dict[str, Any]) -> Any:
    return await _request("POST", "/v1/feedback", json_body=feedback)

