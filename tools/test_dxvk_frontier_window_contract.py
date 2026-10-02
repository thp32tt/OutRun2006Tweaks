#!/usr/bin/env python3
"""Static regression checks for DXVK canonical window frontier contracts.

These checks intentionally avoid PE/runtime dependencies. They protect the
fail-closed evidence boundary used by GitHub-only DXVK disassembly work.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load_extractor():
    spec = importlib.util.spec_from_file_location(
        "extract_dxvk_canonical_window",
        ROOT / "tools" / "extract_dxvk_canonical_window.py",
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load DXVK extractor")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_frontier_discovery_requires_exact_literal_source():
    extractor = _load_extractor()
    result = extractor.discover_frontier_rva(
        ROOT / "tools" / "extract_dxvk_canonical_window.py"
    )

    assert isinstance(result["continuation_id"], int)
    assert result["continuation_id"] > 0
    assert result["basis"] in {"INCOMPLETE_RVA", "PREFIX_END_RVA"}
    assert result["rva"] > 0


if __name__ == "__main__":
    test_frontier_discovery_requires_exact_literal_source()
    print("DXVK frontier window contract: PASS")
