#!/usr/bin/env python3
"""R189 one-pass source/depth WARP contract and four negative mutations."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
h=(root/"src/vr/d3d11/native_indexed_depth_binding.hpp").read_text(encoding="utf-8")
p=(root/"tools/dx11_depth_indexed_probe_r189.cpp").read_text(encoding="utf-8")
manifest=(root/"cmake.toml").read_text(encoding="utf-8")
workflow=(root/".github/workflows/backend-conversion-gate.yml").read_text(encoding="utf-8")
guards=(
    "!verified_indexed_full_target_draw_ready(",
    "liveDsv.Get() != expectedDsv",
    "liveDepthState.Get() != expectedDepthState || stencilRef != 0",
    "depthDevice.Get() != device.Get()",
    "desc.Width != targetWidth || desc.Height != targetHeight",
    "ds.DepthFunc != D3D11_COMPARISON_LESS || ds.StencilEnable",
)
def contract(s): return all(g in s for g in guards)
assert contract(h), "R189 DSV/depth guard missing"
for g in (guards[0],guards[1],guards[2],guards[4]):
    assert not contract(h.replace(g,"",1)), "R189 negative mutation survived: "+g
assert "->Draw(" not in h and "->DrawIndexed(" not in h, "game draw activated"
for term in ("reject null expected DSV","reject same-sized wrong-eye DSV",
             "reject rebound depth state","reject stencil reference drift",
             "reject reversed depth compare","reject stencil-enabled depth",
             "ctx->DrawIndexed(3,0,0);", "ctx->DrawIndexed(3,3,0);",
             "actual depth-tested DrawIndexed green center / black corner pixels"):
    assert term in p, "missing R189 behavioral coverage: "+term
assert "[target.dx11_depth_indexed_probe_r189]" in manifest
assert '"tools/dx11_depth_indexed_probe_r189.cpp"' in manifest
assert "python tools/test_dx11_depth_indexed_r189.py" in workflow
assert workflow.index("Run R189 depth indexed WARP probe") < workflow.index("Build DX11 constant buffer probe")
print("R189 exact DSV/state, four mutants, WARP depth DrawIndexed contract PASS")
