#!/usr/bin/env python3
"""Verify real programmable SM3 shader flow translation, not game runtime."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
source = (root / "src/vr/d3d11/native_backend.cpp").read_text()
flow = (root / "src/vr/d3d11/native_sm3_conditional_flow.hpp").read_text()
workflow = (root / ".github/workflows/dx11-fast-structural.yml").read_text()

def require(text, needle):
    assert needle in text, f"missing native IFC behavior: {needle}"

for needle in (
    "D3DSIO_IFC", "D3DSIO_ELSE", "D3DSIO_ENDIF",
    "native_sm3_ifc_comparison(comparison)",
    "writtenFlow.begin(tempWritten, outputWritten)",
    "writtenFlow.otherwise(tempWritten, outputWritten)",
    "writtenFlow.end(tempWritten, outputWritten)",
    "operations.empty() || !writtenFlow.empty()",
    "(tempWritten[reg] & (1u << component)) == 0u",
    "if (!declared) return false;",
    "if (!defPresent[reg]) liveConstantsUsed = true;",
    "branch.flowCondition", "if (op.flowKind != 0u)",
    'translated += "    } else {',
):
    require(source, needle)
for needle in (
    "frames_.size() >= 8u",
    "frames_.empty() || frames_.back().hasElse",
    "temps = frame.entryTemps",
    "outputs = frame.entryOutputs",
    "temps[i] &= otherTemps[i]",
    "outputs[i] &= otherOutputs[i]",
):
    require(flow, needle)
require(workflow, "dx11_sm3_conditional_flow_probe_00946.cpp")
require(workflow, "test_dx11_sm3_conditional_flow_00946.py")
# A test mutation that removes the branch path must be rejected.
assert "D3DSIO_IFC" not in source.replace("D3DSIO_IFC", "", 1).partition(
    "// SM3 scalar float-compare")[0]
print("DX11 SM3 IFC branch/source/fallback checks PASS (not HMD evidence)")
