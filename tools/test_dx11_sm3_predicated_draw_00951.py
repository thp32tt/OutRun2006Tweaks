#!/usr/bin/env python3
"""D3D9 SM3 predicated arithmetic / explicit-LOD draw parity guard."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
backend = (root / "src/vr/d3d11/native_backend.cpp").read_text()
header = (root / "src/vr/d3d11/native_sm3_predicated_instruction.hpp").read_text()
fast = (root / ".github/workflows/dx11-fast-structural.yml").read_text()
for item in ("D3DSIO_SETP", "D3DSPR_PREDICATE", "sourcePredicated",
             "0x10000000u", "instruction.operandTokens.back()",
             "predicateFlow.ready()", "native_sm3_scalar_predicate(",
             "native_sm3_predicated_write_mask(", "D3DSIO_TEXLDL",
             "D3DSIO_TEXLDD", "append_native_sm3_predicated_begin(",
             "append_native_sm3_predicated_end(", "op.predicated"):
    assert item in backend, item
for item in ("predicateInitialized", "sourceSwizzle != 0u",
             "predicated ? definiteWritten", "if (r283_p0)", "if (!r283_p0)"):
    assert item in header, item
for item in ("dx11_sm3_predicated_draw_probe_00951.cpp",
             "test_dx11_sm3_predicated_draw_00951.py"):
    assert item in fast, item
print("SM3 scalar predicated native Draw source/fallback checks PASS")
