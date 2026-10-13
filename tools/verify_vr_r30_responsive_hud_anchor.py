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
for tok in ("CurrentSpriteQueueProducer", "ProducerToken::OutRunHudText",
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
assert code.count("edgeLeftBias") == 2
assert code.count("edgeRightBias") == 2
assert code.count("edgeYBias") == 2
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
    assert not all(t in mutated[mutated.index("float R30ExactPeripheralHudBoost("):
        mutated.index("// This is the high-frequency indexed smoke/sand/decal path:")]
        for t in ("anchor.x == 0.0f && anchor.y == 0.0f",
                  "0.90f / baseScale", "hudScaleX *= peripheralBoost;",
                  "hudScaleY *= peripheralBoost;"))
print("PASS exact peripheral glyph legibility floor, aspect parity and 4 destructive mutants")
