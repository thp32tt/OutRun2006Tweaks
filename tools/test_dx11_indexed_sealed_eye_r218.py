#!/usr/bin/env python3
"""R218 single execution: composed indexed full-eye fail-closed mutants and WARP proof."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
src = (root/"src/vr/d3d11/native_indexed_target_viewport.hpp").read_text(encoding="utf-8")
probe = (root/"tools/dx11_indexed_draw_probe_r186.cpp").read_text(encoding="utf-8")
workflow = (root/".github/workflows/backend-conversion-gate.yml").read_text(encoding="utf-8")
r218 = src.split("// R218: composed indexed full-eye D32 readiness:", 1)[1]
guards = (
    "verified_indexed_sealed_opaque_eye_draw_ready(",
    "!context || !expectedDsv || !expectedRaster",
    "!verified_indexed_full_target_draw_ready(",
    "!verified_indexed_opaque_depth_single_eye_ready(",
    "depthView.ViewDimension != D3D11_DSV_DIMENSION_TEXTURE2D",
    "depthView.Texture2D.MipSlice != 0",
    "depthView.Format != DXGI_FORMAT_D32_FLOAT",
    "depthView.Flags != 0",
    "FAILED(depthResource.As(&depthTexture))",
    "depthDesc.Width != width || depthDesc.Height != height",
    "depthDesc.MipLevels != 1 || depthDesc.ArraySize != 1",
    "depthDesc.SampleDesc.Count != 1",
    "depthDesc.Format != DXGI_FORMAT_D32_FLOAT",
    "depthDesc.Usage != D3D11_USAGE_DEFAULT",
    "depthDesc.MiscFlags != 0",
    "depthDesc.BindFlags != D3D11_BIND_DEPTH_STENCIL",
    "liveRaster.Get() != expectedRaster",
    "liveDevice.Get() != rasterDevice.Get()",
    "rasterDesc.CullMode == D3D11_CULL_NONE",
    "!rasterDesc.ScissorEnable && rasterDesc.DepthClipEnable",
)
def passes(s): return all(g in s for g in guards)
assert passes(r218), "R218 production readiness guards missing"
for guard in guards:
    assert not passes(r218.replace(guard, "", 1)), "R218 mutation escaped: "+guard
assert "->Draw(" not in src and "->DrawIndexed(" not in src
for phrase in (
    "R218 initial exact indexed eye", "R218 old guard accepts half viewport",
    "R218 reject cropped viewport", "R218 viewport restored",
    "R218 old guard accepts foreign raster", "R218 reject alien raster",
    "R218 raster restored", "R218 create mip-aliased depth",
    "R218 old guard accepts exact live mip-one DSV",
    "R218 reject mip-aliased DSV", "R218 dedicated depth restored",
    "R218 restored WARP green indexed pixel"
):
    assert phrase in probe, "missing R218 WARP evidence: "+phrase
step = "python tools/test_dx11_indexed_sealed_eye_r218.py"
assert workflow.count(step) == 1
assert workflow.index(step) < workflow.index("Build R186 owned indexed Draw WARP probe")
print("R218/R226 sealed indexed depth-eye: PASS 20 guard mutants, WARP cases wired")
