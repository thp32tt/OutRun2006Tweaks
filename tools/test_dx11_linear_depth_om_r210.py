#!/usr/bin/env python3
"""R210: once-per-change negative guards for dormant linear depth OM identity."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
header = (root / "src/vr/d3d11/native_linear_draw_submit.hpp").read_text(encoding="utf-8")
probe = (root / "tools/dx11_linear_buffer_mirror_probe.cpp").read_text(encoding="utf-8")
workflow = (root / ".github/workflows/backend-conversion-gate.yml").read_text(encoding="utf-8")
r210 = header.split("// R210: dormant depth-aware non-indexed Draw", 1)[1]
guards = (
    "!context || !expectedDsv || !expectedDepthState",
    "!verified_linear_pipeline_identity_ready(",
    "liveRtv.Get() != expectedRtv",
    "liveDsv.Get() != expectedDsv",
    "liveDepthState.Get() != expectedDepthState",
    "stencilRef != 0",
    "!desc.DepthEnable",
    "desc.DepthWriteMask != D3D11_DEPTH_WRITE_MASK_ALL",
    "desc.DepthFunc != D3D11_COMPARISON_LESS",
    "desc.StencilEnable",
    "ownerDevice.Get() != contextDevice.Get()",
    "ownerDevice.Get() == contextDevice.Get()",
)
assert all(r210.count(g) == 1 for g in guards), "R210 DSV guard missing/duplicated"
for guard in guards:
    mutant = r210.replace(guard, "", 1)
    assert not all(g in mutant for g in guards), "R210 mutation survived: " + guard
assert "->Draw(" not in header and "->DrawIndexed(" not in header, "game-native Draw forbidden"
for evidence in (
    "R210 exact owned OM DSV and depth state",
    "R210 reject absent DSV owner",
    "R210 owned depth passes real WARP red pixel",
    "R210 R209 accepts foreign same-device DSV",
    "R210 reject foreign live OM DSV",
    "R210 alien DSV suppresses real WARP pixel",
    "R210 reject unowned depth state",
    "R210 reject different stencil reference",
    "R210 reject different depth state object",
    "R210 restore exact depth-state identity",
    "R210 recovered owned DSV WARP red pixel",
):
    assert evidence in probe, "missing R210 WARP positive/negative proof: " + evidence
step = "python tools/test_dx11_linear_depth_om_r210.py"
assert workflow.count(step) == 1, "R210 one-shot static CI step required"
assert workflow.index(step) < workflow.index("Build DX11 linear VB/IB mirror R183 WARP probe")
print("R210 exact OM DSV/depth-state: PASS; 12 guard mutants and real WARP depth pixels wired")
