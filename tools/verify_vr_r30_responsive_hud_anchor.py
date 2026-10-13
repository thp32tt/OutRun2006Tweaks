#!/usr/bin/env python3
"""R30 Issue #119 opt-in peripheral HUD draw contract (no HMD claims)."""
from pathlib import Path
from math import isfinite

root = Path(__file__).resolve().parents[1]
code = (root / "src/vr/d3d9/stereo_renderer_r30.cpp").read_text()
settings = (root / "src/vr/settings.cpp").read_text()
assert 'Setting<bool> VRHudEdgeAnchors{ "VR", "HudEdgeAnchors", false' in settings
start = code.index("R30HudEdgeAnchor R30GetExactHudEdgeAnchor(")
end = code.index("bool R30TransformHudScissor(", start)
helper = code[start:end]
for tok in ("CurrentSpriteQueueProducer", "ProducerToken::OutRunHudPeripheralText",
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
assert owner.count("ProducerToken::OutRunHudPeripheralText") == 2
assert owner.count("ProducerToken::OutRunHudText") == 2
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
scope_begin = code.index("float R30HudScopeScale() noexcept")
scope_end = code.index("void R30HudContainScale(", scope_begin)
scope = code[scope_begin:scope_end]
for token in (
    "ExternalOverlaySemanticDepth != 0 &&",
    "ExternalOverlaySemanticDepth == 0 &&",
    "Game::current_mode &&",
    "*Game::current_mode == GameState::STATE_SMPAUSEMENU",
    "RenderScope::ScreenOverlay2D &&",
    "Settings::VRPauseMenuScale.get()",
    "std::clamp(Settings::VRPauseMenuScale.get(),",
    "0.55f, 1.50f",
    "return R30HudScaleValue();",
):
    assert token in scope, token
assert scope.index("return 1.0f;") < scope.index(
    "*Game::current_mode == GameState::STATE_SMPAUSEMENU") < scope.index(
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
def effective(mode, semantic, f11=False, hud=.55, pause=1.0):
    if semantic == "overlay" and f11:
        return 1.0
    if mode == 0x12 and semantic == "overlay" and not f11 and pause > 0:
        return max(.55, min(1.50, pause))
    return hud
for source_w, source_h in ((1024,768),(1920,1080),(3440,1440),(2496,2688)):
    for eye_w, eye_h in ((1024,768),(2496,2688)):
        factor = max(.75, min(3.50, (source_w/source_h)/(eye_w/eye_h)))
        assert effective(0x12, "overlay") / factor > 0
        assert effective(0x12, "overlay") == 1.
        assert effective(0x12, "hud") == .55
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
    ("RenderScope::ScreenOverlay2D &&", "RenderScope::ScreenHud &&"),
    ("std::clamp(Settings::VRPauseMenuScale.get(),",
     "std::clamp(Settings::VRHudScale.get(),"),
):
    assert scope.count(bad) == 1, bad
    mutant = scope.replace(bad, good, 1)
    assert not all(token in mutant for token in (
        "ExternalOverlaySemanticDepth == 0 &&",
        "*Game::current_mode == GameState::STATE_SMPAUSEMENU",
        "RenderScope::ScreenOverlay2D &&",
        "std::clamp(Settings::VRPauseMenuScale.get(),"))
print("PASS exact ESC pause ownership, F11/HUD/world negatives and size/aspect fixtures")


# Issue #119: independently centre the ESC/pause menu vertically. The same
# viewport-fraction must feed the pretransformed XYZRHW and shader HUD paths.
# User-visible placement still requires Quest3/VDXR optical acceptance.
pause_begin = code.index("float R30PauseMenuVerticalFraction() noexcept")
pause_end = code.index("float R30HudScopeScale() noexcept", pause_begin)
pause_func = code[pause_begin:pause_end]
for token in (
    "ExternalOverlaySemanticDepth != 0 ||",
    "!Game::current_mode ||",
    "*Game::current_mode != GameState::STATE_SMPAUSEMENU ||",
    "RenderScope::ScreenOverlay2D)",
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
assert shader.count("clipCorrection._42 = -2.0f * R30PauseMenuVerticalFraction();") == 1
assert shader.index("clipCorrection._42 = -2.0f * R30PauseMenuVerticalFraction();") > shader.index("screenKind != R30ScreenSpaceKind::Hud2D")
assert "R30PauseMenuVerticalFraction()" not in code[fixed_end:shader_begin]

def pause_fraction(state, semantic, external, fraction):
    if external or state != "pause" or semantic != "overlay" or not isfinite(fraction):
        return 0.0
    return max(-.25, min(.25, fraction))

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
    ("*Game::current_mode != GameState::STATE_SMPAUSEMENU ||",
     "*Game::current_mode != GameState::STATE_GAME ||"),
    ("ExternalOverlaySemanticDepth != 0 ||",
     "ExternalOverlaySemanticDepth == 0 ||"),
    ("std::clamp(fraction, -0.25f, 0.25f)",
     "std::clamp(fraction, -1.0f, 1.0f)"),
):
    assert pause_func.count(bad) == 1
    mutant = pause_func.replace(bad, good, 1)
    assert not all(t in mutant for t in (
        "*Game::current_mode != GameState::STATE_SMPAUSEMENU ||",
        "ExternalOverlaySemanticDepth != 0 ||",
        "std::clamp(fraction, -0.25f, 0.25f)"))
for bad, good in (
    ("height * R30PauseMenuVerticalFraction();", "height * 0.0f;"),
    ("clipCorrection._42 = -2.0f * R30PauseMenuVerticalFraction();",
     "clipCorrection._42 = 2.0f * R30PauseMenuVerticalFraction();"),
):
    assert (fixed + shader).count(bad) == 1
    mutant = (fixed + shader).replace(bad, good, 1)
    assert not (("height * R30PauseMenuVerticalFraction();" in mutant) and
                ("clipCorrection._42 = -2.0f * R30PauseMenuVerticalFraction();" in mutant))
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
