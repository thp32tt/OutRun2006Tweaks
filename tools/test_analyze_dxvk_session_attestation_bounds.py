#!/usr/bin/env python3
"""Regression guard for DXVK creation attestation identity boundaries.

This static test documents that analyzer input must not accept malformed
attestation identities as a trustworthy creation chronology signal.
"""

from __future__ import annotations

import pathlib
import re


ANALYZER = pathlib.Path(__file__).with_name("analyze_dxvk_session.py")


def main() -> int:
    text = ANALYZER.read_text(encoding="utf-8")

    required_guards = (
        "isinstance(attestation, int) and attestation > 0",
        "len(set(creation_attestation_ids)) == len(creation_attestation_ids)",
        "max(creation_probes, key=lambda probe: probe[\"attestation\"])",
    )
    missing = [guard for guard in required_guards if guard not in text]
    if missing:
        raise AssertionError(f"missing DXVK attestation guard(s): {missing}")

    if not re.search(r"DXVK_DEVICE_CREATION_ATTESTATION_IDS_INVALID", text):
        raise AssertionError("missing fail-closed invalid attestation status")

    print("DXVK analyzer attestation bounds regression guard: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
