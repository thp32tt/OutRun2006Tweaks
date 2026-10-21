#!/usr/bin/env python3
"""00646: real-game D3D9 sparse indexed-VB shadow -> native DrawIndexed."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
def read(path):
    return (root / path).read_text(encoding="utf-8")
span = read("src/vr/d3d11/live_game_primitive_span.hpp")
bridge = read("src/vr/d3d11/live_game_frame_bridge.cpp")
probe = read("tools/dx11_game_primitive_span_probe.cpp")
assert "game_compact_sparse_indices(" in span
for token in ("std::sort(sorted.begin(), sorted.end())",
              "std::unique(sorted.begin(), sorted.end())",
              "std::lower_bound(", "uniquePhysical.swap(sorted)",
              "compactIndices.swap(remapped)",
              "maxUnique == 0u || maxUnique > kMaxNativeGameVertices"):
    assert token in span, token
# 00737 negative controls: the real transient game IndexedUP source must
# validate all absolute indices before any game-owned UP byte copy, bound each
# referenced pointer, and commit compact buffers only on complete success.
# Scope the destructive oracle to its exact gather helper. The adjacent
# IndexedUP physical-stream function legitimately repeats the same overflow
# guard; mutating only the gather must still fail even with that second guard.
up_capture = span.split("inline bool game_gather_indexed_up_vertices(", 1)[1].split(
    "inline bool game_indexed_up_physical_slots(", 1)[0]
up_safe_tokens = (
    "minVertex > (std::numeric_limits<std::uint32_t>::max)() - numVertices",
    "absoluteIndices[i] < minVertex",
    "absoluteIndices[i] - minVertex >= numVertices",
    "indexCount > kMaxNativeGameVertices",
    "offset > available || stride > available - offset",
    "game_compact_sparse_indices(",
    "packedVertices.swap(vertices);",
    "packedIndices.swap(remapped);",
)
def exact_up_capture(candidate):
    return all(t in candidate for t in up_safe_tokens) and (
        candidate.index("absoluteIndices[i] < minVertex") <
        candidate.index("std::memcpy(vertices.data()")
    ) and (
        candidate.index("offset > available || stride > available - offset") <
        candidate.index("std::memcpy(vertices.data()")
    )
assert exact_up_capture(up_capture)
for token in up_safe_tokens:
    damaged = up_capture.replace(token, "/* invalid indexed UP source */", 1)
    assert damaged != up_capture and not exact_up_capture(damaged), token
assert "game_gather_indexed_up_vertices(" in probe
assert "upPacked == keptUp && upRemapped == keptUpIndices" in probe
assert "game_compact_sparse_indices(distant, 5u, 3u" in probe
assert "game_compact_sparse_indices(distant, 5u, 2u" in probe
assert "kMaxNativeGamePrimitives == 2048u" in probe
assert "kMaxNativeGameVertices == kMaxNativeGamePrimitives * 3u" in probe
assert "game_native_primitive_element_count(kind, kMaxNativeGamePrimitives + 1u, elements)" in probe
assert "game_compact_sparse_indices(distant, kMaxNativeGameVertices + 1u" in probe
assert "fullMesh.data()" in probe
assert "kMaxNativeGameVertices - 1u, uniqueSlots, remapped" in probe
assert "uniqueSlots == fullUnique && remapped == fullRemap" in probe
for path in ("src/vr/d3d9/stereo_renderer_r30.cpp",
             "src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp"):
    source = read(path)
    assert source.count("bool R30CopySparseVertexShadow(") == 1, path
    assert source.count("live::game_compact_sparse_indices(") == 1, path
    if path.endswith("/stereo_renderer_r30.cpp"):
        # Two original indexed uses plus verified secondary-stream gathering.
        assert source.count("R30CopySparseVertexShadow(") == 3, path
        assert "capturedPhysical.swap(uniquePhysical);" in source
        assert "capturedPhysical[i]=static_cast<UINT>(low+i);" in source
        assert "R30CaptureNativeAdditionalStreams(" in source
    else:
        assert source.count("R30CopySparseVertexShadow(") == 2, path
    assert "std::lock_guard<std::mutex> lock(entry->mutex)" in source
    assert "!R30RangeValid(entry->valid, static_cast<UINT>(offset)," in source
    assert "nativeVertexCount = static_cast<UINT>(uniquePhysical.size())" in source
    assert "indices.swap(compact)" in source
    assert "high-low+1u <= live::kMaxNativeGameVertices" in source
    assert "physical.size() >" in source
    assert "outrun::vr::dx11::live_game_frame::kMaxNativeGameVertices" in source
    assert "live::kMaxNativeGameVertices, uniquePhysical, compact)" in source
    assert "physical.size() > 128u" not in source
    assert "indices.data(), count, 128u" not in source
    # 00737: actual R30 IndexedUP branch must forward the owned, sparse
    # vertex/index snapshot to the native DrawIndexed observer.
    up = source.split("void R30ObserveNativeIndexedUP(", 1)[1].split(
        "HRESULT __stdcall DrawPrimitiveDestR30(", 1)[0]
    for token in ("const bool sparseWindow =",
                  "numVertices > live::kMaxNativeGameVertices",
                  "live::game_gather_indexed_up_vertices(",
                  "compactVertices.data()", "compactIndices.data()",
                  "firstVertex, stride, numVertices, unpacked.data(), count"):
        assert token in up, (path, token)
    if path.endswith("/stereo_renderer_r30.cpp"):
        # Real IndexedUP stream 0 is rebased for native IA, while secondary
        # stream snapshots MUST retain the game-absolute physical vertex IDs.
        for token in (
                "std::vector<std::uint32_t> rebasedIndices = unpacked;",
                "for (auto& index : rebasedIndices) index -= minVertex;",
                "live::game_indexed_up_physical_slots(",
                "R30CaptureNativeAdditionalStreams(",
                "rebasedIndices.data(), count, &extra"):
            assert token in up, (path, token)
        assert "unpacked[i] -= minVertex;" not in up
        indexed = source.split("void R30ObserveNativeIndexedVB(", 1)[1].split(
            "void R30ObserveNativeIndexedUP(", 1)[0]
        capture = indexed.find("R30CaptureNativeAdditionalStreams(")
        forward = indexed.find("if (ok) nativeSource.forwarded = true;", capture)
        native_draw = indexed.find("live::observe_indexed(", forward)
        assert capture >= 0 and forward > capture and native_draw > forward
        assert "vertices.data(),stride,nativeVertexCount," in indexed
        assert "indices.data(),count,&extra);" in indexed
    else:
        # R26-safe has no physical secondary IA remap; retain original
        # explicitly rebased stream-0 legacy behavior.
        assert "if (!sparseWindow) unpacked[i] -= minVertex;" in up
        assert "if (ok) live::observe_indexed(device, topology, primitiveCount," in source
        assert "vertices.data(), stride, nativeVertexCount," in source
    assert "const HRESULT xyzrhw = R30TryXyzrhwPrimitiveVB(" in source
assert "if (ib) ctx->DrawIndexed(indexCount, 0, 0);" in bridge
# 00678 counts the source ordinal *before* topology/native admission.
# Rejected game Draws must never silently join a later native scene batch.
assert "if (!diagnostic_enabled() || !game) return;" in bridge
observer = bridge.split("void observe(IDirect3DDevice9* game,", 1)[1].split(
    "void observe_linear(", 1)[0]
source_ordinal = "const std::uint64_t sourceOrdinal = s.sourceDrawsThisFrame++;"
primitive_gate = "if (!game_native_primitive_element_count("
assert source_ordinal in observer and primitive_gate in observer
assert observer.index(source_ordinal) < observer.index(primitive_gate)
assert "s.frameBatch.abort();" in observer[observer.index(primitive_gate):]
removed_ordinal = observer.replace(source_ordinal, "", 1)
assert removed_ordinal != observer and source_ordinal not in removed_ordinal
assert "observe_unavailable_game_draw(IDirect3DDevice9* game)" in bridge
linear = bridge.split("void observe_linear(", 1)[1].split("void observe_indexed(", 1)[0]
assert "if (!game_native_primitive_element_count(" in linear
assert "observe_unavailable_game_draw(game);" in linear
assert linear.index("if (!game_native_primitive_element_count(") < linear.index("observe_unavailable_game_draw(game);")
missing = bridge.split("void observe_unavailable_game_draw(", 1)[1].split(
    "void before_game_present(", 1)[0]
# 00765 preserves the same exact raw-game ordinal, but also passes it
# into the guarded offscreen no-pixel source accounting. Do not demand the
# obsolete preincrement spelling or accidentally allow an uncounted Draw.
assert source_ordinal in missing
assert "s.frameBatch.abort();" in missing
assert missing.index(source_ordinal) < missing.index("if (!observe_source_frame_mode(")
broken = missing.replace(source_ordinal, "", 1)
assert broken != missing and source_ordinal not in broken
print("00646 sparse indexed VB shadow -> game native DrawIndexed PASS")
