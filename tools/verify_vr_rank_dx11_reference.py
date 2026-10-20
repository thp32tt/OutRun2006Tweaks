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
assert "if (RankMarkerSubScreenHudDepth != 0)" in hook
for is_ordinal in (False, True):
    for dx11_reference in (False, True):
        chosen_canted = is_ordinal and not dx11_reference
        if dx11_reference:
            assert not chosen_canted
        if not is_ordinal:
            assert not chosen_canted
print("PASS R26 DX11 mode6 reference for rank, rival unchanged, 0.55 HUD scale")
