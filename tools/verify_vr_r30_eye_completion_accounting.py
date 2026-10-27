#!/usr/bin/env python3
"""Verify R30 XYZRHW/HUD L+R completion receipts; HMD remains UNTESTED."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
code=(root/"src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp").read_text(encoding="utf-8")
workflow=(root/".github/workflows/vr-dx9ex-active.yml").read_text(encoding="utf-8")
def region(source, begin, end):
    start=source.index(begin)
    return source[start:source.index(end,start+len(begin))]
xy=region(code,"HRESULT R30ExecuteXyzrhwStereo(","HRESULT R30TryXyzrhwPrimitiveUP(")
hud=region(code,"HRESULT R30TryScreenSpaceFovDraw(","HRESULT R30GuardScreenSpace(")
def check(s, kind):
    marker="const bool pairComplete = SUCCEEDED(rightHr) && restoreOk;"
    gate="if (pairComplete)\n            {"
    idx=s.find(marker)
    if idx<0 or s.find(gate,idx+len(marker))<idx:
        return False
    body=s[s.find(gate,idx):s.index("            if (FAILED(rightHr))",idx)]
    for item in ("FrameHadDuplicatedDraw = true;","++DuplicatedDraws;","++R30SafeTwoEyeDraws;"):
        if item not in body:return False
    if kind=="xy":
        return ("FrameHadWorldStereo = true;" in body and
                "++WorldStereoDraws;" in body and
                "++R30XyzrhwWorldEffectDraws;" in body and
                "++R30XyzrhwHudDraws;" in body and
                body.index("FrameHadDuplicatedDraw = true;") < body.index("FrameHadWorldStereo = true;") and
                s.index("if (FAILED(rightHr))") > s.index("if (pairComplete)") and
                s.index("NoteRestoreFailure(") > s.index("if (FAILED(rightHr))"))
    return ("++R30ScreenSpaceFovDraws;" in body and
            "++R30Hud2DDraws;" in body and
            "++R30WorldBillboardDraws;" in body and
            "if (pairComplete && !firstProjectedScreenEffectLogged)" in s and
            "if (pairComplete && screenKind == R30ScreenSpaceKind::WorldBillboard &&" in s and
            "if (rivalGpuProbe)" in s[s.index("if (pairComplete && !firstProjectedScreenEffectLogged)"):])
assert check(xy,"xy")
assert check(hud,"hud")
assert "const bool f11PairComplete = SUCCEEDED(rightHr) && restored;" in code
# Ensure the source gate detects both independently mutated telemetry paths.
for name,s,kind in (("xy",xy,"xy"),("hud",hud,"hud")):
    for mutation_name,old,new in (
      ("lost right test","SUCCEEDED(rightHr) && restoreOk","true && restoreOk"),
      ("lost restore test","SUCCEEDED(rightHr) && restoreOk","SUCCEEDED(rightHr) && true"),
      ("missing completion guard","if (pairComplete)\n            {","if (true)\n            {"),
      ("false duplicated receipt","FrameHadDuplicatedDraw = true;","FrameHadDuplicatedDraw = false;"),
      ("false two-eye count","++R30SafeTwoEyeDraws;","--R30SafeTwoEyeDraws;"),
    ):
        assert old in s,(name,mutation_name,"fixture missing")
        assert not check(s.replace(old,new,1),kind),(name,mutation_name,"escaped")
assert "'tools/verify_vr_r30_eye_completion_accounting.py'" in workflow
print("PASS R30 XYZRHW/HUD exact L+R and restore-success receipts; F11 preserved, 10 negative controls; HMD UNTESTED")
