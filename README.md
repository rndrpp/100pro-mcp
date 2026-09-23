# 100pro Token Risk Screen — MCP server

[![100pro-token-risk MCP connector](https://glama.ai/mcp/connectors/dev.rendraputra/100pro-token-risk/badges/score.svg)](https://glama.ai/mcp/connectors/dev.rendraputra/100pro-token-risk)

Pre-trade risk screening for EVM token contracts and Solana SPL mints, exposed as a **remote MCP
tool**. Honeypot/tax/owner flags, LP-lock state, mint & freeze authority, transfer fee/hook, holder
concentration, liquidity depth, wash-trade signals — ending in a one-line **Verdict**.

- **Endpoint:** `https://x402.rendraputra.dev/mcp` (MCP streamable HTTP, JSON-RPC 2.0)
- **Tool:** `token_risk_screen` (`token`, `chain`) — read-only, up to 5 comma-separated addresses per call
- **Chains:** `base`, `ethereum`, `bsc`, `polygon`, `arbitrum`, `solana`
- **Price:** **$0.10 USDC per single token**, **$0.25 for a 2-5 token batch**, on Base, paid with
  [x402](https://www.x402.org) v2 — no account,
  no API key, no subscription. An unpaid call answers HTTP 402 with the payment challenge; pay it and
  retry. Free metadata: [`/llms.txt`](https://x402.rendraputra.dev/llms.txt),
  [`/openapi.json`](https://x402.rendraputra.dev/openapi.json),
  [`/.well-known/x402`](https://x402.rendraputra.dev/.well-known/x402).

## Use it as a remote MCP server (no install)

```json
{
  "mcpServers": {
    "100pro-token-risk": {
      "type": "http",
      "url": "https://x402.rendraputra.dev/mcp"
    }
  }
}
```

## Use it through this stdio bridge

Some clients only speak stdio. This tiny proxy forwards `initialize`, `tools/list` and `tools/call`
to the remote endpoint (stdlib only, no dependencies):

```json
{
  "mcpServers": {
    "100pro-token-risk": {
      "command": "python3",
      "args": ["/absolute/path/to/100pro_mcp.py"]
    }
  }
}
```

or straight from the repo, if you use [uv](https://docs.astral.sh/uv/):

```json
{
  "mcpServers": {
    "100pro-token-risk": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/rndrpp/100pro-mcp", "100pro-mcp"]
    }
  }
}
```

### What a call returns

A markdown report per token, e.g.:

```text
## 0x8335…2913 (base)
**Verdict: PASS — no blocking risk signal found.**
...
```

If the call is unpaid the server answers with the x402 payment challenge (HTTP 402). Pay $0.10 USDC
(single token) or $0.25 (2-5 token batch) on
Base to the `payTo` in the challenge and retry; the response carries a `PAYMENT-RESPONSE` receipt
naming the settled transaction.

## Why paying beats a free scanner

Free scanners are the product being sold elsewhere: rate-limited, delay-baiting, or an upsell funnel.
This one is a single priced call with a fail-closed guarantee — the report is generated and returned
**only after the USDC transfer is confirmed on Base**, and every settle attempt is logged with the
on-chain verdict.

## Links

- Discovery: <https://x402.rendraputra.dev/llms.txt>
- OpenAPI: <https://x402.rendraputra.dev/openapi.json>
- x402 protocol: <https://www.x402.org>

MIT licensed.

### Repo layout

- `100pro_mcp.py` — repo-root entry point (`python3 100pro_mcp.py`, and the file container
  checkers execute after cloning); it bootstraps `pro100/bridge.py`.
- `pro100/bridge.py` — the actual stdio bridge: answers `initialize` / `tools/list` locally
  (so introspection needs no network) and forwards `tools/call` to the hosted endpoint.
- `pyproject.toml` — packages `pro100`, console script `100pro-mcp` (so `uvx --from
  git+https://github.com/rndrpp/100pro-mcp 100pro-mcp` works).

Python 3.9+, standard library only — nothing to install for the plain-script path.
