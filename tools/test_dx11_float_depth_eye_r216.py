#!/usr/bin/env python3
"""R216 focused static mutation test; actual D16/D32 pixels run in Windows WARP."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
source = (root / "src/vr/d3d11/native_linear_target_viewport.hpp").read_text(encoding="utf-8")
probe = (root / "tools/dx11_linear_buffer_mirror_probe.cpp").read_text(encoding="utf-8")
workflow = (root / ".github/workflows/backend-conversion-gate.yml").read_text(encoding="utf-8")
assert source.count("// R216: separate precision/readonly-owner fence") == 1
r216 = source.split("// R216: separate precision/readonly-owner fence", 1)[1]
guards = (
    "verified_linear_float_depth_eye_draw_ready(",
    "!expectedDsv ||",
    "!verified_linear_sealed_opaque_eye_draw_ready(",
    "view.Format != DXGI_FORMAT_D32_FLOAT",
    "view.Flags != 0",
    "expectedDsv->GetResource(resource.GetAddressOf())",
    "desc.Format == DXGI_FORMAT_D32_FLOAT",
    "desc.Usage == D3D11_USAGE_DEFAULT",
    "desc.CPUAccessFlags == 0",
)
def passes(s): return all(guard in s for guard in guards)
assert passes(r216), "R216 float-depth seal missing"
for guard in guards:
    assert not passes(r216.replace(guard, "", 1)), "R216 guard mutation escaped: " + guard
assert "->Draw(" not in source and "->DrawIndexed(" not in source, "gameplay native Draw forbidden"
for phrase in (
    "R216 dedicated D32_FLOAT eye initially ready",
    "R216 create dedicated D16 depth texture",
    "R216 create same-size D16 depth view",
    "R216 R215 admits valid lower-precision D16 eye",
    "R216 reject D16 eye masquerading as float depth",
    "R216 real WARP D16 Draw succeeds but is not D32 precision",
    "R216 exact original D32_FLOAT eye restored",
    "R216 real WARP restored D32 eye draws red",
):
    assert phrase in probe, "R216 WARP negative/restore missing: " + phrase
step = "python tools/test_dx11_float_depth_eye_r216.py"
assert workflow.count(step) == 1, "R216 must run exactly once in conversion Gate"
assert workflow.index("python tools/test_dx11_sealed_opaque_eye_r215.py") < workflow.index(step)
assert workflow.index(step) < workflow.index("Build DX11 linear VB/IB mirror R183 WARP probe")
print("R216 float-depth eye: PASS; nine independent guard mutants + Windows WARP negative/restore wired")
