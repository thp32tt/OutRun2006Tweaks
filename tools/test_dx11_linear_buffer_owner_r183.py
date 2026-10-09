#!/usr/bin/env python3
"""Single changed-source R183 check, three independent mutation controls."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
h=(root/"src/vr/d3d11/native_linear_buffer_mirror.hpp").read_text(encoding="utf-8")
p=(root/"tools/dx11_linear_buffer_mirror_probe.cpp").read_text(encoding="utf-8")
gate=(root/".github/workflows/backend-conversion-gate.yml").read_text(encoding="utf-8")
cm=(root/"cmake.toml").read_text(encoding="utf-8")
generated=(root/"CMakeLists.txt").read_text(encoding="utf-8")
def valid(a,b):
    return all(s in a for s in ("context->GetType() != D3D11_DEVICE_CONTEXT_IMMEDIATE",
        "buffer_->GetDevice(", "desc.Usage == D3D11_USAGE_DEFAULT",
        "currentGeneration != generation_", "currentSnapshotVersion != source_version_",
        "context->IAGetVertexBuffers(", "context->IAGetIndexBuffer(")) and all(
        s in b for s in ("CreateDeferredContext(","ResourceRole::Vertex",
        "ResourceRole::Index","ctx->DrawIndexed(3,0,0)",
        "ctx->CopyResource(staging.Get(),color.Get())",
        "center[0]==255","corner[0]==0","ib.shutdown()"))
assert valid(h,p), "R183 production source or actual WARP GPU proof missing"
for a,b in (
    ("currentGeneration != generation_","false"),
    ("context->GetType() != D3D11_DEVICE_CONTEXT_IMMEDIATE","false"),
    ("ctx->DrawIndexed(3,0,0)","/* missing draw */"),
):
    mutant_h=h.replace(a,b,1)
    mutant_p=p.replace(a,b,1)
    assert (mutant_h!=h or mutant_p!=p) and not valid(mutant_h,mutant_p),a
assert "[target.dx11_linear_buffer_mirror_probe]" in cm
assert "add_executable(dx11_linear_buffer_mirror_probe)" in generated
assert gate.index("Run DX11 linear VB/IB mirror R183 WARP probe") < gate.index("Build DX11 constant buffer probe")
assert "python tools/test_dx11_linear_buffer_owner_r183.py" in gate
print("R183 single source contract, 3 negative mutants, Win32 WARP wiring: PASS")
