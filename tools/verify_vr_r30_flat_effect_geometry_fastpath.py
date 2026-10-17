#!/usr/bin/env python3
"""R30 flat-perspective eye-geometry GPU/CPU submission fastpath contract.

Uses destructive source mutations so a missing pose/eye/projection key, lost
reset invalidation, per-draw inverse, or accidental scissor reintroduction
cannot pass the DX9Ex Active policy gate silently.
"""
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "src/vr/d3d9/stereo_renderer_r30.cpp"


def validate(source: str) -> None:
    # Isolate only the new cache helper. The older eye-affine HUD cache
    # also has a poseSequence key and must never satisfy this assertion.
    cache = source.split(
        "const R30FlatEffectGeometryCache* R30PrepareFlatEffectGeometry", 1
    )[1].split("bool R30BuildScreenSpaceEyeConstants", 1)[0]
    draw = source.split("bool R30BuildScreenSpaceEyeConstants", 1)[1].split(
        "template <typename ActualDraw>", 1)[0]
    hud = source.split("HRESULT R30TryScreenSpaceFovDraw", 1)[1].split(
        "template <typename ActualDraw, typename R29Draw>", 1)[0]
    assert "thread_local R30FlatEffectGeometryCache R30FlatEffectGeometry{}" in source
    assert "R30FlatEffectGeometry = {};" in source.split("HRESULT __stdcall ResetDestR30", 1)[1].split("float R30HudScaleValue", 1)[0]
    for key in (
        "cache.poseSequence == stereo.poseSequence",
        "cache.worldScale == worldScale",
        "std::memcmp(&cache.baseProjection, &baseProjection",
        "std::memcmp(&cache.headInverse, &headInverse",
        "std::memcmp(cache.eyeOrientation, stereo.eyeOrientation",
        "std::memcmp(cache.eyeOffset, stereo.eyeOffset",
        "std::memcmp(cache.eyeFov, stereo.eyeFov",
    ):
        assert key in cache, key
    assert "cache.valid = false;" in cache and "next.valid = true;" in cache
    assert "!R30InvertBaseProjectionCached(baseProjection, next.inverseBaseProjection)" in cache
    assert "R29OwnerInverseRigid(eyePose)" in cache
    assert "R29OwnerProjectionFromFov(" in cache
    assert "R29OwnerMatrixFinite(next.eyeInverse[eye])" in cache
    assert "R29OwnerMatrixFinite(next.eyeProjection[eye])" in cache
    # R84 now reconstructs a strictly owned C993 spatial centre in its
    # separate eye path; that branch legitimately inverts the original
    # projection once. The *flat-effect hotpath* must still reuse cached
    # geometry without repeating inversions/pose/projection work per draw.
    assert "geometry->inverseBaseProjection" in draw
    assert "geometry->planeNdcZ" in draw
    assert "geometry->eyeInverse[eye]" in draw
    assert "geometry->eyeProjection[eye]" in draw
    assert "headPoseSequence != stereo.poseSequence" in draw
    assert "R29OwnerMultiplyMatrix(stockWvp, depthReset)" in draw
    assert "commonViewPlane, headInverse)" in draw
    # Both eyes must share exactly one common * head multiply. In particular
    # do not move the operation back into the per-eye loop or reassociate it
    # with the eye inverse/projection: the FP multiply order is intentional.
    flat = draw.split(
        "if (screenKind == R30ScreenSpaceKind::FlatPerspectiveEffect)", 1
    )[1].split("if (screenKind != R30ScreenSpaceKind::Hud2D)", 1)[0]
    assert "R29OwnerInvertMatrix(" not in flat
    assert "R29OwnerInverseRigid(" not in flat
    assert "R29OwnerProjectionFromFov(" not in flat
    assert flat.count("R29OwnerMultiplyMatrix(commonViewPlane, headInverse)") == 1
    assert flat.index("const D3DMATRIX headRelativePlane") < flat.index(
        "for (int eye = 0; eye < 2; ++eye)"
    )
    assert "R29OwnerMultiplyMatrix( headRelativePlane, geometry->eyeInverse[eye])" in " ".join(flat.split())
    assert "headInverse" not in flat.split(
        "for (int eye = 0; eye < 2; ++eye)", 1
    )[1]
    ordinary_hud = draw.split("if (screenKind != R30ScreenSpaceKind::Hud2D)", 1)[1]
    scale_call = "R30HudContainScale(stereo, hudScaleX, hudScaleY);"
    assert ordinary_hud.count(scale_call) == 1
    assert ordinary_hud.index(scale_call) < ordinary_hud.index(
        "for (int eye = 0; eye < 2; ++eye)"
    )
    assert "R29OwnerTryGetTrackedViewport(savedViewport)" in hud
    assert "device->GetViewport(&savedViewport)" in hud  # safe fallback
    assert "device->GetRenderState(D3DRS_SCISSORTESTENABLE" not in hud
    assert "device->GetScissorRect(" not in hud
    assert "device->SetScissorRect(" not in hud
    assert "R30CaptureSkyGlowSceneBeforeHud(device)" in hud
    assert "R29OwnerRestoreRightPassState(" in hud


def negative_mutations(source: str) -> int:
    mutations = [
        ("cache.poseSequence == stereo.poseSequence", "true"),
        ("cache.worldScale == worldScale", "true"),
        ("std::memcmp(&cache.baseProjection, &baseProjection", "std::memcmp(&cache.baseProjection, &cache.baseProjection"),
        ("std::memcmp(&cache.headInverse, &headInverse", "std::memcmp(&cache.headInverse, &cache.headInverse"),
        ("std::memcmp(cache.eyeOrientation, stereo.eyeOrientation", "std::memcmp(cache.eyeOrientation, cache.eyeOrientation"),
        ("std::memcmp(cache.eyeOffset, stereo.eyeOffset", "std::memcmp(cache.eyeOffset, cache.eyeOffset"),
        ("std::memcmp(cache.eyeFov, stereo.eyeFov", "std::memcmp(cache.eyeFov, cache.eyeFov"),
        ("R30FlatEffectGeometry = {};", "/* incorrect: reset cache retained */"),
        ("!R30InvertBaseProjectionCached(baseProjection, next.inverseBaseProjection)",
         "!R29OwnerInvertMatrix(baseProjection, next.inverseBaseProjection)"),
        ("geometry->eyeProjection[eye]", "baseProjection"),
        ("R29OwnerMultiplyMatrix(commonViewPlane, headInverse)",
         "R29OwnerMultiplyMatrix(commonViewPlane, stockWvp)"),
        ("R29OwnerMultiplyMatrix(\n                                headRelativePlane, geometry->eyeInverse[eye])",
         "R29OwnerMultiplyMatrix(\n                                headRelativePlane, headInverse)"),
        ("R30HudContainScale(stereo, hudScaleX, hudScaleY);",
         "/* duplicate HUD contain probe removed entirely */"),
        ("R29OwnerTryGetTrackedViewport(savedViewport)", "false"),
        ("R30CaptureSkyGlowSceneBeforeHud(device)", "/* bloom baseline removed */"),
    ]
    count = 0
    for needle, replacement in mutations:
        assert needle in source, needle
        # There is an earlier, independent HUD FOV cache and an XYZRHW
        # SkyGlow capture. A negative mutation must target THIS new feature,
        # otherwise a different path changes while the faulty code survives.
        if needle.startswith(("cache.", "std::memcmp(")):
            scope = source.index(
                "const R30FlatEffectGeometryCache* R30PrepareFlatEffectGeometry")
        elif needle in (
            "R29OwnerMultiplyMatrix(commonViewPlane, headInverse)",
            "R29OwnerMultiplyMatrix(\n                                headRelativePlane, geometry->eyeInverse[eye])",
            "R30HudContainScale(stereo, hudScaleX, hudScaleY);",
        ):
            scope = source.index("bool R30BuildScreenSpaceEyeConstants")
        elif needle in (
            "R29OwnerTryGetTrackedViewport(savedViewport)",
            "R30CaptureSkyGlowSceneBeforeHud(device)",
        ):
            scope = source.index("HRESULT R30TryScreenSpaceFovDraw")
        else:
            scope = 0
        location = source.find(needle, scope)
        assert location >= 0, f"Scoped mutation missing: {needle}"
        changed = source[:location] + replacement + source[location + len(needle):]
        try:
            validate(changed)
        except AssertionError:
            count += 1
        else:
            raise AssertionError(f"Regression survived mutation: {needle}")
    return count


if __name__ == "__main__":
    text = SOURCE.read_text(encoding="utf-8")
    validate(text)
    count = negative_mutations(text)
    print(f"R30 flat effect pose/projection fastpath PASS; {count} destructive mutations rejected")
