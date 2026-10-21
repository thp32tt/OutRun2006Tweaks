#!/usr/bin/env python3
"""Game D3D9 SM3 CubeTexture->HLSL->D3D11 cube SRV/native Draw. Runtime untested."""
from pathlib import Path
r = Path(__file__).resolve().parents[1]
bridge = (r / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
backend = (r / "src/vr/d3d11/native_backend.cpp").read_text()
helper = (r / "src/vr/d3d11/native_sm3_texture_codegen.hpp").read_text()
for t in ("D3DSTT_CUBE", "samplerCubeDeclared[reg]", "samplerCubeUsed[reg]",
          "append_native_sm3_texturecube_sample(",
          "candidate.vertexCubeSamplerMask", "candidate.pixelCubeSamplerMask"):
    assert t in backend, t
for t in ("IDirect3DCubeTexture9", "D3DRTYPE_CUBETEXTURE",
          "cubeTexture->LockRect(", "cubeTexture->UnlockRect(",
          "native.ArraySize=6u", "D3D11_RESOURCE_MISC_TEXTURECUBE",
          "D3D11_SRV_DIMENSION_TEXTURECUBE", "create_game_sampler(",
          "pipeline.program.vertexCubeSamplerMask", "pipeline.program.pixelCubeSamplerMask",
          "if (budget > (24ull << 20u)) return false;"):
    assert t in bridge, t
assert "native_sm3_cube_source_components(" in helper
assert "context->PSSetShaderResources(0u, 16u, boundViews.data())" in bridge
assert "context->VSSetShaderResources(0u, 4u, boundVertexViews.data())" in bridge
assert "if (nativeIndices) context->DrawIndexed" in bridge
assert "s.frameBatch.abort();" in bridge
print("Native game cube shader and 6-face SRV connected; game/HMD UNTESTED")
