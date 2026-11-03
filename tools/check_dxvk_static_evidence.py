#!/usr/bin/env python3
"""Static DXVK evidence sanity checks.

Keeps repository-side DXVK analysis artifacts fail-closed without requiring the
runtime game machine.
"""

from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    analyzer = ROOT / "tools" / "analyze_outrun_exe.py"
    contract = ROOT / "tools" / "verify_vr_backend_disasm_contract.py"

    for path in (analyzer, contract):
        if not path.exists():
            raise SystemExit(f"missing DXVK static artifact: {path}")
        ast.parse(path.read_text(encoding="utf-8"))

    source = analyzer.read_text(encoding="utf-8")
    required = (
        "collect_raw_rel32_call_candidates",
        "collect_raw_inbound_rel32_candidates",
    )
    missing = [item for item in required if item not in source]
    if missing:
        raise SystemExit(f"DXVK raw evidence helpers missing: {missing}")

    print("DXVK_STATIC_EVIDENCE_CHECK=PASS")


if __name__ == "__main__":
    main()
