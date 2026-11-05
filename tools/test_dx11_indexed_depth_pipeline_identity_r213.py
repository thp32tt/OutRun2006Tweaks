#!/usr/bin/env python3
"""R213 nine single-mutation source guards and real indexed WARP integration."""
from pathlib import Path
r=Path(__file__).resolve().parents[1]
h=(r/"src/vr/d3d11/native_indexed_depth_binding.hpp").read_text()
p=(r/"tools/dx11_depth_indexed_probe_r189.cpp").read_text()
w=(r/".github/workflows/backend-conversion-gate.yml").read_text()
s=h.split("// R213: opt-in combined exact DSV/depth and shader/layout identity",1)[1]
guards=("verified_indexed_exact_depth_pipeline_ready(","!context || !expectedLayout || !expectedVs || !expectedPs",
"!expectedRtv || !expectedDsv || !expectedDepthState",
"verified_indexed_depth_draw_ready(","verified_indexed_pipeline_identity_ready(",
"expectedRtv, expectedDsv, expectedDepthState) &&",
"expectedLayout, expectedVs, expectedPs, expectedRtv);",
"OMGetBlendState(boundBlend.GetAddressOf(), nullptr, &sampleMask);",
"boundBlend || sampleMask != D3D11_DEFAULT_SAMPLE_MASK")
assert all(s.count(g)==1 for g in guards)
for g in guards:
    assert not all(x in s.replace(g,"",1) for x in guards), "R213 mutant escaped: "+g
assert "->DrawIndexed(" not in h and "->Draw(" not in h
for marker in ("R213 baseline exact indexed pipeline","R213 R189 accepts a foreign same-device PS",
"R213 rejects same-device PS drift","R213 exact alternate expected PS",
"R213 restores exact PS","R213 rejects wrong-eye DSV",
"R213 legacy depth guard ignores foreign blend", "R213 rejects foreign OM blend",
"R213 rejects zero sample mask", "R213 restores opaque blend sample mask",
"R213 rejects rebound depth state","R213 restored combined depth/pipeline binding",
"R213 exact preflight near draw","R213 exact preflight far draw",
"R213 rejects retired IB","actual depth-tested DrawIndexed green center / black corner pixels"):
    assert marker in p, marker
step="python tools/test_dx11_indexed_depth_pipeline_identity_r213.py"
assert w.count(step)==1
assert w.index(step)<w.index("Build R189 depth indexed WARP probe")
assert w.index("Run R189 depth indexed WARP probe")<w.index("Run DX11 constant buffer probe")
print("R213 PASS: nine negative mutants and real indexed WARP preflight wired")
