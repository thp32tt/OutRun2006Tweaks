#!/usr/bin/env python3
"""R186 one-shot source contract + isolated WARP proof; 3 source mutations."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
h=(root/"src/vr/d3d11/native_indexed_draw_submit.hpp").read_text(encoding="utf-8")
p=(root/"tools/dx11_indexed_draw_probe_r186.cpp").read_text(encoding="utf-8")
w=(root/".github/workflows/backend-conversion-gate.yml").read_text(encoding="utf-8")
c=(root/"CMakeLists.txt").read_text(encoding="utf-8")
guards=(
    "!vertexOwner.indexed_draw_bounds_exact(",
    "indexCount % 3u != 0",
    "topology != D3D11_PRIMITIVE_TOPOLOGY_TRIANGLELIST",
    "if (!layout || !vs || !ps || !rtv)",
    "owner.Get() == device.Get()",
    "!sameDevice(layout.Get()) || !sameDevice(vs.Get())",
    "!sameDevice(ps.Get()) || !sameDevice(rtv.Get())",
)
def contract(src): return all(t in src for t in guards)
assert contract(h), "missing R186 ownership/topology/pipeline guard"
assert "->Draw(" not in h and "->DrawIndexed(" not in h, "production activation forbidden"
for t in (guards[0], guards[1], guards[3]):
    assert not contract(h.replace(t,"",1)), "R186 mutant survived: "+t
for t in ("context->DrawIndexed(3,0,0);",
          "reject stale VB", "reject stale IB", "reject wrong topology",
          "reject missing PS", "reject missing RTV", "reject retired IB owner",
          "actual DrawIndexed green center / black corner pixels"):
    assert t in p, "missing WARP behavior evidence: "+t
manifest=(root/"cmake.toml").read_text(encoding="utf-8")
assert "[target.dx11_indexed_draw_probe_r186]" in manifest
assert '"tools/dx11_indexed_draw_probe_r186.cpp"' in manifest
assert "add_executable(dx11_indexed_draw_probe_r186)" in c
assert "python tools/test_dx11_indexed_draw_r186.py" in w
assert w.index("Verify R186 native indexed Draw ownership") < w.index("Build DX11 constant buffer probe")
assert w.index("Run R186 owned indexed Draw WARP probe") < w.index("Build DX11 constant buffer probe")

# R235 contract (in addition to the R186 behavior/CI contract above).
mirror=(root/"src/vr/d3d11/native_linear_buffer_mirror.hpp").read_text(encoding="utf-8")
m235=mirror.split("// R235: D3D9 DIP",1)[1].split("void shutdown()",1)[0]
i235=h.split("// R235: D3D9 DrawIndexedPrimitive",1)[1].split("// R217:",1)[0]
gm=("d3d9_declared_index_window_exact(","indexCount > index.index_count_ - startIndex",
    "!index.index_range_tree_ || !index.index_range_leaves_",
    "lastVertex >= available","lowest >= minVertexIndex",
    "static_cast<std::uint64_t>(highest) < declaredEnd")
gi=("verified_d3d9_indexed_triangles_ready(",
    "primitiveCount > (std::numeric_limits<UINT>::max)() / 3u",
    "const UINT indexCount = primitiveCount * 3u",
    "vb.d3d9_declared_index_window_exact(",
    "verified_indexed_single_eye_output_ready(")
def r235_contract(m,i): return all(g in m for g in gm) and all(g in i for g in gi)
assert r235_contract(m235,i235), "missing R235 integrated source command"
for guard in gm: assert not r235_contract(m235.replace(guard,"",1),i235), "surviving mirror mutant: "+guard
for guard in gi: assert not r235_contract(m235,i235.replace(guard,"",1)), "surviving submit mutant: "+guard
for marker in ("R235 valid nonzero DIP source command",
    "R235 reject declared minimum excludes index",
    "R235 reject declared maximum excludes index",
    "R235 reject declared VB end overrun",
    "R235 reject primitive overflow",
    "context->DrawIndexed(3u,3u,3);",
    "R235 nonzero StartIndex/BaseVertex WARP green pixel",
    "R235 reject retired IB"):
    assert marker in p, "missing R235 WARP integration proof: "+marker
assert "->DrawIndexed(" not in h, "R235 native game Draw must remain dormant"
print("R186 native indexed Draw readiness, 3 mutations and WARP GPU probe integration: PASS")
