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
    # Both the pre-bind and live IA verification generation fences are required.
    # A mutant that drops either one must fail, not inherit the other check.
    return a.count("currentGeneration != generation_") == 2 and all(s in a for s in ("context->GetType() != D3D11_DEVICE_CONTEXT_IMMEDIATE",
        "buffer_->GetDevice(", "desc.Usage == D3D11_USAGE_DEFAULT",
        "currentGeneration != generation_", "currentSnapshotVersion != source_version_",
        "context->IAGetVertexBuffers(", "context->IAGetIndexBuffer(")) and all(
        s in b for s in ("CreateDeferredContext(","ResourceRole::Vertex",
        "ResourceRole::Index","ctx->DrawIndexed(3,0,0)",
        "ctx->CopyResource(staging.Get(),color.Get())",
        "center[0]==255","corner[0]==0","ib.shutdown()"))
assert valid(h,p) and h.count("currentGeneration != generation_") == 2, (
    "R183 both generation checks and real WARP GPU proof required")
for a,b in (
    ("currentGeneration != generation_","false"),
    ("context->GetType() != D3D11_DEVICE_CONTEXT_IMMEDIATE","false"),
    ("ctx->DrawIndexed(3,0,0)","/* missing draw */"),
):
    mutant_h=h.replace(a,b,1)
    mutant_p=p.replace(a,b,1)
    assert (mutant_h!=h or mutant_p!=p) and not valid(mutant_h,mutant_p),a

# R233: real IA binding clears all unowned streams; later live mutation
# cannot masquerade as a single-stream snapshot. Getters AddRef buffers.
single_stream_guards = (
    "ID3D11Buffer* nullStreams[D3D11_IA_VERTEX_INPUT_RESOURCE_SLOT_COUNT - 1]{};",
    "nullStreams, zeroStrides, zeroOffsets);",
    "ID3D11Buffer* extraStreams[D3D11_IA_VERTEX_INPUT_RESOURCE_SLOT_COUNT - 1]{};",
    "extraStreams, extraStrides, extraOffsets);",
    "for (auto* stream : extraStreams)",
    "soleOwnedStream = false;",
    "stream->Release();",
    "soleOwnedStream;",
)
def r233_intact(code):
    return all(token in code for token in single_stream_guards)
assert r233_intact(h), "R233 IA stream 1..31 clear/live-check/COM cleanup missing"
for token in single_stream_guards:
    negative = h.replace(token, "/* intentionally removed */", 1)
    assert negative != h and not r233_intact(negative), (
        "R233 negative mutation survived: " + token)

assert "[target.dx11_linear_buffer_mirror_probe]" in cm
assert "add_executable(dx11_linear_buffer_mirror_probe)" in generated
assert gate.index("Run DX11 linear VB/IB mirror R183 WARP probe") < gate.index("Build DX11 constant buffer probe")
assert "python tools/test_dx11_linear_buffer_owner_r183.py" in gate
print("R183 single source contract, 3 negative mutants, Win32 WARP wiring: PASS")
