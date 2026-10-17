#!/usr/bin/env python3
"""Source-to-native integration and destructive fallbacks for viewport Z 00687."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = (ROOT / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")
HEADER = (ROOT / "src/vr/d3d11/live_game_viewport_depth.hpp").read_text(encoding="utf-8")
WORKFLOW = (ROOT / ".github/workflows/dx11-fast-structural.yml").read_text(encoding="utf-8")

def integrated(bridge: str, header: str) -> bool:
    state = bridge.split("bool supported_game_state(", 1)[-1].split("bool translate_vertices(", 1)[0]
    translated = bridge.split("bool translate_vertices(", 1)[-1].split("bool mirror_texture(", 1)[0]
    native = bridge.split("bool submit(", 1)[-1].split("bool observe_source_device(", 1)[0]
    world_hdr = header.split("inline bool game_native_world_depth_clip(", 1)[-1].split(
        "inline bool game_native_screen_depth_clip(", 1)[0]
    screen_hdr = header.split("inline bool game_native_screen_depth_clip(", 1)[-1]
    observer = bridge.split("void observe(", 1)[-1].split("} // namespace", 1)[0]
    return all((
        '#include "live_game_viewport_depth.hpp"' in bridge,
        "game_native_viewport_depth_valid(viewport.MinZ, viewport.MaxZ)" in state,
        "game_native_screen_depth_clip(" in translated,
        "xyz[2], w, vp.MinZ, vp.MaxZ, v.clip[2]" in translated,
        "game_native_world_depth_clip(clip, vp.MinZ, vp.MaxZ)" in translated,
        "game_native_object_clip_position(clip)" in translated,
        translated.find("game_native_world_depth_clip(") < translated.find("game_native_object_clip_position(clip)"),
        "ctx->DrawIndexed(indexCount, 0, 0);" in native,
        "ctx->Draw(static_cast<UINT>(vertices.size()), 0);" in native,
        "if (!translate_vertices(bytes, vertexCount, stride, vp," in observer,
        "if (indexCount &&" in observer,
        "inline bool game_native_world_depth_clip(" in header,
        "const float remapped = (maxZ - minZ) * clip[2] + minZ * clip[3];" in header,
        "inline bool game_native_screen_depth_clip(" in header,
        "const float remapped = windowZ * w;" in header,
        "if (!std::isfinite(remapped)) return false;" in world_hdr,
        "if (!std::isfinite(remapped)) return false;" in screen_hdr,
        "minZ >= 0.0f && minZ <= 1.0f" in header,
        "maxZ >= 0.0f && maxZ <= 1.0f" in header,
    ))

assert integrated(BRIDGE, HEADER), "actual game FVF/viewport-to-native Draw wiring missing"
for token in (
    '#include "live_game_viewport_depth.hpp"',
    "game_native_viewport_depth_valid(viewport.MinZ, viewport.MaxZ)",
    "game_native_world_depth_clip(clip, vp.MinZ, vp.MaxZ)",
    "game_native_screen_depth_clip(",
    "if (!translate_vertices(bytes, vertexCount, stride, vp,",
    "ctx->DrawIndexed(indexCount, 0, 0);",
    "ctx->Draw(static_cast<UINT>(vertices.size()), 0);",
):
    mutated = BRIDGE.replace(token, "REMOVED_00687", 1)
    assert mutated != BRIDGE and not integrated(mutated, HEADER), token
for token in (
    "const float remapped = (maxZ - minZ) * clip[2] + minZ * clip[3];",
    "const float remapped = windowZ * w;",
    "if (!std::isfinite(remapped)) return false;",
    "minZ >= 0.0f && minZ <= 1.0f",
):
    mutant = HEADER.replace(token, "REMOVED_00687", 1)
    assert mutant != HEADER and not integrated(BRIDGE, mutant), token
assert "python tools/test_dx11_live_viewport_depth_00687.py" in WORKFLOW
assert "tools/dx11_game_viewport_depth_probe_00687.cpp" in WORKFLOW
print("00687: real game screen/world viewport Z => native Draw/Indexed, fail closed: PASS")
