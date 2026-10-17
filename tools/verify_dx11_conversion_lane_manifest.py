#!/usr/bin/env python3
"""Static DX11 conversion-lane manifest validator.

This validator intentionally stays offline: it checks repository metadata contracts
without enabling the native draw path or claiming runtime validation.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys


REQUIRED_FILES = (
    "docs/CONVERSION_LANE_STATE.json",
    "AGENTS.md",
)


def main() -> int:
    root = Path(__file__).resolve().parents[1]

    missing = [path for path in REQUIRED_FILES if not (root / path).exists()]
    if missing:
        print("missing required DX11 conversion files:")
        for item in missing:
            print(f"- {item}")
        return 1

    state = json.loads((root / "docs/CONVERSION_LANE_STATE.json").read_text(encoding="utf-8"))

    checks = {
        "schema_version": state.get("schema_version") == 2,
        "lane": state.get("lane") == "DX11",
        "github_only": state.get("environment", {}).get("github_only_development") is True,
        "runtime_unset": state.get("latest_durable_task", {}).get("runtime_validation") == "UNTESTED",
    }

    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        print("DX11 conversion manifest contract failed:")
        for item in failed:
            print(f"- {item}")
        return 1

    print("DX11 conversion manifest contract PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
