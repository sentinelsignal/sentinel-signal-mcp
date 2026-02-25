from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch

from sentinel_signal_mcp.config import Settings
from sentinel_signal_mcp.credentials import (
    CredentialResolutionError,
    bases_match,
    is_expired,
    load_cached_credentials,
    remove_cached_credentials,
    resolve_credentials,
    save_cached_credentials,
)
import sentinel_signal_mcp.credentials as credentials_mod


def _settings(*, api_key: str | None = None, credentials_path: Path, no_trial: bool = False) -> Settings:
    return Settings(
        api_base_url="https://sentinelsignal.io",
        token_base_url="https://sentinel-signal-token-service-prod.fly.dev",
        api_key=api_key,
        credentials_path=credentials_path,
        no_trial=no_trial,
        timeout_seconds=5.0,
    )


class CredentialsCacheTests(unittest.TestCase):
    def test_save_and_load_cached_credentials_sets_permissions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            cred_path = Path(tmp_dir) / "nested" / "credentials.json"
            payload = {
                "api_key": "ss_trial_example",
                "api_base_url": "https://sentinelsignal.io",
                "token_base_url": "https://sentinel-signal-token-service-prod.fly.dev",
            }

            save_cached_credentials(cred_path, payload)
            loaded = load_cached_credentials(cred_path)

            self.assertIsInstance(loaded, dict)
            self.assertEqual(loaded["api_key"], "ss_trial_example")
            mode = stat.S_IMODE(os.stat(cred_path).st_mode)
            self.assertEqual(mode, 0o600)

    def test_remove_cached_credentials(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            cred_path = Path(tmp_dir) / "credentials.json"
            save_cached_credentials(cred_path, {"api_key": "ss_trial_example"})
            self.assertTrue(remove_cached_credentials(cred_path))
            self.assertFalse(cred_path.exists())
            self.assertFalse(remove_cached_credentials(cred_path))

    def test_is_expired_and_base_matching(self) -> None:
        future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat().replace("+00:00", "Z")
        past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat().replace("+00:00", "Z")
        self.assertFalse(is_expired({"expires_at": future}))
        self.assertTrue(is_expired({"expires_at": past}))
        self.assertTrue(is_expired({"expires_at": "not-a-date"}))
        self.assertFalse(is_expired({}))

        creds = {
            "api_base_url": "https://sentinelsignal.io/",
            "token_base_url": "https://sentinel-signal-token-service-prod.fly.dev/",
        }
        self.assertTrue(
            bases_match(
                creds,
                api_base_url="https://sentinelsignal.io",
                token_base_url="https://sentinel-signal-token-service-prod.fly.dev",
            )
        )
        self.assertFalse(
            bases_match(
                creds,
                api_base_url="https://staging.sentinelsignal.io",
                token_base_url="https://sentinel-signal-token-service-prod.fly.dev",
            )
        )


class CredentialResolutionTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        credentials_mod._RESOLVE_LOCK = asyncio.Lock()

    async def test_resolve_prefers_env_key_and_does_not_touch_cache(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            cred_path = Path(tmp_dir) / "credentials.json"
            settings = _settings(api_key="ss_env_key", credentials_path=cred_path)

            with patch("sentinel_signal_mcp.credentials.fetch_trial_key") as mock_fetch:
                resolved = await resolve_credentials(settings)

            self.assertEqual(resolved.api_key, "ss_env_key")
            self.assertEqual(resolved.source, "env")
            mock_fetch.assert_not_called()
            self.assertFalse(cred_path.exists())

    async def test_resolve_uses_valid_cache(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            cred_path = Path(tmp_dir) / "credentials.json"
            expires_at = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat().replace("+00:00", "Z")
            save_cached_credentials(
                cred_path,
                {
                    "api_key": "ss_trial_cached",
                    "expires_at": expires_at,
                    "api_base_url": "https://sentinelsignal.io",
                    "token_base_url": "https://sentinel-signal-token-service-prod.fly.dev",
                    "upgrade_url": "https://sentinelsignal.io/portal/dashboard",
                },
            )
            settings = _settings(credentials_path=cred_path)

            with patch("sentinel_signal_mcp.credentials.fetch_trial_key") as mock_fetch:
                resolved = await resolve_credentials(settings)

            self.assertEqual(resolved.api_key, "ss_trial_cached")
            self.assertEqual(resolved.source, "cache")
            mock_fetch.assert_not_called()

    async def test_resolve_mints_and_caches_trial_key(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            cred_path = Path(tmp_dir) / "credentials.json"
            settings = _settings(credentials_path=cred_path)
            minted = {
                "api_key": "ss_trial_new",
                "account_id": "00000000-0000-0000-0000-000000000001",
                "expires_at": "2099-01-01T00:00:00Z",
                "upgrade_url": "https://sentinelsignal.io/portal/dashboard",
                "limits": {"monthly_quota": 1000, "rps": 1, "burst": 5},
                "api_base_url": "https://sentinelsignal.io",
                "token_base_url": "https://sentinel-signal-token-service-prod.fly.dev",
            }

            async def fake_fetch(_settings: Settings) -> dict:
                return dict(minted)

            with patch("sentinel_signal_mcp.credentials.fetch_trial_key", side_effect=fake_fetch):
                resolved = await resolve_credentials(settings)

            self.assertEqual(resolved.api_key, "ss_trial_new")
            self.assertEqual(resolved.source, "trial")
            cached = load_cached_credentials(cred_path)
            self.assertIsNotNone(cached)
            self.assertEqual(cached["api_key"], "ss_trial_new")
            self.assertEqual(cached["api_base_url"], settings.api_base_url)
            self.assertEqual(cached["token_base_url"], settings.token_base_url)

    async def test_resolve_no_trial_raises_when_no_env_or_cache(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            settings = _settings(credentials_path=Path(tmp_dir) / "credentials.json", no_trial=True)
            with self.assertRaises(CredentialResolutionError):
                await resolve_credentials(settings)


if __name__ == "__main__":
    unittest.main()
