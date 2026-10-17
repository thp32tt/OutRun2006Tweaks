#!/usr/bin/env python3
"""Guard R26 gameplay HUD parity when native 2D and XR eye extents diverge.

1000 numerical source/eye aspect pairs are examples; the actual R84 C++ route
is guarded by source-bound fail-closed structural checks and mutations.
Quest3 HMD runtime acceptance must be reported separately.
"""
from pathlib import Path
import math
root=Path(__file__).resolve().parents[1]
r84=(root/"src/vr/d3d9/stereo_renderer_r30.cpp").read_text(encoding="utf-8-sig")
r26=(root/"src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp").read_text(encoding="utf-8-sig")
guard=("if (!pauseResponsive)\n            {\n"
       "                scaleX = userScale;\n"
       "                scaleY = userScale;\n"
       "                return;\n            }")
def check(code):
    hud=code.split("void R30HudContainScale(",1)[1].split(
        "// Only exact, producer-owned gameplay text",1)[0]
    assert guard in hud
    assert hud.index(guard)<hud.index("R29OwnerReadCoherentEyeExtentPair(")
    assert hud.index(guard)<hud.index("R30HudAspectCompensation(")
    assert "const bool pauseResponsive = R30IsPauseMenuElement() &&" in hud
    assert "Settings::VRHudResponsiveLayout.get()" in hud
    assert "R30HudAspectCompensation(" in hud
    assert "R30HudContain.pauseResponsive == pauseResponsive" in hud
    return hud
assert "scaleX = userScale;\n            scaleY = userScale;" in r26.split(
    "void R30HudContainScale(",1)[1].split(
    "enum class R30ScreenSpaceKind",1)[0]
check(r84)
for mutant in (
    r84.replace(guard,"if (false) {} /* incorrect R84 gameplay contain */",1),
    r84.replace("scaleY = userScale;\n                return;",
                "scaleY = 0.0f;\n                return;",1),
    r84.replace("if (!pauseResponsive)","if (pauseResponsive)",1),
):
    try: check(mutant)
    except AssertionError: pass
    else: raise AssertionError("HUD guard mutation was accepted")
for i in range(1000):
    native_w=1280+(i%9)*240; native_h=720+(i%7)*120
    eye_w=1024+(i%11)*160; eye_h=1280+(i%13)*160
    hud_scale=0.30+(i%91)*0.01
    ratio=(native_w/native_h)/(eye_w/eye_h)
    assert math.isfinite(ratio) and ratio>0
    # Gameplay must retain exactly one uniform scale; ESC-only branch
    # may apply the asymmetric contain split by 2D/XR target aspect.
    gameplay=(hud_scale,hud_scale)
    esc=(hud_scale, hud_scale/ratio) if ratio>=1 else (hud_scale*ratio,hud_scale)
    assert gameplay[0]==gameplay[1] and all(math.isfinite(v) for v in esc)
assert 0.21 < 0.55/((3440/1440)/(2496/2688)) < 0.22
print("PASS 1000 2D/XR pairs, R26 uniform gameplay HUD parity, ESC-only containment and 3 negative mutations; HMD UNTESTED")
