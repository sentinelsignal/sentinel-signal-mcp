# Sentinel Signal MCP

Python MCP server for Sentinel Signal scoring, limits, usage, and feedback tools.

This package provides a drop-in stdio MCP server so agent clients can call the Sentinel Signal API through a local tool connector. It supports either:

PyPI: https://pypi.org/project/sentinel-signal-mcp/

- a user-provided `SENTINEL_API_KEY`, or
- automatic no-signup trial key minting (`POST /v1/keys/trial`) with secure local credential caching

## MVP tools

- `score_workflow` -> `POST /v1/score`
- `get_limits` -> `GET /v1/limits`
- `get_usage` -> `GET /v1/usage`
- `submit_feedback` -> `POST /v1/feedback`

## Quick start (uvx)

1. Install `uv` (if needed): https://docs.astral.sh/uv/
2. Set env vars (optional `SENTINEL_API_KEY`; if omitted, the server auto-mints a trial key and caches it):

```bash
export SENTINEL_BASE_URL="https://api.sentinelsignal.io"                      # optional (default shown)
export SENTINEL_TOKEN_BASE_URL="https://token.sentinelsignal.io"  # optional (default shown)
# export SENTINEL_API_KEY="ss_live_or_test_api_key_here"                       # optional
export SENTINEL_TIMEOUT_SECONDS="30"                                           # optional
```

3. Run the MCP server:

```bash
uvx sentinel-signal-mcp
```

Deliverable behavior: install tool -> (optionally set env vars) -> agent can call `score_workflow`.

If no API key is configured, the MCP server resolves credentials in this order:

1. `SENTINEL_API_KEY` env var
2. cached trial key (`~/.sentinel/credentials.json` by default) if not expired and base URLs match
3. mint a new trial key from `POST {SENTINEL_TOKEN_BASE_URL}/v1/keys/trial`

Disable auto-trial with `SENTINEL_NO_TRIAL=1`.

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
        "SENTINEL_BASE_URL": "https://api.sentinelsignal.io",
        "SENTINEL_TOKEN_BASE_URL": "https://token.sentinelsignal.io",
        "SENTINEL_API_KEY": "ss_live_or_test_api_key_here",
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
  - optional `SENTINEL_API_KEY` (if omitted, auto-trial mint is used unless disabled)
  - optional `SENTINEL_BASE_URL`
  - optional `SENTINEL_TOKEN_BASE_URL`
  - optional `SENTINEL_CREDENTIALS_PATH`
  - optional `SENTINEL_NO_TRIAL=1`
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

## Trial key caching (auto-mint mode)

Default cache path:

- `~/.sentinel/credentials.json` (permissions `0600`)

Cached payload includes the trial key plus metadata used by the agent/runtime:

```json
{
  "api_key": "ss_trial_...",
  "account_id": "uuid",
  "expires_at": "2026-03-10T00:00:00Z",
  "limits": {
    "monthly_quota": 1000,
    "rps": 1,
    "burst": 5
  },
  "upgrade_url": "https://sentinelsignal.io/portal/dashboard",
  "token_base_url": "https://token.sentinelsignal.io",
  "api_base_url": "https://api.sentinelsignal.io"
}
```

The MCP server stores both base URLs in the cache so it does not accidentally reuse a trial key across different environments.

Reset the cached credentials (force a fresh trial key next run):

```bash
uvx sentinel-signal-mcp --reset-credentials
```

## Environment variables

- `SENTINEL_BASE_URL` (optional, default `https://api.sentinelsignal.io`): scoring API base URL
- `SENTINEL_TOKEN_BASE_URL` (optional, default `https://token.sentinelsignal.io`): token-service base URL used for trial key minting
- `SENTINEL_API_KEY` (optional): if set, used directly and never cached
- `SENTINEL_CREDENTIALS_PATH` (optional, default `~/.sentinel/credentials.json`)
- `SENTINEL_NO_TRIAL` (optional): set to `1` to disable auto-trial minting
- `SENTINEL_TIMEOUT_SECONDS` (optional, default `30`)
- `SENTINEL_API_BASE_URL` (legacy alias for `SENTINEL_BASE_URL`)

## Error behavior for agents

The MCP tools return structured payloads for both success and common operational failures:

- success -> `{"ok": true, ...}`

- quota exhausted / payment required (`402`) -> `{"ok": false, "error": {"action": "upgrade_required", "upgrade_url": "...", ...}}`
- rate limited (`429`) -> `{"ok": false, "error": {"action": "retry_later", ...}}`
- auth/config issues (`401`/`403` or missing credentials) -> `{"ok": false, "error": {"action": "configure_credentials", ...}}`

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
- Auto-minted trial credentials are cached locally with file permissions `0600`.
- Use `SENTINEL_CREDENTIALS_PATH=/tmp/...` for ephemeral environments if you do not want a persistent cache.
