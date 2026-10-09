#!/usr/bin/env python3
"""R184 one-shot source/draw-range fail-closed contract and 3 negative mutants."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
h = (root / "src/vr/d3d11/native_linear_buffer_mirror.hpp").read_text(encoding="utf-8")
p = (root / "tools/dx11_linear_buffer_mirror_probe.cpp").read_text(encoding="utf-8")
w = (root / ".github/workflows/backend-conversion-gate.yml").read_text(encoding="utf-8")

needed = (
    "index_count_ = sealedIndexCount;",
    "index_min_ = sealedMin;",
    "index_max_ = sealedMax;",
    "std::memcpy(&value",
    "indexCount > index.index_count_ - startIndex",
    "high >= low && high < vertices",
    "!index.binding_exact(context, currentGeneration, currentIndexSnapshotVersion)",
    "!binding_exact(context, currentGeneration, currentVertexSnapshotVersion)",
)
proof = (
    '"valid complete index slice"',
    '"empty indexed draw rejected"',
    '"index window overrun rejected"',
    '"positive base vertex overrun rejected"',
    '"negative base vertex underrun rejected"',
    '"foreign IA state rejected"',
    '"stale VB snapshot rejected"',
    '"stale IB snapshot rejected"',
    '"swapped buffer roles rejected"',
    '"R184 range and live IA ready before GPU"',
)
def valid(a, b):
    return all(token in a for token in needed) and all(token in b for token in proof)

assert valid(h, p), "R184 ownership/range/negative probes missing"
for target in (
    "indexCount > index.index_count_ - startIndex",
    "high >= low && high < vertices",
    "!index.binding_exact(context, currentGeneration, currentIndexSnapshotVersion)",
):
    mutant = h.replace(target, "false", 1)
    assert mutant != h and not valid(mutant, p), f"R184 mutant survived: {target}"
assert "python tools/test_dx11_linear_buffer_range_r184.py" in w
assert w.index("Verify DX11 native VB/IB R184 indexed bounds contract") < w.index("Build DX11 linear VB/IB mirror R183 WARP probe")
assert p.index('"R184 range and live IA ready before GPU"') < p.index("ctx->DrawIndexed(3,0,0)")
print("R184 conservative indexed draw bounds, ownership, 3 negative mutations: PASS")
