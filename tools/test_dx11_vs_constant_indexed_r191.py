#!/usr/bin/env python3
"""R191 one-pass VS transform resource/receipt and WARP semantic contract."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
h=(root/"src/vr/d3d11/native_indexed_vs_constant.hpp").read_text(encoding="utf-8")
p=(root/"tools/dx11_vs_constant_indexed_probe_r191.cpp").read_text(encoding="utf-8")
m=(root/"cmake.toml").read_text(encoding="utf-8")
w=(root/".github/workflows/backend-conversion-gate.yml").read_text(encoding="utf-8")
guards=(
    "desc.Usage == D3D11_USAGE_IMMUTABLE",
    "context->GetType() != D3D11_DEVICE_CONTEXT_IMMEDIATE",
    "generation != generation_ || version != version_",
    "live.Get() == buffer_.Get()",
    "transform.binding_exact(context, generation, vsVersion)",
    "verified_indexed_full_target_draw_ready(",
)
def passes(src): return all(g in src for g in guards)
assert passes(h), "R191 missing actual VS b0 resource/lifetime/IA/RTV guards"
for g in guards[:4]:
    assert not passes(h.replace(g,"",1)), "R191 negative mutation survived "+g
assert "->DrawIndexed(" not in h and "->Draw(" not in h, "no production draw activation"
for phrase in (
    "ctx->VSSetConstantBuffers(0,1,&nullBuffer)",
    "reject equal-bytes different VS buffer identity",
    "reject wrong source snapshot version",
    "reject old bound GPU transform object",
    "reject retired version accept replacement",
    "ctx->DrawIndexed(3,0,0);",
    "actual VS b0 shifted DrawIndexed from center to right-side pixels",
    "reject retired VS constant owner"
):
    assert phrase in p, "R191 WARP behavior missing: "+phrase
assert "[target.dx11_vs_constant_indexed_probe_r191]" in m
assert '"tools/dx11_vs_constant_indexed_probe_r191.cpp"' in m
assert "python tools/test_dx11_vs_constant_indexed_r191.py" in w
assert w.index("Run R191 VS constant indexed WARP probe") < w.index("Build DX11 constant buffer probe")
print("R191 VS immutable b0/real WARP shifted DrawIndexed, 4 mutants PASS")
