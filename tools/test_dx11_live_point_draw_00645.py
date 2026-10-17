#!/usr/bin/env python3
"""Real D3D9 R30 point VB/IB/UP -> guarded native POINTLIST draw regression."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
def read(path):
    return (root / path).read_text(encoding="utf-8")

span = read("src/vr/d3d11/live_game_primitive_span.hpp")
bridge = read("src/vr/d3d11/live_game_frame_bridge.cpp")
probe = read("tools/dx11_game_primitive_span_probe.cpp")
assert "case 1u: // D3DPT_POINTLIST" in span
assert "elements = primitiveCount;" in span
assert "game_native_unit_point_raster(" in span
assert "perVertexPointSize" in span and "!perVertexPointSize" in span
for token in ("sizeBits == one", "minBits <= one", "maxBits >= one",
              "maxBits < 0x7f800000u", "spriteEnabled == 0u",
              "scaleEnabled == 0u"):
    assert token in span, token
for name in ("POINTSIZE", "POINTSIZE_MIN", "POINTSIZE_MAX",
             "POINTSPRITEENABLE", "POINTSCALEENABLE"):
    assert "GetRenderState(D3DRS_" + name in bridge, name
assert "layout.hasPointSize" in bridge
assert "topology == D3DPT_POINTLIST" in bridge
assert "D3D11_PRIMITIVE_TOPOLOGY_POINTLIST" in bridge
assert bridge.count("game_native_primitive_element_count(") == 2
assert "if (ib) ctx->DrawIndexed(indexCount, 0, 0);" in bridge
assert "else ctx->Draw(static_cast<UINT>(vertices.size()), 0);" in bridge
for source in ("src/vr/d3d9/stereo_renderer_r30.cpp",
               "src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp"):
    caller = read(source)
    assert caller.count("topology != D3DPT_POINTLIST") == 3, source
    assert caller.count("game_native_primitive_element_count(") == 3, source
    assert "R30CopyVertexShadow" in caller and "R30CopyIndexShadow" in caller
    assert "live::observe_linear" in caller and "live::observe_indexed" in caller
    if source == "src/vr/d3d9/stereo_renderer_r30.cpp":
        assert "const HRESULT gameHr = R30GuardScreenSpace(" in caller
        assert "R30CompleteNativeGameSource(device, gameHr);" in caller
        assert "return gameHr;" in caller
    else:
        # R26-safe cannot return the guard immediately: R30 HUD rollback may
        # fail before original D3D9 Draw, requiring native frame revocation.
        assert "const HRESULT gameHr = R30GuardScreenSpace(" in caller
        assert "R30CompleteNativeGameSourceR26Safe(device, gameHr);" in caller
        assert "return gameHr;" in caller
assert "game_native_primitive_element_count(1, 512, elements)" in probe
assert "game_native_unit_point_raster" in probe
for negative in ("maximum, 1, 0, false", "maximum, 0, 1, false",
                 "maximum, 0, 0, true", "0x40000000u, zero, maximum",
                 "one, 0x40000000u, maximum", "one, zero, 0x3f000000u",
                 "one, zero, 0x7fc00000u"):
    assert negative in probe, negative
assert "GetEnvironmentVariableW" in bridge
print("00645 live D3D9 point VB/IB/UP -> guarded native D3D11 POINTLIST: PASS")
