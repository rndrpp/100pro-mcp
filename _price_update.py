"""Update the public MCP bridge repo (README + stdio bridge + registry manifest) to tiered pricing."""
import pathlib

root = pathlib.Path("/opt/data/profiles/100pro/home/mcp-repo")
subs = {
    "server.json": [
        ('"description": "Risk screen for EVM tokens and Solana mints: honeypot, LP lock, mint/freeze. $0.05 USDC on Base.",',
         '"description": "Risk screen for EVM tokens and Solana mints: honeypot, LP lock, mint/freeze. $0.10 USDC on Base.",'),
        ('"version": "1.0.1",', '"version": "1.0.2",'),
    ],
    "src/100pro_mcp.py": [
        ('"per call. $0.05 USDC per call on Base via x402 v2 — no account, no API key. "',
         '"per call. $0.10 USDC for one token, $0.25 for a 2-5 token batch, on Base via x402 v2 — "\n'
         '                    "no account, no API key. "'),
        ('"instructions": ("Paid tool: $0.05 USDC per call on Base (x402 v2, no account, no API key). "',
         '"instructions": ("Paid tool: $0.10 USDC per single token, $0.25 for a 2-5 token batch, "\n'
         '                             "on Base (x402 v2, no account, no API key). "'),
    ],
    "README.md": [
        ("- **Price:** **$0.05 USDC per call** on Base, paid with [x402](https://www.x402.org) v2 — no account,",
         "- **Price:** **$0.10 USDC per single token**, **$0.25 for a 2-5 token batch**, on Base, paid with\n"
         "  [x402](https://www.x402.org) v2 — no account,"),
        ("If the call is unpaid the server answers with the x402 payment challenge (HTTP 402). Pay $0.05 USDC on\n",
         "If the call is unpaid the server answers with the x402 payment challenge (HTTP 402). Pay $0.10 USDC\n"
         "(single token) or $0.25 (2-5 token batch) on\n"),
    ],
}
for fname, pairs in subs.items():
    p = root / fname
    t = p.read_text()
    for old, new in pairs:
        if old not in t:
            raise SystemExit(f"NOT FOUND in {fname}: {old[:80]!r}")
        t = t.replace(old, new, 1)
    p.write_text(t)
    print("updated", fname)
