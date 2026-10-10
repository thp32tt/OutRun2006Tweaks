#!/usr/bin/env python3
"""R187/R204/R205 single-pass contract with targeted negative source mutations."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
h=(root/"src/vr/d3d11/native_indexed_target_viewport.hpp").read_text(encoding="utf-8")
p=(root/"tools/dx11_viewport_draw_probe_r187.cpp").read_text(encoding="utf-8")
manifest=(root/"cmake.toml").read_text(encoding="utf-8")
workflow=(root/".github/workflows/backend-conversion-gate.yml").read_text(encoding="utf-8")
guards=(
    "!verified_indexed_linear_draw_ready(",
    "view.ViewDimension != D3D11_RTV_DIMENSION_TEXTURE2D",
    "desc.Width != width || desc.Height != height",
    "context->RSGetViewports(&boundCount, nullptr)",
    "boundCount != 1",
    "rasterDesc.ScissorEnable",
    "target.Get() != expectedTarget",
    "!expectedTarget",
    "Microsoft::WRL::ComPtr<ID3D11DepthStencilView> unownedDepth;",
    "outputs, unownedDepth.GetAddressOf());",
    "if (unownedDepth.Get() != expectedDepthTarget || hasExtraOutput ||",
    "outputs[slot]->Release();",
    "ID3D11DepthStencilView* expectedDepthTarget = nullptr",
)
# R218 adds an independent raster contract in this header; mutation checks
# must scope to the original R187/R204/R205 helper, never a later helper.
r187 = h.split("// R218: composed indexed full-eye D32 readiness:", 1)[0]
def contract(text): return all(g in text for g in guards)
assert contract(r187), "missing native indexed viewport/target protection"
for g in (guards[0],guards[2],guards[5],guards[6],guards[7],guards[8],guards[9],guards[10],guards[11],guards[12]):
    assert not contract(r187.replace(g,"",1)), "source mutation survived: "+g
assert "->Draw(" not in h and "->DrawIndexed(" not in h, "game Draw activation prohibited"
for phrase in ("ctx->DrawIndexed(3,0,0);", "reject missing viewport",
    "reject extra viewport", "reject half viewport", "reject scissor enabled",
    "reject wrong target width", "reject wrong view format",
    "reject missing bound RTV", "reject retired IB",
    "reject null expected RTV", "reject same-sized different RTV",
    "restore original owned RTV",
    "reject stale second-eye indexed RTV",
    "restore sole indexed RTV after MRT",
    "reject unowned indexed DSV",
    "restore no-depth indexed owner after DSV",
    "actual DrawIndexed green center / black corner pixels"):
    assert phrase in p, "missing WARP behavior coverage: "+phrase
assert "[target.dx11_viewport_draw_probe_r187]" in manifest
assert '"tools/dx11_viewport_draw_probe_r187.cpp"' in manifest
assert "python tools/test_dx11_viewport_draw_r187.py" in workflow
assert workflow.index("Run R187 indexed viewport WARP probe") < workflow.index("Build DX11 constant buffer probe")
print("R187/R204/R205 indexed viewport, sole RTV/no foreign DSV, 10 source mutations and WARP contract: PASS")
