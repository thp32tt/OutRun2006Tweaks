#!/usr/bin/env python3
"""Live D3D9 stencil -> native full-frame fixed/SM3 Draw contract; not HMD proof."""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
bridge = (root / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
header = (root / "src/vr/d3d11/native_game_inert_stencil_mrt.hpp").read_text()
def check(cond, why):
    if not cond:
        raise SystemExit("DX11 live stencil FAIL: " + why)
start = bridge.index("bool game_live_stencil_inert(")
end = bridge.index("// A native diagnostic draw must originate", start)
capture = bridge[start:end]
for token in (
    "D3DRS_STENCILFUNC", "D3DRS_CCW_STENCILFUNC",
    "D3DRS_STENCILWRITEMASK", "D3DRS_TWOSIDEDSTENCILMODE",
    "D3DRS_STENCILFAIL", "D3DRS_STENCILZFAIL", "D3DRS_STENCILPASS",
    "D3DRS_CCW_STENCILFAIL", "D3DRS_CCW_STENCILZFAIL",
    "D3DRS_CCW_STENCILPASS", "writeMask != 0u",
    "evidence.operationsKnown = true",
    "GameNativeInertStencilMrt::draw_inert(evidence)",
):
    check(token in capture, "missing captured front/back state " + token)
check(capture.index("writeMask != 0u") <
      capture.index("evidence.operationsKnown = true"),
      "unknown stencil ops must not be admitted")
for token in ("s.frontCompare != kCompareAlways",
              "s.twoSided && s.backCompare != kCompareAlways",
              "if (s.writeMask == 0u) return true",
              "if (!s.operationsKnown) return false",
              "for (const auto op : s.frontOps)",
              "for (const auto op : s.backOps)"):
    check(token in header, "missing fail-closed portable proof " + token)
# Both real fixed-function and programmable game Draw paths must use the
# same source capture before accepting the native frame/GPU submission.
fixed = bridge.index("bool game_live_stencil_inert(")
sm3 = bridge.index("bool submit_live_sm3_game_draw(")
check(bridge.count("!game_live_stencil_inert(game, stencil)") == 2,
      "fixed and SM3 must both bind live inert stencil admission")
check(fixed < bridge.index("!game_live_stencil_inert(game, stencil)") < sm3 <
      bridge.rindex("!game_live_stencil_inert(game, stencil)") <
      bridge.index("context->DrawIndexed(nativeIndexCount"),
      "stencil admission not attached to both real Draw callsites")
print("DX11 live native D3D9 stencil source and GPU integration PASS")
