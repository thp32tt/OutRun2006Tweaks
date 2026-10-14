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
                  "if (!sparseWindow) unpacked[i] -= minVertex;",
                  "firstVertex, stride, numVertices, unpacked.data(), count"):
        assert token in up, (path, token)
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
assert "++s.sourceDrawsThisFrame;" in missing
assert "s.frameBatch.abort();" in missing
broken = missing.replace("++s.sourceDrawsThisFrame;", "", 1)
assert broken != missing and "++s.sourceDrawsThisFrame;" not in broken
print("00646 sparse indexed VB shadow -> game native DrawIndexed PASS")
