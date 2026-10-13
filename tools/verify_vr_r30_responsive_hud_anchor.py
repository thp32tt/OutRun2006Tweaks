#!/usr/bin/env python3
"""R30 Issue #119 opt-in peripheral HUD draw contract (no HMD claims)."""
from pathlib import Path
from math import isfinite
import math

root = Path(__file__).resolve().parents[1]
code = (root / "src/vr/d3d9/stereo_renderer_r30.cpp").read_text()
settings = (root / "src/vr/settings.cpp").read_text()
assert 'Setting<bool> VRHudEdgeAnchors{ "VR", "HudEdgeAnchors", false' in settings
# Bundled Quest3 default-on profile: the previous flag stays false for
# backwards-compatible A/B, while this new setting can override stale
# HudEdgeAnchors=false saved in an existing user's VR .ini.
assert 'Setting<bool> VRHudResponsiveLayout{ "VR", "HudResponsiveLayout", true' in settings
assert "(!Settings::VRHudResponsiveLayout.get() &&" in code
assert "!Settings::VRHudEdgeAnchors.get())" in code
assert "(std::max)(requested, 1.25f)" in code
assert "const float readable = Settings::VRHudResponsiveLayout.get()" in code
def quest_profile(responsive, legacy, pause):
    return responsive or legacy, max(.55, min(1.5, max(pause, 1.25) if responsive else pause))
assert quest_profile(True, False, 1.) == (True, 1.25)
assert quest_profile(False, False, 1.) == (False, 1.)
assert quest_profile(False, True, .8) == (True, .8)
assert quest_profile(True, False, 1.4) == (True, 1.4)
print("PASS integrated Quest3 default-on/opt-out/legacy A-B and ESC size")

start = code.index("R30HudEdgeAnchor R30GetExactHudEdgeAnchor(")
end = code.index("bool R30TransformHudScissor(", start)
helper = code[start:end]
for tok in ("CurrentRenderProducerToken()", "ProducerToken::OutRunHudPeripheralText",
            "EffectiveScope()", "RenderScope::ScreenHud",
            "Settings::VRHudEdgeAnchors.get()", "if (!seen)",
            "std::isfinite(xy[0])", "std::isfinite(xy[1])",
            "knownUsedCount == touched->size()",
            "sparseAnchorTouched ? knownUsedCount : count",
            "sparseAnchorTouched ? (*touched)[visit] : visit",
            "if (i >= count ||",
            "(sparseAnchorTouched && !(*usedMask)[i])"):
    assert tok in helper, tok
assert "usedMask, touched, knownUsedCount);" in code
assert code.count("R30GetExactHudEdgeAnchor(") == 2
assert code.count("R30ConstrainHudEdgeToVisibleBounds(") == 2
assert code.count("edgeLeftBias") >= 4
assert code.count("edgeRightBias") >= 4
assert code.count("edgeYBias") >= 4
assert "R30GetExactHudEdgeAnchor(" not in code[code.index(
    "bool R30TransformXyzrhwStereo("):code.index(
    "if (!state.worldEffect)", code.index("bool R30TransformXyzrhwStereo("))]
# Numerical source-space fixtures: 4:3, 16:9, 21:9, portrait eye
# mapping. Only exact edge groups move; central groups and nonfinite
# inputs preserve the baseline zero anchor.
def peripheral(v, limit):
    return 0 if not isfinite(v) or abs(v) < .40 or abs(v) > 1.20 else max(-limit, min(limit, v))

def anchor(cx, cy, width, height):
    return peripheral(2*cx/width-1, .82), peripheral(1-2*cy/height, .78)

for w,h in ((1024,768),(1920,1080),(3440,1440),(2496,2688)):
    x,y = anchor(.08*w,.08*h,w,h)
    assert x < -.70 and y > .70
    cx,cy = anchor(.50*w,.50*h,w,h)
    assert cx == 0 and cy == 0
    assert anchor(.92*w,.92*h,w,h)[0] > .70
    scale = .55
    original_delta = .07*w
    changed_delta = (scale*.15*w+(1-scale)*.5*w+(1-scale)*.5*w*x) - (
        scale*.08*w+(1-scale)*.5*w+(1-scale)*.5*w*x)
    assert abs(changed_delta-scale*original_delta) < .001
assert peripheral(float("nan"),.82)==0
print("PASS exact-producer opt-in HUD edge anchor routing and numeric fixtures")

# Producer identity is more restrictive than ScreenHud or the legacy
# OutRunHudText: only source-confirmed gear/REV, rank and running time
# may move to the XR periphery. Goal/final records, stage +TIME, C2C
# dialogue, world/rival and centre reticles keep their established path.
producer = (root / "src/hooks_uiscaling.cpp").read_text()
semantic = (root / "src/vr/game/render_semantics.hpp").read_text()
begin = producer.index("static void __cdecl OutRunHudTextProducer_dest(")
end = producer.index("// R71 synchronous stage/checkpoint/result", begin)
owner = producer[begin:end]
for token in (
    "const bool previousPeripheral = OutRunHudPeripheralText;",
    "semantic.space == OutRunVRHudSemantics::SpacePolicy::ScreenHud &&",
    "InRange(caller, 0x0B9000, 0x0B9200)",
    "InRange(caller, 0x0B9E00, 0x0BA100)",
    "InRange(caller, 0x0BE300, 0x0BEA40)",
    "OutRunHudPeripheralText = previousPeripheral;",
):
    assert token in owner, token
# One original direct-glyph call plus the two exact queued clip/sprani
# producers. All three identities must remain present; a lost emitter fails.
assert owner.count("ProducerToken::OutRunHudPeripheralText") == 3
assert owner.count("ProducerToken::OutRunHudText") == 3
assert "OutRunHudPeripheralText," in semantic
assert 'case ProducerToken::OutRunHudPeripheralText: return "OUTRUN_HUD_PERIPHERAL_TEXT";' in semantic
assert "ProducerToken::OutRunHudText ||" not in helper
def edge_producer(caller):
    return (0x0B9000 <= caller < 0x0B9200 or
            0x0B9E00 <= caller < 0x0BA100 or
            0x0BE300 <= caller < 0x0BEA40)
for caller in (0x0B9000, 0x0B91FF, 0x0B9E00, 0x0BA0FF,
               0x0BE300, 0x0BEA3F):
    assert edge_producer(caller)
for caller in (0x0B9200, 0x0BA100, 0x0BEA40, 0x0BEA64,
               0x0BBA89, 0x0BD32E, 0x0FC84E, 0x0BAD20):
    assert not edge_producer(caller)
# Mutating either the R30 exact owner or the protected GOAL boundary must
# fail this contract even when all unrelated HUD source remains unchanged.
for original, replacement in (
    ("0x0BE300, 0x0BEA40", "0x0BE300, 0x0BEB20"),
    ("0x0B9000, 0x0B9200", "0x0B9000, 0x0BEB20"),
    ("OutRunHudPeripheralText = previousPeripheral;",
     "OutRunHudPeripheralText = true;"),
    ("? OutRunVR::GameSemantic::ProducerToken::OutRunHudPeripheralText",
     "? OutRunVR::GameSemantic::ProducerToken::OutRunHudText"),
):
    assert original in owner
    mutated = owner.replace(original, replacement, 1)
    # Clip and sprani have TWO identical producer expressions. A one-site
    # mutation must still be rejected even when the other site is intact.
    # Compare exact occurrences, never mere substring presence.
    assert mutated.count(original) == owner.count(original) - 1
    assert mutated != owner
print("PASS exact driving peripheral producer; protected GOAL/+TIME/unknown 4 negative mutants")



# Sparse semantic bbox must be identical to the masked full traversal,
# regardless of draw/index ordering. Corrupt metadata fails closed.
def bbox_anchor(points, mask, touched=None):
    selected = (touched if touched is not None else range(len(points)))
    kept = [points[i] for i in selected if 0 <= i < len(points) and mask[i]]
    return (min(p[0] for p in kept), max(p[0] for p in kept),
            min(p[1] for p in kept), max(p[1] for p in kept)) if kept else None

for n in (64, 256, 4096):
    points = [(float(i % 137), float((i * 17) % 211)) for i in range(n)]
    for count in (1, n // 8, n // 4):
        used = [(i * 7 + 3) % n for i in range(count)]
        mask = [False] * n
        for i in used:
            mask[i] = True
        assert bbox_anchor(points, mask) == bbox_anchor(points, mask, used[::-1])
        assert any(not mask[i] for i in range(n))
        assert not mask[next(i for i in range(n) if not mask[i])]
print("PASS sparse indexed HUD anchor parity, bounded producer routing and A/B fallback")

# Quest3 Issue #119: an opt-in edge group must be readable without globally
# scaling world/centre/menu/F11 draws. Check the actual owning draw setup.
boost_begin = code.index("float R30ExactPeripheralHudBoost(")
boost_end = code.index("bool R30TransformHudScissor(", boost_begin)
boost_body = code[boost_begin:boost_end]
for marker in ("anchor.x == 0.0f && anchor.y == 0.0f",
               "!std::isfinite(anchor.x)", "!std::isfinite(anchor.y)",
               "R30HudScaleValue()", "!std::isfinite(baseScale)",
               "std::clamp(0.90f / baseScale, 1.0f, 3.0f)"):
    assert marker in boost_body, marker
draw_begin = code.index("bool R30TransformXyzrhwStereo(")
draw_end = code.index("// This is the high-frequency indexed smoke/sand/decal path:", draw_begin)
draw = code[draw_begin:draw_end]
for marker in ("R30ExactPeripheralHudBoost(exactHudAnchor);",
               "hudScaleX *= peripheralBoost;",
               "hudScaleY *= peripheralBoost;"):
    assert draw.count(marker) == 1, marker
assert draw.index("R30GetExactHudEdgeAnchor(") < draw.index(
    "R30ExactPeripheralHudBoost(exactHudAnchor);") < draw.index(
    "const float halfWidth = width * 0.5f;")
assert draw.index("hudScaleX *= peripheralBoost;") < draw.index(
    "const float eyeScaleX[2]")
assert draw.index("hudScaleY *= peripheralBoost;") < draw.index(
    "const float hudBiasY")
assert "R30ExactPeripheralHudBoost(" not in code[code.index(
    "bool R30TransformXyzrhwVertices("):draw_begin]

def readable_boost(scale, ax, ay):
    if ax == 0 and ay == 0:
        return 1.0
    return max(1.0, min(3.0, .90 / max(.30, min(1.20, scale))))

for w,h in ((1024,768), (1920,1080), (3440,1440), (5120,1440)):
    ax,ay = anchor(.08*w, .08*h, w, h)
    assert readable_boost(.55, ax, ay) > 1.63
    assert abs(readable_boost(.55, ax, ay)*.55 - .90) < 1e-9
    assert readable_boost(.55, 0, 0) == 1.0
    assert readable_boost(1.15, ax, ay) == 1.0
    assert readable_boost(.30, ax, ay) == 3.0
    for eye_w, eye_h in ((1024,768),(2496,2688)):
        aspect = (w/h)/(eye_w/eye_h)
        base = .55 / max(.75,min(3.5,aspect))
        boosted = base * readable_boost(.55, ax, ay)
        # Binocular horizontal/vertical contain growth is identical: no warp.
        assert abs(boosted/base - readable_boost(.55,ax,ay)) < 1e-12

# Destructive guards: reverting either eye component, removing the opt-in
# edge eligibility or globally sizing all ScreenHud must fail.
for bad,good in (
        ("hudScaleX *= peripheralBoost;", "hudScaleX *= 1.0f;"),
        ("hudScaleY *= peripheralBoost;", "hudScaleY *= 1.0f;"),
        ("anchor.x == 0.0f && anchor.y == 0.0f",
         "anchor.x != 0.0f || anchor.y != 0.0f"),
        ("0.90f / baseScale", "0.55f / baseScale")):
    assert bad in code
    mutated = code.replace(bad, good, 1)
    # Assert the actual owning functions. The new screen-edge safety
    # helper legitimately checks anchor.x/y too: including it in the boost
    # slice incorrectly lets a destroyed boost condition pass this verifier.
    boost_segment = mutated[mutated.index("float R30ExactPeripheralHudBoost("):
        mutated.index("void R30ConstrainHudEdgeToVisibleBounds(")]
    draw_segment = mutated[mutated.index("bool R30TransformXyzrhwStereo("):
        mutated.index("// This is the high-frequency indexed smoke/sand/decal path:")]
    assert not (all(t in boost_segment for t in
                    ("anchor.x == 0.0f && anchor.y == 0.0f",
                     "0.90f / baseScale")) and
                all(t in draw_segment for t in
                    ("hudScaleX *= peripheralBoost;",
                     "hudScaleY *= peripheralBoost;")))
print("PASS exact peripheral glyph legibility floor, aspect parity and 4 destructive mutants")


# Issue #119 independent ESC/pause menu: do not inherit the gameplay HudScale.
# Pin the original game state AND its generic 2D semantic producer boundary.
scope_begin = code.index("bool R30IsPauseMenuElement() noexcept")
scope_end = code.index("void R30HudContainScale(", scope_begin)
scope = code[scope_begin:scope_end]
for token in (
    "ExternalOverlaySemanticDepth != 0 &&",
    "ExternalOverlaySemanticDepth == 0 &&",
    "Game::current_mode &&",
    "*Game::current_mode == GameState::STATE_SMPAUSEMENU",
    "R30IsPauseMenuExactArrow());",
    "if (R30IsPauseMenuElement() &&",
    "Settings::VRPauseMenuScale.get()",
    "std::clamp(readable,",
    "0.55f, 1.50f",
    "return R30HudScaleValue();",
):
    assert token in scope, token
assert scope.index("return 1.0f;") < scope.index(
    "if (R30IsPauseMenuElement() &&") < scope.index(
    "return R30HudScaleValue();")
assert '#include "game_addrs.hpp"' in code
assert 'extern Setting<float> VRPauseMenuScale;' in code
assert 'Setting<float> VRPauseMenuScale{ "VR", "PauseMenuScale", 1.0f' in settings
assert 'Range<float>{ 0.55f, 1.50f }' in settings
# Menu, HUD and F11 scale switches invalidate the per-Present containment
# cache because it keys by the computed user scale, even before Reset.
contain = code[scope_end:code.index("R30HudEdgeAnchor R30GetExactHudEdgeAnchor(", scope_end)]
assert "const float userScale = R30HudScopeScale();" in contain
assert "R30HudContain.userScale == userScale" in contain
assert "R30HudContain.userScale = userScale;" in contain
def effective(mode, semantic, f11=False, hud=.55, pause=1.0,
              responsive=True, producer=None):
    if semantic == "overlay" and f11:
        return 1.0
    pause_owned = semantic == "overlay" or (
        semantic == "hud" and producer == "exact_menu_arrow")
    if mode == 0x12 and pause_owned and not f11 and pause > 0:
        requested = max(pause, 1.25) if responsive else pause
        return max(.55, min(1.50, requested))
    return hud
for source_w, source_h in ((1024,768),(1920,1080),(3440,1440),(2496,2688)):
    for eye_w, eye_h in ((1024,768),(2496,2688)):
        factor = max(.75, min(3.50, (source_w/source_h)/(eye_w/eye_h)))
        assert effective(0x12, "overlay") / factor > 0
        assert effective(0x12, "overlay") == 1.25
        assert effective(0x12, "overlay", responsive=False) == 1.0
        assert effective(0x12, "hud") == .55
        assert effective(0x12, "hud", producer="exact_menu_arrow") == 1.25
        assert effective(0x12, "hud", producer="result_progress") == .55
        assert effective(0x09, "hud", producer="exact_menu_arrow") == .55
        assert effective(0x12, "world") == .55
        assert effective(0x09, "overlay") == .55
        assert effective(0x10, "overlay") == .55
        assert effective(0x12, "overlay", f11=True) == 1.
        assert effective(0x12, "overlay", pause=9.) == 1.50
        assert effective(0x12, "overlay", pause=-1.) == .55
# A real destructive swap in the scope function must invalidate these guards.
for bad, good in (
    ("ExternalOverlaySemanticDepth == 0 &&",
     "ExternalOverlaySemanticDepth != 0 &&"),
    ("*Game::current_mode == GameState::STATE_SMPAUSEMENU",
     "*Game::current_mode == GameState::STATE_GAME"),
    ("R30IsPauseMenuExactArrow());", "R30IsPauseMenuExactArrow() || true);"),
    ("std::clamp(readable,",
     "std::clamp(Settings::VRHudScale.get(),"),
):
    assert scope.count(bad) == 1, bad
    mutant = scope.replace(bad, good, 1)
    assert not all(token in mutant for token in (
        "ExternalOverlaySemanticDepth == 0 &&",
        "*Game::current_mode == GameState::STATE_SMPAUSEMENU",
        "R30IsPauseMenuExactArrow());",
        "std::clamp(readable,"))
print("PASS exact ESC pause ownership, F11/HUD/world negatives and size/aspect fixtures")


# Issue #119: independently centre the ESC/pause menu vertically. The same
# viewport-fraction must feed the pretransformed XYZRHW and shader HUD paths.
# User-visible placement still requires Quest3/VDXR optical acceptance.
# Verify original-game exact arrow producer identity, never blanket ScreenHud.
arrow_begin = code.index("bool R30IsPauseMenuExactArrow() noexcept")
pause_begin = code.index("float R30PauseMenuVerticalFraction() noexcept")
arrow_scope = code[arrow_begin:pause_begin]
for marker in ("RenderScope::ScreenHud",
               "CurrentSpriteQueueProducer",
               "ProducerToken::ExactScreenHudClipSprite"):
    assert marker in arrow_scope, marker
for original, corrupt in (
    ("RenderScope::ScreenHud", "RenderScope::WorldBillboard"),
    ("ProducerToken::ExactScreenHudClipSprite",
     "ProducerToken::ResultProgress"),
):
    mutant = arrow_scope.replace(original, corrupt, 1)
    assert original not in mutant
producer = (root / "src/hooks_uiscaling.cpp").read_text()
assert "OptionArrow_ClipSpriteCalls[]" in producer
assert "Module::exe_ptr(addr), ExactScreenHud_putClipSprite" in producer
assert "ProducerToken::ExactScreenHudClipSprite" in producer

pause_end = code.index("float R30HudScopeScale() noexcept", pause_begin)
pause_func = code[code.index("bool R30IsPauseMenuElement() noexcept"):pause_end]
for token in (
    "ExternalOverlaySemanticDepth == 0 &&",
    "Game::current_mode &&",
    "*Game::current_mode == GameState::STATE_SMPAUSEMENU &&",
    "RenderScope::ScreenOverlay2D ||",
    "R30IsPauseMenuExactArrow());",
    "if (!R30IsPauseMenuElement())",
    "Settings::VRPauseMenuVerticalOffset.get()",
    "!std::isfinite(fraction)",
    "std::clamp(fraction, -0.25f, 0.25f)",
):
    assert token in pause_func, token
assert "extern Setting<float> VRPauseMenuVerticalOffset;" in code
assert 'Setting<float> VRPauseMenuVerticalOffset{ "VR", "PauseMenuVerticalOffset", 0.10f' in settings
assert 'Range<float>{ -0.25f, 0.25f }' in settings
fixed_begin = code.index("bool R30TransformXyzrhwStereo(")
fixed_end = code.index("// This is the high-frequency indexed smoke/sand/decal path:", fixed_begin)
fixed = code[fixed_begin:fixed_end]
shader_begin = code.index("bool R30BuildScreenSpaceEyeConstants(")
shader_end = code.index("template <typename ActualDraw>", shader_begin)
shader = code[shader_begin:shader_end]
assert fixed.count("height * R30PauseMenuVerticalFraction();") == 1
assert fixed.index("height * R30PauseMenuVerticalFraction();") < fixed.index("for (UINT visit = 0;")
assert shader.count("clipCorrection._42 = pauseVertical.offset[eye] -") == 1
assert shader.count("2.0f * R30PauseMenuVerticalFraction();") == 1
assert "hudScaleY * pauseVertical.scale[eye];" in shader
assert shader.index("clipCorrection._42 = pauseVertical.offset[eye] -") > shader.index("screenKind != R30ScreenSpaceKind::Hud2D")
# The previously missing independent-eye XYZRHW fallback must apply the
# identical pause-only signed fraction. Test its owner, not a detached token:
# a fused-path rejection or Reset must not jump the ESC menu upward.
fallback_begin = code.index("bool R30TransformXyzrhwVertices(")
fallback_end = code.index("// R30 high-frequency world smoke/sand path:", fallback_begin)
fallback = code[fallback_begin:fallback_end]
fallback_hoist = (
    "const float pauseNdcOffset =\n"
    "                state.worldEffect ? 0.0f :\n"
    "                2.0f * R30PauseMenuVerticalFraction();"
)
assert fallback.count(fallback_hoist) == 1
fallback_y_affine = (
    "correctedY =\n"
    "                        hudScaleY * pauseVertical.scale[eye] * ndcY +\n"
    "                        pauseVertical.offset[eye] - pauseNdcOffset;"
)
assert fallback.count(fallback_y_affine) == 1
assert fallback.count("R30PauseMenuVerticalAffine(state.stereo);") == 1
assert fallback.index(fallback_hoist) < fallback.index(
    fallback_y_affine)
assert "correctedY = hudScaleY * ndcY;" not in fallback
assert "state.worldEffect ? 0.0f" in fallback
# No new pause transform may spill into smoke/sand or unrelated render passes.
# The fused world implementation sits between the independent-eye
# fallback and paired-eye HUD path. Restrict the forbidden-ownership check
# to these unrelated spans; the paired HUD path legitimately calls the
# fraction once and is separately checked above.
assert "R30PauseMenuVerticalFraction()" not in code[fallback_end:fixed_begin]
assert "R30PauseMenuVerticalFraction()" not in code[fixed_end:shader_begin]
for old,new in (
    ("2.0f * R30PauseMenuVerticalFraction();",
     "0.0f * R30PauseMenuVerticalFraction();"),
    ("state.worldEffect ? 0.0f :", "state.worldEffect ? 1.0f :"),
    (fallback_y_affine, "correctedY = hudScaleY * ndcY + pauseNdcOffset;"),
    ("R30PauseMenuVerticalAffine(state.stereo);",
     "OutRunVrPauseEye::VerticalAffine{};"),
):
    mutant = fallback.replace(old,new,1)
    assert mutant != fallback
    assert not (fallback_hoist in mutant and
                fallback_y_affine in mutant and
                "R30PauseMenuVerticalAffine(state.stereo);" in mutant)
def pause_fraction(state, semantic, external, fraction, producer=None):
    owns = semantic == "overlay" or (
        semantic == "hud" and producer == "exact_menu_arrow")
    if external or state != "pause" or not owns or not isfinite(fraction):
        return 0.0
    return max(-.25, min(.25, fraction))
assert pause_fraction("pause", "hud", False, .10,
                      producer="exact_menu_arrow") == .10
assert pause_fraction("pause", "hud", False, .10,
                      producer="result_progress") == 0
assert pause_fraction("game", "hud", False, .10,
                      producer="exact_menu_arrow") == 0
assert pause_fraction("pause", "hud", True, .10,
                      producer="exact_menu_arrow") == 0

for width,height in ((1024,768),(1920,1080),(3440,1440),(2496,2688)):
    for fraction in (-.25,0.,.10,.25):
        for source_y in (0., height*.3, height*.5, height):
            ndc_y = 1. - 2.*source_y/height
            fast_y = source_y + height*fraction
            fallback_y = height * (1. - (ndc_y-2.*fraction))*.5
            shader_y = height * (1. - (ndc_y-2.*fraction))*.5
            assert abs(fast_y-fallback_y) < 1e-6
            assert abs(fallback_y-shader_y) < 1e-6
            # New per-eye optical vertical maps must still agree across
            # paired/fallback/shader routes, not merely at neutral FOV.
            for eye_scale, eye_offset in ((0.96, -0.08), (1.04, 0.12)):
                corrected = eye_scale*ndc_y + eye_offset - 2.*fraction
                fallback_optical = height*(1. - corrected)*.5
                paired_optical = eye_scale*source_y + (
                    (1.-eye_scale)*height*.5
                    - eye_offset*height*.5 + fraction*height)
                shader_optical = height*(1. - corrected)*.5
                assert abs(fallback_optical-paired_optical) < 1e-6
                assert abs(paired_optical-shader_optical) < 1e-6
            # World/F11/gameplay/GOAL are non-pause semantic owners.
            for context in (("game","overlay",False),("pause","hud",False),
                            ("pause","world",False),("pause","overlay",True)):
                assert pause_fraction(*context,fraction) == 0.0
print("PASS ESC fallback/paired/shader vertical parity across 4 dimensions and 3 source-owning mutations")

for width, height in ((1024, 768), (1920, 1080), (3440, 1440), (2496, 2688)):
    for fraction in (-.25, 0.0, .10, .25, .50, float("nan")):
        v = pause_fraction("pause", "overlay", False, fraction)
        assert abs(v*height - (-2*v)*(-height/2)) < 1e-6
        assert -height/4 <= v*height <= height/4
        for context in (("game", "overlay", False), ("pause", "hud", False),
                        ("pause", "world", False), ("pause", "overlay", True),
                        ("menu", "overlay", False)):
            assert pause_fraction(*context, fraction) == 0
# Destructive controls must reject wrong scope, inverted shader sign and a
# missing fixed-function offset, rather than passing a detached static test.
for bad, good in (
    ("*Game::current_mode == GameState::STATE_SMPAUSEMENU &&",
     "*Game::current_mode == GameState::STATE_GAME &&"),
    ("ExternalOverlaySemanticDepth == 0 &&",
     "ExternalOverlaySemanticDepth != 0 &&"),
    ("std::clamp(fraction, -0.25f, 0.25f)",
     "std::clamp(fraction, -1.0f, 1.0f)"),
):
    assert pause_func.count(bad) == 1
    mutant = pause_func.replace(bad, good, 1)
    assert not all(t in mutant for t in (
        "*Game::current_mode == GameState::STATE_SMPAUSEMENU &&",
        "ExternalOverlaySemanticDepth == 0 &&",
        "std::clamp(fraction, -0.25f, 0.25f)"))
for bad, good in (
    ("height * R30PauseMenuVerticalFraction();", "height * 0.0f;"),
    ("clipCorrection._42 = pauseVertical.offset[eye] -",
     "clipCorrection._42 = pauseVertical.offset[eye] +"),
):
    assert (fixed + shader).count(bad) == 1
    mutant = (fixed + shader).replace(bad, good, 1)
    assert not (("height * R30PauseMenuVerticalFraction();" in mutant) and
                ("clipCorrection._42 = pauseVertical.offset[eye] -" in mutant))
print("PASS pause-only vertical placement, 4 source/eye resolutions, exact ownership and 5 destructive controls")

# Issue #119: exact producer group must remain INSIDE the visible region
# after the 0.55 -> 0.90 boost. A shared x correction is the only permitted
# left/right correction; independently clamping each eye destroys disparity.
safe_begin = code.index("void R30ConstrainHudEdgeToVisibleBounds(")
safe_end = code.index("bool R30TransformHudScissor(", safe_begin)
safe = code[safe_begin:safe_end]
for token in (
    "anchor.hasBounds", "anchor.minX < x0", "anchor.maxX > x1",
    "anchor.minY < y0", "anchor.maxY > y1",
    "kSafeInset = 0.025f", "safeLeft - leftMin",
    "safeLeft - rightMin", "safeRight - leftMax",
    "safeRight - rightMax", "shiftMin <= shiftMax",
    "edgeLeftBias += sharedShift;", "edgeRightBias += sharedShift;",
    "verticalMin <= verticalMax", "edgeYBias += std::clamp(",
):
    assert token in safe, token
draw = code[code.index("bool R30TransformXyzrhwStereo("):
            code.index("// This is the high-frequency indexed smoke/sand/decal path:")]
assert "R30ConstrainHudEdgeToVisibleBounds(" in draw
assert draw.index("R30ConstrainHudEdgeToVisibleBounds(") < draw.index("for (UINT visit = 0;")
assert "minX, maxX, minY, maxY, true" in code

def visible_fit(box, bounds, scales, biases, wanted, inset=.025):
    lo, hi = bounds
    amin, amax = box
    if amin < lo or amax > hi:
        return wanted
    allowed_lo = max((lo + (hi-lo)*inset) - (s*amin + b + w)
                     for s, b, w in zip(scales, biases, wanted))
    allowed_hi = min((hi - (hi-lo)*inset) - (s*amax + b + w)
                     for s, b, w in zip(scales, biases, wanted))
    if allowed_lo > allowed_hi:
        return wanted
    delta = max(allowed_lo, min(allowed_hi, 0.0))
    return tuple(w+delta for w in wanted)

for w,h in ((1024,768),(1920,1080),(3440,1440),(2496,2688)):
    # Right-edge enlarged HUD is inset without altering binocular separation.
    box = (.91*w, .995*w)
    scales = (.90, .91)
    biases = (.05*w, .045*w)
    orig = (.042*w, .041*w)
    shifted = visible_fit(box, (0,w), scales, biases, orig)
    assert abs((shifted[0]-shifted[1]) - (orig[0]-orig[1])) < 1e-7*w
    for s,base,shift in zip(scales,biases,shifted):
        assert s*box[0]+base+shift >= .025*w - 1e-6*w
        assert s*box[1]+base+shift <= .975*w + 1e-6*w
    # Previous layout untouched for partially offscreen transition sprites.
    assert visible_fit((-.1*w,.2*w),(0,w),scales,biases,orig) == orig
    # Oversized groups have no feasible shared shift: no false correction.
    assert visible_fit((.05*w,.95*w),(0,w),(1.4,1.4),(0,0),orig) == orig
    # Upper HUD safe inset is symmetrical on the independent vertical axis.
    yorig=(.04*h,)
    yfit=visible_fit((.005*h,.10*h),(0,h),(.90,),(.05*h,),yorig)
    assert .90*.005*h+.05*h+yfit[0] >= .025*h-1e-6*h

# Destructive regression: either-eye correction, viewport bounds or the
# source-bbox material integration must be detectably removed.
for wrong, replacement in (
    ("edgeRightBias += sharedShift;", "edgeRightBias += 0.0f;"),
    ("safeRight - rightMax", "safeRight - leftMax"),
    ("anchor.maxX > x1 ||", "anchor.maxX > x1 + width ||"),
    ("kSafeInset = 0.025f", "kSafeInset = 0.0f"),
):
    assert wrong in safe
    changed = safe.replace(wrong,replacement,1)
    assert changed != safe
    assert not all(item in changed for item in (
        "edgeRightBias += sharedShift;", "safeRight - rightMax",
        "anchor.maxX > x1 ||", "kSafeInset = 0.025f"))
print("PASS Quest3 peripheral HUD visible-area fit: stereo shift parity, 4 resolutions, bounds fail-closed")


# Issue #119 binocular FOV fallback: a single finite but inverted eye
# cannot authorize BOTH eyes' HUD contain aspect during VDXR recenter.
section = code[code.index("float R30HudAspectCompensation("):
               code.index("float R30PauseMenuVerticalFraction()")]
assert "if (targetEyes != 2)\n                return 1.0f;" in section
assert section.index("targetEyes = 2;") < section.index("if (targetEyes != 2)")

def fov_pair_aspect(eyes):
    aspects = []
    for l, r, d, u in eyes:
        h = math.tan(r) - math.tan(l)
        v = math.tan(u) - math.tan(d)
        if not isfinite(h) or not isfinite(v) or h <= .05 or v <= .05:
            continue
        aspect = h / v
        if isfinite(aspect) and .25 <= aspect <= 4.0:
            aspects.append(aspect)
    return sum(aspects) / 2.0 if len(aspects) == 2 else 1.0

valid = (-.7, .7, -.8, .8)
other = (-.75, .75, -.8, .8)
inverted = (.7, -.7, -.8, .8)
assert abs(fov_pair_aspect((valid, other)) -
    (fov_pair_aspect((valid, valid)) + fov_pair_aspect((other, other))) / 2) < 1e-6
for pair in ((valid, inverted), (inverted, valid), (inverted, inverted)):
    assert fov_pair_aspect(pair) == 1.0
assert "if (targetEyes != 2)" not in section.replace(
    "if (targetEyes != 2)", "if (!targetEyes)", 1)
print("PASS binocular FOV fallback rejects unilateral aspect at recenter")

# Issue #119 binocular XR extent coherence: only a jointly published
# pixel pair may drive HUD aspect. One-eye or mixed-generation extents
# must fall back to actual angular FOV, not average incompatible pixels.
start_pair = code.index("float R30HudAspectCompensation(")
end_pair = code.index("float R30PauseMenuVerticalFraction()", start_pair)
pair = code[start_pair:end_pair]

def verify_binocular_pair(body):
    for token in ("bool coherentEyePair = true;",
                  "coherentEyePair = false;",
                  "pixelWidth[eye] = w;",
                  "pixelHeight[eye] = h;",
                  "pixelAspect[eye] = aspect;",
                  "if (coherentEyePair &&",
                  "(std::max)(pixelWidth[0], pixelWidth[1])",
                  "(std::max)(pixelHeight[0], pixelHeight[1])",
                  "targetAspectSum = pixelAspect[0] + pixelAspect[1];",
                  "targetEyes = 2;",
                  "if (!targetEyes)"):
        assert token in body, token
    assert body.index("if (coherentEyePair &&") < body.index(
        "targetEyes = 2;") < body.index("if (!targetEyes)")
    assert body.count("targetEyes = 2;") == 1
    # An independent one-eye success must NOT enter the pixel sum.
    assert "targetAspectSum += aspect;" not in body[:body.index("if (!targetEyes)")]

verify_binocular_pair(pair)
for good, bad in (
    ("if (coherentEyePair &&", "if (true &&"),
    ("coherentEyePair = false;", "coherentEyePair = true;"),
    ("0.10f *", "1.00f *"),
    ("targetAspectSum = pixelAspect[0] + pixelAspect[1];",
     "targetAspectSum = pixelAspect[0];"),
):
    assert good in pair
    mutated = pair.replace(good, bad, 1)
    # Verify the actual safety clauses instead of just a marker.
    try:
        verify_binocular_pair(mutated)
        assert "if (true &&" not in mutated
        assert mutated.count("coherentEyePair = false;") == pair.count(
            "coherentEyePair = false;")
        assert mutated.count("0.10f *") == pair.count("0.10f *")
        assert "targetAspectSum = pixelAspect[0] + pixelAspect[1];" in mutated
    except AssertionError:
        pass
    else:
        raise AssertionError("Eye-extent regression mutant escaped: " + bad)

def coherent_aspect(left, right, angular=1.02):
    lw, lh = left
    rw, rh = right
    if not (lw and lh and rw and rh):
        return angular
    a, b = lw / lh, rw / rh
    if not (.25 <= a <= 4 and .25 <= b <= 4):
        return angular
    if abs(lw - rw) > .10 * max(lw, rw) or abs(lh - rh) > .10 * max(lh, rh):
        return angular
    return (a+b)*.5

for a in ((1024,768),(1920,1080),(2496,2688),(3440,1440)):
    assert abs(coherent_aspect(a,a) - a[0]/a[1]) < 1.e-8
assert coherent_aspect((2496,2688),(1024,768)) == 1.02
assert coherent_aspect((2496,2688),(0,0)) == 1.02
assert coherent_aspect((0,0),(2496,2688)) == 1.02
assert coherent_aspect((2496,2688),(2400,2600)) != 1.02
# A later complete pair immediately restores the pixel rather than a sticky
# fallback after Reset, and both eyes still share the same HUD contain value.
assert coherent_aspect((2496,2688),(2496,2688)) == 2496/2688
print("PASS binocular HUD extent coherence, resize fallback and four destructive mutants")


# Issue #119: real source-code adaptive peripheral readability. The opt-in
# exact gear/rank/time producer only may increase its 0.90-horizontal floor
# toward a 0.65 vertical floor, if a SHARED bilateral viewport displacement
# can contain the COMPLETE source bbox. A/B-off and GOAL/world/F11 remain
# unreachable from this branch. No HMD PASS is inferred from this fixture.
assert "float R30AdaptivePeripheralHudBoost(" in code
assert "peripheralBoost = R30AdaptivePeripheralHudBoost(" in draw
adaptive = code[code.index("float R30AdaptivePeripheralHudBoost("):
                code.index("bool R30TransformHudScissor(")]
for marker in ("anchor.hasBounds", "0.65f / hudScaleY",
               "shiftMin <= shiftMax", "eyeScale[eye]", "eyeOffset[eye]",
               "if (!fitsBothEyes(previousBoost))", "if (fitsBothEyes(desired))",
               "for (int i = 0; i < 8; ++i)", "return low;"):
    assert marker in adaptive, marker
assert draw.index("R30GetExactHudEdgeAnchor(") < draw.index(
    "R30ExactPeripheralHudBoost(exactHudAnchor);") < draw.index(
    "R30AdaptivePeripheralHudBoost(") < draw.index(
    "hudScaleX *= peripheralBoost;")
assert draw.count("R30AdaptivePeripheralHudBoost(") == 1

def adaptive_compatible_fit(box, viewport, eye_scales, eye_offsets,
                            base_x, base_y, anchors, boost):
    w,h = viewport
    lo_x,hi_x,lo_y,hi_y = box
    ax,ay = anchors
    if w <= 0 or h <= 0 or not all(isfinite(v) for v in (
            *box, *eye_scales, *eye_offsets, base_x, base_y, ax, ay, boost)):
        return False
    shift_min,shift_max = float("-inf"),float("inf")
    for eye in range(2):
        sx = base_x * boost * eye_scales[eye]
        bias = (1-sx) * (.5*w + .5*w*ax) + .5*w*eye_offsets[eye]
        if sx <= 0: return False
        shift_min = max(shift_min, .025*w - (sx*lo_x + bias))
        shift_max = min(shift_max, .975*w - (sx*hi_x + bias))
    sy = base_y*boost
    bias_y = (1-sy)*(.5*h - .5*h*ay)
    return (shift_min <= shift_max and sy > 0 and
            .025*h - (sy*lo_y + bias_y) <=
            .975*h - (sy*hi_y + bias_y))

def adaptive_boost(box,viewport,scales,offsets,base_x,base_y,anchors,old):
    target = max(old,min(3.0,.65/base_y))
    fits = lambda b: adaptive_compatible_fit(
        box,viewport,scales,offsets,base_x,base_y,anchors,b)
    if not fits(old): return old
    if fits(target): return target
    lo,hi = old,target
    for _ in range(8):
        mid=(lo+hi)*.5
        if fits(mid): lo=mid
        else: hi=mid
    return lo

for w,h in ((1024,768),(1920,1080),(3440,1440),(2496,2688)):
    box=(.03*w,.15*w,.06*h,.20*h)
    old=readable_boost(.55,-.82,.78)
    new=adaptive_boost(box,(w,h),(1.0,1.03),(-.035,.035),
                       .55,.214,(-.82,.78),old)
    assert new >= old
    assert new > old + .1   # exact edge glyphs enlarge in portrait eye
    assert new <= 3.
    assert adaptive_compatible_fit(box,(w,h),(1.0,1.03),(-.035,.035),
                                   .55,.214,(-.82,.78),new)
    # Large edge group cannot have an unbounded boost; source stays contained.
    wide=(0.,.95*w,0.,.80*h)
    restricted=adaptive_boost(wide,(w,h),(1.0,1.03),(-.035,.035),
                              .55,.214,(-.82,.78),old)
    assert old <= restricted < new
    assert adaptive_compatible_fit(wide,(w,h),(1.0,1.03),
                                   (-.035,.035),.55,.214,(-.82,.78),restricted)
    # A corrupt second eye is NOT independently re-centered.
    assert not adaptive_compatible_fit(
        box,(w,h),(1.0,float("nan")),(-.035,.035),
        .55,.214,(-.82,.78),3.)
    # Baseline A/B guard: default-off lacks an exact bbox, so the real
    # dispatcher does not enter the adaptive scaling path at all.
    assert "(!Settings::VRHudResponsiveLayout.get() &&" in helper
    assert "!Settings::VRHudEdgeAnchors.get()) ||" in helper
for removed in ("eyeOffset[eye] * halfWidth", "shiftMin <= shiftMax",
                "if (!fitsBothEyes(previousBoost))"):
    assert removed in adaptive
    assert removed not in adaptive.replace(removed, "", 1)
print("PASS adaptive Quest3 peripheral glyph sizing, bilateral safe bounds, desktop aspect/reset and negative eye fixture")


# Issue #119 exact peripheral HUD: the bilateral safe-area fit is affine
# in one common boost. The hot path must solve all cross-eye inequalities
# before the existing bounded binary-search fallback. This is a real C++
# execution path, not a review-only guard or a declared FPS speedup.
analytical = code[code.index("float R30AdaptivePeripheralHudBoost("):
                  code.index("bool R30TransformHudScissor(")]
for token in (
    "float cappedBoost = desired;",
    "const float anchorCenter = centerX + halfWidth * anchor.x;",
    "for (int minEye = 0; minEye < 2; ++minEye)",
    "for (int maxEye = 0; maxEye < 2; ++maxEye)",
    "(eyeOffset[maxEye] - eyeOffset[minEye]) * halfWidth;",
    "((safeRight - safeLeft) - baselineSpan) / slope",
    "if (std::isfinite(cappedBoost) &&",
    "fitsBothEyes(cappedBoost))",
    "if (fitsBothEyes(desired))",
    "for (int i = 0; i < 8; ++i)",
):
    assert token in analytical, token
assert analytical.index("if (fitsBothEyes(desired))") < analytical.index(
    "float cappedBoost = desired;") < analytical.index(
    "for (int i = 0; i < 8; ++i)")
assert analytical.count("fitsBothEyes(cappedBoost)") == 1

def stereo_safe(boost, dims, box, center_anchor, scale, offsets):
    w, h = dims
    x0, x1, y0, y1 = box
    ax, ay = center_anchor
    sx, sy, eye_scales = scale
    cx, cy = .5*w, .5*h
    left_min, right_max = -float("inf"), float("inf")
    for e in range(2):
        eff = sx * boost * eye_scales[e]
        bias = (1-eff)*(cx + .5*w*ax) + .5*w*offsets[e]
        left_min = max(left_min, .025*w - (eff*x0+bias))
        right_max = min(right_max, .975*w - (eff*x1+bias))
    vertical_span = sy*boost*(y1-y0)
    return left_min <= right_max and vertical_span <= .95*h

def algebraic_stereo_cap(desired, dims, box, anchor, scale, offsets):
    w, h = dims
    x0, x1, y0, y1 = box
    sx, sy, eye_scales = scale
    center = .5*w + .5*w*anchor[0]
    bound = desired
    if y1 > y0:
        bound = min(bound, .95*h / (sy*(y1-y0)))
    for min_eye in range(2):
        for max_eye in range(2):
            slope = sx * (eye_scales[max_eye]*(x1-center) -
                          eye_scales[min_eye]*(x0-center))
            baseline = .5*w*(offsets[max_eye]-offsets[min_eye])
            if slope > 0.0:
                bound = min(bound,(.95*w-baseline)/slope)
    return bound

for dims in ((1024,768),(1920,1080),(3440,1440),(2496,2688)):
    w,h = dims
    for anchor in ((-.82,.78),(.82,-.78)):
        # Offset asymmetry is intentionally different between the eyes;
        # translating each eye separately would incorrectly pass this test.
        box=(.03*w,.23*w,.07*h,.22*h)
        scales=(.55,.214,(1.0,1.04))
        offsets=(-.065,.06)
        old=1.60
        target=3.0
        assert stereo_safe(old,dims,box,anchor,scales,offsets)
        capped=algebraic_stereo_cap(target,dims,box,anchor,scales,offsets)
        assert old <= capped <= target
        assert stereo_safe(capped-1.e-5,dims,box,anchor,scales,offsets)
        if capped < target-1.e-3:
            assert not stereo_safe(capped+.005,dims,box,anchor,
                                   scales,offsets)
        # Source-height enlargement can be the limiting constraint.
        tall=(.08*w,.20*w,.02*h,.82*h)
        tall_cap=algebraic_stereo_cap(target,dims,tall,anchor,scales,offsets)
        assert tall_cap <= .95*h/(.214*(tall[3]-tall[2]))+1.e-7
# The full-screen/GOAL/world/F11 producers cannot enter this exact-owner
# hot path. Retain original static scope safety predicates and baseline.
assert "ProducerToken::OutRunHudPeripheralText" in helper
assert "(!Settings::VRHudResponsiveLayout.get() &&" in helper
assert "!Settings::VRHudEdgeAnchors.get()) ||" in helper
print("PASS stereo analytical peripheral fit, clip bounds, two-eye constraints, bisection fallback")


# Issue #119: partially off-viewport text must retain its source transform.
# The bilateral correction skips this case; the preceding exact-producer
# boost/anchor path must make the same decision or an entering glyph jumps.
anchor_fn = code[code.index("R30HudEdgeAnchor R30GetExactHudEdgeAnchor("):
                 code.index("float R30ExactPeripheralHudBoost(")]
for part in ("if (minX < x0 || maxX > x0 + width ||",
             "minY < y0 || maxY > y0 + height)",
             "return {};"):
    assert part in anchor_fn
assert anchor_fn.index("if (!seen)") < anchor_fn.index(
    "if (minX < x0 ||") < anchor_fn.index("const float cx =")
def source_box_contained(bounds, viewport):
    x0,y0,w,h = viewport
    left,right,top,bottom = bounds
    return (left >= x0 and right <= x0+w and
            top >= y0 and bottom <= y0+h)
for w,h in ((1024,768),(1920,1080),(3440,1440),(2496,2688)):
    assert source_box_contained((.04*w,.16*w,.05*h,.20*h),(0,0,w,h))
    assert source_box_contained((0,w,0,h),(0,0,w,h))
    for bad in ((-.1*w,.16*w,.05*h,.20*h),
                (.04*w,1.08*w,.05*h,.20*h),
                (.04*w,.16*w,-.02*h,.20*h),
                (.04*w,.16*w,.05*h,1.02*h)):
        assert not source_box_contained(bad,(0,0,w,h))
    assert not source_box_contained((0,w+.5,0,h),(0,0,w,h))
# Destructive control: dropping the protection restores old discontinuity.
mutated = anchor_fn.replace(
    "if (minX < x0 || maxX > x0 + width ||", "if (false ||", 1)
assert "if (minX < x0 || maxX > x0 + width ||" not in mutated
print("PASS exact peripheral HUD off-viewport animation excludes boost/anchor")

# BA9D0 immediate HUD glyphs and queued children must share exact
# provenance while a real queue node, GOAL, +TIME or desktop drawing never
# inherits the previous producer's peripheral location.
sem = (root / "src/vr/game/render_semantics.hpp").read_text()
s = sem[sem.index("class ScopedExactProducerSemantic final"):
        sem.index("inline void RegisterSpriteNodeScope(", sem.index("class ScopedExactProducerSemantic final"))]
for x in ("savedDirectProducer_ = CurrentDirectExactProducer;",
          "CurrentDirectExactProducer = directProducer;",
          "CurrentDirectExactProducer = savedDirectProducer_;",
          "SpriteQueueDepth == 0 && scope != RenderScope::None"):
    assert x in s, x
sel = sem[sem.index("inline ProducerToken CurrentRenderProducerToken()"):
          sem.index("inline const ProjectedMarkerInfo* CurrentProjectedMarker()")]
assert "SpriteQueueDepth != 0" in sel
assert "? CurrentSpriteQueueProducer : CurrentDirectExactProducer;" in sel
src = (root / "src/hooks_uiscaling.cpp").read_text()
direct = src[src.index("static void __cdecl OutRunHudTextProducer_dest("):
             src.index("static int __cdecl OutRunHudText_clip(")]
for x in ("semantic.space == OutRunVRHudSemantics::SpacePolicy::ScreenHud",
          "std::optional<OutRunVR::GameSemantic::ScopedExactProducerSemantic>",
          "directHudOwner.emplace(", "nullptr, false, token);",
          "OutRunHudTextProducerHook.call("):
    assert x in direct, x
assert direct.index("directHudOwner.emplace(") < direct.index("OutRunHudTextProducerHook.call(")
assert direct.index("OutRunHudTextProducerHook.call(") < direct.index("OutRunHudPeripheralText = previousPeripheral;")
# Both original BA9D0 emitters stay on their exact queued-SpriteNode path
# even if direct glyph raster occurs during the enclosing C++ CALL.
# This slice deliberately ends before clip/sprani: only the immediate
# BA9D0 producer belongs here; the two queued emitters are asserted above.
assert direct.count("ProducerToken::OutRunHudPeripheralText") == 1
assert direct.count("ProducerToken::OutRunHudText") == 1
assert direct.count("OutRunHudTextProducerHook.call(") == 1
assert "if (Settings::VREnabled &&" in direct
assert "R30GetExactHudEdgeAnchor(" in code
assert "CurrentRenderProducerToken() !=" in code

def select(depth, queue, direct):
    return queue if depth else direct
assert select(0, "stale_goal", "peripheral") == "peripheral"
assert select(1, "world_marker", "peripheral") == "world_marker"
assert select(0, "stale_goal", "none") == "none"
assert select(1, "goal", "none") == "goal"
# Destructive source mutants: all three ownership controls are mandatory.
for x in ("CurrentDirectExactProducer = savedDirectProducer_;",
          "CurrentDirectExactProducer = directProducer;"):
    mutant = s.replace(x, "/* removed owner transfer */", 1)
    assert x not in mutant
assert "SpriteQueueDepth != 0" not in sel.replace(
    "SpriteQueueDepth != 0", "SpriteQueueDepth == 0", 1)
assert "directHudOwner.emplace(" not in direct.replace(
    "directHudOwner.emplace(", "/* missing exact owner */(", 1)
print("PASS immediate/queued BA9D0 VR HUD source ownership and four destructive regressions")
