#!/usr/bin/env python3
"""Fail-closed C993 R84 *physical* stereo route contract, not just telemetry.

The original game c64 belongs to one exact central sun producer. Only that
producer may use the R26-proven stock-WVP -> worldView -> head -> eye -> FOV
chain in the independent R84 R30/R32/R33 renderer. Preserve the CURRENT GPU
constants separately for restoration. CI compile/link is not HMD acceptance.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATHS = (
    "src/vr/core/r29_owner_api.hpp",
    "src/vr/d3d9/stereo_renderer_r29.cpp",
    "src/vr/d3d9/stereo_renderer_r30.cpp",
    "src/vr/d3d9/lens_centre_source_provenance.hpp",
    "src/vr/core/r30_support_api.hpp",
    "src/vr/core/r32_review_api.hpp",
    "src/vr/d3d9/stereo_renderer_r32.cpp",
    "src/vr/d3d9/stereo_renderer_r33.cpp",
    ".github/workflows/vr-dx9ex-active.yml",
    "src/hooks_graphics.cpp",
    "src/vr/game/render_semantics.hpp",
)


def check(api, r29, r30, proof, r30api, r32api, r32, r33, workflow, hooks, semantic):
    assert "std::uint64_t R29OwnerTopLevelDrawSerial() noexcept;" in api
    assert "return GetTopLevelDrawSerial();" in r29
    assert '#include "lens_centre_source_provenance.hpp"' in r30
    owned = r30.split("bool R30HasExactLensCentreRawWvp(", 1)[1].split(
        "R30ScreenSpaceKind R30ClassifyScreenSpacePass(", 1)[0]
    for marker in (
        "QueueRenderActive()",
        "EffectiveScope() != RenderScope::WorldBillboard",
        "CurrentRenderProducerToken() != ProducerToken::LensFlareCentre",
        "GetLastRawGameWvpWrite(",
        "GetLastGameWvpSemanticProvenance(",
        "R29OwnerCurrentShaderEpoch(currentShader, currentShaderEpoch)",
        "CurrentLensCentreCallEpoch",
        "GetLastGameWvpLensCentreCallEpoch()",
        "GetCurrentLatchedPoseEpoch()",
        "GetLastGameWvpPoseEpoch(),",
        "R29OwnerTopLevelDrawSerial() + 1u",
        "sourceScope == RenderScope::WorldBillboard",
        "sourceProducer == ProducerToken::LensFlareCentre",
        "queueNode == nullptr",
        "OutRunVR::LensCentre::OwnsRawWvp({",
    ):
        assert marker in owned, "C993 producer evidence missing: " + marker
    route = r30.split("R30ScreenSpaceKind R30ClassifyScreenSpacePass(", 1)[1].split(
        "// Only the OpenXR pose/FOV signature affects this affine.", 1)[0]
    for marker in (
        "!OutRunVR::GameSemantic::QueueRenderActive()",
        "scope == OutRunVR::GameSemantic::RenderScope::WorldBillboard",
        "CurrentRenderProducerToken() ==",
        "ProducerToken::LensFlareCentre)",
        "R30HasExactLensCentreRawWvp(originalGameWvp)",
        "OutRunVR::LensCentre::SelectWorldRoute(true, owned)",
        "OutRunVR::LensCentre::WorldRoute::ExactCentreStereo",
        "return R30ScreenSpaceKind::ExactLensCentreWorld;",
        "return R30ScreenSpaceKind::None;",
        "VR R84 C993 RAW_WVP_SOURCE: {}",
        'owned ? "EXACT_OWNER" : "MISSING_OR_STALE"',
        "return R30ScreenSpaceKind::FlatPerspectiveEffect;",
    ):
        assert marker in route, "R84 centre classification missing: " + marker
    assert (route.index("R30HasExactLensCentreRawWvp(originalGameWvp)") <
        route.index("SelectWorldRoute(true, owned)") <
        route.index("return R30ScreenSpaceKind::ExactLensCentreWorld;") <
        route.rindex("return R30ScreenSpaceKind::None;"))
    # Never require VRTelemetry to perform the stereo route. Telemetry guards
    # logging only; geometry is driven by authenticated original-game data.
    assert route.index("R30HasExactLensCentreRawWvp(originalGameWvp)") < (
        route.index("if (Settings::VRTelemetry)"))
    assert "if (Settings::VRTelemetry &&" not in route

    bld = r30.split("bool R30BuildScreenSpaceEyeConstants(", 1)[1].split(
        "template <typename ActualDraw>", 1)[0]
    lens = bld.split(
        "if (screenKind == R30ScreenSpaceKind::ExactLensCentreWorld)", 1)[1].split(
        "if (screenKind == R30ScreenSpaceKind::FlatPerspectiveEffect)", 1)[0]
    for marker in (
        "R30ScreenSpaceKind::ExactLensCentreWorld",
        "GetVertexShaderConstantF(",
        "R30SupportWvpFirstRegister, original",
        "R30HasExactLensCentreRawWvp(rawGameWvp)",
        "std::memcpy(&rawUploadedT, rawGameWvp, sizeof(rawUploadedT))",
        "R29OwnerTransposeMatrix(rawUploadedT)",
        "R29OwnerInvertMatrix(baseProjection,",
        "R29OwnerMultiplyMatrix(stockRawWvp,",
        "const float affineError =",
        "const float viewDepth =",
        "const float clipW =",
        "affineError > 0.02f",
        "viewDepth < 1.25f || viewDepth >= 1000000.0f",
        "clipW <= 0.05f",
        "R29OwnerMultiplyMatrix(worldView, headInverse)",
        "headPoseSequence != stereo.poseSequence",
        "R29OwnerMatrixFromQuaternionTranslation(",
        "R29OwnerInverseRigid(eyePose)",
        "R29OwnerProjectionFromFov(baseProjection,",
        "R29OwnerMultiplyMatrix(",
        "headRelative, eyeInverse",
        "R29OwnerMatrixFinite(corrected)",
        "std::memcpy(eyeConstants[eye], &correctedT",
        "return false;",
    ):
        assert marker in bld if marker in (
            "GetVertexShaderConstantF(",
            "R30SupportWvpFirstRegister, original",
            "R30ScreenSpaceKind::ExactLensCentreWorld",
        ) else marker in lens, "exact C993 per-eye transform lost: " + marker
    # R84 now contains an additional separately source-proven HUD plane
    # ahead of C993. Check C993's OWN scoped transform ordering; matching
    # rawUploadedT in the earlier HUD cannot be mistaken for lens execution.
    assert (bld.index("GetVertexShaderConstantF(") <
        bld.index("if (screenKind == R30ScreenSpaceKind::ExactLensCentreWorld)"))
    assert (lens.index("R30HasExactLensCentreRawWvp(rawGameWvp)") <
        lens.index("R29OwnerTransposeMatrix(rawUploadedT)") <
        lens.index("R29OwnerMultiplyMatrix(stockRawWvp,") <
        lens.index("R29OwnerMultiplyMatrix(worldView, headInverse)") <
        lens.index("R29OwnerProjectionFromFov(baseProjection,"))
    # The original GPU constants are needed to restore the source draw;
    # replacing `original` with a stock raw WVP would corrupt D3D9 state.
    assert "headPoseSequence != stereo.poseSequence" in lens
    assert "R29OwnerProjectionFromFov(baseProjection," in lens
    assert "std::memcpy(original, rawGameWvp" not in bld
    assert "std::memcpy(&uploadedT, original" in bld

    for source in (r30api, r32api):
        assert "ExactLensCentreWorld" in source
    assert "return R30SupportScreenSpaceKind::ExactLensCentreWorld;" in r30
    assert "lower = R30ScreenSpaceKind::ExactLensCentreWorld;" in r30
    assert "return R32ReviewScreenSpaceKind::ExactLensCentreWorld;" in r32
    assert "lower = R30SupportScreenSpaceKind::ExactLensCentreWorld;" in r32
    physical = r33.split("R32ReviewOwnedResult R33TryHud(", 1)[1].split(
        "template <typename ActualDraw, typename LowerR29Draw>", 1)[0]
    for marker in (
        "screenKind == R32ReviewScreenSpaceKind::ExactLensCentreWorld",
        "R33TelemetryEnabled()",
        "SUCCEEDED(result.hr)",
        "SUCCEEDED(rightHr) && restoreOk",
        'VR R84 C993 EXACT_STEREO_DRAW: {}',
        '"BOTH_EYES_OK" : "EYE_OR_RESTORE_FAILED"',
        "stereo->poseSequence",
    ):
        assert marker in physical, "R33 C993 physical draw proof lost: " + marker
    assert (physical.index("R32ReviewOwnedResult result{ true, actualDraw() };") <
        physical.index("if (screenKind == R32ReviewScreenSpaceKind::ExactLensCentreWorld") <
        physical.index('VR R84 C993 EXACT_STEREO_DRAW: {}'))
    assert "e.currentCall == e.writtenCall" in proof
    assert "e.currentPoseEpoch == e.writtenPoseEpoch" in proof
    assert "e.shaderEpoch == e.writtenShaderEpoch" in proof
    assert "e.nextDraw - e.writtenDraw <= 128u" in proof
    assert "static_assert(!OwnsRawWvp(" in proof
    assert "run: python tools/verify_dx9ex_r84_lens_source.py" in workflow
    # The original C993 game draw can enter inner SceneEffect helper scopes
    # after its parent producer was tagged. The GPU submission and c64
    # provenance must keep the exact centre identity for the whole call.
    c993 = hooks.split("static void __cdecl DrawObjectAlphaCentre(", 1)[1].split(
        "public:", 1)[0]
    for marker in (
        "objectId == 0x570002",
        "!OutRunVR::GameSemantic::QueueRenderActive()",
        "ScopedExactProducerSemantic semantic(",
        "ScopedExactLensCentreGpuDraw centreGpuOwner(",
        "Game::DrawObjectAlpha_Internal(objectId, alpha, work, flags);",
    ):
        assert marker in c993, "exact original C993 GPU lifetime lost: " + marker
    assert (c993.index("ScopedExactProducerSemantic semantic(") <
            c993.index("ScopedExactLensCentreGpuDraw centreGpuOwner(") <
            c993.index("Game::DrawObjectAlpha_Internal(objectId, alpha, work, flags);"))
    for marker in (
        "DirectLensCentreOwnsGpuDraw(",
        "static_assert(!DirectLensCentreOwnsGpuDraw(true, true, false))",
        "static_assert(!DirectLensCentreOwnsGpuDraw(true, false, true))",
        "if (ExactLensCentreDrawOwnsSemantic())",
        "return RenderScope::WorldBillboard;",
        "return ProducerToken::LensFlareCentre;",
        "if (SpriteQueueDepth != 0)",
        "return CurrentSpriteQueueProducer;",
        "class ScopedExactLensCentreGpuDraw final",
        "++ExactLensCentreGpuDrawDepth;",
        "--ExactLensCentreGpuDrawDepth;",
    ):
        assert marker in semantic, "exact C993 scope lifecycle lost: " + marker
    effective = semantic.split("inline RenderScope EffectiveScope()", 1)[1].split(
        "inline void ArmNextDraw", 1)[0]
    producer = semantic.split("inline ProducerToken CurrentRenderProducerToken()", 1)[1].split(
        "class ScopedExactLensCentreGpuDraw", 1)[0]
    assert effective.index("if (ExternalOverlaySemanticDepth != 0)") < (
        effective.index("if (ExactLensCentreDrawOwnsSemantic())")) < (
        effective.index("if (CurrentQueueExactScope =="))
    assert producer.index("if (SpriteQueueDepth != 0)") < (
        producer.index("if (ExactLensCentreDrawOwnsSemantic())"))
    assert "return CurrentDirectExactProducer;" in producer


def main():
    values = tuple((ROOT / path).read_text(encoding="utf-8-sig")
                   for path in PATHS)
    check(*values)
    mutants = [
        (0, "std::uint64_t R29OwnerTopLevelDrawSerial() noexcept;", "// removed facade"),
        (1, "return GetTopLevelDrawSerial();", "return 0;"),
        (2, "QueueRenderActive()", "false"),
        (2, "sourceProducer == ProducerToken::LensFlareCentre", "true"),
        (2, "R29OwnerCurrentShaderEpoch(currentShader, currentShaderEpoch)", "true"),
        (2, "OutRunVRRenderer::GetLastGameWvpPoseEpoch(),", "0,"),
        (2, "R29OwnerTopLevelDrawSerial() + 1u", "0"),
        (2, "SelectWorldRoute(true, owned)", "SelectWorldRoute(true, true)"),
        (2, "return R30ScreenSpaceKind::ExactLensCentreWorld;", "return R30ScreenSpaceKind::None;"),
        (2, "R30HasExactLensCentreRawWvp(rawGameWvp)", "true /* non-owned GPU c64 */"),
        (2, "R29OwnerMultiplyMatrix(stockRawWvp,", "R29OwnerMultiplyMatrix(stockWvp,"),
        (2, "affineError > 0.02f", "affineError > 200.0f"),
        (2, "viewDepth < 1.25f || viewDepth >= 1000000.0f", "viewDepth < 0.0f || viewDepth >= 1000000.0f"),
        (2, "clipW <= 0.05f", "clipW < -1000000.0f"),
        (2, "headPoseSequence != stereo.poseSequence", "false"),
        (2, "R29OwnerMultiplyMatrix(worldView, headInverse)", "R29OwnerMultiplyMatrix(headInverse, worldView)"),
        (2, "std::memcpy(&rawUploadedT, rawGameWvp, sizeof(rawUploadedT))", "std::memcpy(&rawUploadedT, original, sizeof(rawUploadedT))"),
        (3, "e.nextDraw - e.writtenDraw <= 128u", "true"),
        (4, "None, Hud2D, FlatPerspectiveEffect, ExactLensCentreWorld", "None, Hud2D, FlatPerspectiveEffect"),
        (5, "ExactLensCentreWorld", "WrongLensMode"),
        (6, "return R32ReviewScreenSpaceKind::ExactLensCentreWorld;", "return R32ReviewScreenSpaceKind::None;"),
        (6, "lower = R30SupportScreenSpaceKind::ExactLensCentreWorld;", "lower = R30SupportScreenSpaceKind::None;"),
        (7, "SUCCEEDED(rightHr) && restoreOk", "true"),
        (7, "screenKind == R32ReviewScreenSpaceKind::ExactLensCentreWorld", "screenKind == R32ReviewScreenSpaceKind::Hud2D"),
        (8, "run: python tools/verify_dx9ex_r84_lens_source.py", "run: echo BYPASS"),
        (9, "ScopedExactLensCentreGpuDraw centreGpuOwner(", "/*lost owner*/ centreGpuOwner("),
        (10, "if (ExactLensCentreDrawOwnsSemantic())", "if (false)"),
        (10, "return ProducerToken::LensFlareCentre;", "return ProducerToken::None;"),
        (10, "if (SpriteQueueDepth != 0)", "if (false)"),
        (10, "++ExactLensCentreGpuDrawDepth;", "/*forgot to arm*/"),
        (10, "--ExactLensCentreGpuDrawDepth;", "/*scope leaked*/"),
    ]
    for idx, old, new in mutants:
        assert old in values[idx], "negative mutation fixture absent: " + old
        mod = list(values)
        # R84 has a separately source-owned HUD plane ahead of C993.
        # Whole-file first-occurrence replacement can mutate that HUD
        # instead, falsely reporting that a broken lens guard survived.
        if idx == 2 and old in (
            "QueueRenderActive()",
            "R29OwnerCurrentShaderEpoch(currentShader, currentShaderEpoch)",
            "OutRunVRRenderer::GetLastGameWvpPoseEpoch(),",
            "R29OwnerTopLevelDrawSerial() + 1u",
            "sourceProducer == ProducerToken::LensFlareCentre",
        ):
            start = mod[2].index("bool R30HasExactLensCentreRawWvp(")
            end = mod[2].index("R30ScreenSpaceKind R30ClassifyScreenSpacePass(", start)
            owned = mod[2][start:end]
            assert old in owned, "C993 provenance mutant missing exact owner: " + old
            mod[2] = (mod[2][:start] + owned.replace(old, new, 1) +
                      mod[2][end:])
        elif idx == 2 and old in (
            "headPoseSequence != stereo.poseSequence",
            "std::memcpy(&rawUploadedT, rawGameWvp, sizeof(rawUploadedT))",
        ):
            start = mod[2].index(
                "if (screenKind == R30ScreenSpaceKind::ExactLensCentreWorld)")
            end = mod[2].index(
                "if (screenKind == R30ScreenSpaceKind::FlatPerspectiveEffect)", start)
            owned = mod[2][start:end]
            assert old in owned, "C993 GPU transform mutant missing: " + old
            mod[2] = (mod[2][:start] + owned.replace(old, new, 1) +
                      mod[2][end:])
        else:
            mod[idx] = mod[idx].replace(old, new, 1)
        try:
            check(*mod)
        except (AssertionError, ValueError, IndexError):
            continue
        raise AssertionError("C993 unsafe world reprojection mutation escaped: " + old)
    print(f"R84 exact C993 stereo route PASS ({len(mutants)} negative mutations); "
          "R26-approved matrix order and GPU c64 restore; HMD UNTESTED")


if __name__ == "__main__":
    main()
