#!/usr/bin/env python3
"""Source integration checks for shader-owned D3D9 DEFB/IF native game shader."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
backend = (root / "src/vr/d3d11/native_backend.cpp").read_text()
helper = (root / "src/vr/d3d11/native_sm3_constant_codegen.hpp").read_text()
workflow = (root / ".github/workflows/dx11-fast-structural.yml").read_text()
for needle in (
    "D3DSIO_DEFB", "D3DSIO_IF", "D3DSPR_CONSTBOOL",
    "boolDefPresent[reg] = true;", "boolDefBits[reg] = literal;",
    "literal > 1u", "reg >= boolDefPresent.size()",
    "native_sm3_bool_reference(", "writtenFlow.begin(tempWritten, outputWritten)",
    "writtenFlow.otherwise(tempWritten, outputWritten)",
    "writtenFlow.end(tempWritten, outputWritten)", "!writtenFlow.empty()",
    "branch.flowCondition = std::move(boolCondition);",
    "append_native_sm3_defb(", "D3DSP_SRCMOD_MASK",
    "D3DSHADER_ADDRESSMODE_MASK", "(swizzle != 0xe4u && swizzle != 0u)",
):
    assert needle in backend, needle
for needle in (
    "reg >= 16u || !defined", "reg >= 16u || literal > 1u",
    "static const bool r283_b", " = true;", " = false;",
):
    assert needle in helper, needle
assert "dx11_sm3_boolean_flow_probe_00947.cpp" in workflow
assert "test_dx11_sm3_boolean_flow_00947.py" in workflow
print("SM3 shader-local Boolean native IF and D3D9 fallback source checks PASS")
