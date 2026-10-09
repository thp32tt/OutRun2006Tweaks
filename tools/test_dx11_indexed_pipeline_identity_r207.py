#!/usr/bin/env python3
"""R207 changed-input contract: exact live indexed pipeline objects, five negatives."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
source = (root / "src/vr/d3d11/native_indexed_draw_submit.hpp").read_text(encoding="utf-8")
probe = (root / "tools/dx11_indexed_draw_probe_r186.cpp").read_text(encoding="utf-8")
workflow = (root / ".github/workflows/backend-conversion-gate.yml").read_text(encoding="utf-8")
r207 = source.split("// R207: stronger, opt-in object provenance", 1)[1]
guards = (
    "!expectedLayout || !expectedVs || !expectedPs || !expectedRtv",
    "!verified_indexed_linear_draw_ready(",
    "layout.Get() == expectedLayout",
    "vs.Get() == expectedVs",
    "ps.Get() == expectedPs",
    "rtv.Get() == expectedRtv",
)
assert all(guard in r207 for guard in guards), "R207 exact pipeline requirement incomplete"
for guard in guards:
    mutant = r207.replace(guard, "", 1)
    assert not all(g in mutant for g in guards), "R207 negative mutant escaped: " + guard
assert "->Draw(" not in source and "->DrawIndexed(" not in source, "production native Draw activation forbidden"
for evidence in (
    "R207 exact indexed pipeline initial objects",
    "R207 same-device base guard cannot identify alien PS",
    "R207 reject same-device alien PS identity",
    "R207 alien PS changes real WARP indexed pixel to red",
    "R207 restore exact expected PS",
    "context->DrawIndexed(3,0,0);",
):
    assert evidence in probe, "R207 WARP behavior missing: " + evidence
step = "python tools/test_dx11_indexed_pipeline_identity_r207.py"
assert workflow.count(step) == 1
assert workflow.index("Verify R207 native indexed exact pipeline identity") < workflow.index("Build R186 owned indexed Draw WARP probe")
print("R207 exact indexed IA/VS/PS/RTV: PASS; 6 source-negative mutants; WARP alien-PS pixel wired")
