# Sentinel Signal MCP

Python MCP tool server for the Sentinel Signal API.

This package lets MCP-compatible agent clients call Sentinel Signal scoring and billing-aware utility endpoints through a local MCP server process.

## MVP tools

- `score_workflow` -> `POST /v1/score`
- `get_limits` -> `GET /v1/limits`
- `get_usage` -> `GET /v1/usage`
- `submit_feedback` -> `POST /v1/feedback`

## Quick start (uvx)

1. Install `uv` (if needed): https://docs.astral.sh/uv/
2. Set env vars:

```bash
export SENTINEL_API_KEY="ss_live_or_test_api_key_here"
export SENTINEL_API_BASE_URL="https://sentinelsignal.io"  # optional (default shown)
export SENTINEL_TIMEOUT_SECONDS="30"                      # optional
```

3. Run the MCP server:

```bash
uvx sentinel-signal-mcp
```

Deliverable behavior: install tool -> set env vars -> agent can call `score_workflow`.

## MCP client config snippets

### Claude Desktop (macOS/Linux example)

Add this to your MCP config JSON (`mcpServers` section):

```json
{
  "mcpServers": {
    "sentinel-signal": {
      "command": "uvx",
      "args": ["sentinel-signal-mcp"],
      "env": {
        "SENTINEL_API_KEY": "ss_live_or_test_api_key_here",
        "SENTINEL_API_BASE_URL": "https://sentinelsignal.io",
        "SENTINEL_TIMEOUT_SECONDS": "30"
      }
    }
  }
}
```

### Generic MCP stdio client

If your client accepts a command + args + env definition:

- command: `uvx`
- args: `["sentinel-signal-mcp"]`
- env:
  - `SENTINEL_API_KEY`
  - optional `SENTINEL_API_BASE_URL`
  - optional `SENTINEL_TIMEOUT_SECONDS`

## Tool details

### `score_workflow`

Calls the Sentinel Signal unified scoring endpoint (`POST /v1/score`).

Arguments:

- `workflow` (`str`): workflow ID (for example `healthcare.denial`, `healthcare.prior_auth`, `healthcare.reimbursement`)
- `payload` (`object`): workflow payload object
- `options` (`object`, optional): scoring options object

Example MCP tool call input:

```json
{
  "workflow": "healthcare.denial",
  "payload": {
    "payer_id": 44,
    "provider_id": 1021,
    "patient_id": "PT_DEMO_001",
    "patient_age": 57,
    "patient_sex": "F",
    "cpt_code": "99214",
    "icd10_code": "M5450",
    "service_date": "2026-02-13",
    "place_of_service": "11",
    "units": 1,
    "billed_amount": 210.0,
    "allowed_amount": 145.0,
    "claim_frequency_code": "1",
    "network_status": "in_network",
    "prior_authorization_required": true,
    "prior_authorization_on_file": false,
    "referral_on_file": false,
    "is_emergency": false,
    "modifier_1": "25",
    "submission_channel": "edi",
    "data_source": "api"
  },
  "options": {
    "allow_fallback": true,
    "distribution_profile": "commercial_beta",
    "operating_point": "high_recall"
  }
}
```

### `get_limits`

Calls `GET /v1/limits` for the current API key.

No arguments.

### `get_usage`

Calls `GET /v1/usage`.

Arguments:

- `month` (`str`, optional): month filter (for example `2026-02`)

### `submit_feedback`

Calls `POST /v1/feedback` with a structured feedback payload.

Arguments:

- `feedback` (`object`): raw `FeedbackRequest` object

Example input:

```json
{
  "feedback": {
    "request_id": "00000000-0000-0000-0000-000000000001",
    "endpoint": "denial",
    "observed_outcome": "denied",
    "expected_outcome": "paid",
    "confidence_mismatch": true,
    "payer_id": 44,
    "cpt": "99214",
    "denial_reason_code": "AUTH_MISSING",
    "severity": "med",
    "days_to_outcome": 12,
    "notes": "Example feedback payload for agent integration testing."
  }
}
```

## Environment variables

- `SENTINEL_API_KEY` (required): API key sent as `Authorization: Bearer <key>`
- `SENTINEL_API_BASE_URL` (optional, default `https://sentinelsignal.io`)
- `SENTINEL_TIMEOUT_SECONDS` (optional, default `30`)

## Publishing (Python / uvx path)

This package is set up for PyPI publishing so users can run it with:

```bash
uvx sentinel-signal-mcp
```

Typical release commands:

```bash
python -m build
python -m twine upload dist/*
```

## Security notes

- Do not commit real API keys or customer payloads.
- Use placeholder values in client configs and examples.
- The server only reads credentials from environment variables at runtime.

