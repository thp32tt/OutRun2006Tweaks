#!/usr/bin/env python3
"""R194 source-level cull/face ownership contract; 4 negative mutations once."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
h=(root/"src/vr/d3d11/native_indexed_cull_binding.hpp").read_text(encoding="utf-8")
p=(root/"tools/dx11_cull_indexed_probe_r194.cpp").read_text(encoding="utf-8")
m=(root/"cmake.toml").read_text(encoding="utf-8")
w=(root/".github/workflows/backend-conversion-gate.yml").read_text(encoding="utf-8")
guards=(
    "verified_indexed_full_target_draw_ready(",
    "rasterOwner.Get() != device.Get()",
    "liveRaster.Get() != expectedRaster",
    "raster.CullMode == expectedCull",
    "raster.FrontCounterClockwise == (expectedFrontCCW ? TRUE : FALSE)",
    "!raster.ScissorEnable && raster.DepthClipEnable",
)
def intact(source):
    return all(g in source for g in guards)
assert intact(h),"R194 native cull provenance guard missing"
for g in guards[1:5]:
    assert not intact(h.replace(g,"",1)), "negative mutant unexpectedly passed: "+g
assert "->DrawIndexed(" not in h and "->Draw(" not in h
for phrase in (
    "reject stale winding intent","reject stale bound raster owner",
    "reject stale cull intent","reject cull-none intent",
    "reject stale generation","reject disabled raster cull",
    "WARP winding polarity must flip DrawIndexed pixel visibility",
    "reject retired index snapshot","ctx->DrawIndexed(3,0,0);"):
    assert phrase in p,"missing WARP/negative exercise: "+phrase
assert "[target.dx11_cull_indexed_probe_r194]" in m
assert '"tools/dx11_cull_indexed_probe_r194.cpp"' in m
assert "python tools/test_dx11_cull_indexed_r194.py" in w
assert w.index("Run R194 cull indexed WARP probe") < w.index("Build DX11 constant buffer probe")
print("R194 indexed CullBack front-face source contract + 4 negative mutants: PASS")
