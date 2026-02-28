# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog, and this project follows Semantic Versioning.

## [Unreleased]

- No unreleased changes yet.

## [0.1.3] - 2026-02-28

- Repositioned the package as hosted and local MCP access for healthcare claims workflow scoring.
- Front-loaded hosted MCP endpoint, Smithery listing, and trial-key path in the README.
- Tightened package metadata keywords/description for healthcare claims discovery.

## [0.1.2] - 2026-02-26

- PyPI release: https://pypi.org/project/sentinel-signal-mcp/0.1.2/
- Added GitHub source metadata URLs for package directories (`Repository`, `Issues`) and set `Homepage` metadata to the PyPI project page.
- Front-loaded README quickstart with `uvx sentinel-signal-mcp` and drop-in MCP client config snippets.
- Added LobeHub MCP badge and renamed tools section to `Skills (MCP Tools)`.

## [0.1.1] - 2026-02-26

- PyPI release: https://pypi.org/project/sentinel-signal-mcp/0.1.1/
- Added packaging safety bound for MCP dependency (`mcp>=1.0.0,<2`).
- Added root `LICENSE` file and file-based license metadata for package consumers/scanners.
- Added Trove classifiers, `dev` optional dependencies, and changelog project URL metadata.
- Synced default user agent with package version automatically and standardized `ok: true` success responses.
- Added explicit PyPI links in README and package metadata.

## [0.1.0] - 2026-02-25

- PyPI release: https://pypi.org/project/sentinel-signal-mcp/0.1.0/
- Added Python MCP server tools for Sentinel Signal scoring, limits, usage, and feedback.
- Added auto-trial credential minting/caching and structured upgrade-aware error handling.
- Added defaults for dedicated API/token hostnames (`api.sentinelsignal.io`, `token.sentinelsignal.io`).
- Hardened packaging metadata (MIT `LICENSE`, `mcp<2`, classifiers) and standardized tool responses.
