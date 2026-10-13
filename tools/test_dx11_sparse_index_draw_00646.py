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
assert "kMaxNativeGameVertices == 512u * 3u" in probe
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
    assert "high-low+1u <= 1536u" in source
    assert "physical.size() >" in source
    assert "outrun::vr::dx11::live_game_frame::kMaxNativeGameVertices" in source
    assert "live::kMaxNativeGameVertices, uniquePhysical, compact)" in source
    assert "physical.size() > 128u" not in source
    assert "indices.data(), count, 128u" not in source
    assert "if (ok) live::observe_indexed(device, topology, primitiveCount," in source
    assert "vertices.data(), stride, nativeVertexCount," in source
    assert "const HRESULT xyzrhw = R30TryXyzrhwPrimitiveVB(" in source
assert "if (ib) ctx->DrawIndexed(indexCount, 0, 0);" in bridge
assert "if (!diagnostic_enabled() || !game ||" in bridge
print("00646 sparse indexed VB shadow -> game native DrawIndexed PASS")
