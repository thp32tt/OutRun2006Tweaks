#!/usr/bin/env python3
"""Static DX11 conversion audit helpers.

This utility deliberately audits source/config evidence only. It never enables
NativeDrawPathActive and never reports runtime readiness.
"""

from pathlib import Path


FORBIDDEN_RUNTIME_CLAIMS = (
    "RUNTIME_VALIDATION=PASS",
    "QUEST3_VALIDATED",
    "VDXR_VALIDATED",
)


def validate_evidence(text: str) -> bool:
    """Return False for evidence that incorrectly claims runtime validation."""
    return not any(marker in text for marker in FORBIDDEN_RUNTIME_CLAIMS)


def audit_file(path: Path) -> int:
    return 0 if validate_evidence(path.read_text(encoding="utf-8")) else 1


if __name__ == "__main__":
    import sys

    raise SystemExit(audit_file(Path(sys.argv[1])))
