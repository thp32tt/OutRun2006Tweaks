#!/usr/bin/env python3
"""R212 one-shot static negative mutations, real indexed SV_Target1 WARP."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
h=(root/"src/vr/d3d11/native_indexed_draw_submit.hpp").read_text(encoding="utf-8")
p=(root/"tools/dx11_indexed_draw_probe_r186.cpp").read_text(encoding="utf-8")
w=(root/".github/workflows/backend-conversion-gate.yml").read_text(encoding="utf-8")
s=h.split("// R212: indexed DrawIndexed exact OM eye ownership",1)[1]
guards=(
    "!context || !expectedRtv",
    "!verified_indexed_pipeline_identity_ready(",
    "ID3D11RenderTargetView* views[D3D11_SIMULTANEOUS_RENDER_TARGET_COUNT]{}",
    "context->OMGetRenderTargets(",
    "bool single = views[0] == expectedRtv",
    "for (UINT i=1;",
    "if (views[i]) single=false",
    "if (v) v->Release()",
    "return single;"
)
assert all(s.count(g)==1 for g in guards), "R212 exact guard missing/duplicate"
for g in guards:
    mutant=s.replace(g,"",1)
    assert not all(x in mutant for x in guards), "R212 source mutation survived: "+g
assert "->DrawIndexed(" not in h and "->Draw(" not in h
for e in (
    "R212 compile dual PS","R212 second eye RTV",
    "context->OMSetRenderTargets(2,twoEyes,nullptr)",
    "R212 R207 accepts second eye","R212 rejects second eye",
    "R212 real indexed eye leak red pixel","R212 recovered single eye",
    "R212 recovered original shader","context->DrawIndexed(3,0,0);"
):
    assert e in p, "missing WARP evidence: "+e
step="python tools/test_dx11_indexed_single_eye_mrt_r212.py"
assert w.count(step)==1 and w.index(step)<w.index("Build R186 owned indexed Draw WARP probe")
print("R212 indexed MRT PASS: nine negative mutants and real WARP leak wired")
