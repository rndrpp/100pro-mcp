#!/usr/bin/env python3
"""Repo-root entry point.

Kept here because directory checkers (Glama) run `python3 /app/100pro_mcp.py` after cloning
the repository. It only bootstraps the real implementation in `pro100/bridge.py`.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pro100.bridge import run  # noqa: E402

if __name__ == "__main__":
    run()
