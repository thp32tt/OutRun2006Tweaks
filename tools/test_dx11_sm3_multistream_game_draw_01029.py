#!/usr/bin/env python3
"""Native game D3D9 stream 0..15 source -> D3D11 SM3 per-Draw bridge."""
from pathlib import Path
base=Path(__file__).resolve().parents[1]
read=lambda p:(base/p).read_text()
api=read("src/vr/d3d11/live_game_frame_bridge.hpp")
capture=read("src/vr/d3d9/stereo_renderer_r30.cpp")
bridge=read("src/vr/d3d11/live_game_frame_bridge.cpp")
assembly=read("src/vr/d3d11/live_game_sm3_stream_assembly.hpp")
checks={
"all D3D9 epoch shadow slots": "std::array<bool,16> used{};" in capture and "R30CopySparseVertexShadow" in capture,
"source capture staging bound": "capturedExtraBytes > (1ull << 27u)" in capture,
"all draw callsites": capture.count("std::array<std::vector<std::uint8_t>,15> owned{};")==5,
"source lifetime": "std::array<View, 15> extra{};" in api,
"native IA declaration": "if (in.Stream >= 16u" in bridge,
"native packed streams": "std::array<GameSm3StreamView,16> instanceStreams{};" in bridge and
    "auto& streams = instanceStreams;" in bridge and
    "instanceElements, instanceStreams, vertexCount," in bridge and
    "firstChunkInstances," in bridge and
    "chunkInstances, instanceSteps, unpacked, instance" in bridge,
"instance rate and indexed GPU draw": "std::array<std::uint32_t,16> instanceSteps{};" in bridge and
    "context->DrawIndexed(nativeIndexCount, 0u, static_cast<INT>(base))" in bridge,
"16 stream IA consumer": assembly.count("const std::array<GameSm3StreamView,16>& streams")>=5 and
    # Every original instance/fan, indexed-window and indexed-fan assembler
    # uses the full 16-slot live D3D9 view instead of dropping stream 1..15.
    # Adding one source-backed helper must not invalidate older negative tests.
    "game_sm3_assemble_indexed_window(" in assembly and
    "game_sm3_assemble_indexed_fan_window(" in assembly and
    "selected.push_back(indices[0u]);" in assembly and
    "selected.push_back(indices[firstRim + i - 1u]);" in assembly and
    "return game_sm3_assemble_indexed_window(" in assembly and
    "game_sm3_copy_native_indexed_fan_window(" in assembly and
    "indices[v ? firstRim + v - 1u : 0u] >= sourceVertices" in assembly and
    "indices[firstIndex+v] >= stream.vertexCount" in assembly and
    "output.swap(staged)" in assembly and
    "game_sm3_assemble_fan_window(" in assembly and
    "game_sm3_assemble_streams(elements, streams, 1u, center)" in assembly and
    "game_sm3_assemble_streams(elements, streams," in assembly and
    "windowVertices - 1u, rim, firstRim" in assembly,
"positive/negative legacy probe": "std::array<GameSm3StreamView,16> streams" in
    read("tools/dx11_live_sm3_instancing_00992.cpp"),
"fail-closed original D3D9": "observe_unavailable_game_draw(device)" in capture and
    "if (!captured) return false;" in capture,
}
for label,ok in checks.items():
    if not ok: raise SystemExit("01029 FAIL: "+label)
print("01029 DX11 full-game SM3 16 stream IA / Draw: PASS_STATIC")
