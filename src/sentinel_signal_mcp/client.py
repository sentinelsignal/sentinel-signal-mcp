from __future__ import annotations

from typing import Any

import httpx

from .config import Settings, load_settings
from .credentials import CredentialResolutionError, ResolvedCredentials, resolve_credentials


class SentinelAPIError(RuntimeError):
    """Raised when the Sentinel Signal API returns an error."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        code: str | None = None,
        action: str | None = None,
        upgrade_url: str | None = None,
        retry_after_seconds: int | None = None,
        payload: Any | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.action = action
        self.upgrade_url = upgrade_url
        self.retry_after_seconds = retry_after_seconds
        self.payload = payload


def _headers(settings: Settings, *, api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "User-Agent": settings.user_agent,
    }


def _parse_json_or_text(response: httpx.Response) -> Any:
    content_type = (response.headers.get("content-type") or "").lower()
    if "application/json" in content_type:
        try:
            return response.json()
        except ValueError:
            return {"raw_text": response.text}
    return {"raw_text": response.text}


def _extract_error_object(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    for key in ("error", "detail"):
        candidate = payload.get(key)
        if isinstance(candidate, dict):
            return candidate
    return payload


def _extract_message(payload: Any, *, status_code: int) -> str:
    error_obj = _extract_error_object(payload)
    for key in ("message", "detail", "error"):
        value = error_obj.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    if isinstance(payload, dict):
        detail = payload.get("detail")
        if isinstance(detail, str) and detail.strip():
            return detail.strip()
    return f"Sentinel API error {status_code}"


def _extract_code(payload: Any) -> str | None:
    error_obj = _extract_error_object(payload)
    value = error_obj.get("code")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _extract_upgrade_url(payload: Any) -> str | None:
    if isinstance(payload, dict):
        for top_key in ("upgrade_url",):
            value = payload.get(top_key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        for nested_key in ("error", "detail"):
            nested = payload.get(nested_key)
            if isinstance(nested, dict):
                value = nested.get("upgrade_url")
                if isinstance(value, str) and value.strip():
                    return value.strip()
    return None


def _parse_retry_after_seconds(response: httpx.Response) -> int | None:
    raw = (response.headers.get("retry-after") or "").strip()
    if not raw:
        return None
    try:
        value = int(raw)
    except ValueError:
        return None
    return value if value >= 0 else None


def _raise_for_error_response(
    response: httpx.Response,
    *,
    payload: Any,
    credentials: ResolvedCredentials,
) -> None:
    status_code = response.status_code
    message = _extract_message(payload, status_code=status_code)
    code = _extract_code(payload)
    upgrade_url = _extract_upgrade_url(payload) or (
        credentials.metadata.get("upgrade_url") if isinstance(credentials.metadata, dict) else None
    )

    if status_code == 402:
        agent_code = "quota_exhausted"
        if code and code.strip():
            agent_code = "quota_exhausted" if code == "trial_quota_exhausted" else code
        raise SentinelAPIError(
            message,
            status_code=status_code,
            code=agent_code,
            action="upgrade_required",
            upgrade_url=upgrade_url,
            payload=payload,
        )

    if status_code == 429:
        raise SentinelAPIError(
            message,
            status_code=status_code,
            code=code or "rate_limited",
            action="retry_later",
            retry_after_seconds=_parse_retry_after_seconds(response),
            payload=payload,
        )

    if status_code in (401, 403):
        raise SentinelAPIError(
            "Authentication failed. Check SENTINEL_API_KEY or refresh cached trial credentials.",
            status_code=status_code,
            code=code or "auth_failed",
            action="configure_credentials",
            payload=payload,
        )

    raise SentinelAPIError(
        f"Sentinel API error {status_code}: {payload}",
        status_code=status_code,
        code=code,
        payload=payload,
    )


async def _request(
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
) -> Any:
    settings = load_settings()
    try:
        credentials = await resolve_credentials(settings)
    except CredentialResolutionError:
        raise
    except Exception as exc:  # pragma: no cover - defensive wrapper
        raise CredentialResolutionError(f"Failed to resolve credentials: {exc}") from exc

    try:
        async with httpx.AsyncClient(
            base_url=settings.api_base_url,
            timeout=settings.timeout_seconds,
            headers=_headers(settings, api_key=credentials.api_key),
        ) as client:
            response = await client.request(method, path, params=params, json=json_body)
    except httpx.HTTPError as exc:
        raise SentinelAPIError(f"HTTP request to Sentinel API failed: {exc}") from exc

    payload = _parse_json_or_text(response)
    if response.is_error:
        _raise_for_error_response(response, payload=payload, credentials=credentials)
    return payload


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
