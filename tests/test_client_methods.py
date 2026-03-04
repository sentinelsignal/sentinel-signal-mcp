from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from sentinel_signal_mcp import client


class ClientMethodTests(unittest.IsolatedAsyncioTestCase):
    async def test_workflow_helpers_delegate_to_expected_endpoints(self) -> None:
        with patch("sentinel_signal_mcp.client._request", new_callable=AsyncMock) as request:
            request.return_value = {"ok": True}

            await client.list_workflows()
            await client.get_workflow_schema(workflow="healthcare.denial")
            await client.validate_workflow_payload(workflow="healthcare.denial", payload={"payer_id": 44})
            await client.score_batch(items=[{"workflow": "healthcare.denial", "payload": {"payer_id": 44}}])

        expected = [
            (("GET", "/v1/workflows"), {}),
            (("GET", "/v1/workflows/healthcare.denial/schema"), {}),
            (("POST", "/v1/workflows/healthcare.denial/validate"), {"json_body": {"payload": {"payer_id": 44}}}),
            (("POST", "/v1/score/batch"), {"json_body": {"items": [{"workflow": "healthcare.denial", "payload": {"payer_id": 44}}], "continue_on_error": True}}),
        ]
        self.assertEqual(request.await_args_list, [unittest.mock.call(*args, **kwargs) for args, kwargs in expected])


if __name__ == "__main__":
    unittest.main()
