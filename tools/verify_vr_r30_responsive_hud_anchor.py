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
# Quest3 R84 reported that the default 1.0 pause slider is magnified twice.
# The R84 visual recovery keeps the displayed ESC scale exactly user-defined.
assert "const float readable = OutRunVrPauseEye::ResponsiveUserScale(" not in code
assert "return std::clamp(requested, 0.55f, 1.50f);" in code
assert "const float opticalScale = userScale;" in code
assert "ResponsiveMenuScale(" not in code
pause_helper = (root / "src/vr/d3d9/pause_menu_eye_affine.hpp").read_text()
assert "inline float ResponsiveUserScale(" in pause_helper
assert "0.55f + (bounded - 0.55f) * (0.70f / 0.45f)" in pause_helper
assert "1.25f + (bounded - 1.0f) * 0.50f" in pause_helper
def responsive_pause(requested):
    bounded = max(.55, min(1.50, requested))
    return (.55 + (bounded - .55) * (.70 / .45) if bounded <= 1.
            else 1.25 + (bounded - 1.) * .50)
def quest_profile(responsive, legacy, pause):
    return responsive or legacy, max(.55, min(1.5, pause))
assert quest_profile(True, False, 1.) == (True, 1.)
assert quest_profile(False, False, 1.) == (False, 1.)
assert quest_profile(False, True, .8) == (True, .8)
assert quest_profile(True, False, 1.4) == (True, 1.4)
assert quest_profile(True, False, .55) == (True, .55)
assert quest_profile(True, False, .75)[1] < quest_profile(True, False, 1.0)[1]
assert quest_profile(True, False, 1.0)[1] < quest_profile(True, False, 1.5)[1]
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

# A reentrant BA9D0 text emission may enter through an unclassified internal
# helper while the exact driving-HUD parent is still active. Preserve that
# parent only for Unknown nested callers; classified GOAL, C2C HUD and
# projected/world markers may not borrow the peripheral anchor.
inherit_guard = owner[owner.index("OutRunHudPeripheralText =\\n".replace("\\n", "\n")):
                      owner.index("// BA9D0 may rasterize", owner.index("OutRunHudPeripheralText =\\n".replace("\\n", "\n")))]
assert "previousPeripheral &&" in inherit_guard
assert "semantic.space == OutRunVRHudSemantics::SpacePolicy::Unknown" in inherit_guard
assert inherit_guard.count("semantic.space == OutRunVRHudSemantics::SpacePolicy::ScreenHud") == 1
def nested_peripheral(parent, space, exact=False):
    return (space == "ScreenHud" and exact) or (parent and space == "Unknown")
assert nested_peripheral(False, "ScreenHud", True)
assert nested_peripheral(True, "Unknown")
assert not nested_peripheral(False, "Unknown")
assert not nested_peripheral(True, "ScreenHud")   # GOAL/other classified HUD
assert not nested_peripheral(True, "WorldBillboard")
assert not nested_peripheral(False, "ScreenHud")  # unrelated text
assert "OutRunHudPeripheralText = previousPeripheral;" in owner
for original, wrong in (
    ("previousPeripheral &&", "false &&"),
    ("SpacePolicy::Unknown);", "SpacePolicy::ScreenHud);"),
    ("SpacePolicy::ScreenHud &&", "SpacePolicy::Unknown &&"),
):
    assert original in inherit_guard
    mutated = inherit_guard.replace(original, wrong, 1)
    assert not all(x in mutated for x in (
        "previousPeripheral &&",
        "SpacePolicy::Unknown);",
        "SpacePolicy::ScreenHud &&"))
print("PASS nested driving text owner, classified GOAL/world exclusions and 3 destructive mutations")




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
    "if (R30IsPauseMenuElement())",
    "if (!std::isfinite(requested) || requested <= 0.0f)",
    "Settings::VRPauseMenuScale.get()",
    "std::clamp(requested,",
    "0.55f, 1.50f",
    "return R30HudScaleValue();",
):
    assert token in scope, token
assert scope.index("return 1.0f;") < scope.index(
    "if (R30IsPauseMenuElement())") < scope.index(
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
    if mode == 0x12 and pause_owned and not f11 and math.isfinite(pause) and pause > 0:
        requested = pause
        return max(.55, min(1.50, requested))
    return hud
for source_w, source_h in ((1024,768),(1920,1080),(3440,1440),(2496,2688)):
    for eye_w, eye_h in ((1024,768),(2496,2688)):
        factor = max(.75, min(3.50, (source_w/source_h)/(eye_w/eye_h)))
        assert effective(0x12, "overlay") / factor > 0
        assert effective(0x12, "overlay") == 1.0
        assert effective(0x12, "overlay", responsive=False) == 1.0
        assert effective(0x12, "hud") == .55
        assert effective(0x12, "hud", producer="exact_menu_arrow") == 1.0
        assert effective(0x12, "hud", producer="result_progress") == .55
        assert effective(0x09, "hud", producer="exact_menu_arrow") == .55
        assert effective(0x12, "world") == .55
        assert effective(0x09, "overlay") == .55
        assert effective(0x10, "overlay") == .55
        assert effective(0x12, "overlay", f11=True) == 1.
        assert effective(0x12, "overlay", pause=.55) == .55
        assert effective(0x12, "overlay", pause=.75) < effective(0x12, "overlay", pause=1.)
        assert effective(0x12, "overlay", pause=1.5) == 1.50
        assert effective(0x12, "overlay", pause=9.) == 1.50
        assert effective(0x12, "overlay", pause=-1.) == .55
        assert effective(0x12, "overlay", pause=float('nan')) == .55
        assert effective(0x12, "overlay", pause=float('inf')) == .55
# Reject a source mutation that bypasses disabled/nonfinite pause fallback.
assert "if (!std::isfinite(requested) || requested <= 0.0f)" in scope
assert "std::isfinite(Settings::VRPauseMenuScale.get()) &&" in contain
assert "Settings::VRPauseMenuScale.get() > 0.0f;" in contain
for fragment in (
    "if (!std::isfinite(requested) || requested <= 0.0f)",
    "std::isfinite(Settings::VRPauseMenuScale.get()) &&",
    "Settings::VRPauseMenuScale.get() > 0.0f;",
):
    original = scope if fragment in scope else contain
    assert fragment in original
    assert fragment not in original.replace(fragment, "false", 1)
# A real destructive swap in the scope function must invalidate these guards.
for bad, good in (
    ("ExternalOverlaySemanticDepth == 0 &&",
     "ExternalOverlaySemanticDepth != 0 &&"),
    ("*Game::current_mode == GameState::STATE_SMPAUSEMENU",
     "*Game::current_mode == GameState::STATE_GAME"),
    ("R30IsPauseMenuExactArrow());", "R30IsPauseMenuExactArrow() || true);"),
    ("std::clamp(requested,",
     "std::clamp(Settings::VRHudScale.get(),"),
):
    assert scope.count(bad) == 1, bad
    mutant = scope.replace(bad, good, 1)
    assert not all(token in mutant for token in (
        "ExternalOverlaySemanticDepth == 0 &&",
        "*Game::current_mode == GameState::STATE_SMPAUSEMENU",
        "R30IsPauseMenuExactArrow());",
        "std::clamp(requested,"))
print("PASS exact ESC pause ownership, F11/HUD/world negatives and size/aspect fixtures")


# Issue #119: independently centre the ESC/pause menu vertically. The same
# viewport-fraction must feed the pretransformed XYZRHW and shader HUD paths.
# User-visible placement still requires Quest3/VDXR optical acceptance.
# Verify original-game exact arrow producer identity, never blanket ScreenHud.
arrow_begin = code.index("bool R30IsPauseMenuExactArrow() noexcept")
pause_begin = code.index("float R30PauseMenuVerticalFraction() noexcept")
arrow_scope = code[arrow_begin:pause_begin]
for marker in ("RenderScope::ScreenHud",
               "CurrentRenderProducerToken()",
               "OutRunVrPauseEye::ExactArrowOwner(",
               "ProducerToken::ExactScreenHudClipSprite",
               "ProducerToken::PauseOptionArrow"):
    assert marker in arrow_scope, marker
assert "CurrentSpriteQueueProducer ==" not in arrow_scope
# An active queued node wins over the exact direct E8 caller; on a
# synchronous original call, that same semantic API supplies direct owner.
semantic_src = (root / "src/vr/game/render_semantics.hpp").read_text()
assert "SpriteQueueDepth != 0" in semantic_src
# The exact synchronous C993 lens lifetime now takes precedence over nested
# direct helper scopes, but never over an active queued ESC SpriteNode.
# Keep the ESC contract tied to executable producer priority, not to the
# historical ternary implementation's literal source formatting.
queue_ownership = semantic_src.split(
    "inline ProducerToken CurrentRenderProducerToken() noexcept", 1)[1].split(
    "class ScopedExactLensCentreGpuDraw", 1)[0]
assert queue_ownership.index("if (SpriteQueueDepth != 0)") < (
    queue_ownership.index("return CurrentSpriteQueueProducer;")) < (
    queue_ownership.index("if (ExactLensCentreDrawOwnsSemantic())")) < (
    queue_ownership.index("return CurrentDirectExactProducer;"))
assert "return ProducerToken::LensFlareCentre;" in queue_ownership
for original, corrupt in (
    ("if (SpriteQueueDepth != 0)", "if (false)"),
    ("return CurrentSpriteQueueProducer;", "return CurrentDirectExactProducer;"),
    ("return CurrentDirectExactProducer;", "return ProducerToken::None;"),
):
    mutant = queue_ownership.replace(original, corrupt, 1)
    assert original not in mutant
for original, corrupt in (
    ("RenderScope::ScreenHud", "RenderScope::WorldBillboard"),
    ("ProducerToken::ExactScreenHudClipSprite",
     "ProducerToken::ResultProgress"),
    ("ProducerToken::PauseOptionArrow",
     "ProducerToken::ResultProgress"),
):
    mutant = arrow_scope.replace(original, corrupt, 1)
    assert original not in mutant
producer = (root / "src/hooks_uiscaling.cpp").read_text()
assert "OptionArrow_ClipSpriteCalls[]" in producer
assert "Module::exe_ptr(addr), PauseOptionArrow_putClipSprite" in producer
assert "ProducerToken::ExactScreenHudClipSprite" in producer
arrow_hook = producer[producer.index("static int __cdecl PauseOptionArrow_putClipSprite("):
                      producer.index("static int __cdecl RivalMarker_sprani(")]
for token in ("GameState::STATE_SMPAUSEMENU",
              "ScopedExactProducerSemantic directArrowOwner(",
              "RenderScope::ScreenHud, nullptr, true,",
              "ProducerToken::PauseOptionArrow",
              "FlushD3DXBeforeDirectGoalSource()",
              "FlushD3DXAtDirectGoalSourceExit()",
              "ExactScreenHud_putClipSpriteOwned("):
    assert token in arrow_hook, token
assert arrow_hook.index("FlushD3DXBeforeDirectGoalSource()") < \
       arrow_hook.index("ScopedExactProducerSemantic directArrowOwner(") < \
       arrow_hook.index("ExactScreenHud_putClipSpriteOwned(") < \
       arrow_hook.index("FlushD3DXAtDirectGoalSourceExit()")
assert "ProducerToken::ExactScreenHudClipSprite" not in arrow_hook
# The normal clip entrypoint must keep its original token and cannot gain
# the direct pause-specific D3DX flush authority.
normal_clips = producer[producer.index("static int __cdecl ExactScreenHud_putClipSprite("):
                        producer.index("// Exact original ESC arrow",
                                       producer.index("static int __cdecl ExactScreenHud_putClipSprite("))]
assert "ProducerToken::ExactScreenHudClipSprite" in normal_clips
assert "FlushD3DXBeforeDirectGoalSource" not in normal_clips

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
# Anchor the ESC pause bias to the *ordinary HUD* traversal, not the
# earlier isolated +TIME/GOAL stage-extension vertex loop.
normal_hud_loop = "for (UINT visit = 0; visit < hudVisitCount; ++visit)"
assert fixed.count(normal_hud_loop) == 1
assert fixed.index("height * R30PauseMenuVerticalFraction();") < fixed.index(normal_hud_loop)
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
assert draw.count(normal_hud_loop) == 1
assert draw.index("R30ConstrainHudEdgeToVisibleBounds(") < draw.index(normal_hud_loop)
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

    # Non-symmetric left/right vertical FOV or optical centres must fit
    # BOTH actual eye affines. The old scalar HudScaleY/HudBiasY check
    # silently excluded right-eye bounds and clipped the top/right-eye HUD.
    y_box=(.005*h,.10*h)
    y_scales=(.90,.94)
    y_biases=(0.,-.04*h)
    y_wanted=(.04*h,.04*h)
    paired=visible_fit(y_box,(0,h),y_scales,y_biases,y_wanted)
    first_only=visible_fit(y_box,(0,h),y_scales[:1],y_biases[:1],y_wanted[:1])
    assert paired[0]>first_only[0]+.01*h
    assert abs((paired[0]-paired[1]) -
               (y_wanted[0]-y_wanted[1])) < 1e-7*h
    for s,b,wanted in zip(y_scales,y_biases,paired):
        assert s*y_box[0]+b+wanted >= .025*h-1e-6*h
        assert s*y_box[1]+b+wanted <= .975*h+1e-6*h
    # Bottom edge in either eye is equally authoritative.
    bottom=visible_fit((.90*h,.995*h),(0,h),
                       (.91,.95),(.05*h,.06*h),y_wanted)
    assert bottom[0] < y_wanted[0]
    for s,b,wanted in zip((.91,.95),(.05*h,.06*h),bottom):
        assert s*.995*h+b+wanted <= .975*h+1e-6*h
    # Offscreen-transition / infeasible stereo fit retains the old input.
    assert visible_fit((-.02*h,.12*h),(0,h),
                       y_scales,y_biases,y_wanted)==y_wanted
    assert visible_fit((.05*h,.95*h),(0,h),
                       (1.4,1.4),(0.,0.),y_wanted)==y_wanted

# Additional bilateral layout regression: swapping left/right calibration
# must only swap the outputs, not change the shared source-space translation.
# Exercise distinct top and bottom dominant eyes and nonidentical existing
# per-eye biases so a future one-eye-only adjustment cannot pass by symmetry.
for height in (768., 1080., 1440., 2688.):
    cases = (
        ((.005*height, .12*height), (.88, .94),
         (.045*height, -.05*height), (.011*height, -.009*height)),
        ((.88*height, .995*height), (.85, .96),
         (.08*height, .055*height), (.011*height, -.009*height)),
    )
    for box, scales, biases, offsets in cases:
        actual = visible_fit(box, (0., height), scales, biases, offsets)
        reversed_eye = visible_fit(
            box, (0., height), tuple(reversed(scales)),
            tuple(reversed(biases)), tuple(reversed(offsets)))
        assert abs(actual[0] - reversed_eye[1]) <= 1e-7 * height
        assert abs(actual[1] - reversed_eye[0]) <= 1e-7 * height
        correction = actual[0] - offsets[0]
        assert abs(correction - (actual[1] - offsets[1])) <= 1e-7 * height
        for s, b, offset in zip(scales, biases, actual):
            assert s*box[0] + b + offset >= .025*height - 1e-6*height
            assert s*box[1] + b + offset <= .975*height + 1e-6*height

# A corrupt eye calibration must not silently become a unilateral HUD fit.
# Reject replacing any paired-eye nonfinite/nonpositive validation with a no-op.
for validation_guard in (
    "!std::isfinite(eyeScaleY[0])",
    "!std::isfinite(eyeScaleY[1])",
    "!std::isfinite(eyeBiasY[0])",
    "!std::isfinite(eyeBiasY[1])",
    "eyeScaleY[0] <= 0.0f",
    "eyeScaleY[1] <= 0.0f",
):
    assert safe.count(validation_guard) == 1, validation_guard
    mutant = safe.replace(validation_guard, "false", 1)
    assert mutant.count(validation_guard) == 0
print("PASS bilateral top/bottom eye-swap invariance, disparate offsets, six invalid-calibration mutants")

# Structural/mutation acceptance: both eyes are mandatory; neither the
# pre-FOV scalar approximation nor separately clamped eye shifts is valid.
for marker in (
    "const float eyeScaleY[2], const float eyeBiasY[2]",
    "eyeScaleY[0] * anchor.minY + eyeBiasY[0] + edgeYBias",
    "eyeScaleY[1] * anchor.minY + eyeBiasY[1] + edgeYBias",
    "eyeScaleY[0] * anchor.maxY + eyeBiasY[0] + edgeYBias",
    "eyeScaleY[1] * anchor.maxY + eyeBiasY[1] + edgeYBias",
    "safeTop - leftYMin, safeTop - rightYMin",
    "safeBottom - leftYMax, safeBottom - rightYMax",
    "edgeYBias += std::clamp(0.0f, verticalMin, verticalMax);",
):
    assert marker in safe, marker
assert "eyeScaleY, eyeBiasY," in draw
for wrong,replacement in (
    ("safeTop - rightYMin", "safeTop - leftYMin"),
    ("safeBottom - rightYMax", "safeBottom - leftYMax"),
    ("eyeScaleY[1] * anchor.minY", "hudScaleY * anchor.minY"),
    ("eyeBiasY[1] + edgeYBias", "hudBiasY + edgeYBias"),
):
    assert wrong in safe
    changed=safe.replace(wrong,replacement,1)
    assert changed!=safe
    assert not all(token in changed for token in (
        "safeTop - leftYMin, safeTop - rightYMin",
        "safeBottom - leftYMax, safeBottom - rightYMax",
        "eyeScaleY[1] * anchor.minY + eyeBiasY[1] + edgeYBias"))
print("PASS bilateral vertical inset, 4 aspect fixtures and 4 destructive source mutants")

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
assert "return CurrentSpriteQueueProducer;" in sel
assert "return CurrentDirectExactProducer;" in sel
assert sel.index("if (SpriteQueueDepth != 0)") < (
    sel.index("return CurrentSpriteQueueProducer;")) < (
    sel.index("if (ExactLensCentreDrawOwnsSemantic())")) < (
    sel.index("return CurrentDirectExactProducer;"))
# The direct non-lens HUD owner still survives when no SpriteNode is active.
assert "return ProducerToken::LensFlareCentre;" in sel
src = (root / "src/hooks_uiscaling.cpp").read_text()
direct = src[src.index("static void __cdecl OutRunHudTextProducer_dest("):
             src.index("static int __cdecl OutRunHudText_clip(")]
for x in ("semantic.space == OutRunVRHudSemantics::SpacePolicy::ScreenHud",
          "std::optional<OutRunVR::GameSemantic::ScopedExactProducerSemantic>",
          "directHudOwner.emplace(", "nullptr, true, token);",
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
# The former false path let a preceding world Draw's NextDrawScope win over
# direct BA9D0 ScreenHud. Verify the old value is a failing mutation, while
# preserving queue priority and the original text producer entrypoint.
assert "nullptr, false, token);" not in direct
direct_isolation_mutant = direct.replace(
    "nullptr, true, token);", "nullptr, false, token);", 1)
assert direct_isolation_mutant != direct
assert "nullptr, true, token);" not in direct_isolation_mutant
print("PASS immediate/queued BA9D0 VR HUD source ownership and four destructive regressions")


# Exact peripheral fallback: if the ordinary 0.90x boosted sprite would
# clip across asymmetric Quest eyes, solve the largest common safe multiplier
# down to 1x. The old return(previousBoost) exposed a clipped glyph group.
adaptive = code[code.index("float R30AdaptivePeripheralHudBoost("):
                code.index("bool R30TransformHudScissor(")]
assert "previousBoost > 3.0f" in adaptive
assert "previousBoost >= 3.0f" not in adaptive
assert "if (!fitsBothEyes(previousBoost))" in adaptive
assert "if (!fitsBothEyes(1.0f))" in adaptive
assert "float low = 1.0f, high = previousBoost;" in adaptive
assert "for (int i = 0; i < 10; ++i)" in adaptive
assert adaptive.index("if (!fitsBothEyes(previousBoost))") < adaptive.index(
    "if (desired <= previousBoost)")
assert adaptive.index("if (!fitsBothEyes(1.0f))") < adaptive.index(
    "float low = 1.0f, high = previousBoost;") < adaptive.index(
    "if (fitsBothEyes(desired))")

def bilateral_fits(b, width, height, bounds, anchor_xy, eye_offset, scale_x=.55, scale_y=.35):
    min_x, max_x, min_y, max_y = bounds
    ax, ay = anchor_xy
    midx, midy = width * .5, height * .5
    min_shift, max_shift = -math.inf, math.inf
    for offset in eye_offset:
        sx = scale_x*b
        bias_x = (1.-sx)*(midx + midx*ax) + offset*midx
        min_shift = max(min_shift, .025*width - (sx*min_x + bias_x))
        max_shift = min(max_shift, .975*width - (sx*max_x + bias_x))
    sy = scale_y*b
    by = (1.-sy)*(midy - midy*ay)
    ymin = sy*min_y + by
    ymax = sy*max_y + by
    return (min_shift <= max_shift and
            .025*height - ymin <= .975*height - ymax)

def fallback_bilateral(previous, fits):
    if fits(previous):
        return previous
    if not fits(1.):
        return 1.
    low, high = 1., previous
    for _ in range(10):
        mid = low + (high-low)*.5
        if fits(mid):
            low = mid
        else:
            high = mid
    return low

for w,h in ((1024,768), (1920,1080), (3440,1440)):
    box = (0., .4*w, .6*h, .7*h)
    fits = lambda b: bilateral_fits(
        b, w, h, box, (-.6,.45), (-.6,.6))
    original_boost = .90/.55
    assert fits(1.) and not fits(original_boost)
    repaired = fallback_bilateral(original_boost, fits)
    assert 1. < repaired < original_boost and fits(repaired)
    assert not fits(min(original_boost, repaired + .01))
    assert fallback_bilateral(1., fits) == 1.
    assert fallback_bilateral(3., lambda b: False) == 1.
    assert fallback_bilateral(3., lambda b: True) == 3.
# Mutation cases must break exact owning source and not merely comments or
# a Python-only model.
for before, after in (
    ("if (!fitsBothEyes(previousBoost))", "if (fitsBothEyes(previousBoost))"),
    ("if (!fitsBothEyes(1.0f))", "if (fitsBothEyes(1.0f))"),
    ("float low = 1.0f, high = previousBoost;",
     "float low = previousBoost, high = previousBoost;"),
    ("return low;\n            }\n            if (desired <= previousBoost)",
     "return previousBoost;\n            }\n            if (desired <= previousBoost)"),
):
    assert before in adaptive
    mutant = adaptive.replace(before, after, 1)
    assert not all(t in mutant for t in (
        "if (!fitsBothEyes(previousBoost))",
        "if (!fitsBothEyes(1.0f))",
        "float low = 1.0f, high = previousBoost;",
        "return low;\n            }\n            if (desired <= previousBoost)"))
print("PASS opt-in stereo HUD bilateral clip recovery, 4:3/16:9/21:9 and 4 negative mutations")
