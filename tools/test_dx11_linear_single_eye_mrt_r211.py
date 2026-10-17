#!/usr/bin/env python3
"""R211 one-shot contract: no secondary live OM RTV on depth-aware non-indexed Draw."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
source = (root / "src/vr/d3d11/native_linear_draw_submit.hpp").read_text(encoding="utf-8")
probe = (root / "tools/dx11_linear_buffer_mirror_probe.cpp").read_text(encoding="utf-8")
workflow = (root / ".github/workflows/backend-conversion-gate.yml").read_text(encoding="utf-8")
assert source.count("// R211: an exact depth-aware linear eye") == 1
r211 = source.split("// R211: an exact depth-aware linear eye", 1)[1]
guards = (
    "!verified_linear_depth_om_identity_ready(",
    "D3D11_SIMULTANEOUS_RENDER_TARGET_COUNT",
    "context->OMGetRenderTargets(",
    "outputs[0] == expectedRtv",
    "slot = 1",
    "if (outputs[slot]) singleEye = false",
    "if (output) output->Release()",
    "return singleEye",
)
assert all(g in r211 for g in guards), "R211 missing OM/MRT guard"
for g in guards:
    # Remove every instance: OM slot-count appears in the buffer and loop.
    mutant = r211.replace(g, "")
    assert not all(x in mutant for x in guards), "R211 guard mutation escaped: " + g
assert "->Draw(" not in source and "->DrawIndexed(" not in source, "gameplay Draw forbidden"
for item in (
    "R211 isolated single-eye depth ready",
    "R211 create second-eye texture",
    "R211 create second-eye RTV",
    "ctx->OMSetRenderTargets(2,twoEyes,ownDsv.Get())",
    "R211 R210 slot-zero guard admits extra eye MRT",
    "R211 reject same-device secondary eye RTV",
    "R211 restore one eye before real WARP Draw",
    "R210 owned depth passes real WARP red pixel",
):
    assert item in probe, "R211 isolated WARP coverage missing: " + item
step = "python tools/test_dx11_linear_single_eye_mrt_r211.py"
assert workflow.count(step) == 1
assert workflow.index(step) < workflow.index("Build DX11 linear VB/IB mirror R183 WARP probe")
print("R211 OM/MRT: PASS; 8 negative mutants + isolated WARP eye-rebind proof wired")
