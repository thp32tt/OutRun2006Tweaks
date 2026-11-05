#!/usr/bin/env python3
"""Verify live VS/PS IFC/BREAKC/SETP source translation, not real game/HMD."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
source = (root / "src/vr/d3d11/native_backend.cpp").read_text()
flow = (root / "src/vr/d3d11/native_sm3_conditional_flow.hpp").read_text()
workflow = (root / ".github/workflows/dx11-fast-structural.yml").read_text()

begin = source.index("if (instruction.opcode == static_cast<DWORD>(D3DSIO_IFC)")
end = source.index("if (instruction.opcode == static_cast<DWORD>(D3DSIO_IF))", begin)
block = source[begin:end]
for needle in (
    "D3DSIO_BREAKC", "D3DSIO_SETP", "predicateWrite",
    "native_sm3_scalar_condition_required_components(swizzle, modifier)",
    "(tempWritten[reg] & requiredComponents) != requiredComponents",
    "append_native_sm3_scalar_condition_operand(",
    "branch.flowCondition = scalarOperands[0]",
    "r283_decode_register_type(token)","D3DSPR_CONST", "D3DSPR_INPUT",
    "D3DSPR_TEMP", "D3DSHADER_ADDRESSMODE_MASK",
    "if (!defPresent[reg]) liveConstantsUsed = true;",
):
    assert needle in block, needle
for needle in (
    "native_sm3_source_modifier_components(1u, modifier)",
    "native_sm3_swizzled_components(",
    "append_native_sm3_source_modifier(operand, modifier)",
    "value = \"(\" + operand + \").x\";",
    "modifier > 12u",
):
    assert needle in flow, needle
assert "swizzle != 0x00u && swizzle != 0x55u" not in block
assert "modifier != D3DSPSM_NONE" not in block
assert "dx11_sm3_scalar_branch_modifiers_probe_00956.cpp" in workflow
assert "test_dx11_sm3_scalar_branch_modifiers_00956.py" in workflow
print("DX11 live SM3 IFC/BREAKC/SETP scalar source family PASS; runtime UNTESTED")
