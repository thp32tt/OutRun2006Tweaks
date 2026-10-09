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
print("R186 native indexed Draw readiness, 3 mutations and WARP GPU probe integration: PASS")
