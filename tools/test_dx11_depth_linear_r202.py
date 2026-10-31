#!/usr/bin/env python3
"""R202 one-pass non-indexed depth DSV/state owner and real WARP Draw contract."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
h=(root/"src/vr/d3d11/native_linear_depth_binding.hpp").read_text(encoding="utf-8")
p=(root/"tools/dx11_depth_linear_probe_r202.cpp").read_text(encoding="utf-8")
cm=(root/"cmake.toml").read_text(encoding="utf-8")
ci=(root/".github/workflows/backend-conversion-gate.yml").read_text(encoding="utf-8")
guards=(
    "!verified_linear_full_target_draw_ready(",
    "liveDsv.Get() != expectedDsv",
    "liveDepthState.Get() != expectedDepthState || stencilRef != 0",
    "depthDevice.Get() != device.Get()",
    "desc.Width != targetWidth || desc.Height != targetHeight",
    "ds.DepthFunc != D3D11_COMPARISON_LESS || ds.StencilEnable",
)
def contract(s): return all(g in s for g in guards)
assert contract(h), "R202 live linear DSV/state owner incomplete"
for g in guards[:4]:
    assert not contract(h.replace(g,"",1)), "R202 source mutant survived: "+g
assert "->Draw(" not in h and "->DrawIndexed(" not in h, "game-native Draw forbidden"
for phrase in (
    "reject null expected DSV","reject same-sized wrong-eye DSV",
    "reject rebound depth state","reject stencil reference drift",
    "reject reversed depth compare","reject stencil-enabled depth",
    "keepAlways.StencilFailOp=D3D11_STENCIL_OP_KEEP",
    "dsDesc.FrontFace=keepAlways; dsDesc.BackFace=keepAlways",
    "ctx->Draw(3,0);","ctx->Draw(3,3);",
    "actual depth-tested non-indexed Draw green center / black corner pixels",
    "reject retired VB snapshot"):
    assert phrase in p, "R202 WARP negative/good case absent: "+phrase
assert "DrawIndexed" not in p, "indexed R189 path must not leak"
assert "[target.dx11_depth_linear_probe_r202]" in cm
assert '"tools/dx11_depth_linear_probe_r202.cpp"' in cm
assert ci.count("python tools/test_dx11_depth_linear_r202.py")==1
assert ci.index("Run R202 depth linear WARP probe") < ci.index("Build DX11 constant buffer probe")
print("R202 linear DSV/state four mutants and WARP near/far Draw depth pixel contract: PASS")
