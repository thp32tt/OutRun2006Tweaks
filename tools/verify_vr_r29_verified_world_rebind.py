#!/usr/bin/env python3
"""R84 live shader-switch continuation: source-bound positive/negative guard.

Protect user-proven R26 world path without granting stale WVP to UI/FX.
Actual Quest3 stereo acceptance is separate from source/build validation.
"""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
r29 = (root / "src/vr/d3d9/stereo_renderer_r29.cpp").read_text(encoding="utf-8-sig")
r26 = (root / "src/vr/d3d9/stereo_renderer_r26.cpp").read_text(encoding="utf-8-sig")
r31 = (root / "src/vr/d3d9/stereo_renderer_r31.cpp").read_text(encoding="utf-8-sig")
r33 = (root / "src/vr/d3d9/stereo_renderer_r33.cpp").read_text(encoding="utf-8-sig")

def check(main: str) -> None:
    block = main.split("HRESULT R29GuardStableDraw(", 1)[1].split("bool fragile = true;", 1)[0]
    required = [
        "R29StableStereoBase(device)", "TryBootstrapRightDepthFromRecentClear(device)",
        "const auto worldRebindScope =", "OutRunVR::GameSemantic::EffectiveScope()",
        "RenderScope::ScreenHud", "RenderScope::ScreenOverlay2D",
        "RenderScope::ProjectedScreenEffect2D",
        "RenderScope::ProjectedWorldMarker2D",
        "ForceZeroDisparity(",
        "if (allowVerifiedWorldRebind &&", "R28CanRebindVerifiedWorld(",
        "CurrentVertexShaderIdentity.exchange(", "VertexShaderSerial.exchange(",
        "R29DirectTwoEye(", "false, site);",
        "CurrentVertexShaderIdentity.compare_exchange_strong(",
        "VertexShaderSerial.compare_exchange_strong(",
        "return rebound;", "R28PerspectiveWorldSemantic()",
    ]
    for token in required:
        assert token in block, f"R84 must retain shader-switch owner: {token}"
    assert "OUTRUN_VR_R29_R28_CLASSIFICATION_COMPARE" not in block, "comparison-only gate regressed"
    assert block.count("if (allowVerifiedWorldRebind &&") == 2, (
        "both shader-rebind and direct perspective routes must veto HUD/SkyGlow")
    assert "ForceZeroDisparity(\n                    worldRebindScope)" in block, (
        "sky postprocessing must not be stereo-reprojected as road geometry")
    assert block.index("const bool allowVerifiedWorldRebind") < block.index("if (allowVerifiedWorldRebind &&")
    assert block.index("if (allowVerifiedWorldRebind &&") < block.index("R29DirectTwoEye(")
    assert block.index("CurrentVertexShaderIdentity.compare_exchange_strong(") < block.index("return rebound;")
    assert block.index("VertexShaderSerial.compare_exchange_strong(") < block.index("return rebound;")

assert "R28CanRebindVerifiedWorld(" in r26
for proof in ("R28PerspectiveWorldSemantic()", "FloatArrayNear(current, verified",
              "FloatArrayNear(reinterpret_cast<const float*>(&currentProjection)",
              "poseSequence != stereo.poseSequence", "TargetIsBackBuffer()",
              "AnyAuxRenderTargetActive()"):
    assert proof in r26, f"legacy rebind proof weakened: {proof}"
assert "currentShader != verifiedShader" in r31 and "currentShaderSerial != verifiedShaderSerial" in r31
assert "R33TryFastWorld(device" in r33 and "return fallbackToR29();" in r33
check(r29)
# A source mutation that skips only the second (same-shader) ownership gate
# previously survived and routed flat HUD/SkyGlow using a stale world WVP.
for old_predicate in (
    "if (allowVerifiedWorldRebind &&\n                OutRunVRRenderer::R28PerspectiveWorldSemantic())",
    "if (allowVerifiedWorldRebind &&\n                R28CanRebindVerifiedWorld(",
):
    assert old_predicate in r29, f"required R29 scoped predicate missing: {old_predicate}"
    mutant = r29.replace(old_predicate, old_predicate.replace("allowVerifiedWorldRebind &&\n                ", ""), 1)
    try:
        check(mutant)
    except AssertionError:
        pass
    else:
        raise AssertionError("unscoped shader/perspective world route survived mutation")
for needle in ("OUTRUN_VR_R29_R28_CLASSIFICATION_COMPARE", "RenderScope::ScreenHud",
               "RenderScope::ScreenOverlay2D", "RenderScope::ProjectedScreenEffect2D",
               "RenderScope::ProjectedWorldMarker2D", "ForceZeroDisparity(",
               "if (allowVerifiedWorldRebind &&", "R28CanRebindVerifiedWorld(",
               "VertexShaderSerial.compare_exchange_strong("):
    changed = r29.replace(needle, "DELETED_FOR_NEGATIVE_TEST", 1)
    if changed == r29:
        assert needle == "OUTRUN_VR_R29_R28_CLASSIFICATION_COMPARE"
        changed = r29.replace("const bool allowVerifiedWorldRebind =", "#if defined(OUTRUN_VR_R29_R28_CLASSIFICATION_COMPARE)\n            const bool allowVerifiedWorldRebind =", 1)
    try:
        check(changed)
    except AssertionError:
        pass
    else:
        raise AssertionError(f"negative mutation escaped: {needle}")
print("PASS R84 R28 c64/projection/pose world continuation and BOTH HUD/SkyGlow non-world vetoes; Quest3 UNTESTED")
