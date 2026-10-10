#!/usr/bin/env python3
"""R215: one-shot mutation guard for composed full-eye/RS/opaque ownership."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
source = (root / "src/vr/d3d11/native_linear_target_viewport.hpp").read_text(encoding="utf-8")
probe = (root / "tools/dx11_linear_buffer_mirror_probe.cpp").read_text(encoding="utf-8")
workflow = (root / ".github/workflows/backend-conversion-gate.yml").read_text(encoding="utf-8")
assert source.count("// R215: compose the previously independent") == 1
r215 = source.split("// R215: compose the previously independent", 1)[1]
guards = (
    "verified_linear_sealed_opaque_eye_draw_ready(",
    "!context || !expectedRaster ||",
    "!verified_linear_full_target_draw_ready(",
    "!verified_linear_opaque_single_eye_draw_ready(",
    "liveRaster.Get() != expectedRaster",
    "rasterDevice.Get() != liveDevice.Get()",
    "depthView.ViewDimension != D3D11_DSV_DIMENSION_TEXTURE2D",
    "depthView.Texture2D.MipSlice != 0",
    "depthDesc.Width != width || depthDesc.Height != height",
    "depthDesc.MipLevels != 1 || depthDesc.ArraySize != 1",
    "depthDesc.SampleDesc.Count != 1",
    "depthDesc.BindFlags & D3D11_BIND_DEPTH_STENCIL",
    "desc.CullMode == D3D11_CULL_NONE",
    "!desc.ScissorEnable && desc.DepthClipEnable",
)
def passes(text): return all(g in text for g in guards)
assert passes(r215), "R215 composite readiness guards missing"
for guard in guards:
    assert not passes(r215.replace(guard, "", 1)), "R215 mutation escaped: " + guard
assert "->Draw(" not in source and "->DrawIndexed(" not in source, "gameplay native Draw forbidden"
for phrase in (
    "R215 sealed opaque eye initial readiness",
    "R215 R214 admits retained half viewport",
    "R215 reject half-eye viewport",
    "R215 real WARP half-viewport suppresses center pixel",
    "R215 full-eye viewport restored",
    "R215 R214 admits foreign raster",
    "R215 reject foreign raster owner",
    "R215 exact raster object restored",
    "R215 real WARP restores full-eye red pixel",
    "R215 R214 admits nonbase depth mip view",
    "R215 reject nonbase depth mip view",
    "R215 real WARP nonbase depth mip renders red",
    "R215 original depth eye recovered",
):
    assert phrase in probe, "missing R215 real WARP negative/restore evidence: " + phrase
step = "python tools/test_dx11_sealed_opaque_eye_r215.py"
assert workflow.count(step) == 1, "R215 must run exactly once in full conversion Gate"
assert workflow.index(step) < workflow.index("Build DX11 linear VB/IB mirror R183 WARP probe")
print("R215 sealed opaque eye: PASS; fourteen guard mutants and real WARP probes wired")
