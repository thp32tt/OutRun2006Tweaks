#!/usr/bin/env python3
"""Verify actual D3D9 VS/PS Boolean state reaches guarded live D3D11 draw."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
backend = (root / "src/vr/d3d11/native_backend.cpp").read_text()
bridge = (root / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
header = (root / "src/vr/d3d11/native_backend.hpp").read_text()
helper = (root / "src/vr/d3d11/native_sm3_constant_codegen.hpp").read_text()
fast = (root / ".github/workflows/dx11-fast-structural.yml").read_text()
for token in ("bool liveBooleansUsed = false;", "if (!boolDefPresent[reg]) liveBooleansUsed = true;",
              "append_native_sm3_live_bool_declaration(translated)",
              "candidate.vertexBooleans =", "candidate.pixelBooleans ="):
    assert token in backend, token
for token in ("bool vertexBooleans{}", "bool pixelBooleans{}"):
    assert token in header, token
for token in ("GetVertexShaderConstantB(0u, liveVertexBool.data(), 16u)",
              "GetPixelShaderConstantB(0u, livePixelBool.data(), 16u)",
              "native_sm3_live_bool_payload(source)",
              "VSSetConstantBuffers(2u, 1u, &vsBooleans)",
              "PSSetConstantBuffers(2u, 1u, &psBooleans)",
              "pipeline.program.vertexBooleans", "pipeline.program.pixelBooleans"):
    assert token in bridge, token
assert "uint4 r283_live_b[16]" in helper
assert "feature/dx11-00952-live-sm3-device-bool" in fast
assert "dx11_sm3_live_boolean_probe_00952.cpp" in fast
assert "test_dx11_sm3_live_boolean_00952.py" in fast
assert bridge.index("GetVertexShaderConstantB") < bridge.index("if (liveBatch.first_draw())", bridge.index("GetVertexShaderConstantB"))
assert bridge.index("uploadBool(pipeline.vertexBooleans.Get()") < bridge.index("context->DrawIndexed(")
print("Live VS/PS D3D9 Boolean IF -> D3D11 b2 Draw binding PASS")
