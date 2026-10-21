#!/usr/bin/env python3
"""Live game GPU cube-RT -> D3D9 SYSTEMMEM -> native VS/PS cube SRV."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
src = (root / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
hdr = (root / "src/vr/d3d11/live_game_cube_rt_readback.hpp").read_text()
wf = (root / ".github/workflows/dx11-fast-structural.yml").read_text()
def integrated(x):
    cube = x[x.index("bool mirror_cube_texture("):x.index("bool mirror_texture(")]
    tokens = ("base.Pool == D3DPOOL_DEFAULT", "D3DUSAGE_RENDERTARGET",
      "base.Format == D3DFMT_A8R8G8B8", "base.Format == D3DFMT_X8R8G8B8",
      "if (!cpuLocked && !gpuCubeRt) return false;",
      "cube_rt_readback::bounded_six_face_bgra8(base.Width, uploadedLevels)",
      "capture.cubeTexture->GetDevice(gameDevice.GetAddressOf())",
      "capture.cubeTexture->GetCubeMapSurface(",
      "faceDesc.MultiSampleType != D3DMULTISAMPLE_NONE",
      "native_rt_readback::matching_mip_extent(",
      "gameDevice->CreateOffscreenPlainSurface(",
      "gameDevice->GetRenderTargetData(",
      "readback->LockRect(&locked, nullptr, D3DLOCK_READONLY)",
      "capture.cubeTexture->LockRect(", "readback->UnlockRect()",
      "capture.cubeTexture->UnlockRect(cubeFace, level)",
      "D3D11_RESOURCE_MISC_TEXTURECUBE", "create_game_sampler(dev, capture, uploadedLevels, sampler)")
    return all(y in cube for y in tokens) and cube.index("GetRenderTargetData(") < cube.index("CreateTexture2D(")
assert integrated(src)
for needle in ("if (!cpuLocked && !gpuCubeRt) return false;",
  "cube_rt_readback::bounded_six_face_bgra8(base.Width, uploadedLevels)",
  "gameDevice->GetRenderTargetData(", "native_rt_readback::matching_mip_extent(",
  "readback->UnlockRect()"):
    assert not integrated(src.replace(needle, "/* removed */", 1)), needle
assert "24ull << 20u" in hdr and "face > (maximum - total) / 6u" in hdr
assert "dx11_live_game_cube_rt_00973.cpp" in wf
assert "test_dx11_live_game_cube_rt_00973.py" in wf
assert "mirrorLiveSampler(capture," in src and "context->DrawIndexed(nativeIndexCount, 0u, 0)" in src
print("PASS live game GPU cube six-face mip mirror with DX9Ex fallback")
