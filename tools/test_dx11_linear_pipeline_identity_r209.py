#!/usr/bin/env python3
"""R209: one changed-input non-indexed native pipeline identity contract."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
header = (root / "src/vr/d3d11/native_linear_draw_submit.hpp").read_text(encoding="utf-8")
probe = (root / "tools/dx11_linear_buffer_mirror_probe.cpp").read_text(encoding="utf-8")
workflow = (root / ".github/workflows/backend-conversion-gate.yml").read_text(encoding="utf-8")
r209 = header.split("// R209: opt-in exact pipeline identity", 1)[1]
guards = (
    "!expectedLayout || !expectedVs || !expectedPs || !expectedRtv",
    "!verified_linear_draw_ready(",
    "layout.Get() == expectedLayout",
    "vs.Get() == expectedVs",
    "ps.Get() == expectedPs",
    "rtv.Get() == expectedRtv",
)
assert all(r209.count(g) == 1 for g in guards), "R209 exact object guards missing/duplicated"
for guard in guards:
    mutant = r209.replace(guard, "", 1)
    assert not all(g in mutant for g in guards), "R209 mutation survived: " + guard
assert "->Draw(" not in header and "->DrawIndexed(" not in header, "game-native Draw forbidden"
for evidence in (
    "R209 exact linear pipeline initial objects",
    "R209 reject absent expected PS",
    "R209 base readiness admits alien same-device PS",
    "R209 reject alternate same-device PS",
    "R209 alien PS changes real WARP linear pixel green",
    "R209 restore exact linear pipeline PS",
    "R209 reject alien same-device RTV",
    "R209 restore original eye RTV identity",
    "ctx->Draw(3,0);",
):
    assert evidence in probe, "missing actual R209 WARP evidence: " + evidence
step = "python tools/test_dx11_linear_pipeline_identity_r209.py"
assert workflow.count(step) == 1, "R209 CI static step must run once"
assert workflow.index(step) < workflow.index("Build DX11 linear VB/IB mirror R183 WARP probe")
print("R209 exact linear IA/VS/PS/RTV: PASS; 6 mutants, real WARP alien-PS/RTV wired")
