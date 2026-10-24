#!/usr/bin/env python3
"""DX11 00728: real game multi-rectangle full Clear -> fresh same-Present Draw."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
src=(root/"src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")
cov=(root/"src/vr/d3d11/native_game_clear_coverage.hpp").read_text(encoding="utf-8")
wf=(root/".github/workflows/dx11-fast-structural.yml").read_text(encoding="utf-8")
def valid(s,h):
    a=s.find("void observe_game_clear(")
    b=s.find("void observe_unavailable_game_draw(",a)
    body=s[a:b]
    i=body.find("GameNativeClearCoverage::covers_whole(")
    j=body.find("s.clearColor.record(",i)
    k=body.find("if (wholeBackbuffer && env_full_game_opt_in())",j)
    return all((
        '#include "native_game_clear_coverage.hpp"' in s,
        a>=0 and b>a and 0<=i<j<k,
        "bbDesc.Width, bbDesc.Height, viewport.X, viewport.Y," in body,
        "viewport.Width, viewport.Height, count, rects" in body,
        "targetIdentity.Get() == backbufferIdentity.Get()" in body,
        "s.frameBatch.reset();" in body[k:],
        "s.pending = false;" in body[k:],
        "s.sourceDrawsThisFrame = 0u;" in body[k:],
        "s.eligibleThisFrame = 0u;" in body[k:],
        "s.clearColor.native_color(s.sourceGameDevice, output.targetIdentity, kBackground)" in s,
        "if (!rects || count > 16u) return false;" in h,
        "if (nextX==x) return false;" in h,
    ))
assert valid(src,cov), "game Clear->full native Draw source link missing"
a=src.index("void observe_game_clear(");b=src.index("void observe_unavailable_game_draw(",a)
for old,new in (
    ("GameNativeClearCoverage::covers_whole(","GameNativeClearCoverage::skipped("),
    ("if (wholeBackbuffer && env_full_game_opt_in())","if (false)"),
    ("s.frameBatch.reset();","s.frameBatch.abort();"),
    ("s.pending = false;","s.pending = true;"),
    ("s.sourceDrawsThisFrame = 0u;","s.sourceDrawsThisFrame = 1u;")
):
    body=src[a:b];changed=body.replace(old,new,1)
    assert changed!=body and not valid(src[:a]+changed+src[b:],cov),old
for old,new in (("if (nextX==x) return false;","if (false) return false;"),
                ("if (!rects || count > 16u) return false;","if (false) return false;")):
    changed=cov.replace(old,new,1)
    assert changed!=cov and not valid(src,changed),old
assert "python tools/test_dx11_full_clear_resume_00728.py" in wf
assert "tools/dx11_full_clear_resume_probe_00728.cpp" in wf
print("00728 post-Clear full native menu/race Draw source/fallback PASS")
