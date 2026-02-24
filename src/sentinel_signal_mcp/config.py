from __future__ import annotations

from dataclasses import dataclass
import os


DEFAULT_API_BASE_URL = "https://sentinelsignal.io"
DEFAULT_TIMEOUT_SECONDS = 30.0
DEFAULT_USER_AGENT = "sentinel-signal-mcp/0.1.0"


@dataclass(frozen=True)
class Settings:
    api_base_url: str
    api_key: str
    timeout_seconds: float
    user_agent: str = DEFAULT_USER_AGENT


def load_settings() -> Settings:
    api_key = os.getenv("SENTINEL_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("SENTINEL_API_KEY is required")

    api_base_url = os.getenv("SENTINEL_API_BASE_URL", DEFAULT_API_BASE_URL).strip() or DEFAULT_API_BASE_URL
    api_base_url = api_base_url.rstrip("/")

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

    return Settings(
        api_base_url=api_base_url,
        api_key=api_key,
        timeout_seconds=timeout_seconds,
    )

