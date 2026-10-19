#!/usr/bin/env python3
"""DX9Ex ESC/pause vertical FOV owner: source integration and negative mutation."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / "src/vr/d3d9/stereo_renderer_r30.cpp").read_text(encoding="utf-8")
helper = (ROOT / "src/vr/d3d9/pause_menu_eye_affine.hpp").read_text(encoding="utf-8")
tests = (ROOT / "vrhost/tests/pause_menu_eye_affine_smoke.cpp").read_text(encoding="utf-8")
ui_source = (ROOT / "src/hooks_uiscaling.cpp").read_text(encoding="utf-8")
pause_source = (ROOT / "src/hooks_drawdistance.cpp").read_text(encoding="utf-8")
semantics = (ROOT / "src/vr/game/render_semantics.hpp").read_text(encoding="utf-8")

def require(condition: bool, context: str = "ESC source invariant") -> None:
    # Never rely on Python's 'assert': -O/PYTHONOPTIMIZE must not bypass
    # the production gate or turn negative-mutation checks into false PASS.
    if not condition:
        raise AssertionError(context)


def check(s: str, h: str) -> None:
    require('#include "pause_menu_eye_affine.hpp"' in s)
    # Other HUD paths also gate F11: check the specific ESC owner.
    exact_pause = s[s.index('bool R30IsPauseMenuElement()'):
                    s.index('constexpr float R30PauseShaderPlaneScale(')]
    require('ExternalOverlaySemanticDepth == 0' in exact_pause)
    require('GameState::STATE_SMPAUSEMENU' in s)
    require('R30IsPauseMenuExactArrow()' in s)
    arrow = s[s.index('bool R30IsPauseMenuExactArrow()'):s.index('bool R30IsPauseMenuExactShell()')]
    require('OutRunVrPauseEye::ExactArrowOwner(' in arrow)
    # R84 accepts both the newly isolated exact pause-arrow producer and
    # already-owned generic paused UI. Mutating either producer lookup to a
    # queue-only lookup must fail: synchronous native E8 calls also render.
    require(arrow.count('GameSemantic::CurrentRenderProducerToken() ==') == 2)
    require('ProducerToken::PauseOptionArrow' in arrow)
    require('ProducerToken::ExactScreenHudClipSprite' in arrow)
    require('GameSemantic::CurrentQueueProducerToken()' not in arrow)
    require('CurrentSpriteQueueProducer ==' not in arrow)
    require('constexpr bool ExactArrowOwner(bool screenHud, bool exactProducer)' in h)
    require('return screenHud && exactProducer;' in h)
    require('ExactArrowOwner(true, true)' in tests)
    require('ExactArrowOwner(true, false)' in tests)
    require('bool R30IsPauseMenuExactShell() noexcept' in s)
    shell = s[s.index('bool R30IsPauseMenuExactShell() noexcept'):
              s.index('bool R30IsPauseMenuElement() noexcept')]
    require('OutRunVrPauseEye::ExactShellOwner(' in shell)
    require('RenderScope::ScreenOverlay2D' in shell)
    require('CurrentRenderProducerToken() ==' in shell)
    require('ProducerToken::PauseFrameShell' in shell)
    require('constexpr bool ExactShellOwner(bool screenOverlay, bool exactProducer)' in h)
    require('return screenOverlay && exactProducer;' in h)
    require('ExactShellOwner(true, true)' in tests)
    require('ExactShellOwner(true, false)' in tests)
    require('(R30IsPauseMenuExactShell() || R30IsPauseMenuExactArrow())' in exact_pause)
    require(s.count('R30PauseMenuVerticalAffine(') == 4)
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
        require(required in s, required)
    # Asymmetric horizontal eye FOV must not detach the shader shell from
    # XYZRHW arrows; ordinary HUD/F11 remain on their old shader scale.
    require('const bool pauseOwned = R30IsPauseMenuElement();' in s)
    require('clipCorrection._11 = OutRunVrPauseEye::ShaderHorizontalScale(' in s)
    require('hudScaleX, eyeScale[eye], pauseOwned);' in s)
    require('inline float ShaderHorizontalScale(' in h)
    require('return pauseOwned ? commonScale * eyeFovScale : commonScale;' in h)
    require('ShaderHorizontalScale(' in tests and 'xyzrhwNdc' in tests)
    require('const float o = -sum[eye] / span[eye];' in h)
    require('span[eye] <= 0.05f || span[eye] > 10.0f' in h)
    require('return {};' in h)
    require('failOne.valid' in tests and 'extreme.valid' in tests)
    # Full ESC optical-size ownership is independent of gameplay HUD and F11.
    require('inline float ResponsiveUserScale(' in h)
    require('0.55f + (bounded - 0.55f) * (0.70f / 0.45f)' in h)
    require('1.25f + (bounded - 1.0f) * 0.50f' in h)
    require('const float readable = OutRunVrPauseEye::ResponsiveUserScale(' not in s)
    require('return std::clamp(requested, 0.55f, 1.50f);' in s)
    require('return shoulder + headroom * excess / (headroom + excess);' in h)
    require('const float smallOptical = ResponsiveMenuScale(' in tests)
    require('defaultOptical < largeOptical && largeOptical < 2.25f' in tests)
    require('inline float ResponsiveMenuScale(' in h)
    require('menuScale * std::sqrt(boundedAspect)' in h)
    require('constexpr float shoulder = 1.95f;' in h)
    require('const bool exactPauseShaderOwner =\n                    OutRunVrPauseEye::OwnsPauseShaderPlane(' in s)
    require('exactHud, genericQueuedHud, R30IsPauseMenuElement());' in s)
    require('constexpr bool OwnsPauseShaderPlane(' in h)
    require('return originalPause && (sourceHud || sourceQueuedOverlay);' in h)
    require('OwnsPauseShaderPlane(false, true, true)' in tests)
    require('OwnsPauseShaderPlane(false, false, true)' in tests)
    require('const bool pauseResponsive = R30IsPauseMenuElement() &&' in s)
    require('if (!std::isfinite(requested) || requested <= 0.0f)' in s)
    require('std::isfinite(Settings::VRPauseMenuScale.get()) &&' in s)
    require('Settings::VRPauseMenuScale.get() > 0.0f;' in s)
    require('R30HudContain.pauseResponsive == pauseResponsive' in s)
    require('R30HudContain.pauseResponsive = pauseResponsive;' in s)
    # User's R84 HMD regression: do not multiply pause size twice in XR.
    require('OutRunVrPauseEye::ResponsiveMenuScale(' not in s)
    require('const auto contained = OutRunVrPauseEye::ContainNativePauseScale(' in s)
    require('scaleX = contained.x;' in s and 'scaleY = contained.y;' in s)
    require('userScale / sourceOverTarget' in h)
    require('userScale * sourceOverTarget' in h)
    require('ContainNativePauseScale(1.0f, sourceOverEye, true)' in tests)
    require('if (exactPauseShaderOwner)\n                    R30HudContainScale(stereo, shaderPauseX, shaderPauseY);' in s)
    require('hudScale._11 = shaderPauseX;' in s and
            'hudScale._22 = shaderPauseY;' in s)
    require('const float questScale = ResponsiveMenuScale(' in tests)
    require('ResponsiveMenuScale(1.25f, factor, false)' in tests)


def check_pause_frame_owner(ui: str, pause: str, semantic_source: str) -> None:
    require('PauseFrameShell,' in semantic_source,
            'exact PauseFrameDisp producer token missing')
    frame = pause[pause.index('class PauseMenuVisibility'):
                  pause.index('PauseMenuVisibility PauseMenuVisibility::instance;')]
    for required in (
        'Module::exe_ptr(0x8C5F0)',
        'ScopedExactProducerSemantic pauseFrameOwner(\n'
        '\t\t\tOutRunVR::GameSemantic::RenderScope::ScreenOverlay2D,\n'
        '\t\t\tnullptr, true,\n'
        '\t\t\tOutRunVR::GameSemantic::ProducerToken::PauseFrameShell);',
        'FirstVerifiedAppendedNodeOnStableRoot(',
        'PeekSpriteNodeProducerToken(node) == ProducerToken::None',
        'TagPauseFrameNodes(before, rootsBefore, entrySerial);',
    ):
        require(required in frame, required)

    hud = ui[ui.index('static void __cdecl OutRunHudTextProducer_dest('):
             ui.index('static int __cdecl OutRunHudText_clip(')]
    require('const bool pauseFrameParent =' in hud)
    require('ProducerToken::PauseFrameShell' in hud)
    require(
        'OutRunHudTextScreenHud = previous ||\n'
        '\t\t\t(!pauseFrameParent &&\n'
        '\t\t\t semantic.space == '
        'OutRunVRHudSemantics::SpacePolicy::ScreenHud);' in hud,
        'BA9D0 pause parent must not promote ESC child text to gameplay HUD')

    glyph = ui[ui.index('static int __cdecl TextGlyph_putSprite('):
               ui.index('enum SpriteScaleType')]
    for required in (
        'const bool pauseFrameGlyph = !exactGoalResult &&',
        'ProducerToken::PauseFrameShell',
        'else if (pauseFrameGlyph)',
        'RenderScope::ScreenOverlay2D',
        'nullptr, &rootsBefore, entrySerial',
    ):
        require(required in glyph, required)


check_pause_frame_owner(ui_source, pause_source, semantics)
for bad_ui, bad_pause, bad_semantics in (
    (ui_source.replace('else if (pauseFrameGlyph)', 'else if (false)', 1),
     pause_source, semantics),
    (ui_source.replace(
        '(!pauseFrameParent &&\n\t\t\t semantic.space ==',
        '(true &&\n\t\t\t semantic.space ==', 1),
     pause_source, semantics),
    (ui_source,
     pause_source.replace(
        'PeekSpriteNodeProducerToken(node) == ProducerToken::None',
        'true', 1),
     semantics),
    (ui_source,
     pause_source.replace(
        'OutRunVR::GameSemantic::RenderScope::ScreenOverlay2D,\n'
        '\t\t\tnullptr, true,',
        'OutRunVR::GameSemantic::RenderScope::ScreenHud,\n'
        '\t\t\tnullptr, true,', 1),
     semantics),
    (ui_source, pause_source,
     semantics.replace('PauseFrameShell,', 'PauseFrameShell_REMOVED,', 1)),
):
    require(
        bad_ui != ui_source or bad_pause != pause_source or
        bad_semantics != semantics,
        'PauseFrame negative mutation did not change source')
    try:
        check_pause_frame_owner(bad_ui, bad_pause, bad_semantics)
    except AssertionError:
        continue
    raise AssertionError("unsafe PauseFrame owner mutation escaped verification")

check(source, helper)
for mutant_index, mutant in enumerate((
    source.replace('GameSemantic::CurrentRenderProducerToken() ==',
                   'GameSemantic::CurrentQueueProducerToken() ==', 1),
    source.replace('return OutRunVrPauseEye::ExactArrowOwner(',
                   'return OutRunVrPauseEye::ShaderHorizontalScale(', 1),
    source.replace('return OutRunVrPauseEye::ExactShellOwner(',
                   'return OutRunVrPauseEye::ExactArrowOwner(', 1),
    source.replace('ProducerToken::PauseFrameShell',
                   'ProducerToken::None', 1),
    source.replace('hudScaleX, eyeScale[eye], pauseOwned);',
                   'hudScaleX, eyeScale[eye], false);', 1),
    source.replace('const bool pauseOwned = R30IsPauseMenuElement();',
                   'const bool pauseOwned = false;', 1),
    source.replace('clipCorrection._11 = OutRunVrPauseEye::ShaderHorizontalScale(',
                   'clipCorrection._11 = (', 1),
    source.replace('return std::clamp(requested, 0.55f, 1.50f);',
                   'return std::clamp(requested * 1.25f, 0.55f, 1.50f);', 1),
    source.replace('scaleX = contained.x;',
                   'scaleX = contained.y;', 1),
    source.replace('hudScaleY * pauseVertical.scale[eye] * ndcY',
                   'hudScaleY * ndcY', 1),
    source.replace('rightDst[1] = transformedRightY;',
                   'rightDst[1] = transformedLeftY;', 1),
    source.replace('clipCorrection._42 = pauseVertical.offset[eye] -',
                   'clipCorrection._42 =', 1),
    # Mutate the ESC owner only. A separate rank/HUD source guard now has
    # the same expression and must not make this mutation a false failure.
    source[:source.index('bool R30IsPauseMenuElement()')] +
    source[source.index('bool R30IsPauseMenuElement()'):].replace(
        'ExternalOverlaySemanticDepth == 0',
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
    source.replace('scaleY = contained.y;',
                   'scaleY = contained.x;', 1),
    source.replace('exactHud, genericQueuedHud, R30IsPauseMenuElement());',
                   'exactHud, false, R30IsPauseMenuElement());', 1),
    source.replace('if (exactPauseShaderOwner)\n                    R30HudContainScale(stereo, shaderPauseX, shaderPauseY);',
                   'if (false)\n                    R30HudContainScale(stereo, shaderPauseX, shaderPauseY);', 1),
)):
    try:
        check(mutant, helper)
    except AssertionError:
        continue
    raise AssertionError(f"unsafe ESC mutation #{mutant_index} escaped verification")
for bad_helper in (
    helper.replace('return screenOverlay && exactProducer;',
                   'return screenOverlay;'),
    helper.replace('originalPause && (sourceHud || sourceQueuedOverlay)',
                   'originalPause && sourceHud'),
    helper.replace('originalPause && (sourceHud || sourceQueuedOverlay)',
                   'sourceHud || sourceQueuedOverlay'),
    helper.replace('pauseOwned ? commonScale * eyeFovScale : commonScale',
                   'commonScale'),
    helper.replace('pauseOwned ? commonScale * eyeFovScale : commonScale',
                   'commonScale * eyeFovScale'),
    helper.replace('userScale / sourceOverTarget',
                   'userScale * sourceOverTarget'),
    helper.replace('userScale * sourceOverTarget',
                   'userScale'),
):
    try:
        check(source, bad_helper)
    except AssertionError:
        continue
    raise AssertionError("shader/XYZRHW pause scale mutation escaped verification")
print("DX9Ex ESC vertical affine source/mutation PASS")
