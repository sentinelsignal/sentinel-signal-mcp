from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


DEFAULT_API_BASE_URL = "https://sentinelsignal.io"
DEFAULT_TOKEN_BASE_URL = "https://sentinel-signal-token-service-prod.fly.dev"
DEFAULT_CREDENTIALS_PATH = Path.home() / ".sentinel" / "credentials.json"
DEFAULT_TIMEOUT_SECONDS = 30.0
DEFAULT_USER_AGENT = "sentinel-signal-mcp/0.1.0"


@dataclass(frozen=True)
class Settings:
    api_base_url: str
    token_base_url: str
    api_key: str | None
    credentials_path: Path
    no_trial: bool
    timeout_seconds: float
    user_agent: str = DEFAULT_USER_AGENT


def _parse_env_flag(name: str) -> bool:
    raw = os.getenv(name, "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _normalize_base_url(value: str, *, env_name: str) -> str:
    normalized = value.strip().rstrip("/")
    if not normalized:
        raise RuntimeError(f"{env_name} must not be empty")
    if not (normalized.startswith("http://") or normalized.startswith("https://")):
        raise RuntimeError(f"{env_name} must start with http:// or https://")
    return normalized


def load_settings() -> Settings:
    api_key = os.getenv("SENTINEL_API_KEY", "").strip() or None

    api_base_url = (
        os.getenv("SENTINEL_BASE_URL")
        or os.getenv("SENTINEL_API_BASE_URL")  # backward compatibility
        or DEFAULT_API_BASE_URL
    )
    token_base_url = os.getenv("SENTINEL_TOKEN_BASE_URL") or DEFAULT_TOKEN_BASE_URL
    api_base_url = _normalize_base_url(api_base_url, env_name="SENTINEL_BASE_URL")
    token_base_url = _normalize_base_url(token_base_url, env_name="SENTINEL_TOKEN_BASE_URL")

    timeout_raw = (
        os.getenv("SENTINEL_TIMEOUT_SECONDS")
        or os.getenv("SENTINEL_API_TIMEOUT_SECONDS")
        or str(DEFAULT_TIMEOUT_SECONDS)
    ).strip()
    try:
        timeout_seconds = float(timeout_raw)
    except ValueError as exc:
        raise RuntimeError("SENTINEL_TIMEOUT_SECONDS must be a number") from exc
    if timeout_seconds <= 0:
        raise RuntimeError("SENTINEL_TIMEOUT_SECONDS must be > 0")

    credentials_path_raw = os.getenv("SENTINEL_CREDENTIALS_PATH", "").strip()
    credentials_path = (
        Path(credentials_path_raw).expanduser()
        if credentials_path_raw
        else DEFAULT_CREDENTIALS_PATH
    )

    return Settings(
        api_base_url=api_base_url,
        token_base_url=token_base_url,
        api_key=api_key,
        credentials_path=credentials_path,
        no_trial=_parse_env_flag("SENTINEL_NO_TRIAL"),
        timeout_seconds=timeout_seconds,
    )
