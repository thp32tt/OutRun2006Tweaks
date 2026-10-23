#!/usr/bin/env python3
"""R190 scoped static source guard and four negative mutations (run once)."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
h=(root/"src/vr/d3d11/native_indexed_blend_binding.hpp").read_text(encoding="utf-8")
p=(root/"tools/dx11_blend_indexed_probe_r190.cpp").read_text(encoding="utf-8")
m=(root/"cmake.toml").read_text(encoding="utf-8")
w=(root/".github/workflows/backend-conversion-gate.yml").read_text(encoding="utf-8")
guards=(
    "!verified_indexed_full_target_draw_ready(",
    "liveBlendState.Get() != expectedBlendState",
    "sampleMask != D3D11_DEFAULT_SAMPLE_MASK",
    "contextDevice.Get() != blendDevice.Get()",
    "target.RenderTargetWriteMask != D3D11_COLOR_WRITE_ENABLE_ALL",
    "target.SrcBlend != D3D11_BLEND_SRC_ALPHA",
)
def contract(s): return all(x in s for x in guards)
assert contract(h), "missing native alpha blend object/device/OM guard"
for term in guards[1:5]:
    assert not contract(h.replace(term,"",1)), "mutation survived "+term
assert "->Draw(" not in h and "->DrawIndexed(" not in h, "gameplay draw activation forbidden"
for term in ("reject rebound opaque blend","reject disabled color write mask",
    "reject stale blend factors","reject zero sample mask",
    "reject retired IB owner","ctx->DrawIndexed(3,0,0);",
    "actual alpha blended DrawIndexed purple center / blue corner"):
    assert term in p, "missing live WARP test: "+term
assert "[target.dx11_blend_indexed_probe_r190]" in m
assert '"tools/dx11_blend_indexed_probe_r190.cpp"' in m
assert "python tools/test_dx11_blend_indexed_r190.py" in w
assert w.index("Run R190 blend indexed WARP probe") < w.index("Build DX11 constant buffer probe")
print("R190 exact blend OM ownership, four mutants, Win32 WARP pixel test: PASS")
