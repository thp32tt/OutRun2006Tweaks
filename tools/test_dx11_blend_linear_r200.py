#!/usr/bin/env python3
"""R200 one-shot independent linear native alpha-blend source contract."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
h=(root/"src/vr/d3d11/native_linear_blend_binding.hpp").read_text(encoding="utf-8")
p=(root/"tools/dx11_blend_linear_probe_r200.cpp").read_text(encoding="utf-8")
cm=(root/"cmake.toml").read_text(encoding="utf-8")
ci=(root/".github/workflows/backend-conversion-gate.yml").read_text(encoding="utf-8")
guards=(
    "!verified_linear_full_target_draw_ready(",
    "liveBlend.Get() != expectedBlendState",
    "mask != D3D11_DEFAULT_SAMPLE_MASK",
    "blendDevice.Get() != device.Get()",
    "rt.RenderTargetWriteMask != D3D11_COLOR_WRITE_ENABLE_ALL",
    "rt.SrcBlend != D3D11_BLEND_SRC_ALPHA",
)
def contract(s): return all(x in s for x in guards)
assert contract(h), "R200 non-indexed alpha OM owner incomplete"
for x in guards[1:5]:
    assert not contract(h.replace(x,"",1)), "R200 source mutant survived: "+x
assert "->Draw(" not in h and "->DrawIndexed(" not in h, "production Draw activation forbidden"
for x in ("verified_linear_blend_draw_ready(vb,ctx.Get(),0,3,gen,ver,",
    "reject rebound opaque state", "reject disabled write mask",
    "reject stale blend factors", "reject zero sample mask",
    "ctx->Draw(3,0);", "actual alpha blended Draw purple center",
    "actual wrong live blend changes purple to red",
    "actual restored blend recovers purple", "reject retired linear VB owner"):
    assert x in p, "missing real WARP case: "+x
assert "[target.dx11_blend_linear_probe_r200]" in cm
assert '"tools/dx11_blend_linear_probe_r200.cpp"' in cm
assert ci.count("python tools/test_dx11_blend_linear_r200.py")==1
assert ci.index("Run R200 blend linear WARP probe") < ci.index("Build DX11 constant buffer probe")
print("R200 linear OM owned alpha, four mutants and actual purple/red/restore WARP pixels: PASS")
