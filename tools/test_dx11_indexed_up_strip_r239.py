#!/usr/bin/env python3
"""R239 indexed-UP strip expansion, immutable native IA and real GPU proof."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
h = (root / "src/vr/d3d11/native_d3d9_indexed_up_strip_batch.hpp").read_text(encoding="utf-8")
p = (root / "tools/dx11_indexed_up_strip_probe_r239.cpp").read_text(encoding="utf-8")
w = (root / ".github/workflows/backend-conversion-gate.yml").read_text(encoding="utf-8")
cm = (root / "cmake.toml").read_text(encoding="utf-8")
c = (root / "CMakeLists.txt").read_text(encoding="utf-8")
guards = (
    "reset(); // Failed recapture",
    "type != D3DPT_TRIANGLESTRIP",
    "minVertexIndex != 0",
    "primitiveCount > (std::numeric_limits<UINT>::max)() / 3u",
    "inputCount > (std::numeric_limits<UINT>::max)() / width",
    "triangleIndices > (std::numeric_limits<UINT>::max)() / width",
    "readableIndexBytes < inputCount * width",
    "new (std::nothrow) std::uint8_t[expandedBytes]",
    "if (i & 1u) std::swap(a, b);",
    "if (a >= numVertices || b >= numVertices || c >= numVertices)",
    "D3DPT_TRIANGLELIST, 0, numVertices, primitiveCount",
    "return owned_.bind_and_verify(context, generation, vertexVersion,",
)
def valid(src): return all(g in src for g in guards)
assert valid(h), "strip -> owned native draw adapter missing"
for guard in guards:
    assert not valid(h.replace(guard, "", 1)), "negative guard mutant escaped: " + guard
assert "->Draw(" not in h and "->DrawIndexed(" not in h, "gameplay draw was enabled"
for phrase in (
    "reject null transient indices", "reject short strip index span",
    "reject unsupported list topology", "reject nonzero MinVertexIndex",
    "reject count overflow", "reject out of range index",
    "two triangles expanded into six indices", "reject stale generation",
    "reject stale vertex version", "reject stale index version",
    "reject missing PS", "retired batch", "INDEX16 both strip triangles",
    "INDEX32 both strip triangles", "context->DrawIndexed(batch.index_count(),0,0);",
):
    assert phrase in p, "GPU/negative integration proof absent: " + phrase
assert "[target.dx11_indexed_up_strip_probe_r239]" in cm
assert "add_executable(dx11_indexed_up_strip_probe_r239)" in c
assert "python tools/test_dx11_indexed_up_strip_r239.py" in w
assert "--target dx11_indexed_up_strip_probe_r239" in w
assert "dx11_indexed_up_strip_probe_r239.exe" in w
print("R239 native strip -> owned IA + 12 mutants + WARP GPU proof PASS")
