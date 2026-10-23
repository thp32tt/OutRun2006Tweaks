#!/usr/bin/env python3
"""R192 exactly one scoped source/negative-mutant and WARP integration contract."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
h=(root/"src/vr/d3d11/native_indexed_ps_constant.hpp").read_text(encoding="utf-8")
p=(root/"tools/dx11_ps_constant_indexed_probe_r192.cpp").read_text(encoding="utf-8")
m=(root/"cmake.toml").read_text(encoding="utf-8")
w=(root/".github/workflows/backend-conversion-gate.yml").read_text(encoding="utf-8")
guards=(
    "desc.Usage == D3D11_USAGE_IMMUTABLE",
    "context->GetType() != D3D11_DEVICE_CONTEXT_IMMEDIATE",
    "generation != generation_ || version != version_",
    "live.Get() == buffer_.Get()",
    "psColor.binding_exact(context, generation, psVersion)",
    "verified_indexed_vs_transform_draw_ready(",
)
def contract(src): return all(g in src for g in guards)
assert contract(h),"R192 incomplete native immutable PS b0 ownership"
for guard in guards[:4]:
    assert not contract(h.replace(guard,"")),"R192 negative mutant survived: "+guard
assert "->DrawIndexed(" not in h and "->Draw(" not in h,"no gameplay draw activation"
for phrase in (
    "ctx->PSSetConstantBuffers(0,1,&nullBuffer)",
    "reject equal-bytes different PS GPU buffer identity",
    "reject wrong PS source version",
    "reject stale bound red GPU color buffer",
    "reject retired PS color version",
    "ctx->DrawIndexed(3,0,0);",
    "actual WARP indexed PS b0 red center / black corner",
    "actual WARP indexed PS b0 blue center / black corner",
    "reject shutdown PS color owner",
):
    assert phrase in p,"R192 missing GPU evidence: "+phrase
assert "[target.dx11_ps_constant_indexed_probe_r192]" in m
assert '"tools/dx11_ps_constant_indexed_probe_r192.cpp"' in m
assert "python tools/test_dx11_ps_constant_indexed_r192.py" in w
assert w.index("Run R192 PS constant indexed WARP probe") < w.index("Build DX11 constant buffer probe")
print("R192 immutable PS b0 / 4 mutants / real red-to-blue DrawIndexed: PASS")
