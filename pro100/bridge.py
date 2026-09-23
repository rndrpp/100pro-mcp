#!/usr/bin/env python3
"""100pro Token Risk Screen — MCP stdio bridge.

Forwards JSON-RPC 2.0 to the hosted x402 endpoint so stdio-only MCP clients can use it.
Stdlib only: no dependencies, nothing to install beyond Python 3.9+.

    python3 100pro_mcp.py            # speaks MCP on stdin/stdout
    python3 100pro_mcp.py --probe    # one-shot: print tools/list and exit (smoke test)
"""
import json
import os
import sys
import urllib.error
import urllib.request

ENDPOINT = os.environ.get("PRO100_MCP_ENDPOINT", "https://x402.rendraputra.dev/mcp")
UA = "100pro-mcp-bridge/1.1"
PRICE_NOTE = ("$0.10 USDC per single address, $0.25 for a 2-5 address batch, on Base via x402 v2 — "
              "no account, no API key. ")

TOOL = {
    "name": "token_risk_screen",
    "description": ("Pre-trade risk screen for an EVM token contract or a Solana SPL mint (Base, "
                    "Ethereum, BSC, Polygon, Arbitrum, Solana): honeypot/tax/owner flags, LP-lock "
                    "state, mint & freeze authority, holder concentration, liquidity depth, "
                    "wash-trade signals, and a final Verdict line. Up to 5 comma-separated tokens "
                    "per call. $0.10 USDC for one token, $0.25 for a 2-5 token batch, on Base via x402 v2 — "
                    "no account, no API key. "
                    "An unpaid call answers HTTP 402 with the payment challenge; sign it and retry "
                    "with the payment under params._meta['x402/payment']."),
    "inputSchema": {"type": "object", "properties": {
        "token": {"type": "string", "description": "Contract address (0x...) or Solana mint; up to 5 comma-separated"},
        "chain": {"type": "string", "enum": ["solana", "base", "ethereum", "bsc", "polygon", "arbitrum"],
                  "description": "Optional; inferred from the address shape when omitted"}},
        "required": ["token"]},
    "annotations": {"title": "Token risk screen (read-only)", "readOnlyHint": True,
                    "destructiveHint": False, "idempotentHint": True, "openWorldHint": True},
}


def _addr_tool(name, title, what, noun, chains, example):
    return {
        "name": name,
        "title": title,
        "description": (f"{what} ${PRICE_NOTE} "
                        "An unpaid call answers HTTP 402 with the payment challenge; sign it and retry "
                        "with the payment under params._meta['x402/payment']."),
        "inputSchema": {"type": "object", "properties": {
            "address": {"type": "string", "examples": [example],
                        "description": f"{noun}; up to 5 comma-separated"},
            "chain": {"type": "string", "enum": chains, "description": "Optional; defaults to base"}},
            "required": ["address"]},
        "annotations": {"title": title, "readOnlyHint": True, "destructiveHint": False,
                        "idempotentHint": True, "openWorldHint": True},
    }


CONTRACT_TOOL = _addr_tool(
    "contract_source_check", "Contract source check (EVM, read-only)",
    "Contract-level due diligence for an EVM address: is the source verified and via which route, "
    "fully vs partially, does the deployed bytecode still match the source, proxy pattern and "
    "implementation address, deployer and creation tx, age, and a capability scan of the verified "
    "source (mint, pause, blacklist, selfdestruct, delegatecall) — ending in a Verdict line.",
    "EVM contract address (0x...)", ["base", "ethereum", "bsc", "polygon", "arbitrum"],
    "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913")

WALLET_TOOL = _addr_tool(
    "wallet_risk_screen", "Wallet risk screen (EVM, read-only)",
    "Wallet-level due diligence for an EVM address: EOA vs contract, age from its first transaction, "
    "activity counters, balance, funding source, contracts deployed, Blockscout scam/reputation tags "
    "and GoPlus address-security flags (sanctioned, phishing, mixer, money laundering).",
    "EVM wallet address (0x...)", ["base", "ethereum", "bsc", "polygon", "arbitrum"],
    "0x6aAFF8af0ae8017725312C388bA3745dfE91185B")

TOOLS = [TOOL, CONTRACT_TOOL, WALLET_TOOL]



def local_reply(msg):
    """Answer initialize / tools/list / ping without touching the network.

    Introspection has to work inside sandboxes with no egress (directory checkers run this bridge
    in a container and only need the server to start and answer introspection), so these three are
    served locally; only tools/call is forwarded to the paid endpoint."""
    m, rid = msg.get("method"), msg.get("id")
    if m == "initialize":
        return {"jsonrpc": "2.0", "id": rid, "result": {
            "protocolVersion": (msg.get("params") or {}).get("protocolVersion") or "2025-06-18",
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "100pro-token-risk-screen", "version": "1.0.0"},
            "instructions": ("Paid tools: token_risk_screen, contract_source_check, wallet_risk_screen. "
                             "$0.10 USDC per single address, $0.25 for a 2-5 address batch, "
                             "on Base (x402 v2, no account, no API key). "
                             "Calls are forwarded to https://x402.rendraputra.dev/mcp; an unpaid call "
                             "returns HTTP 402 with the payment challenge.")}}
    if m == "tools/list":
        return {"jsonrpc": "2.0", "id": rid, "result": {"tools": TOOLS}}
    if m == "ping":
        return {"jsonrpc": "2.0", "id": rid, "result": {}}
    return None


def forward(msg, timeout=60):
    """POST one JSON-RPC message; return the parsed reply (or None for notifications)."""
    body = json.dumps(msg).encode()
    req = urllib.request.Request(ENDPOINT, data=body, method="POST",
                                 headers={"Content-Type": "application/json",
                                          "Accept": "application/json",
                                          "User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode() or "{}"), None
    except urllib.error.HTTPError as e:              # 402 = payment required: expected, not a bug
        raw = e.read().decode(errors="replace")
        try:
            detail = json.loads(raw)
        except Exception:
            detail = {"raw": raw[:400]}
        return None, {"status": e.code, "body": detail,
                      "challenge": e.headers.get("PAYMENT-REQUIRED")}
    except Exception as e:
        return None, {"status": 0, "body": {"error": f"{type(e).__name__}: {e}"}}


def emit(obj):
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def payment_note(err):
    """Turn a 402 into something a model can act on."""
    acc = ((err.get("body") or {}).get("accepts") or [{}])[0]
    return ("Payment required: ${} USDC on {} to {}. Sign an EIP-3009 transferWithAuthorization "
            "for that amount, base64 the x402 v2 PaymentPayload and retry the same call with it "
            "under params._meta['x402/payment'] (or a PAYMENT-SIGNATURE header). "
            "Offer/instructions: https://x402.rendraputra.dev/llms.txt").format(
        int(acc.get("amount", 50000)) / 1e6, acc.get("network", "eip155:8453"),
        acc.get("payTo", "the payTo address in the challenge"))


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except Exception:
            emit({"jsonrpc": "2.0", "id": None,
                  "error": {"code": -32700, "message": "parse error"}})
            continue
        if msg.get("id") is None:                     # notification: no response is expected
            continue
        local = local_reply(msg)
        if local is not None:                         # introspection: no network needed
            emit(local)
            continue
        reply, err = forward(msg)
        if err is None:
            emit(reply)
            continue
        if err["status"] == 402:
            emit({"jsonrpc": "2.0", "id": msg.get("id"),
                  "error": {"code": -32003, "message": payment_note(err)}})
        else:
            emit({"jsonrpc": "2.0", "id": msg.get("id"),
                  "error": {"code": -32603, "message": json.dumps(err)[:400]}})


def run(argv=None):
    """Entry point: `--probe` prints tools/list and exits, otherwise serve stdio."""
    argv = sys.argv[1:] if argv is None else argv
    if "--probe" in argv:
        r, e = forward({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        print(json.dumps(r if e is None else e, indent=2)[:1200])
        return
    main()


if __name__ == "__main__":
    run()
