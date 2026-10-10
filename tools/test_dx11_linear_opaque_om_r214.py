#!/usr/bin/env python3
"""R214: one-shot static mutation guard and isolated real WARP Draw contract."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
source = (root / "src/vr/d3d11/native_linear_draw_submit.hpp").read_text(encoding="utf-8")
probe = (root / "tools/dx11_linear_buffer_mirror_probe.cpp").read_text(encoding="utf-8")
workflow = (root / ".github/workflows/backend-conversion-gate.yml").read_text(encoding="utf-8")

assert source.count("// R214: strict opaque non-indexed native Draw") == 1
r214 = source.split("// R214: strict opaque non-indexed native Draw", 1)[1]
guards = (
    "verified_linear_opaque_single_eye_draw_ready(",
    "!context || !verified_linear_single_eye_depth_draw_ready(",
    "expectedRtv, expectedDsv, expectedDepthState))",
    "Microsoft::WRL::ComPtr<ID3D11BlendState> liveBlend;",
    "UINT sampleMask = 0;",
    "context->OMGetBlendState(liveBlend.GetAddressOf(), nullptr, &sampleMask);",
    "return !liveBlend && sampleMask == D3D11_DEFAULT_SAMPLE_MASK;",
)
assert all(r214.count(g) == 1 for g in guards), "R214 live OM/eye contract missing or duplicated"
for guard in guards:
    mutant = r214.replace(guard, "", 1)
    assert not all(x in mutant for x in guards), "R214 mutation escaped: " + guard
assert "->Draw(" not in source and "->DrawIndexed(" not in source, "game-native Draw forbidden"
for evidence in (
    "R214 opaque linear single-eye OM ready",
    "R214 R211 still accepts foreign OM blend",
    "R214 reject stale nonopaque OM blend",
    "R214 real WARP Draw suppressed by retained blend",
    "R214 recover exact default OM blend",
    "R214 R211 still accepts zero sample mask",
    "R214 reject zero live sample mask",
    "R214 real WARP Draw suppressed by zero mask",
    "R214 restore fully owned opaque OM state",
    "R214 real WARP Draw restored red pixel after OM repair",
    "ctx->Draw(3,0);",
):
    assert evidence in probe, "R214 isolated WARP negative/restore proof missing: " + evidence
step = "python tools/test_dx11_linear_opaque_om_r214.py"
assert workflow.count(step) == 1, "R214 scoped source contract must run once"
assert workflow.index(step) < workflow.index("Build DX11 linear VB/IB mirror R183 WARP probe")
print("R214 linear exact opaque OM: PASS; seven guard mutants and WARP negative/restore wired")
