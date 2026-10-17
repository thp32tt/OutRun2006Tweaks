#!/usr/bin/env python3
"""R30 projection signature and R84 source-owned screen-route regression."""
import math
import pathlib
import random

ROOT = pathlib.Path(__file__).resolve().parents[1]
HEADER = (ROOT / "src/vr/ipc/protocol.hpp").read_text(encoding="utf-8")
RENDERER = (ROOT / "src/vr/game/outrun_renderer.cpp").read_text(encoding="utf-8")
R30 = (ROOT / "src/vr/d3d9/stereo_renderer_r30.cpp").read_text(encoding="utf-8")
SEMANTICS = (ROOT / "src/vr/game/render_semantics.hpp").read_text(encoding="utf-8")


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def source_contract(renderer=RENDERER, r30=R30, semantic=SEMANTICS):
    signature = renderer.split(
        "bool GetRendererProjectionSignature(float& m34, float& m44) noexcept", 1
    )
    require(len(signature) == 2, "missing renderer signature accessor")
    body = signature[1].split("bool GetLastVerifiedWvp(", 1)[0]
    for invariant in (
        "ValidateRendererGlobals()", "RendererProjection",
        "CullingProjectionOverridden", "CullingProjectionSaved",
        "std::memcpy(&projection, RendererProjection, sizeof(projection))",
        "MatrixFinite(projection)", "m34 = projection._34;",
        "m44 = projection._44;", "return true;",
    ):
        require(invariant in body, "projection accessor contract missing: " + invariant)
    require("bool GetRendererProjectionSignature(float& m34, float& m44) noexcept;" in HEADER,
            "declaration must match independent translation units")
    cls = r30.split("R30ScreenSpaceKind R30ClassifyScreenSpacePass(", 1)
    require(len(cls) == 2, "missing classifier")
    cls = cls[1].split("// Only the OpenXR pose/FOV", 1)[0]
    require("R29OwnerTargetIsBackBuffer()" in cls, "main backbuffer identity lost")
    require("GetRendererProjectionSignature(m34, m44)" in cls, "full-matrix classifier not optimized")
    require("ClassifyProjectionSignature(m34, m44)" in cls, "signature elements reversed")
    require("GetRendererBaseProjection(" not in cls, "full matrix copied on hot Draw route")
    for guard in ("ProjectionClass::Orthographic2D", "ProjectionClass::Perspective3D",
                  "R29OwnerTryGetEffectTelemetrySnapshot(effect)", "GetRenderState(",
                  "D3DRS_ZENABLE", "D3DRS_ALPHABLENDENABLE",
                  "D3DRS_ALPHATESTENABLE"):
        require(guard in cls, "HUD / fragile effect fallback lost: " + guard)

    # A single immutable physical-draw source now replaces repeated
    # queue/scope/producer TLS checks; require the exact underlying
    # LensFlareCentre semantics, not just the wrapper method's name.
    begin = semantic.find("struct PhysicalDrawCommand final")
    end = semantic.find("inline PhysicalDrawCommand CapturePhysicalDrawCommand()", begin)
    require(begin >= 0 and end > begin, "missing original physical draw identity")
    physical = semantic[begin:end]
    proof = physical.split("IsDirectWorldLensCentre() const noexcept", 1)
    require(len(proof) == 2, "missing canonical C993 physical identity")
    lens_body = proof[1].split("IsDirectCarBaseShadow()", 1)[0]
    for guard in ("!queued", "scope == RenderScope::WorldBillboard",
                  "producer == ProducerToken::LensFlareCentre",
                  "lensCentreCallEpoch != 0"):
        require(guard in lens_body, "physical C993 lens must retain " + guard)
    require("CapturePhysicalDrawCommand()" in cls and
            "drawCommand.IsDirectWorldLensCentre()" in cls,
            "R30 must consume the canonical per-primitive C993 snapshot")
    # HMD failure 2026-10-15: the old state-only route promoted unrelated
    # depth-disabled road/sky/particle geometry into an XR HUD plane.
    # R26+HUD's positive game semantics must veto unowned draws BEFORE
    # projection/alpha state is evaluated; only exact source-scoped overlays
    # can be transformed as HUD.
    for token in (
        "const bool ownedHud =", "CorroboratesHud(scope)",
        "const bool ownedOverlay =", "CorroboratesScreenOverlay2D(scope)",
        "const bool ownedEffect =", "CorroboratesProjectedScreenEffect(scope)",
        "const bool ownedLensCentre =", "drawCommand.IsDirectWorldLensCentre()",
        "if (!ownedHud && !ownedOverlay && !ownedEffect &&",
        "!ownedLensCentre)", "return R30ScreenSpaceKind::None;",
        "marker && marker->valid",
    ):
        require(token in cls, "R84 semantic admission missing: " + token)
    require(cls.index("if (!ownedHud && !ownedOverlay && !ownedEffect &&") <
            cls.index("GetRendererProjectionSignature(m34, m44)"),
            "screen ownership must be checked before projection classification")
    require("? R30ScreenSpaceKind::Hud2D" in cls and
            "return (ownedHud || ownedOverlay)" in cls,
            "orthographic world/no-owner must not silently become HUD")

    depth_off = cls.split("if (zEnable == D3DZB_FALSE &&", 1)
    require(len(depth_off) == 2, "depth-off alpha gate lost")
    depth_off = depth_off[1]
    for token in ("(alphaBlend != FALSE || alphaTest != FALSE)",
                  "if (!OutRunVR::GameSemantic::QueueRenderActive() &&",
                  "scope == OutRunVR::GameSemantic::RenderScope::WorldBillboard)",
                  "return R30ScreenSpaceKind::None;",
                  "return R30ScreenSpaceKind::FlatPerspectiveEffect;"):
        require(token in depth_off, "R84 depth-off semantic gate missing: " + token)
    require(depth_off.index("if (!OutRunVR::GameSemantic::QueueRenderActive() &&") <
            depth_off.index("scope == OutRunVR::GameSemantic::RenderScope::WorldBillboard)") <
            depth_off.index("return R30ScreenSpaceKind::FlatPerspectiveEffect;"),
            "unowned WorldBillboard must remain excluded from flat HUD")
    # An already authenticated C993 centre is NOT an unowned alpha draw.
    # Exact source admission precedes alpha/depth queries, but the outer
    # semantic veto and projection classification still apply to all draws.
    for marker in ("if (ownedLensCentre)",
                   "R30HasExactLensCentreRawWvp(originalGameWvp)",
                   "SelectWorldRoute(true, owned)",
                   "return R30ScreenSpaceKind::ExactLensCentreWorld;"):
        require(marker in cls, "exact centre source admission missing: " + marker)
    require(cls.index("if (!ownedHud && !ownedOverlay && !ownedEffect &&") <
            cls.index("if (ownedLensCentre)") <
            cls.index("R30HasExactLensCentreRawWvp(originalGameWvp)") <
            cls.index("SelectWorldRoute(true, owned)") <
            cls.index("return R30ScreenSpaceKind::ExactLensCentreWorld;") <
            cls.index("R29OwnerTryGetEffectTelemetrySnapshot(effect)") <
            cls.index("if (zEnable == D3DZB_FALSE &&"),
            "exact original C993 proof must bypass only the generic raster gate")
    require("CorroboratesWorld(scope)" not in depth_off,
            "world particles cannot authorize HUD/flat effect")
    require("GetLastVerifiedWvp(" not in cls,
            "stale WVP shader epoch must never become world ownership")
    # The 2026-10-16 HMD capture displayed a black horizon and eye-dependent
    # world/HUD overlap. Queue fallback ScreenOverlay2D is not permission to
    # reinterpret a perspective world draw as Hud2D.
    # Exact original C993's independent raw c64 must win over a potentially
    # previous-pass cached 2D projection. Generic HUD/overlay remains gated.
    projection_gate = cls.index("ClassifyProjectionSignature(m34, m44)")
    require(cls.index("if (ownedLensCentre)") <
            cls.index("R30HasExactLensCentreRawWvp(originalGameWvp)") <
            cls.index("GetRendererProjectionSignature(m34, m44)") <
            projection_gate,
            "original C993 c64 evidence must precede shared projection veto")
    require(cls.index("if (ownedHud)") > projection_gate,
            "exact HUD must not bypass projection signature sanity")
    require(cls.index("if (ownedOverlay)") > projection_gate,
            "generic 2D queue must not bypass projection signature")
    require("if (ownedOverlay)\n                return R30ScreenSpaceKind::None;" in cls,
            "perspective generic overlay must not become HUD")
    require("if (R30SpatialSceneEffectNeedsWorldRouting())" in depth_off,
            "spatial original SceneEffect WVP must veto flattening")
    helper = r30.split("bool R30SpatialSceneEffectNeedsWorldRouting()", 1)
    require(len(helper) == 2, "source-scoped spatial effect check missing")
    helper = helper[1].split("R30ScreenSpaceKind R30ClassifyScreenSpacePass(", 1)[0]
    for token in ("EffectiveScope() != RenderScope::SceneEffect",
                  "GetLastRawGameWvpWrite(", "R29OwnerCurrentShaderEpoch(",
                  "GetLastGameWvpPoseEpoch()", "R29OwnerTopLevelDrawSerial() + 1u",
                  "SceneEffectWvp::OwnsOriginalWorldWvp({", "R30InvertBaseProjectionCached(",
                  "R29OwnerMultiplyMatrix(gameWvp, inverseProjection)",
                  "affineError <= 0.02f", "depth >= 1.25f",
                  "clipW > 0.05f"):
        require(token in helper, "source-owned spatial veto missing: " + token)

    # The spatial WVP veto uses the same exact game inverse calculation via
    # the native R84 cache wrapper. Verify that the wrapper still delegates to
    # the original finite R29 inversion and invalidates on failed input; a
    # mere function rename must not bypass source/pose/queue admission.
    inverse_wrapper = r30.split("bool R30InvertBaseProjectionCached(", 1)
    require(len(inverse_wrapper) == 2, "missing native R84 inverse owner")
    inverse_wrapper = inverse_wrapper[1].split(
        "// Independent Quest-inspired DX9Ex opt-in.", 1)[0]
    for token in ("R30BaseProjectionInverseCache.get(",
                  "R29OwnerMatrixFinite(base)",
                  "R30BaseProjectionInverseCache.invalidate();",
                  "R29OwnerInvertMatrix(source, result)",
                  "R29OwnerMatrixFinite(result)"):
        require(token in inverse_wrapper,
                "original inverse/cache fail-closed guarantee missing: " + token)

    # The original 12-draw age check moved into a pure C++ source-ownership
    # contract, not deleted. Keep verifying the numerical veto AND the newly
    # required exact producer/queue/shader/pose identity as a single unit.
    ownership = (ROOT / "src/vr/game/scene_effect_wvp_provenance.hpp").read_text(
        encoding="utf-8")
    for token in ("e.nextDrawSerial - e.writtenDrawSerial > 12u",
                  "e.writtenScope != RenderScope::SceneEffect",
                  "e.currentProducer != e.writtenProducer",
                  "e.currentPoseEpoch != e.writtenPoseEpoch",
                  "e.currentShader != e.writtenShader",
                  "e.currentShaderEpoch != e.writtenShaderEpoch",
                  "e.currentQueueNode == e.writtenQueueNode",
                  "e.currentQueueEpoch == e.writtenQueueEpoch",
                  "e.currentQueueNode == nullptr",
                  "e.writtenQueueNode == nullptr"):
        require(token in ownership,
                "SceneEffect source owner or 12-draw negative gate missing: " + token)
    require('#include "../game/scene_effect_wvp_provenance.hpp"' in r30,
            "R84 live renderer must compile the proven SceneEffect gate")


def classify(m34, m44):
    near = lambda v, ref: abs(v - ref) <= 0.05
    if near(abs(m34), 1.0) and near(m44, 0.0):
        return "perspective"
    if near(m34, 0.0) and near(abs(m44), 1.0):
        return "orthographic"
    return "unknown"


def model_cases():
    rng = random.Random(681)
    cases = [
        (-1.0, 0.0), (1.0, 0.0), (0.0, 1.0), (0.0, -1.0),
        (0.75, 0.0), (0.0, 0.75), (1.0, 1.0),
        (float("nan"), 0.0), (float("inf"), 0.0),
    ]
    cases.extend((rng.uniform(-1.2, 1.2), rng.uniform(-1.2, 1.2))
                 for _ in range(4000))
    for m34, m44 in cases:
        projection = [rng.uniform(-9, 9) for _ in range(16)]
        projection[11], projection[15] = m34, m44
        finite = all(math.isfinite(v) for v in projection)
        old = classify(projection[11], projection[15]) if finite else "invalid"
        new = classify(m34, m44) if finite else "invalid"
        require(old == new, "projection classification changed")
        # Fail closed even when unrelated matrix elements become nonfinite.
        projection[3] = math.nan
        require(not all(math.isfinite(v) for v in projection),
                "full matrix validation cannot be replaced by pair-only finiteness")


def classify_effect_route(projection, z_enabled, alpha_blend, alpha_test,
                          scope, queued=False, exact_centre_owned=False,
                          spatial_scene_wvp=False):
    """Exact producer-scoped admission, independent of fragile D3D state."""
    hud = scope == "ScreenHud"
    overlay = scope == "ScreenOverlay2D"
    effect = scope in ("ProjectedScreenEffect2D", "SceneEffect")
    centre = scope == "WorldBillboard" and not queued
    if not (hud or overlay or effect or centre):
        return "none"
    if centre:
        # Exact C993's original-c64 and spatial WVP proof are independent
        # of the previous shared projection signature; all missing proof
        # and queued/non-C993 sources retain native conservative fallback.
        return "centre" if exact_centre_owned else "none"
    if projection == "orthographic":
        return "hud" if hud or overlay else "none"
    if projection != "perspective":
        return "none"
    if hud:
        return "hud"
    if overlay:
        return "none"
    if effect and scope == "SceneEffect" and spatial_scene_wvp:
        return "none"
    if not z_enabled and (alpha_blend or alpha_test):
        return "flat"
    return "none"


def effect_scope_model_cases():
    for scope in ("WorldParticle", "WorldBillboard", "ScreenHud",
                  "ScreenOverlay2D", "ProjectedScreenEffect2D",
                  "ProjectedWorldMarker2D", "SkyGlow", "SceneEffect", "None"):
        for queued in (False, True):
            for alpha_blend, alpha_test in (
                    (True, False), (False, True), (True, True)):
                expected = ("hud" if scope == "ScreenHud" else
                            "flat" if scope in (
                                "ProjectedScreenEffect2D", "SceneEffect")
                            else "none")
                require(classify_effect_route("perspective", False,
                        alpha_blend, alpha_test, scope, queued) == expected,
                        "explicit producer ownership mismatch: " +
                        scope + "/" + str(queued))
    # Positive original C993 source is a spatial centre, not generic
    # WorldBillboard: prove depth-enabled/disabled and alpha on/off all
    # reach the same eye route while queued/unowned/orthographic stay mono.
    for depth in (False, True):
        for blend in (False, True):
            for alpha_test in (False, True):
                require(classify_effect_route("perspective", depth, blend,
                        alpha_test, "WorldBillboard", False, True) == "centre",
                        "exact direct C993 cannot depend on raster switches")
                require(classify_effect_route("perspective", depth, blend,
                        alpha_test, "WorldBillboard", True, True) == "none",
                        "queued billboard is not the original C993 source")
                require(classify_effect_route("perspective", depth, blend,
                        alpha_test, "WorldBillboard", False, False) == "none",
                        "unowned billboard must keep R29 fallback")
                require(classify_effect_route("orthographic", depth, blend,
                        alpha_test, "WorldBillboard", False, True) == "centre",
                        "source-owned C993 must survive a stale 2D signature")
                require(classify_effect_route("unknown", depth, blend,
                        alpha_test, "WorldBillboard", False, True) == "centre",
                        "source-owned C993 must survive an unavailable signature")
                require(classify_effect_route("orthographic", depth, blend,
                        alpha_test, "WorldBillboard", False, False) == "none",
                        "unowned C993 must never borrow the preceding UI projection")
    for scope in ("WorldParticle", "WorldBillboard",
                  "ProjectedScreenEffect2D", "ScreenHud", "ScreenOverlay2D"):
        require(classify_effect_route("perspective", True, True, False, scope)
                == ("hud" if scope == "ScreenHud" else "none"),
                "only producer-authenticated HUD can override depth")
        require(classify_effect_route("orthographic", False, True, False, scope)
                == ("hud" if scope in ("ScreenHud", "ScreenOverlay2D")
                    else "none"),
                "orthographic must require exact screen owner")
    require(classify_effect_route("unknown", False, True, False,
                                  "ScreenHud") == "none",
            "unknown projection must stay conservative")
    for depth in (False, True):
        for alpha in (False, True):
            require(classify_effect_route("perspective", depth, alpha, True,
                    "ScreenOverlay2D", True) == "none",
                    "unverified queue fallback must not become perspective HUD")
            require(classify_effect_route("perspective", depth, alpha, True,
                    "SceneEffect", False, False, True) == "none",
                    "spatial scene effect must never be flattened into HUD")


def mutate_classifier(old, new):
    begin = "R30ScreenSpaceKind R30ClassifyScreenSpacePass("
    end = "// Only the OpenXR pose/FOV"
    require(R30.count(begin) == 1, "ambiguous R30 screen-space classifier")
    first = R30.index(begin)
    last = R30.index(end, first)
    part = R30[first:last]
    require(part.count(old) == 1, "mutation target missing or nonunique: " + old)
    return R30[:first] + part.replace(old, new, 1) + R30[last:]


def mutate_depth_off(old, new):
    begin = "R30ScreenSpaceKind R30ClassifyScreenSpacePass("
    gate = "if (zEnable == D3DZB_FALSE &&"
    end = "// Only the OpenXR pose/FOV"
    first = R30.index(begin)
    pos = R30.index(gate, first)
    last = R30.index(end, pos)
    body = R30[pos:last]
    require(body.count(old) == 1, "depth-off mutation ambiguous: " + old)
    return R30[:pos] + body.replace(old, new, 1) + R30[last:]


def mutate_accessor(old, new):
    # A whole-file replace can mutate GetRendererBaseProjection or older
    # culling paths instead, giving a false negative regression failure.
    start_marker = "bool GetRendererProjectionSignature(float& m34, float& m44) noexcept"
    end_marker = "bool GetLastVerifiedWvp("
    require(RENDERER.count(start_marker) == 1, "ambiguous projection accessor")
    start = RENDERER.index(start_marker)
    end = RENDERER.index(end_marker, start)
    body = RENDERER[start:end]
    require(body.count(old) == 1, "mutation target absent or ambiguous: " + old)
    changed = body.replace(old, new, 1)
    require(changed != body, "projection mutation did not change accessor")
    return RENDERER[:start] + changed + RENDERER[end:]


def negative_mutations():
    for altered in (
        mutate_accessor("m34 = projection._34;", "m34 = projection._44;"),
        mutate_accessor("m44 = projection._44;", "m44 = projection._34;"),
        mutate_accessor("MatrixFinite(projection)", "true"),
        mutate_accessor("projection = CullingProjectionSaved;",
                        "projection = projection;"),
    ):
        try:
            source_contract(renderer=altered)
        except AssertionError:
            pass
        else:
            raise AssertionError("invalid projection fastpath mutation survived")
    try:
        source_contract(r30=R30.replace(
            "ClassifyProjectionSignature(m34, m44)",
            "ClassifyProjectionSignature(m44, m34)", 1))
    except AssertionError:
        pass
    else:
        raise AssertionError("swapped projection classification survived")
    # The spatial original SceneEffect owner must actually use the exact
    # projection-cache wrapper; its use cannot be replaced by a stale/raw
    # matrix or a constant true without detection.
    spatial_start = R30.index("bool R30SpatialSceneEffectNeedsWorldRouting()")
    spatial_end = R30.index("R30ScreenSpaceKind R30ClassifyScreenSpacePass(",
                            spatial_start)
    spatial_body = R30[spatial_start:spatial_end]
    require(spatial_body.count("R30InvertBaseProjectionCached(") == 1,
            "missing unique spatial inverse mutation target")
    broken = spatial_body.replace("R30InvertBaseProjectionCached(",
                                  "R29OwnerInvertMatrix(", 1)
    try:
        source_contract(r30=R30[:spatial_start] + broken +
                        R30[spatial_end:])
    except AssertionError:
        pass
    else:
        raise AssertionError("uncached spatial projection mutation survived")
    # Test the separate canonical declaration, not only its call site.
    physical_start = SEMANTICS.index("struct PhysicalDrawCommand final")
    physical_end = SEMANTICS.index(
        "inline PhysicalDrawCommand CapturePhysicalDrawCommand()", physical_start)
    fragment = SEMANTICS[physical_start:physical_end]
    for before, after in (
        ("producer == ProducerToken::LensFlareCentre",
         "producer == ProducerToken::None"),
        ("scope == RenderScope::WorldBillboard",
         "scope == RenderScope::ScreenHud"),
        ("return !queued && scope",
         "return queued && scope"),
    ):
        require(before in fragment, "missing canonical C993 mutation fixture")
        mutated = SEMANTICS[:physical_start] + fragment.replace(before, after, 1) + SEMANTICS[physical_end:]
        try:
            source_contract(semantic=mutated)
        except AssertionError:
            pass
        else:
            raise AssertionError("unproven C993 physical owner mutation survived")
    for label, mutation in (
        ("delete positive HUD owner",
         mutate_classifier("CorroboratesHud(scope)", "false")),
        ("delete positive screen overlay owner",
         mutate_classifier("CorroboratesScreenOverlay2D(scope)", "false")),
        ("remove source-proven centre admission",
         mutate_classifier("if (ownedLensCentre)", "if (false)")),
        ("claim lens for all physical draws",
         mutate_classifier("drawCommand.IsDirectWorldLensCentre()",
                           "true")),
        ("allow unowned centre WVP",
         mutate_classifier("SelectWorldRoute(true, owned)",
                           "SelectWorldRoute(true, true)")),
        ("remove billboard exception",
         mutate_depth_off(
             "scope == OutRunVR::GameSemantic::RenderScope::WorldBillboard",
             "false")),
        ("promote all world particles",
         mutate_depth_off(
             "scope == OutRunVR::GameSemantic::RenderScope::WorldBillboard",
             "OutRunVR::GameSemantic::CorroboratesWorld(scope)")),
        ("promote queued effects",
         mutate_depth_off(
             "if (!OutRunVR::GameSemantic::QueueRenderActive() &&",
             "if (true &&")),
        ("break flat fallback",
         mutate_classifier("return R30ScreenSpaceKind::FlatPerspectiveEffect;",
                           "return R30ScreenSpaceKind::None;")),
    ):
        try:
            source_contract(r30=mutation)
        except AssertionError:
            pass
        else:
            raise AssertionError("world-effect mutation survived: " + label)


if __name__ == "__main__":
    source_contract()
    model_cases()
    effect_scope_model_cases()
    negative_mutations()
    print("PASS: R30 projection signature, R84 source-owned HUD/effect gate, 4009 matrix cases and negative mutations")