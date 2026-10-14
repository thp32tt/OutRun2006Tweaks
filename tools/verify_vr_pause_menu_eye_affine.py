#!/usr/bin/env python3
"""DX9Ex ESC/pause vertical FOV owner: source integration and negative mutation."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / "src/vr/d3d9/stereo_renderer_r30.cpp").read_text(encoding="utf-8")
helper = (ROOT / "src/vr/d3d9/pause_menu_eye_affine.hpp").read_text(encoding="utf-8")
tests = (ROOT / "vrhost/tests/pause_menu_eye_affine_smoke.cpp").read_text(encoding="utf-8")

def check(s: str, h: str) -> None:
    assert '#include "pause_menu_eye_affine.hpp"' in s
    assert 'ExternalOverlaySemanticDepth == 0' in s
    assert 'GameState::STATE_SMPAUSEMENU' in s
    assert 'R30IsPauseMenuExactArrow()' in s
    assert s.count('R30PauseMenuVerticalAffine(') == 4
    for required in (
        'hudScaleY * pauseVertical.scale[eye] * ndcY',
        'eyeScaleY[0] * src[1] + eyeBiasY[0]',
        'eyeScaleY[1] * src[1] + eyeBiasY[1]',
        'clipCorrection._22 =',
        'hudScaleY * pauseVertical.scale[eye];',
        'clipCorrection._42 = pauseVertical.offset[eye] -',
        'leftDst[1] = transformedLeftY;',
        'rightDst[1] = transformedRightY;',
    ):
        assert required in s, required
    # Asymmetric horizontal eye FOV must not detach the shader shell from
    # XYZRHW arrows; ordinary HUD/F11 remain on their old shader scale.
    assert 'const bool pauseOwned = R30IsPauseMenuElement();' in s
    assert 'clipCorrection._11 = OutRunVrPauseEye::ShaderHorizontalScale(' in s
    assert 'hudScaleX, eyeScale[eye], pauseOwned);' in s
    assert 'inline float ShaderHorizontalScale(' in h
    assert 'return pauseOwned ? commonScale * eyeFovScale : commonScale;' in h
    assert 'ShaderHorizontalScale(' in tests and 'xyzrhwNdc' in tests
    assert 'const float o = -sum[eye] / span[eye];' in h
    assert 'span[eye] <= 0.05f || span[eye] > 10.0f' in h
    assert 'return {};' in h
    assert 'failOne.valid' in tests and 'extreme.valid' in tests
    # Full ESC optical-size ownership is independent of gameplay HUD and F11.
    assert 'inline float ResponsiveUserScale(' in h
    assert '0.55f + (bounded - 0.55f) * (0.70f / 0.45f)' in h
    assert '1.25f + (bounded - 1.0f) * 0.50f' in h
    assert 'const float readable = OutRunVrPauseEye::ResponsiveUserScale(' in s
    assert 'requested, Settings::VRHudResponsiveLayout.get());' in s
    assert 'return shoulder + headroom * excess / (headroom + excess);' in h
    assert 'const float smallOptical = ResponsiveMenuScale(' in tests
    assert 'defaultOptical < largeOptical && largeOptical < 2.25f' in tests
    assert 'inline float ResponsiveMenuScale(' in h
    assert 'menuScale * std::sqrt(boundedAspect)' in h
    assert 'constexpr float shoulder = 1.95f;' in h
    assert 'const bool pauseResponsive = R30IsPauseMenuElement() &&' in s
    assert 'if (!std::isfinite(requested) || requested <= 0.0f)' in s
    assert 'std::isfinite(Settings::VRPauseMenuScale.get()) &&' in s
    assert 'Settings::VRPauseMenuScale.get() > 0.0f;' in s
    assert 'R30HudContain.pauseResponsive == pauseResponsive' in s
    assert 'R30HudContain.pauseResponsive = pauseResponsive;' in s
    assert 'OutRunVrPauseEye::ResponsiveMenuScale(' in s
    assert 'userScale, sourceOverTarget, pauseResponsive);' in s
    assert 'scaleX = opticalScale;' in s
    assert 'scaleY = opticalScale / sourceOverTarget;' in s
    assert 'scaleX = opticalScale * sourceOverTarget;' in s
    assert 'scaleY = opticalScale;' in s
    assert 'const float questScale = ResponsiveMenuScale(' in tests
    assert 'ResponsiveMenuScale(1.25f, factor, false)' in tests

check(source, helper)
for mutant in (
    source.replace('hudScaleX, eyeScale[eye], pauseOwned);',
                   'hudScaleX, eyeScale[eye], false);', 1),
    source.replace('const bool pauseOwned = R30IsPauseMenuElement();',
                   'const bool pauseOwned = false;', 1),
    source.replace('clipCorrection._11 = OutRunVrPauseEye::ShaderHorizontalScale(',
                   'clipCorrection._11 = (', 1),
    source.replace('const float readable = OutRunVrPauseEye::ResponsiveUserScale(',
                   'const float readable = (std::max)(', 1),
    source.replace('requested, Settings::VRHudResponsiveLayout.get());',
                   'requested, 1.25f);', 1),
    source.replace('hudScaleY * pauseVertical.scale[eye] * ndcY',
                   'hudScaleY * ndcY', 1),
    source.replace('rightDst[1] = transformedRightY;',
                   'rightDst[1] = transformedLeftY;', 1),
    source.replace('clipCorrection._42 = pauseVertical.offset[eye] -',
                   'clipCorrection._42 =', 1),
    source.replace('ExternalOverlaySemanticDepth == 0',
                   'ExternalOverlaySemanticDepth != 0', 1),
    source.replace('std::isfinite(Settings::VRPauseMenuScale.get()) &&',
                   'true &&', 1),
    source.replace('Settings::VRPauseMenuScale.get() > 0.0f;',
                   'true;', 1),
    source.replace('if (!std::isfinite(requested) || requested <= 0.0f)',
                   'if (false)', 1),
    source.replace('R30HudContain.pauseResponsive == pauseResponsive',
                   'R30HudContain.pauseResponsive == false', 1),
    source.replace('R30HudContain.pauseResponsive = pauseResponsive;',
                   'R30HudContain.pauseResponsive = false;', 1),
    source.replace('userScale, sourceOverTarget, pauseResponsive);',
                   'userScale, sourceOverTarget, false);', 1),
    source.replace('scaleY = opticalScale / sourceOverTarget;',
                   'scaleY = userScale / sourceOverTarget;', 1),
):
    try:
        check(mutant, helper)
    except AssertionError:
        continue
    raise AssertionError("unsafe ESC mutation escaped verification")
for bad_helper in (
    helper.replace('pauseOwned ? commonScale * eyeFovScale : commonScale',
                   'commonScale'),
    helper.replace('pauseOwned ? commonScale * eyeFovScale : commonScale',
                   'commonScale * eyeFovScale'),
):
    try:
        check(source, bad_helper)
    except AssertionError:
        continue
    raise AssertionError("shader/XYZRHW pause scale mutation escaped verification")
print("DX9Ex ESC vertical affine source/mutation PASS")
