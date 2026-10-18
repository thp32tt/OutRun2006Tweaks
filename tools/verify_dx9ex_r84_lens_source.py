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
    "src/vr/d3d9/r84_spatial_eye_route.hpp",
)


def check(api, r29, r30, proof, r30api, r32api, r32, r33, workflow, hooks, semantic, spatial):
    assert "std::uint64_t R29OwnerTopLevelDrawSerial() noexcept;" in api
    assert "return GetTopLevelDrawSerial();" in r29
    assert '#include "lens_centre_source_provenance.hpp"' in r30
    # Isolate C993 before the subsequent car-shadow and rank-marker owners.
    # Both reuse shader/pose/draw predicates; a mutation to either must not
    # masquerade as mutation of this independent lens producer.
    owned = r30.split("bool R30HasExactLensCentreRawWvp(", 1)[1].split(
        "bool R30HasExactCarBaseShadowRawWvp(", 1)[0]
    for marker in (
        "const auto drawCommand = CapturePhysicalDrawCommand();",
        "if (!original || !drawCommand.IsDirectWorldLensCentre())",
        "GetLastRawGameWvpWrite(",
        "GetLastGameWvpSemanticProvenance(",
        "R29OwnerCurrentShaderEpoch(currentShader, currentShaderEpoch)",
        "drawCommand.lensCentreCallEpoch",
        "GetLastGameWvpLensCentreCallEpoch()",
        "GetCurrentLatchedPoseEpoch()",
        "GetLastGameWvpPoseEpoch(),",
        "R29OwnerTopLevelDrawSerial()",
        "OutRunVR::LensCentre::AdmitsCentreRawSourceScope(",
        "sourceProducer == ProducerToken::LensFlareCentre",
        "queueNode == nullptr",
        "OutRunVR::LensCentre::OwnsRawWvp({",
    ):
        assert marker in owned, "C993 producer evidence missing: " + marker
    route = r30.split("R30ScreenSpaceKind R30ClassifyScreenSpacePass(", 1)[1].split(
        "// Only the OpenXR pose/FOV signature affects this affine.", 1)[0]
    for marker in (
        "const auto drawCommand =",
        "OutRunVR::GameSemantic::CapturePhysicalDrawCommand();",
        "const auto scope = drawCommand.scope;",
        "drawCommand.IsDirectWorldLensCentre();",
        # This exact original producer is established by ownedLensCentre
        # outside the old depth-off-only raster branch.
        "const bool ownedLensCentre =",
        "if (ownedLensCentre)",
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
    # Source-owned C993 must beat the cached/shared orthographic signature,
    # including when that signature is absent after Reset/menu transitions.
    assert route.index("if (ownedLensCentre)") < route.index(
        "GetRendererProjectionSignature(m34, m44)")
    assert route.index("return R30ScreenSpaceKind::ExactLensCentreWorld;") < (
        route.index("ClassifyProjectionSignature(m34, m44)"))
    assert route.index("return R30ScreenSpaceKind::None;",
        route.index("if (ownedLensCentre)")) < route.index(
        "GetRendererProjectionSignature(m34, m44)")
    # Source-proven C993 classification precedes alpha and depth queries:
    # depth-enabled and non-blended variants must still reach R33 stereo.
    assert (route.index("if (ownedLensCentre)") <
        route.index("R30HasExactLensCentreRawWvp(originalGameWvp)") <
        route.index("return R30ScreenSpaceKind::ExactLensCentreWorld;") <
        route.index("R29OwnerTryGetEffectTelemetrySnapshot(effect)"))
    assert route.count("R30HasExactLensCentreRawWvp(originalGameWvp)") == 1
    assert route.index("return R30ScreenSpaceKind::ExactLensCentreWorld;") < (
        route.index("GetRenderState(D3DRS_ZENABLE"))
    assert route.index("scope == OutRunVR::GameSemantic::RenderScope::WorldBillboard)") < (
        route.index("return R30ScreenSpaceKind::FlatPerspectiveEffect;"))

    # Never require VRTelemetry to perform the stereo route. Telemetry guards
    # logging only; geometry is driven by authenticated original-game data.
    assert route.index("R30HasExactLensCentreRawWvp(originalGameWvp)") < (
        route.index("if (Settings::VRTelemetry)"))
    assert "if (Settings::VRTelemetry &&" not in route

    bld = r30.split("bool R30BuildScreenSpaceEyeConstants(", 1)[1].split(
        "template <typename ActualDraw>", 1)[0]
    spatial_gate = "if (screenKind == R30ScreenSpaceKind::ExactLensCentreWorld ||"
    # Exact 3D sources must bypass ONLY the unrelated flat HUD tangent-affine
    # precondition. A stale/unknown world source never gains this exception:
    # source provenance remains checked in the separately guarded spatial arm.
    spatial_admission = (
        "const bool exactLensWorld =\n"
        "                screenKind == R30ScreenSpaceKind::ExactLensCentreWorld;\n"
        "            const bool exactShadowWorld =\n"
        "                screenKind == R30ScreenSpaceKind::ExactCarBaseShadowWorld;\n"
        "            if (OutRunVR::SpatialEyeRoute::NeedsFlatHudAffine(\n"
        "                    exactLensWorld, exactShadowWorld) &&\n"
        "                !R30BuildEyeAffine(stereo, eyeScale, eyeOffset))\n"
        "                return false;"
    )
    assert spatial_admission in bld, "exact spatial owners lost scoped HUD-affine bypass"
    assert bld.index(spatial_admission) < bld.index(spatial_gate)
    assert bld.count("R30BuildEyeAffine(stereo, eyeScale, eyeOffset)") == 1
    for exact_lens, exact_shadow in (
        ("false", "false"), ("true", "false"),
        ("false", "true"), ("true", "true")
    ):
        predicate = f"NeedsFlatHudAffine({exact_lens}, {exact_shadow})"
        assert predicate in spatial, "spatial flat-HUD predicate fixture missing: " + predicate
    assert "return !exactWorldLensCentre && !exactWorldCarShadow;" in spatial
    assert "std::isfinite(worldScale) && worldScale > 0.0f" in spatial
    assert ('#include "r84_spatial_eye_route.hpp"' in r30 and
            "inline bool PositiveWorldScale(float worldScale)" in spatial)
    # Degenerate/nonfinite scale must reject BOTH spatial-eye matrices;
    # the original native lens draw stays the conservative fallback.
    assert ("if (!OutRunVR::SpatialEyeRoute::PositiveWorldScale(\n"
            "                        lensWorldScale))\n"
            "                    return false;") in bld

    # C993 and exact car shadow share a spatial eye matrix. Their original
    # raw c64 evidence must still be selected independently.
    lens = bld.split(spatial_gate, 1)[1].split(
        "if (screenKind == R30ScreenSpaceKind::FlatPerspectiveEffect)", 1)[0]
    for marker in (
        "screenKind == R30ScreenSpaceKind::ExactCarBaseShadowWorld",
        "const bool exactShadow =\n                    screenKind == R30ScreenSpaceKind::ExactCarBaseShadowWorld;",
        "? R30HasExactCarBaseShadowRawWvp(rawGameWvp)",
        ": R30HasExactLensCentreRawWvp(rawGameWvp)",
        "viewDepth < (exactShadow ? 0.05f : 1.25f)",
    ):
        assert marker in lens, "shared eye path lost source-specific proof: " + marker
    for marker in (
        "R30ScreenSpaceKind::ExactLensCentreWorld",
        "GetVertexShaderConstantF(",
        "R30SupportWvpFirstRegister, original",
        "R30HasExactLensCentreRawWvp(rawGameWvp)",
        "std::memcpy(&rawUploadedT, rawGameWvp, sizeof(rawUploadedT))",
        "R29OwnerTransposeMatrix(rawUploadedT)",
        "R30InvertBaseProjectionCached(baseProjection,",
        "R29OwnerMultiplyMatrix(stockRawWvp,",
        "const float affineError =",
        "const float viewDepth =",
        "const float clipW =",
        "affineError > 0.02f",
        "viewDepth < (exactShadow ? 0.05f : 1.25f)",
        "viewDepth >= 1000000.0f ||",
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
        bld.index(spatial_gate))
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
    # The new R33 physical fence must run AFTER the original left native
    # Draw and BEFORE any right-eye submission. Both source integrity and
    # original-c64 rollback are required: removing either is a regression.
    for marker in (
        "const bool exactCentreEye =",
        "screenKind == R32ReviewScreenSpaceKind::ExactLensCentreWorld;",
        "const auto centreBeforeLeft = exactCentreEye",
        "const bool centreSourceChanged = exactCentreEye &&",
        "OutRunVR::LensCentre::SameStereoDrawSource(",
        "centreBeforeLeft, centreAfterLeft) ||",
        "OutRunVR::LensCentre::SameRawStereoSource(",
        "centreRawBeforeLeft, centreRawAfterLeft) ||",
        "OutRunVR::LensCentre::IsCoherentNativeCentrePair(",
        "centreAfterLeft, centreRawAfterLeft));",
        # The GOAL result owns an additional independent post-left fence.
        # Keep the C993 centre and car-shadow checks mandatory in that same
        # composite guard rather than requiring an obsolete two-term string.
    ):
        assert marker in physical, "C993 binocular source fence missing: " + marker
    # Rank shader/c64 is a sixth physical GPU source alongside C993,
    # shadow, GOAL, +TIME and ordinary native HUD. Preserve ALL vetoes:
    # the original left callback may reenter a different vehicle marker.
    guard_marker = ("if (centreSourceChanged || shadowSourceChanged ||" +
                    chr(10) + "                goalSourceChanged || stageSourceChanged ||" +
                    chr(10) + "                nativeHudSourceChanged || rankSourceChanged)")
    assert guard_marker in physical, "C993/GOAL/+TIME/HUD/rank composite fence missing"
    assert "const bool goalSourceChanged = exactGoalEye &&" in physical
    assert "OutRunVR::GoalPhysical::SameAfterNativeLeft(" in physical
    assert "const bool stageSourceChanged = exactStageEye &&" in physical
    # Both independent stage fences are required: immediately after native
    # LEFT and again after RIGHT RT/depth/viewport setters.  A one-shot
    # mutation must not survive by matching the other intact callsite.
    stage_fence = "OutRunVR::StageExtensionPhysical::SameAfterNativeLeft("
    assert physical.count(stage_fence) == 2, (
        "R33 +TIME post-LEFT and post-RIGHT-state physical fences missing")
    right_stage_fence = (
        "if (SUCCEEDED(rightHr) && exactStageEye &&" + chr(10) +
        "                    !OutRunVR::StageExtensionPhysical::SameAfterNativeLeft(")
    assert right_stage_fence in physical, (
        "R33 +TIME source guard missing after native RIGHT state setters")
    assert "const bool exactStageEye = goalCommand.IsExactFiniteResultHud() &&" in physical
    assert "R33/+TIME-source-changed" in physical
    assert "const bool exactNativeHud = goalCommand.IsSourceProvenHud() &&" in physical
    assert "const auto hudBeforeLeft = exactNativeHud" in physical
    assert "OutRunVR::HudNativeSource::IsExactHudSource(hudBeforeLeft)" in physical
    assert "const bool nativeHudSourceChanged = exactNativeHud &&" in physical
    assert "OutRunVR::HudNativeSource::SameSourceAfterNativeUpload(" in physical
    assert "R33/HUD-source-changed" in physical
    for marker in (
        "const bool exactRankEye =",
        "screenKind == R32ReviewScreenSpaceKind::ProjectedWorldMarker2D;",
        "const auto rankBeforeLeft = exactRankEye",
        "OutRunVR::RankMarker::ValidRankSource(rankBeforeLeft)",
        "const bool rankSourceChanged = exactRankEye &&",
        "OutRunVR::RankMarker::SameRankSourceAfterNativeLeft(",
        "rankBeforeLeft, captureRankSource());",
        "R33/rank-marker-source-changed",
        "R33 rank marker original c64 rollback",
    ):
        assert marker in physical, "projected rank physical GPU fence missing: " + marker
    left_draw = physical.index("R32ReviewOwnedResult result{ true, actualDraw() };")
    after_left = physical.index(guard_marker)
    right_eye = physical.index("IDirect3DSurface9* rightEye =")
    assert left_draw < after_left < right_eye
    # Assert both actual physical draw ownership checks, not unrelated HUD.
    before_native_left = physical[:left_draw]
    after_native_left = physical[left_draw:after_left]
    for marker in ("const auto centreAfterLeft = exactCentreEye",
                   "const auto centreRawAfterLeft = exactCentreEye"):
        assert marker in after_native_left, "C993 post-left snapshot lost: " + marker
    for section, label in ((before_native_left, "pre-left"),
                           (after_native_left, "post-left")):
        assert "!OutRunVR::LensCentre::IsCoherentNativeCentrePair(" in section, (
            "C993 coherent source pair veto lost: " + label)
    assert "centreBeforeLeft, centreRawBeforeLeft)) ||" in before_native_left
    assert "centreAfterLeft, centreRawAfterLeft));" in after_native_left
    assert "OutRunVR::RankMarker::ValidRankSource(rankBeforeLeft)" in before_native_left
    assert "const bool rankSourceChanged = exactRankEye &&" in after_native_left
    assert physical.index("const auto rankBeforeLeft = exactRankEye") < left_draw
    assert physical.index("const bool rankSourceChanged = exactRankEye &&") < after_left
    assert physical.index("const bool centreSourceChanged = exactCentreEye &&") < after_left
    assert physical.index("OutRunVR::LensCentre::SameStereoDrawSource(") < after_left
    assert physical.index("OutRunVR::LensCentre::SameRawStereoSource(") < after_left
    # A changed original-game c64 serial must be sampled before the native
    # left GPU Draw and fenced before right-eye render target submission.
    raw_capture = physical.index("const auto centreRawBeforeLeft = exactCentreEye")
    assert raw_capture < left_draw
    for marker in (
        "OutRunVRRenderer::GetLastRawGameWvpWrite(",
        "OutRunVRRenderer::GetLastGameWvpSemanticProvenance(",
        "OutRunVRRenderer::GetLastGameWvpLensCentreCallEpoch()",
        "OutRunVRRenderer::GetLastGameWvpPoseEpoch()",
        "OutRunVR::LensCentre::AdmitsCentreRawSourceScope(",
        "R29OwnerCurrentShaderEpoch(shader, shaderEpoch)",
        "writtenShaderEpoch == shaderEpoch",
    ):
        assert marker in physical, "C993 raw c64 provenance missing: " + marker
    fenced = physical[after_left:physical.index(
        "IDirect3DSurface9* savedRt", after_left)]
    for marker in (
        "R32ReviewSetWvpBatch(device, original)",
        "R32ReviewMarkFrameRightDrawFailed();",
        "R33InvalidateRightForLeftWrite(",
        "R32ReviewArmStereoRecoverySafety();",
        "return result;",
    ):
        assert marker in fenced, "C993 left/right fallback lost: " + marker
    exact_log = ("if (screenKind == "
        "R32ReviewScreenSpaceKind::ExactLensCentreWorld &&" + chr(10) +
        "                R33TelemetryEnabled())")
    # The distinct old diagnostic must remain independent of the new
    # per-eye source gate; otherwise a destructive mutation can hit only
    # the early guard and silently leave telemetry unchanged.
    assert exact_log in physical

    assert (physical.index("R32ReviewOwnedResult result{ true, actualDraw() };") <
        physical.index("if (screenKind == R32ReviewScreenSpaceKind::ExactLensCentreWorld") <
        physical.index('VR R84 C993 EXACT_STEREO_DRAW: {}'))
    # Nested original-game SceneEffect c64 is permitted only for the very
    # next draw of the SAME central producer; generic effects cannot gain
    # lens ownership. This is a required *additional* guard, not relaxation
    # of the original raw shader, pose, call and finite depth contracts.
    for marker in (
        "writtenProducer != ProducerToken::LensFlareCentre",
        "writtenQueueNode != nullptr",
        "currentCall != writtenCall",
        "nextDraw <= writtenDraw",
        "writtenScope == RenderScope::WorldBillboard",
        "writtenScope == RenderScope::SceneEffect &&",
        "nextDraw - writtenDraw == 1u",
    ):
        assert marker in proof, "C993 nested source owner weakened: " + marker
    assert "AdmitsCentreRawSourceScope(" in physical
    assert "OutRunVR::LensCentre::AdmitsCentreRawSourceScope(" in owned
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
    # The immutable command is only valid for this direct, nonqueued world
    # producer; keep its derivation tied to the canonical queue-aware scope.
    lens_command = semantic.split(
        "constexpr bool IsDirectWorldLensCentre() const noexcept", 1)[1].split(
        "constexpr bool IsDirectCarBaseShadow()", 1)[0]
    for marker in ("!queued && scope == RenderScope::WorldBillboard",
                   "producer == ProducerToken::LensFlareCentre",
                   "lensCentreCallEpoch != 0"):
        assert marker in lens_command, "exact C993 draw-command guard lost: " + marker
    capture = semantic.split(
        "inline PhysicalDrawCommand CapturePhysicalDrawCommand() noexcept", 1)[1].split(
        "// A direct original-game source CALL", 1)[0]
    for marker in ("QueueRenderActive()", "EffectiveScope()",
                   "CurrentRenderProducerToken()", "CurrentQueueNode()",
                   "CurrentLensCentreCallEpoch", "ExactLensCentreDrawOwnsSemantic()"):
        assert marker in capture, "C993 physical command provenance lost: " + marker
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
        (2, "!drawCommand.IsDirectWorldLensCentre()", "false"),
        (2, "drawCommand.IsDirectWorldLensCentre();", "false;"),
        (2, "sourceProducer == ProducerToken::LensFlareCentre", "true"),
        (2, "R29OwnerCurrentShaderEpoch(currentShader, currentShaderEpoch)", "true"),
        (2, "OutRunVRRenderer::GetLastGameWvpPoseEpoch(),", "0,"),
        (2, "R29OwnerTopLevelDrawSerial()", "0"),
        (2, "if (ownedLensCentre)\n            {", "if (false)\n            {"),
        (2, "SelectWorldRoute(true, owned)", "SelectWorldRoute(true, true)"),
        (2, "return R30ScreenSpaceKind::ExactLensCentreWorld;", "return R30ScreenSpaceKind::None;"),
        (2, "R30HasExactLensCentreRawWvp(rawGameWvp)", "true /* non-owned GPU c64 */"),
        (2, "R30InvertBaseProjectionCached(baseProjection,",
            "R29OwnerInvertMatrix(baseProjection,"),
        (2, "R29OwnerMultiplyMatrix(stockRawWvp,", "R29OwnerMultiplyMatrix(stockWvp,"),
        (2, "affineError > 0.02f", "affineError > 200.0f"),
        (2, "viewDepth < (exactShadow ? 0.05f : 1.25f)", "viewDepth < 0.0f"),
        (2, "clipW <= 0.05f", "clipW < -1000000.0f"),
        (2, "screenKind == R30ScreenSpaceKind::ExactCarBaseShadowWorld;",
            "screenKind == R30ScreenSpaceKind::ExactLensCentreWorld;"),
        (2, "? R30HasExactCarBaseShadowRawWvp(rawGameWvp)",
            "? R30HasExactLensCentreRawWvp(rawGameWvp)"),
        (2, ": R30HasExactLensCentreRawWvp(rawGameWvp)",
            ": R30HasExactCarBaseShadowRawWvp(rawGameWvp)"),
        (2, "viewDepth < (exactShadow ? 0.05f : 1.25f)",
            "viewDepth < (exactShadow ? 0.05f : 0.0f)"),
        (2, "const bool exactLensWorld =\n                screenKind == R30ScreenSpaceKind::ExactLensCentreWorld;",
            "const bool exactLensWorld = false;"),
        (2, "const bool exactShadowWorld =\n                screenKind == R30ScreenSpaceKind::ExactCarBaseShadowWorld;",
            "const bool exactShadowWorld = false;"),
        (2, "OutRunVR::SpatialEyeRoute::NeedsFlatHudAffine(",
            "OutRunVR::SpatialEyeRoute::AlwaysNeedFlatHudAffine("),
        (2, "OutRunVR::SpatialEyeRoute::PositiveWorldScale(",
            "OutRunVR::SpatialEyeRoute::AllowDegenerateScale("),
        (11, "return !exactWorldLensCentre && !exactWorldCarShadow;",
            "return true; /* incorrectly require HUD affine for 3D */"),
        (11, "std::isfinite(worldScale) && worldScale > 0.0f",
            "std::isfinite(worldScale) && worldScale >= 0.0f"),
        (2, "headPoseSequence != stereo.poseSequence", "false"),
        (2, "R29OwnerMultiplyMatrix(worldView, headInverse)", "R29OwnerMultiplyMatrix(headInverse, worldView)"),
        (2, "std::memcpy(&rawUploadedT, rawGameWvp, sizeof(rawUploadedT))", "std::memcpy(&rawUploadedT, original, sizeof(rawUploadedT))"),
        (3, "e.nextDraw - e.writtenDraw <= 128u", "true"),
        (2, "OutRunVR::LensCentre::AdmitsCentreRawSourceScope(",
             "OutRunVR::LensCentre::UnboundedCentreRawScope("),
        (3, "writtenProducer != ProducerToken::LensFlareCentre", "false"),
        (3, "writtenQueueNode != nullptr", "false"),
        (3, "currentCall != writtenCall", "false"),
        (3, "writtenScope == RenderScope::SceneEffect &&",
             "writtenScope != RenderScope::ScreenHud &&"),
        (3, "nextDraw - writtenDraw == 1u", "nextDraw - writtenDraw <= 128u"),
        (7, "OutRunVR::LensCentre::AdmitsCentreRawSourceScope(",
             "OutRunVR::LensCentre::NeverProvenNestedSource("),
        (4, "None, Hud2D, FlatPerspectiveEffect, ExactLensCentreWorld", "None, Hud2D, FlatPerspectiveEffect"),
        (5, "ExactLensCentreWorld", "WrongLensMode"),
        (6, "return R32ReviewScreenSpaceKind::ExactLensCentreWorld;", "return R32ReviewScreenSpaceKind::None;"),
        (6, "lower = R30SupportScreenSpaceKind::ExactLensCentreWorld;", "lower = R30SupportScreenSpaceKind::None;"),
        (7, "SUCCEEDED(rightHr) && restoreOk", "true"),
        (7, "if (screenKind == R32ReviewScreenSpaceKind::ExactLensCentreWorld &&" +
             chr(10) + "                R33TelemetryEnabled())",
             "if (screenKind == R32ReviewScreenSpaceKind::Hud2D &&" +
             chr(10) + "                R33TelemetryEnabled())"),
        (7, "OutRunVR::LensCentre::SameStereoDrawSource(",
             "OutRunVR::LensCentre::NeverOwnSource("),
        (7, "OutRunVR::LensCentre::SameRawStereoSource(",
             "OutRunVR::LensCentre::NeverOwnRawSource("),
        (7, "centreRawBeforeLeft, centreRawAfterLeft) ||",
             "centreRawBeforeLeft, centreRawBeforeLeft) ||"),
        (7, "centreAfterLeft, centreRawAfterLeft));",
             "centreAfterLeft, centreRawBeforeLeft));"),
        (7, "centreBeforeLeft, centreRawBeforeLeft)) ||",
             "centreBeforeLeft, centreRawAfterLeft)) ||"),
        (7, "OutRunVRRenderer::GetLastGameWvpLensCentreCallEpoch()",
             "0 /* no matching original sun c64 source */"),
        (7, "writtenShaderEpoch == shaderEpoch",
             "true /* ignore overwritten shader c64 source */"),
        (7, "const bool exactCentreEye =",
             "const bool disabledCentreEye ="),
        (7, "if (centreSourceChanged || shadowSourceChanged ||" + chr(10) +
             "                goalSourceChanged || stageSourceChanged ||" + chr(10) +
             "                nativeHudSourceChanged || rankSourceChanged)",
             "if (centreSourceChanged || shadowSourceChanged ||" + chr(10) +
             "                goalSourceChanged || stageSourceChanged ||" + chr(10) +
             "                nativeHudSourceChanged)"),
        (7, "const bool rankSourceChanged = exactRankEye &&",
             "const bool rankSourceChanged = false &&"),
        (7, "OutRunVR::RankMarker::SameRankSourceAfterNativeLeft(",
             "OutRunVR::RankMarker::NeverCheckPhysicalRankSource("),
        (7, "OutRunVR::RankMarker::ValidRankSource(rankBeforeLeft)",
             "OutRunVR::RankMarker::NeverCheckPreLeftRankSource(rankBeforeLeft)"),
        (7, "const bool nativeHudSourceChanged = exactNativeHud &&",
             "const bool nativeHudSourceChanged = false &&"),
        (7, "OutRunVR::HudNativeSource::SameSourceAfterNativeUpload(",
             "OutRunVR::HudNativeSource::NeverSameSource("),
        (7, "const bool goalSourceChanged = exactGoalEye &&",
             "const bool goalSourceChanged = false &&"),
        (7, "const bool stageSourceChanged = exactStageEye &&",
             "const bool stageSourceChanged = false &&"),
        (7, "OutRunVR::StageExtensionPhysical::SameAfterNativeLeft(",
             "OutRunVR::StageExtensionPhysical::NeverSameAfterLeft("),
        (8, "run: python tools/verify_dx9ex_r84_lens_source.py", "run: echo BYPASS"),
        (9, "ScopedExactLensCentreGpuDraw centreGpuOwner(", "/*lost owner*/ centreGpuOwner("),
        (10, "!queued && scope == RenderScope::WorldBillboard",
             "scope == RenderScope::WorldBillboard"),
        (10, "producer == ProducerToken::LensFlareCentre",
             "producer == ProducerToken::None"),
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
            "!drawCommand.IsDirectWorldLensCentre()",
            "R29OwnerCurrentShaderEpoch(currentShader, currentShaderEpoch)",
            "OutRunVRRenderer::GetLastGameWvpPoseEpoch(),",
            "R29OwnerTopLevelDrawSerial()",
            "sourceProducer == ProducerToken::LensFlareCentre",
        ):
            start = mod[2].index("bool R30HasExactLensCentreRawWvp(")
            end = mod[2].index("bool R30HasExactCarBaseShadowRawWvp(", start)
            owned = mod[2][start:end]
            assert old in owned, "C993 provenance mutant missing exact owner: " + old
            # R23 has already incremented the physical Draw serial before
            # R30/R33. R30 consumes that CURRENT serial in BOTH source-age and
            # nested SceneEffect provenance checks. Mutate both callsites.
            if old == "R29OwnerTopLevelDrawSerial()":
                assert owned.count(old) == 2
                owned = owned.replace(old, new)
            else:
                owned = owned.replace(old, new, 1)
            mod[2] = mod[2][:start] + owned + mod[2][end:]
        elif idx == 2 and old in (
            "headPoseSequence != stereo.poseSequence",
            "std::memcpy(&rawUploadedT, rawGameWvp, sizeof(rawUploadedT))",
            "R30InvertBaseProjectionCached(baseProjection,",
            "screenKind == R30ScreenSpaceKind::ExactCarBaseShadowWorld;",
            "? R30HasExactCarBaseShadowRawWvp(rawGameWvp)",
            ": R30HasExactLensCentreRawWvp(rawGameWvp)",
            "viewDepth < (exactShadow ? 0.05f : 1.25f)",
        ):
            start = mod[2].index(
                "if (screenKind == R30ScreenSpaceKind::ExactLensCentreWorld ||")
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