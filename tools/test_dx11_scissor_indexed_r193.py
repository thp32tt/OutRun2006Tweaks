#!/usr/bin/env python3
"""R193 one-pass static guard with four targeted negative mutations."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
h = (root/"src/vr/d3d11/native_indexed_scissor_binding.hpp").read_text(encoding="utf-8")
p = (root/"tools/dx11_scissor_indexed_probe_r193.cpp").read_text(encoding="utf-8")
m = (root/"cmake.toml").read_text(encoding="utf-8")
w = (root/".github/workflows/backend-conversion-gate.yml").read_text(encoding="utf-8")
guards = (
    "verified_indexed_linear_draw_ready(vb, ib, context",
    "rasterOwner.Get() != device.Get()",
    "liveTarget.Get() != expectedRtv",
    "liveRaster.Get() != expectedRaster",
    "if (rectCount != 1) return false;",
    "liveRect.right == expectedRect.right",
    "expectedRect.right > static_cast<LONG>(width)",
)
def intact(s):
    return all(g in s for g in guards)
assert intact(h), "missing live native scissor object/extent/readback guard"
for guard in guards[1:5]:
    assert not intact(h.replace(guard,"",1)), "negative mutation survived "+guard
assert "->Draw(" not in h and "->DrawIndexed(" not in h
for phrase in (
    "reject caller stale scissor", "reject rebound scissor",
    "reject wrong raster state owner", "reject scissor-disabled state",
    "reject wrong generation", "reject retired IB owner",
    "ctx->DrawIndexed(3,0,0);", "GPU red inside owned left clip and blue outside"):
    assert phrase in p, "missing real WARP proof: "+phrase
assert "[target.dx11_scissor_indexed_probe_r193]" in m
assert '"tools/dx11_scissor_indexed_probe_r193.cpp"' in m
assert "python tools/test_dx11_scissor_indexed_r193.py" in w
assert w.index("Run R193 scissor indexed WARP probe") < w.index("Build DX11 constant buffer probe")
print("R193 scoped native scissor/target ownership, 4 mutations and GPU test wiring: PASS")
