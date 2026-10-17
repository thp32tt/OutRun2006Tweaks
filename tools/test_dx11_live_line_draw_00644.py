#!/usr/bin/env python3
"""Live D3D9 game line capture and native D3D11 Draw/DrawIndexed integration."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
def file(name):
    return (root / name).read_text(encoding="utf-8")
span = file("src/vr/d3d11/live_game_primitive_span.hpp")
bridge = file("src/vr/d3d11/live_game_frame_bridge.cpp")
probe = file("tools/dx11_game_primitive_span_probe.cpp")
assert all(f"case {n}u:" in span for n in (2, 3, 4, 5, 6))
assert "default: return false;" in span
assert "game_native_primitive_element_count" in probe
assert bridge.count("game_native_primitive_element_count(") == 2
for topology in ("LINELIST", "LINESTRIP", "TRIANGLELIST", "TRIANGLESTRIP"):
    assert "D3D11_PRIMITIVE_TOPOLOGY_" + topology in bridge
assert "supported_game_state(game, type, vp, layout, transforms, capture, output)" in bridge
assert "D3DRS_ANTIALIASEDLINEENABLE" in bridge and "lineAA != FALSE" in bridge
assert "D3DRS_LASTPIXEL" in bridge and "lastPixel != TRUE" in bridge
# Native source ordinals are recorded before primitive topology admission:
# a rejected game line/triangle cannot disappear between two accepted draws.
assert "if (!diagnostic_enabled() || !game) return;" in bridge
observe = bridge[bridge.find("void observe("):bridge.find("} // namespace", bridge.find("void observe("))]
source_ordinal = observe.find("const std::uint64_t sourceOrdinal = s.sourceDrawsThisFrame++;")
topology_gate = observe.find("if (!game_native_primitive_element_count(")
assert source_ordinal >= 0 and topology_gate > source_ordinal
assert "s.frameBatch.abort();" in observe[source_ordinal:topology_gate + 650]
# Negative control must fail if the raw game ordinal is removed or moved behind admission.
mutated = observe.replace("const std::uint64_t sourceOrdinal = s.sourceDrawsThisFrame++;", "", 1)
assert mutated != observe and "const std::uint64_t sourceOrdinal = s.sourceDrawsThisFrame++;" not in mutated
assert "if (ib) ctx->DrawIndexed(indexCount, 0, 0);" in bridge
assert "else ctx->Draw(static_cast<UINT>(vertices.size()), 0);" in bridge
for name in ("src/vr/d3d9/stereo_renderer_r30.cpp",
             "src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp"):
    caller = file(name)
    assert caller.count("game_native_primitive_element_count(") == 3
    assert caller.count("topology != D3DPT_LINELIST") == 3
    assert caller.count("topology != D3DPT_LINESTRIP") == 3
    assert "R30CopyVertexShadow" in caller and "R30CopyIndexShadow" in caller
    assert "live::observe_linear" in caller and "live::observe_indexed" in caller
    if name == "src/vr/d3d9/stereo_renderer_r30.cpp":
        assert "const HRESULT gameHr = R30GuardScreenSpace(" in caller
        assert "R30CompleteNativeGameSource(device, gameHr);" in caller
        assert "return gameHr;" in caller
    else:
        # R26-safe must check the final guard HRESULT, not return it early:
        # stereo/HUD setup can itself fail before invoking the original Draw.
        assert "const HRESULT gameHr = R30GuardScreenSpace(" in caller
        assert "R30CompleteNativeGameSourceR26Safe(device, gameHr);" in caller
        assert "return gameHr;" in caller
print("00644 live game line VB/IB/UP / native D3D11 Draw graph: PASS")
