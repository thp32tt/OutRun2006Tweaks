#!/usr/bin/env python3
"""R221 one-shot static guard mutations and WARP negative+repair contract."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
h=(root/"src/vr/d3d11/native_linear_uav_eye_guard.hpp").read_text()
# R230 composes this R221 guard, so exclude downstream callers from
# R221 single-function deletion-mutation checks (retain full-header Draw ban).
r221=h.split("// R230: a live D3D11 predicate",1)[0]
p=(root/"tools/dx11_linear_buffer_mirror_probe.cpp").read_text()
w=(root/".github/workflows/backend-conversion-gate.yml").read_text()
guards=(
    "verified_linear_uav_isolated_eye_ready(",
    "!context || !expectedRtv || !expectedDsv",
    "!verified_linear_float_depth_eye_draw_ready(",
    "OMGetRenderTargetsAndUnorderedAccessViews(",
    "D3D11_PS_CS_UAV_REGISTER_COUNT, uavs",
    "liveRtv == expectedRtv && liveDsv == expectedDsv",
    "if (liveRtv) liveRtv->Release();",
    "if (liveDsv) liveDsv->Release();",
    "isolated = false;",
    "uav->Release();",
)
assert all(x in r221 for x in guards)
for g in guards:
    assert not all(x in r221.replace(g,"",1) for x in guards),g
assert "->Draw(" not in h and "->DrawIndexed(" not in h
for phrase in (
    "R221 old R216 admits hidden OM UAV",
    "R221 rejects hidden OM UAV",
    "OMSetRenderTargetsAndUnorderedAccessViews(",
    "psSide","ps_5_0",
    "R221 WARP second-eye UAV pixel write",
    "R221 isolation recovered","R221 WARP red eye recovered",
):
    assert phrase in p,phrase
step="python tools/test_dx11_linear_uav_eye_r221.py"
assert w.count(step)==1
assert w.index(step)<w.index("Build DX11 linear VB/IB mirror R183 WARP probe")
print("R221 linear UAV isolation: PASS 10 mutants and WARP negative/restore wired")
