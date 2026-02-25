from __future__ import annotations

import unittest

import httpx

from sentinel_signal_mcp.client import SentinelAPIError, _raise_for_error_response
from sentinel_signal_mcp.credentials import ResolvedCredentials


def _resolved(meta: dict | None = None) -> ResolvedCredentials:
    return ResolvedCredentials(
        api_key="ss_trial_example",
        source="cache",
        metadata=meta or {},
    )


class ClientErrorMappingTests(unittest.TestCase):
    def test_maps_trial_quota_402_to_upgrade_required(self) -> None:
        response = httpx.Response(
            402,
            json={
                "detail": {
                    "code": "trial_quota_exhausted",
                    "message": "Trial monthly quota exhausted.",
                    "upgrade_url": "https://sentinelsignal.io/portal/dashboard",
                }
            },
        )

        with self.assertRaises(SentinelAPIError) as ctx:
            _raise_for_error_response(response, payload=response.json(), credentials=_resolved())

        exc = ctx.exception
        self.assertEqual(exc.status_code, 402)
        self.assertEqual(exc.code, "quota_exhausted")
        self.assertEqual(exc.action, "upgrade_required")
        self.assertEqual(exc.upgrade_url, "https://sentinelsignal.io/portal/dashboard")

    def test_maps_429_to_retry_later(self) -> None:
        response = httpx.Response(
            429,
            headers={"Retry-After": "2"},
            json={"detail": "Trial rate limit exceeded"},
        )

        with self.assertRaises(SentinelAPIError) as ctx:
            _raise_for_error_response(response, payload=response.json(), credentials=_resolved())

        exc = ctx.exception
        self.assertEqual(exc.status_code, 429)
        self.assertEqual(exc.code, "rate_limited")
        self.assertEqual(exc.action, "retry_later")
        self.assertEqual(exc.retry_after_seconds, 2)


if __name__ == "__main__":
    unittest.main()
