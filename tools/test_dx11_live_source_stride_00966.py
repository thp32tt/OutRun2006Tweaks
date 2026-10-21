#!/usr/bin/env python3
"""Real-game small-stride native source interception structural regression.
This proves no game/HMD pixels; original D3D9 fallback remains authoritative.
"""
from pathlib import Path
r = Path(__file__).resolve().parents[1]
hook = (r / "src/vr/d3d9/stereo_renderer_r30.cpp").read_text()
bridge = (r / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
header = (r / "src/vr/d3d11/live_game_source_stride.hpp").read_text()
assert "stride >= 4u && stride <= 512u" in header
assert hook.count("game_native_source_stride_valid(stride)") == 5
assert "stride < 16 || stride > 512" not in hook
assert "R30CopyVertexShadow(" in hook and "R30CopySparseVertexShadow(" in hook
assert "R30CaptureNativeAdditionalStreams(" in hook
# A game-created IndexedUP index pointer must be bounded before any read.
assert hook.count("game_indexed_up_index_source_range(") == 1
indexed = hook.split("void R30ObserveNativeIndexedUP(", 1)[1].split(
    "// Preserve game-absolute D3D9 slot identities", 1)[0]
assert indexed.index("game_indexed_up_index_source_range(") < indexed.index(
    "std::memcpy(&shortIndex")
assert "format == D3DFMT_INDEX16 ? 2u : 4u" in indexed
assert "game_indexed_up_index_source_range(" in (
    r / "src/vr/d3d11/live_game_primitive_span.hpp").read_text()
assert "game_indexed_up_dense_source_range(" in hook
assert "reinterpret_cast<const std::uint8_t*>(firstAddress)" in hook
assert "game_indexed_up_dense_source_range(" in (
    r / "src/vr/d3d11/live_game_primitive_span.hpp").read_text()
assert "observe_linear(device,topology,primitiveCount," in hook
assert "observe_indexed(device,topology,primitiveCount," in hook
layout = bridge.split("bool live_sm3_input_layout(", 1)[1].split(
    "bool live_sm3_shader_bytes(", 1)[0]
assert "!game_native_source_stride_valid(stride)" in layout
assert "static_cast<UINT>(in.Offset) + width > sourceStride" in layout
assert "in.Stream >= 4u" in layout
assert "if (!extra || !extra->extra[in.Stream-1u].bytes) return false;" in layout
draw = bridge.split("bool submit_live_sm3_game_draw(", 1)[1].split(
    "// Reuse geometric growth buffers", 1)[0]
assert "!game_native_source_stride_valid(stride)" in draw
assert "capture_live_sm3_sampler(" in draw and "context->DrawIndexed(" in draw
assert "context->Draw(" in draw and "liveBatch.record_source_draw(sourceOrdinal)" in draw
assert "s.frameBatch.abort();" in draw
assert "if (StereoWanted()) return;" in hook
print("PASS: genuine small-stride D3D9 source capture uses strict native IA/Draw; hardware UNTESTED")
