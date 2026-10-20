#!/usr/bin/env python3
"""Real SM3 DCL partial-lane VS/PS source integration; strict fallback."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
backend = (root / "src/vr/d3d11/native_backend.cpp").read_text()
header = (root / "src/vr/d3d11/native_sm3_interface_channels.hpp").read_text()
pipeline = (root / "src/vr/d3d11/pipeline_translation.cpp").read_text()
workflow = (root / ".github/workflows/dx11-fast-structural.yml").read_text()
for semantic in ("BLENDWEIGHT", "BLENDINDICES", "NORMAL", "TEXCOORD", "TANGENT", "BINORMAL", "COLOR"):
    assert semantic in header and f'return "{semantic}";' in pipeline, semantic
for required in (
    '#include "native_sm3_interface_channels.hpp"',
    "std::array<unsigned, 16> inputDeclaredMasks{}",
    "std::array<unsigned, 16> outputDeclaredMasks{}",
    "native_sm3_interface_semantic(",
    "native_sm3_declared_components_cover(",
    "native_sm3_declared_output_complete(",
    "outputDeclaredMasks[op.destinationRegister], mask",
    "inputDeclaredMasks[reg], requiredComponents",
    "inputDeclaredMasks[reg], required",
):
    assert required in backend, required
assert "semantic.writeMask != D3DSP_WRITEMASK_ALL" not in backend
assert "R283_D3D9_SM3_REGISTER_ARITHMETIC_TEXTURE2D_MATRIX_IFC_HLSL_MATERIALIZER_V11" in backend
assert "dx11_sm3_interface_channels_probe_00957.cpp" in workflow
assert "test_dx11_sm3_interface_channels_00957.py" in workflow
print("SM3 DCL vertex semantics, partial-lane read and write provenance wired; HMD UNTESTED")
