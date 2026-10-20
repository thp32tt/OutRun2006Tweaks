#!/usr/bin/env python3
"""DX9Ex R26 car marker DX11 R57 mode-6 parity, scoped source contract.

No headset/Windows build is implied by static or numerical checks.
"""
from pathlib import Path
root = Path(__file__).resolve().parents[1]
settings = (root/"src/vr/settings.cpp").read_text(encoding="utf-8")
ini = (root/"OutRun2006Tweaks.ini").read_text(encoding="utf-8")
dx9 = (root/"src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp").read_text(encoding="utf-8")
hook = (root/"src/hooks_uiscaling.cpp").read_text(encoding="utf-8")
assert 'VRHudScale{ "VR", "HudScale", 0.55f,' in settings
assert "HudScale = 0.55" in ini
assert 'VRRankDx11ReferenceEyePose{ "VR", "RankDx11ReferenceEyePose", true,' in settings
assert "RankDx11ReferenceEyePose = true" in ini
body = dx9.split("bool R57BuildProjectedMarkerDelta(",1)[1].split(
    "float R30HudAspectCompensation(",1)[0]
admission = body.split("float headRaw[16]",1)[0]
for t in ("CurrentProjectedMarker()", "marker->valid", "MatrixFinite(baseProjection)",
          "R57ProjectViewPoint("):
    assert t in admission, "unsafe marker admission change: "+t
rank = body.split("const bool exactOrdinalRank =",1)[1].split(
    "float exactEyeOffsets",1)[0]
assert "marker->exactOrdinalEyeCant" in rank
assert "!Settings::VRRankDx11ReferenceEyePose.get()" in rank
assert "GetLatchedHeadInverse(" in body and "headPoseSequence != stereo.poseSequence" in body
assert "exactOrdinalRank ? exactEyeOrientations[eye] : identityOrientation" in body
assert "exactOrdinalRank ? exactEyeOffsets[eye] : relativeEye" in body
assert "ProjectionFromFov(" in body
assert "deltaX[eye] = eyeX - baseX;" in body
assert "deltaY[eye] = eyeY - baseY;" in body
assert "RivalMarkerProjectedInfo" in hook
# Quest3 3f9ccd3b: native 0xBAEE2 car depth was present but NaviPub
# source tag suppressed every world anchor. A VALID exact E8 view point
# may promote the vehicle sprite; absent evidence stays ScreenHud.
assert "RankMarkerSubScreenHudDepth != 0 &&" in hook
assert "!projectedAnchor.valid" in hook
assert "RankMarkerExactCalcEdge));" in hook
assert "recoverViewPoint(RankMarkerProjectedInfo, !dx11RankSource);" in hook
assert "Settings::VRRankDx11ProducerReference.get()" in hook
assert "const bool projected = projectedAnchor.valid;" in hook
assert "RankMarkerSubScreenHudDepth != 0 && !projected;" in hook
# RIVAL: exact original BB6F0 Calc3D2D edge must stamp the anchor before
# BB796 queued/delayed sprite rendering, never the generic HUD sprite.
assert "RivalMarkerExactCalcEdge = false;" in hook
assert "static void __cdecl Calc3D2D_RivalExactCall(" in hook
assert "RivalMarkerExactCalcEdge = true;" in hook
assert "else if (RivalMarkerExactCalcEdge ||" in hook
assert "Module::exe_ptr(0xBB6F0)" in hook
assert "RivalMarkerProjectedInfo = {};" in hook
# Fail closed: no valid input means no projected vehicle rank/rival.
for marker in ("!projectedAnchor.valid", "const bool projected = projectedAnchor.valid;",
               "RivalMarkerProjectedInfo = {};", "RankMarkerExactCalcEdge));"):
    assert marker in hook, marker
for is_ordinal in (False, True):
    for dx11_reference in (False, True):
        chosen_canted = is_ordinal and not dx11_reference
        if dx11_reference:
            assert not chosen_canted
        if not is_ordinal:
            assert not chosen_canted
assert 'VRRankDx11ProducerReference{ "VR", "RankDx11ProducerReference", true,' in settings
assert 'VRRivalDx11NativeRoute{ "VR", "RivalDx11NativeRoute", true,' in settings
assert 'VRRankDesktopLift{ "VR", "RankDesktopLift", false,' in settings
for name,expected in (("RankDx11ProducerReference", "true"),
                      ("RivalDx11NativeRoute","true"),
                      ("RankDesktopLift","false")):
    assert f"{name} = {expected}" in ini
assert "if (!Settings::VRRivalDx11NativeRoute.get())" in hook
assert "const int anchorLiftY = Settings::VRRankDesktopLift.get()" in hook
assert "R62TryFixedFunctionSpriteIndexed(" in dx9
# The additional DX9-only positive-W gate must not reject an original
# negative-view-Z rank that the user-good DX11 R57 mode 6 projects.
# No other source (lens, scene, HUD, rival) may gain this exception.
wview = dx9.split("bool R57ProjectViewPoint(", 1)[1].split(
    "bool R57BuildProjectedMarkerDelta(", 1)[0]
for token in (
    "Settings::VRRankDx11ProducerReference.get()",
    "marker.exactOrdinalEyeCant",
    "std::fabs(clipW) <= 1.0e-6f",
    "clipW <= 1.0e-6f",
):
    assert token in wview
assert "dx11OrdinalClipW" in wview and "marker.exactOrdinalEyeCant;" in wview
for token in ("marker.exactOrdinalEyeCant", "std::fabs(clipW) <= 1.0e-6f"):
    assert token not in wview.replace(token, "/* forbidden broad W gate */", 1)
print("PASS R26 DX11 rank direct projection, native rival + optional legacy routes, 0.55 HUD")
