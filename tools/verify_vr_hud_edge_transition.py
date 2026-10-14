#!/usr/bin/env python3
"""DX9Ex exact producer HUD continuous anchor/zoom: source and mutations."""
from pathlib import Path
import math
root=Path(__file__).resolve().parents[1]
src=(root/"src/vr/d3d9/stereo_renderer_r30.cpp").read_text(encoding="utf-8")
hdr=(root/"src/vr/d3d9/hud_edge_transition.hpp").read_text(encoding="utf-8")
smoke=(root/"vrhost/tests/hud_edge_transition_smoke.cpp").read_text(encoding="utf-8")
def check(s,h):
    for token in (
        '#include "hud_edge_transition.hpp"',
        'ProducerToken::OutRunHudPeripheralText',
        'RenderScope::ScreenHud',
        'return OutRunVrHudEdge::PeripheralAnchor(ndc, limit);',
        'OutRunVrHudEdge::PeripheralWeight(rawAnchorX)',
        'OutRunVrHudEdge::PeripheralWeight(rawAnchorY)',
        'OutRunVrHudEdge::BlendBoost(1.0f, targetBoost, anchor.weight);',
        'previousBoost, fullDesired, anchor.weight);',
        'R30ConstrainHudEdgeToVisibleBounds(',
        'hudScaleX *= peripheralBoost;',
        'hudScaleY *= peripheralBoost;',
    ):
        assert token in s, token
    for token in (
        'distance <= 0.35f',  # guard the 0.35 NDC entry boundary against mutations
        'const float t = (distance - 0.35f) / 0.25f;',
        'return t * t * (3.0f - 2.0f * t);',
        'if (weight == 0.0f)',
        'return std::clamp(ndc, -limit, limit) * weight;',
        'std::clamp(weight, 0.0f, 1.0f)',
    ):
        assert token in h, token
    assert 'const float rawAnchorX = ' in s
    assert 'const float rawAnchorY = ' in s
    assert 'std::clamp(0.90f / baseScale, 1.0f, 3.0f)' in s
    assert '0.65f / hudScaleY, previousBoost, 3.0f' in s
check(src,hdr)
for original,wrong in (
    ('return OutRunVrHudEdge::PeripheralAnchor(ndc, limit);','return ndc;'),
    ('OutRunVrHudEdge::PeripheralWeight(rawAnchorX)','1.0f'),
    ('OutRunVrHudEdge::PeripheralWeight(rawAnchorY)','1.0f'),
    ('BlendBoost(1.0f, targetBoost, anchor.weight)','BlendBoost(1.0f, targetBoost, 1.0f)'),
    ('previousBoost, fullDesired, anchor.weight);','previousBoost, fullDesired, 1.0f);'),
):
    assert original in src
    try: check(src.replace(original,wrong,1),hdr)
    except AssertionError: pass
    else: raise AssertionError("HUD source mutation escaped: "+original)
for original,wrong in (
    ('if (weight == 0.0f)','if (false)'),
    ('t * t * (3.0f - 2.0f * t)','t'),
    ('std::clamp(weight, 0.0f, 1.0f)','weight'),
    ('distance <= 0.35f','distance <= 0.60f'),
):
    assert original in hdr
    try: check(src,hdr.replace(original,wrong,1))
    except AssertionError: pass
    else: raise AssertionError("HUD helper mutation escaped: "+original)
def weight(x):
    if not math.isfinite(x) or abs(x)<=.35 or abs(x)>1.2: return 0.
    if abs(x)>=.60: return 1.
    t=(abs(x)-.35)/.25
    return t*t*(3-2*t)
def anchor(x,limit):
    w=weight(x)
    return max(-limit,min(limit,x))*w if w else 0.
for aspect in (4/3,16/9,21/9):
    prev_a,prev_b=0.,1.
    for i in range(201,701):
        x=i/1000
        a=anchor(x,.82)
        b=1+(.9/.55-1)*weight(x)
        assert 0<=a-prev_a<=.004 and 0<=b-prev_b<=.007
        prev_a,prev_b=a,b
    assert anchor(.72,.82)*aspect==anchor(.72,.82)*aspect
assert anchor(float("nan"),.82)==0 and anchor(.2,.82)==0
assert "4.0f/3.0f" in smoke and "16.0f/9.0f" in smoke and "21.0f/9.0f" in smoke
assert "PeripheralAnchor(nan,.82f)" in smoke
print("DX9Ex HUD edge continuity 4:3/16:9/21:9, 9 destructive mutations PASS")

// Exact producer HUD: all four source clip edges must smoothly gate both
// geometry placement and optical-size enlargement. Other owners never enter
// this producer gate. Mutation controls protect the source, not just a model.
visibility_tokens = (
    'OutRunVrHudEdge::FullyVisibleWeight(',
    'minX - x0, (x0 + width) - maxX,',
    'minY - y0, (y0 + height) - maxY, width, height);',
    'R30PeripheralAnchor(rawAnchorX, 0.82f) * fullyVisibleWeight',
    'R30PeripheralAnchor(rawAnchorY, 0.78f) * fullyVisibleWeight',
    'transitionWeight * fullyVisibleWeight',
)
for token in visibility_tokens:
    assert token in src, token
for token in ('inline float FullyVisibleWeight(', '0.015f * sourceWidth',
              '0.015f * sourceHeight', 'const float t = (std::min)(x, y);'):
    assert token in hdr, token
for token in ('FullyVisibleWeight(', 'return 8;', 'return 9;', 'return 10;'):
    assert token in smoke, token
for original, mutant in (
    ('R30PeripheralAnchor(rawAnchorX, 0.82f) * fullyVisibleWeight',
     'R30PeripheralAnchor(rawAnchorX, 0.82f)'),
    ('R30PeripheralAnchor(rawAnchorY, 0.78f) * fullyVisibleWeight',
     'R30PeripheralAnchor(rawAnchorY, 0.78f)'),
    ('transitionWeight * fullyVisibleWeight', 'transitionWeight'),
):
    assert original in src
    assert not all(t in src.replace(original, mutant, 1)
                   for t in visibility_tokens)
def visible(inset,width):
    if not math.isfinite(inset) or width<=0: return 0.
    t=max(0.,min(1.,inset/(.015*width)))
    return t*t*(3.-2.*t)
for width in (640.,1920.,3440.):
    prev=0.
    for i in range(-10,111):
        a=visible(i*.00015*width,width)
        if i>=0: assert 0<=a-prev<=.016
        prev=a
    assert visible(-1.,width)==0.
    assert visible(0.,width)==0.
    assert visible(.015*width,width)==1.
print('PASS HUD source-boundary visibility ramp + 3 negative mutations')
