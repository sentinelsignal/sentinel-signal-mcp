from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Any

import httpx

from .config import Settings


_RESOLVE_LOCK = asyncio.Lock()


@dataclass(frozen=True)
class ResolvedCredentials:
    api_key: str
    source: str
    metadata: dict[str, Any]


class CredentialResolutionError(RuntimeError):
    """Raised when the MCP server cannot resolve a usable Sentinel API key."""


def _parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def load_cached_credentials(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def save_cached_credentials(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f"{path.name}.tmp")
    tmp_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    os.chmod(tmp_path, 0o600)
    tmp_path.replace(path)
    os.chmod(path, 0o600)


def remove_cached_credentials(path: Path) -> bool:
    try:
        path.unlink()
        return True
    except FileNotFoundError:
        return False


def is_expired(creds: dict[str, Any]) -> bool:
    expires_at = creds.get("expires_at")
    if not isinstance(expires_at, str) or not expires_at.strip():
        return False
    try:
        expiry = _parse_dt(expires_at.strip())
    except ValueError:
        return True
    return expiry <= datetime.now(timezone.utc)


def bases_match(creds: dict[str, Any], *, api_base_url: str, token_base_url: str) -> bool:
    cached_api_base = str(creds.get("api_base_url") or "").rstrip("/")
    cached_token_base = str(creds.get("token_base_url") or "").rstrip("/")
    return cached_api_base == api_base_url.rstrip("/") and cached_token_base == token_base_url.rstrip("/")


def _validate_cached_credentials(creds: dict[str, Any]) -> bool:
    api_key = creds.get("api_key")
    return isinstance(api_key, str) and bool(api_key.strip())


async def fetch_trial_key(settings: Settings) -> dict[str, Any]:
    url = f"{settings.token_base_url}/v1/keys/trial"
    headers = {
        "Accept": "application/json",
        "User-Agent": settings.user_agent,
    }
    try:
        async with httpx.AsyncClient(timeout=settings.timeout_seconds, headers=headers) as client:
            response = await client.post(url)
    except httpx.HTTPError as exc:
        raise CredentialResolutionError(f"Failed to mint trial key from {url}: {exc}") from exc

    try:
        payload = response.json()
    except ValueError:
        payload = {"raw_text": response.text}

    if response.is_error:
        raise CredentialResolutionError(
            f"Trial key mint failed ({response.status_code}): {payload}"
        )

    if not isinstance(payload, dict):
        raise CredentialResolutionError("Trial key response was not a JSON object")
    api_key = payload.get("api_key")
    if not isinstance(api_key, str) or not api_key.strip():
        raise CredentialResolutionError("Trial key response missing api_key")

    payload["api_base_url"] = settings.api_base_url
    payload["token_base_url"] = settings.token_base_url
    return payload


async def resolve_credentials(settings: Settings) -> ResolvedCredentials:
    if settings.api_key:
        return ResolvedCredentials(
            api_key=settings.api_key,
            source="env",
            metadata={
                "source": "env",
                "api_base_url": settings.api_base_url,
                "token_base_url": settings.token_base_url,
            },
        )

    async with _RESOLVE_LOCK:
        cached = load_cached_credentials(settings.credentials_path)
        if cached and _validate_cached_credentials(cached):
            if not is_expired(cached) and bases_match(
                cached,
                api_base_url=settings.api_base_url,
                token_base_url=settings.token_base_url,
            ):
                return ResolvedCredentials(
                    api_key=str(cached["api_key"]),
                    source="cache",
                    metadata={**cached, "source": "cache"},
                )

        if settings.no_trial:
            raise CredentialResolutionError(
                "SENTINEL_API_KEY is not set and auto-trial is disabled (SENTINEL_NO_TRIAL=1)."
            )

        minted = await fetch_trial_key(settings)
        save_cached_credentials(settings.credentials_path, minted)
        return ResolvedCredentials(
            api_key=str(minted["api_key"]),
            source="trial",
            metadata={**minted, "source": "trial"},
        )

