#!/usr/bin/env python3
"""01072: R30 four real Draw callsites -> geometry-missing, pixel-neutral source continuity."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
hooks = (root / "src/vr/d3d9/stereo_renderer_r30.cpp").read_text(encoding="utf-8")
bridge = (root / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")
header = (root / "src/vr/d3d11/live_game_frame_bridge.hpp").read_text(encoding="utf-8")

def integrated(r30: str, native: str, contract: str) -> bool:
    start = r30.find("struct R30NativeGameSourceGuard {")
    end = r30.find("void R30CaptureNativeAdditionalStreams(", start)
    if start < 0 or end <= start:
        return False
    guard = r30[start:end]
    if not all(token in guard for token in (
        "if (!forwarded)", "topology <= D3DPT_TRIANGLEFAN",
        "observe_unmirrored_game_draw(device, topology, primitives);",
        "observe_unavailable_game_draw(device);")):
        return False
    sections = [
        ("void R30ObserveNativeLinearVB(", "void R30ObserveNativeIndexedVB("),
        ("void R30ObserveNativeIndexedVB(", "void R30ObserveNativeLinearUP("),
        ("void R30ObserveNativeLinearUP(", "void R30ObserveNativeIndexedUP("),
        ("void R30ObserveNativeIndexedUP(", "void R30CompleteNativeGameSource("),
    ]
    for begin, finish in sections:
        i = r30.find(begin)
        j = r30.find(finish, i)
        if i < 0 or j <= i:
            return False
        part = r30[i:j]
        assignments = (
            "nativeSource.topology = topology;",
            "nativeSource.primitives = primitiveCount;",
        )
        if "R30NativeGameSourceGuard nativeSource{device};" not in part or any(
                x not in part for x in assignments):
            return False
        if not part.index(assignments[0]) < part.index("game_native_primitive_element_count("):
            return False

    entry = native.find("void observe(IDirect3DDevice9* game,")
    post = native.find("void observe_unmirrored_game_draw(", entry)
    unavailable = native.find("void observe_unavailable_game_draw(", post)
    if min(entry, post, unavailable) < 0 or not entry < post < unavailable:
        return False
    observer = native[entry:post]
    ordinal = observer.find("const std::uint64_t sourceOrdinal = s.sourceDrawsThisFrame++;")
    neutral = observer.find("if (fullMode && proven_game_draw_no_target_writes(")
    mesh = observer.find("if (!game_native_primitive_element_count(")
    no_geometry = observer.find("if (!bytes || !stride)")
    shader = observer.find("if (!submit_live_sm3_game_draw(")
    if not 0 <= ordinal < neutral < mesh < no_geometry < shader:
        return False
    if "s.frameBatch.must_abort_unsupported(fullMode, multiBatch)" not in observer[no_geometry:shader]:
        return False
    nonmirror = native[post:unavailable]
    if "if (!env_full_game_opt_in())" not in nonmirror or not all(x in nonmirror for x in (
        "observe_unavailable_game_draw(game);",
        "observe(game, type, primitives, nullptr, 0u, 0u, nullptr, 0u, nullptr);")):
        return False
    if "observe_unmirrored_game_draw(IDirect3DDevice9*" not in contract:
        return False
    # The UP prefilter must reuse EXACTLY the same real-source pixel-neutral
    # observer: callers must not silently drop an oversized clipped UP Draw.
    linear = native[native.find("void observe_linear("):native.find("void observe_indexed(")]
    return ("observe_unmirrored_game_draw(game, type, primitives);" in linear and
            "observe_empty_game_draw(game, type);" in linear)

assert integrated(hooks, bridge, header), "real game unmirrored-source continuity disconnected"
for token in (
    "nativeSource.topology = topology;",
    "nativeSource.primitives = primitiveCount;",
    "observe_unmirrored_game_draw(device, topology, primitives);",
):
    candidate = hooks.replace(token, "/* deliberately omitted */", 1)
    assert candidate != hooks and not integrated(candidate, bridge, header), token
for token in ("if (!bytes || !stride)", "observe_unmirrored_game_draw(game, type, primitives);"):
    candidate = bridge.replace(token, "/* deliberately omitted */", 1)
    assert candidate != bridge and not integrated(hooks, candidate, header), token
assert not integrated(hooks, bridge, header.replace(
    "void observe_unmirrored_game_draw(", "void missing_observer(", 1))
print("01072 four-route native no-geometry continuity + fail-closed source contracts PASS")
