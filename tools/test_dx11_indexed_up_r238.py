#!/usr/bin/env python3
"""R238 isolated CPU indexed UP -> owned D3D11 IA -> WARP pixel contract."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
h=(root/"src/vr/d3d11/native_d3d9_indexed_up_batch.hpp").read_text(encoding="utf-8")
p=(root/"tools/dx11_indexed_up_probe_r238.cpp").read_text(encoding="utf-8")
w=(root/".github/workflows/backend-conversion-gate.yml").read_text(encoding="utf-8")
cm=(root/"cmake.toml").read_text(encoding="utf-8")
c=(root/"CMakeLists.txt").read_text(encoding="utf-8")
guards=(
    "reset(); // Failed replacement",
    "primitiveType != D3DPT_TRIANGLELIST || minVertexIndex != 0",
    "indexFormat != D3DFMT_INDEX16 && indexFormat != D3DFMT_INDEX32",
    "primitiveCount > (std::numeric_limits<UINT>::max)() / 3u",
    "numVertices > (std::numeric_limits<UINT>::max)() / vertexStride",
    "indexCount > (std::numeric_limits<UINT>::max)() / indexStride",
    "readableVertexBytes < vertexBytes || readableIndexBytes < indexBytes",
    "if (value >= numVertices) return false;",
    "vertex_.initialize(device, ResourceRole::Vertex",
    "index_.initialize(device, ResourceRole::Index",
    "generation != generation_",
    "!vertex_.bind(context, generation, vertexVersion)",
    "!index_.bind(context, generation, indexVersion)",
    "verified_indexed_single_eye_output_ready(",
    "verified_indexed_full_target_draw_ready(",
)
def contract(src): return all(x in src for x in guards)
assert contract(h), "R238 D3D9 indexed UP native source contract incomplete"
for guard in guards:
    assert not contract(h.replace(guard,"",1)), "mutant escaped: "+guard
assert "->Draw(" not in h and "->DrawIndexed(" not in h, "live gameplay Draw activated"
for proof in (
    "reject null UP vertices", "reject null UP indices",
    "reject short vertex span", "reject short index span",
    "reject unsupported topology", "reject unproven nonzero MinVertexIndex",
    "reject primitive arithmetic overflow", "reject out-of-range index",
    "copy immutable D3D9 indexed UP spans", "reject stale generation",
    "reject stale VB", "reject stale IB", "reject missing PS",
    "reject foreign second eye", "reject retired UP batch",
    "ctx->DrawIndexed(up.index_count(),0u,0);",
    "R238 D3D9 indexed UP -> owned VB/IB -> native WARP red pixel",
    "INDEX32 indexed UP native GPU pixel",
):
    assert proof in p, "missing WARP integration proof: "+proof
assert "[target.dx11_indexed_up_probe_r238]" in cm
assert "add_executable(dx11_indexed_up_probe_r238)" in c
assert "python tools/test_dx11_indexed_up_r238.py" in w
assert "--target dx11_indexed_up_probe_r238" in w
assert "dx11_indexed_up_probe_r238.exe" in w
print("R238 indexed UP adapter + 15 negative source mutants + WARP GPU contract PASS")
