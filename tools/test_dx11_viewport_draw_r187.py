#!/usr/bin/env python3
"""R187 one-shot static contract and 3 negative source mutations."""
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
)
def contract(text): return all(g in text for g in guards)
assert contract(h), "missing native indexed viewport/target protection"
for g in (guards[0],guards[2],guards[5]):
    assert not contract(h.replace(g,"",1)), "source mutation survived: "+g
assert "->Draw(" not in h and "->DrawIndexed(" not in h, "game Draw activation prohibited"
for phrase in ("ctx->DrawIndexed(3,0,0);", "reject missing viewport",
    "reject extra viewport", "reject half viewport", "reject scissor enabled",
    "reject wrong target width", "reject wrong view format",
    "reject missing bound RTV", "reject retired IB",
    "actual DrawIndexed green center / black corner pixels"):
    assert phrase in p, "missing WARP behavior coverage: "+phrase
assert "[target.dx11_viewport_draw_probe_r187]" in manifest
assert '"tools/dx11_viewport_draw_probe_r187.cpp"' in manifest
assert "python tools/test_dx11_viewport_draw_r187.py" in workflow
assert workflow.index("Run R187 indexed viewport WARP probe") < workflow.index("Build DX11 constant buffer probe")
print("R187 viewport/native target exactness, 3 source mutations and WARP probe contract: PASS")
