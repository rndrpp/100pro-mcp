#!/usr/bin/env python3
"""100pro Token Risk Screen — MCP stdio bridge.

Forwards JSON-RPC 2.0 to the hosted x402 endpoint so stdio-only MCP clients can use it.
Stdlib only: no dependencies, nothing to install beyond Python 3.9+.

    python3 100pro_mcp.py            # speaks MCP on stdin/stdout
    python3 100pro_mcp.py --probe    # one-shot: print tools/list and exit (smoke test)
"""
import json
import sys
import urllib.error
import urllib.request

ENDPOINT = "https://x402.rendraputra.dev/mcp"
UA = "100pro-mcp-bridge/1.0"


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
        reply, err = forward(msg)
        if msg.get("id") is None:                     # notification: no response is expected
            continue
        if err is None:
            emit(reply)
            continue
        if err["status"] == 402:
            emit({"jsonrpc": "2.0", "id": msg.get("id"),
                  "error": {"code": -32003, "message": payment_note(err)}})
        else:
            emit({"jsonrpc": "2.0", "id": msg.get("id"),
                  "error": {"code": -32603, "message": json.dumps(err)[:400]}})


if __name__ == "__main__":
    if "--probe" in sys.argv:
        r, e = forward({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
        print(json.dumps(r if e is None else e, indent=2)[:1200])
    else:
        main()
