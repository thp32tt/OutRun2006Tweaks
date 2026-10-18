"""00649: live game D3D9 CW/CCW triangle raster -> D3D11 Draw/Indexed."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
c=(root/"src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")
h=(root/"src/vr/d3d11/live_game_cull_state.hpp").read_text(encoding="utf-8")
p=(root/"tools/dx11_game_cull_probe.cpp").read_text(encoding="utf-8")
def passes(src):
    capture=src.split("bool supported_game_state(",1)[1].split("bool translate_vertices(",1)[0]
    submit=src.split("bool submit(",1)[1].split("void before_game_present(",1)[0]
    return all(token in src for token in (
        '#include "live_game_cull_state.hpp"',
        "GameNativeCullAdmission admittedCull{};",
        "output.nativeCullMode = admittedCull.d3d9Mode;",
        "raster.CullMode = D3D11_CULL_BACK;",
        "raster.FrontCounterClockwise = direction == 0u ? TRUE : FALSE;",
        "raster.ScissorEnable = scissorEnabled ? TRUE : FALSE;",
        "s.diagnosticCullRasters[scissorEnabled * 2u + direction].GetAddressOf()",
        "output.nativeCullMode == D3DCULL_CW",
        "output.nativeCullMode == D3DCULL_CCW",
        "ctx->RSSetState(nativeRaster);",
        "ctx->DrawIndexed(indexCount, 0, 0);",
        "else ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
        "for (auto& item : s.diagnosticCullRasters) item.Reset();",
    )) and "game_native_cull_admission(" in capture and "cullMode != D3DCULL_NONE" not in capture and "fillMode != D3DFILL_SOLID" in capture and all(x in submit for x in (
        "output.scissor ? 2u : 0u", "output.scissor ? 3u : 1u",
        "output.scissor ? s.scissorRaster.Get() : s.raster.Get()"))
assert passes(c)
for original,modified in (
    ("game_native_cull_admission(", "game_native_cull_unchecked("),
    ("output.nativeCullMode = admittedCull.d3d9Mode;", "output.nativeCullMode = D3DCULL_NONE;"),
    ("raster.FrontCounterClockwise = direction == 0u ? TRUE : FALSE;", "raster.FrontCounterClockwise = FALSE;"),
    ("output.scissor ? 2u : 0u", "0u"),
    ("output.scissor ? 3u : 1u", "1u"),
    ("ctx->RSSetState(nativeRaster);", "ctx->RSSetState(s.raster.Get());"),
):
    if original == "game_native_cull_admission(":
        # Mutate the original fixed-function source capture, not the new
        # programmable SM3 caller. Both paths must independently enforce cull.
        before, rest = c.split("bool supported_game_state(", 1)
        capture, after = rest.split("bool translate_vertices(", 1)
        assert original in capture
        altered = (before + "bool supported_game_state(" +
                   capture.replace(original, modified, 1) +
                   "bool translate_vertices(" + after)
    else:
        altered = c.replace(original, modified, 1)
    assert altered != c and not passes(altered), original
assert "primitive >= 4u ? mode : 1u" in h
assert "mode < 1u || mode > 3u" in h
assert "game_native_cull_admission(mode,kind,c)" in p
print("00649 live CW/CCW game Draw raster and DX9Ex fallback PASS")
