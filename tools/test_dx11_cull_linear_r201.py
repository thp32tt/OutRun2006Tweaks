#!/usr/bin/env python3
"""R201 native non-indexed cull/winding: one static source contract & 4 mutants."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
h=(root/"src/vr/d3d11/native_linear_cull_binding.hpp").read_text(encoding="utf-8")
p=(root/"tools/dx11_cull_linear_probe_r201.cpp").read_text(encoding="utf-8")
cm=(root/"cmake.toml").read_text(encoding="utf-8")
ci=(root/".github/workflows/backend-conversion-gate.yml").read_text(encoding="utf-8")
guards=(
    "verified_linear_full_target_draw_ready(",
    "rasterDevice.Get() != device.Get()",
    "liveRaster.Get() != expectedRaster",
    "desc.CullMode == expectedCull",
    "desc.FrontCounterClockwise == (expectedFrontCCW ? TRUE : FALSE)",
    "!desc.ScissorEnable && desc.DepthClipEnable",
)
def contract(s): return all(g in s for g in guards)
assert contract(h), "R201 non-indexed raster owner contract incomplete"
for g in guards[1:5]:
    assert not contract(h.replace(g,"",1)), "negative mutant survived: "+g
assert "->Draw(" not in h and "->DrawIndexed(" not in h,"gameplay native Draw forbidden"
for phrase in ("reject stale front winding intent",
    "reject foreign bound raster state",
    "reject stale cull mode intent",
    "reject cull-none expected mode",
    "reject stale VB generation",
    "reject disabled raster culling",
    "actual non-indexed WARP Draw cull winding must flip GPU pixel",
    "reject retired VB generation owner",
    "ctx->Draw(3,0);"):
    assert phrase in p, "missing R201 WARP proof: "+phrase
assert "[target.dx11_cull_linear_probe_r201]" in cm
assert '"tools/dx11_cull_linear_probe_r201.cpp"' in cm
assert ci.count("python tools/test_dx11_cull_linear_r201.py")==1
assert ci.index("Run R201 cull linear WARP probe") < ci.index("Build DX11 constant buffer probe")
print("R201 exact non-indexed cull/winding owner, 4 mutants and real WARP pixel test: PASS")
