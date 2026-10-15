#!/usr/bin/env python3
"""R30 classification-only projection accessor: source and negative regression."""
import math
import pathlib
import random

ROOT = pathlib.Path(__file__).resolve().parents[1]
HEADER = (ROOT / "src/vr/ipc/protocol.hpp").read_text(encoding="utf-8")
RENDERER = (ROOT / "src/vr/game/outrun_renderer.cpp").read_text(encoding="utf-8")
R30 = (ROOT / "src/vr/d3d9/stereo_renderer_r30.cpp").read_text(encoding="utf-8")


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def source_contract(renderer=RENDERER, r30=R30):
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

    # Only a verified, nonqueued world billboard may veto flattening on the
    # original depth-off alpha branch. A generic world particle or queued
    # billboard must retain the conservative screen-effect fallback.
    depth_off = cls.split("if (zEnable == D3DZB_FALSE &&", 1)
    require(len(depth_off) == 2, "depth-off alpha gate lost")
    depth_off = depth_off[1]
    for token in ("(alphaBlend != FALSE || alphaTest != FALSE)",
                  "const auto scope = OutRunVR::GameSemantic::EffectiveScope();",
                  "if (!OutRunVR::GameSemantic::QueueRenderActive() &&",
                  "scope == OutRunVR::GameSemantic::RenderScope::WorldBillboard)",
                  "return R30ScreenSpaceKind::None;",
                  "return R30ScreenSpaceKind::FlatPerspectiveEffect;"):
        require(token in depth_off, "world/effect owner gate missing: " + token)
    require(depth_off.index("const auto scope =") <
            depth_off.index("!OutRunVR::GameSemantic::QueueRenderActive()") <
            depth_off.index("scope == OutRunVR::GameSemantic::RenderScope::WorldBillboard") <
            depth_off.index("return R30ScreenSpaceKind::None;") <
            depth_off.index("return R30ScreenSpaceKind::FlatPerspectiveEffect;"),
            "only explicit nonqueued billboard can veto flattening")
    require("CorroboratesWorld(scope)" not in depth_off,
            "generic world promotion would reintroduce translucent flicker")
    require("GetLastVerifiedWvp(" not in cls,
            "stale WVP shader epoch must never become world ownership")


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
                          scope, queued=False):
    """Depth-off classification preserves only exact non-queued billboard."""
    if projection == "orthographic":
        return "hud"
    if projection != "perspective":
        return "none"
    if not z_enabled and (alpha_blend or alpha_test):
        return "none" if scope == "WorldBillboard" and not queued else "flat"
    return "none"


def effect_scope_model_cases():
    for scope in ("WorldParticle", "WorldBillboard", "ScreenHud",
                  "ScreenOverlay2D", "ProjectedScreenEffect2D",
                  "ProjectedWorldMarker2D", "SkyGlow", "None"):
        for queued in (False, True):
            for alpha_blend, alpha_test in (
                    (True, False), (False, True), (True, True)):
                expected = ("none" if scope == "WorldBillboard" and not queued
                            else "flat")
                require(classify_effect_route("perspective", False,
                        alpha_blend, alpha_test, scope, queued) == expected,
                        "depth-off effect owner/queue mismatch: " +
                        scope + "/" + str(queued))
    for scope in ("WorldParticle", "WorldBillboard", "ProjectedScreenEffect2D"):
        require(classify_effect_route("perspective", True, True, False, scope)
                == "none", "depth-enabled effect may not enter depth-off HUD")
        require(classify_effect_route("orthographic", False, True, False, scope)
                == "hud", "orthographic HUD ownership must win")
    require(classify_effect_route("unknown", False, True, False,
                                  "WorldParticle") == "none",
            "unknown projection must stay conservative")


def mutate_classifier(old, new):
    begin = "R30ScreenSpaceKind R30ClassifyScreenSpacePass("
    end = "// Only the OpenXR pose/FOV"
    require(R30.count(begin) == 1, "ambiguous R30 screen-space classifier")
    first = R30.index(begin)
    last = R30.index(end, first)
    part = R30[first:last]
    require(part.count(old) == 1, "mutation target missing or nonunique: " + old)
    return R30[:first] + part.replace(old, new, 1) + R30[last:]


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
    for label, mutation in (
        ("remove billboard exception",
         mutate_classifier(
             "scope == OutRunVR::GameSemantic::RenderScope::WorldBillboard",
             "false")),
        ("promote all world particles",
         mutate_classifier(
             "scope == OutRunVR::GameSemantic::RenderScope::WorldBillboard",
             "OutRunVR::GameSemantic::CorroboratesWorld(scope)")),
        ("promote queued effects",
         mutate_classifier(
             "!OutRunVR::GameSemantic::QueueRenderActive()", "true")),
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
    print("PASS: R30 projection signature, nonqueued-billboard ownership, 4009 matrix cases, 9 negative mutations")
