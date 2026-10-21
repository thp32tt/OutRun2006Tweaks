#!/usr/bin/env python3
"""Real-game cube surface format translation and fail-closed integration."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")
FAST = (ROOT / ".github/workflows/dx11-fast-structural.yml").read_text(encoding="utf-8")
NEEDED = (
 "D3DFMT_A8R8G8B8", "D3DFMT_X8R8G8B8",
 "D3DFMT_A8B8G8R8", "D3DFMT_X8B8G8R8",
 "D3DFMT_A2R10G10B10", "D3DFMT_A2B10G10R10",
 "D3DFMT_R5G6B5", "D3DFMT_A1R5G5B5", "D3DFMT_A4R4G4B4",
 "D3DFMT_X1R5G5B5", "D3DFMT_X4R4G4B4",
 "cube_rt_readback::sampleable_color(cubeColor, capture.srgbTexture)",
 "native_rt_readback::source_texel_bytes(cubeColor)",
 "native_rt_readback::unpack_row(", "if (compressed)",
 "std::memcpy(to, from, pitch)",
 "gameDevice->GetRenderTargetData(", "capture.cubeTexture->LockRect(",
 "readback->UnlockRect()", "capture.cubeTexture->UnlockRect(cubeFace, level)",
 "D3D11_RESOURCE_MISC_TEXTURECUBE",
 "create_game_sampler(dev, capture, uploadedLevels, sampler)",
 "cube_rt_readback::bounded_six_face_bgra8(base.Width, uploadedLevels)",
)
def integrated(source):
    body = source[source.index("bool mirror_cube_texture("):source.index("bool mirror_texture(")]
    return (all(key in body for key in NEEDED)
        and body.index("GetRenderTargetData(") < body.index("CreateTexture2D(")
        and body.index("native_rt_readback::unpack_row(") < body.index("CreateTexture2D(")
        and body.index("if (!cpuLocked && !gpuCubeRt) return false;") < body.index("CreateTexture2D("))
assert integrated(SRC)
for token in ("D3DFMT_A2R10G10B10", "D3DFMT_X4R4G4B4",
 "native_rt_readback::source_texel_bytes(cubeColor)",
 "native_rt_readback::unpack_row(", "gameDevice->GetRenderTargetData(",
 "cube_rt_readback::sampleable_color(cubeColor, capture.srgbTexture)"):
    assert not integrated(SRC.replace(token, "/* removed */", 1)), token
assert "dx11_live_game_cube_color_00974.cpp" in FAST
assert "test_dx11_live_game_cube_color_00974.py" in FAST
assert "context->DrawIndexed(nativeIndexCount, 0u, 0)" in SRC
assert "mirrorLiveSampler(capture," in SRC
print("PASS live SM3 cube format family, GPU readback and DX9Ex fallback")
