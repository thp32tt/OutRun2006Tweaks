#!/usr/bin/env python3
"""00647: R30 real-game fragmented VB shadow sparse fallback, no invalid-index promotion."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
def read(p):
    return (root / p).read_text(encoding="utf-8")
span = read("src/vr/d3d11/live_game_primitive_span.hpp")
probe = read("tools/dx11_game_primitive_span_probe.cpp")
assert "constexpr bool game_sparse_shadow_retry_eligible(" in span
assert "return physicalIndicesValid && denseVertexCount == 0u;" in span
assert "static_assert(game_sparse_shadow_retry_eligible(true, 0u));" in probe
assert "static_assert(!game_sparse_shadow_retry_eligible(false, 0u));" in probe
assert "static_assert(!game_sparse_shadow_retry_eligible(true, 3u));" in probe
for path in ("src/vr/d3d9/stereo_renderer_r30.cpp",
             "src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp"):
    src = read(path)
    assert src.count("live::game_sparse_shadow_retry_eligible(") == 1, path
    block = src.split("void R30ObserveNativeIndexedVB(", 1)[1].split(
        "void R30ObserveNativeIndexedUP(", 1)[0]
    assert "const bool validPhysicalIndices = ok && high >= low;" in block
    assert "if (validPhysicalIndices && high-low+1u <= live::kMaxNativeGameVertices)" in block
    assert "R30CopyVertexShadow(vb, static_cast<UINT>(first)," in block
    assert "if (live::game_sparse_shadow_retry_eligible(" in block
    assert "validPhysicalIndices, nativeVertexCount)" in block
    assert "live::game_compact_sparse_indices(" in block
    assert "R30CopySparseVertexShadow(" in block
    assert "indices.swap(compact)" in block
    assert "else if (!validPhysicalIndices) ok = false;" in block
    assert block.index("R30CopyVertexShadow(vb, static_cast<UINT>(first),") < block.index(
        "if (live::game_sparse_shadow_retry_eligible(") < block.index(
        "R30CopySparseVertexShadow(")
    assert "if (ok) live::observe_indexed(device, topology, primitiveCount," in block
print("00647 fragmented VB shadow -> sparse native DrawIndexed fallback PASS")
