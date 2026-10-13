#!/usr/bin/env python3
"""F11 Quest3 eye-aspect raster-density regression (static + numeric/destructive)."""
from pathlib import Path
import math

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "src/overlay/hooks_overlay.cpp"
FONT = ROOT / "src/overlay/overlay.cpp"
HEADER = ROOT / "src/overlay/overlay.hpp"
COMMON = ROOT / "src/vr/d3d9/stereo_renderer_r23.cpp"
EYE_API = ROOT / "src/vr/core/r23_eye_extent_api.hpp"

def check(hook: str, font: str, header: str) -> None:
    # Pin actual owning scopes. Searching whole files misses destructive
    # mutations when a second valid-looking token remains in a separate
    # ImGui draw call or VR shell sizing path.
    font_guard = font.split("void Overlay::rebuild_fonts()", 1)[1].split(
        "// Metrics shared by every theme.", 1
    )[0]
    shell_guard = font.split("void Overlay::render_shell()", 1)[1].split(
        "void Overlay::init()", 1
    )[0]
    density_guard = hook.split("float vrFontMultiplier = 1.0f;", 1)[1].split(
        "// A new atlas needs a new font texture.", 1
    )[0]
    for target, needles in (
        (density_guard, (
            "overlayActive && Game::is_vr_gameplay_presentation()",
            "R23TryGetPublishedEyeExtent(0, lw, lh)",
            "R23TryGetPublishedEyeExtent(1, rw, rh)",
            "lw >= 640u && lh >= 480u && rw >= 640u && rh >= 480u",
            "std::isfinite(factor) && factor > 0.0f",
            "std::ceil(factor * 4.0f) * 0.25f, 1.0f, 3.0f",
            "Overlay::FontsDirty = true;",
        )),
        (hook, ("ImGui_ImplDX9_InvalidateDeviceObjects();",)),
        (font_guard, (
            "std::clamp(GlobalFontScale, 0.5f, 5.0f)",
            "std::clamp(VrFontMultiplier, 1.0f, 3.0f)",
            "ImGui::GetStyle().FontSizeBase = sizePixels;",
            "io.Fonts->Clear();",
        )),
        (shell_guard, (
            "std::clamp(VrFontMultiplier, 1.0f, 3.0f)",
            "1130.f * vrDensity",
            "600.f * vrDensity",
            "ImGuiCond_Appearing : ImGuiCond_FirstUseEver",
        )),
        (header, ("inline static float VrFontMultiplier = 1.0f;",)),
    ):
        for marker in needles:
            assert marker in target, f"missing F11 density guard: {marker}"
    assert hook.index("Overlay::FontsDirty = true;") < hook.index(
        "Overlay::rebuild_fonts();"
    ) < hook.index("ImGui_ImplDX9_NewFrame();")

def check_projection(renderer: str, semantic: str) -> None:
    # F11 must not be reduced by VR.HudScale *after* rebuilding a sharp
    # source-resolution font atlas. The external semantic is not permission
    # to relax generic game ScreenOverlay2D/menu or projected-world content.
    start = renderer.index("float R30HudScopeScale() noexcept")
    end = renderer.index("void R30HudContainScale(", start)
    scope = renderer[start:end]
    for token in (
        "ExternalOverlaySemanticDepth != 0",
        "EffectiveScope() ==",
        "RenderScope::ScreenOverlay2D",
        "return 1.0f;",
        "return R30HudScaleValue();",
    ):
        assert token in scope, token
    assert scope.index("ExternalOverlaySemanticDepth != 0") < scope.index(
        "return 1.0f;") < scope.index("return R30HudScaleValue();")
    contain = renderer[end:renderer.index("bool R30TransformHudScissor(", end)]
    assert "const float userScale = R30HudScopeScale();" in contain
    assert "R30HudContain.userScale == userScale" in contain
    assert "scaleY = userScale / sourceOverTarget;" in contain
    assert "scaleX = userScale * sourceOverTarget;" in contain
    for marker in (
        "inline thread_local unsigned ExternalOverlaySemanticDepth = 0;",
        "++ExternalOverlaySemanticDepth;",
        "--ExternalOverlaySemanticDepth;",
        "if (ExternalOverlaySemanticDepth != 0)",
    ):
        assert marker in semantic, marker


def check_projection_mutations(renderer: str, semantic: str) -> None:
    mutants = (
        ("ExternalOverlaySemanticDepth != 0", "ExternalOverlaySemanticDepth == 0"),
        ("RenderScope::ScreenOverlay2D)", "RenderScope::ScreenHud)"),
        ("return 1.0f;", "return R30HudScaleValue();"),
        ("const float userScale = R30HudScopeScale();",
         "const float userScale = R30HudScaleValue();"),
        ("R30HudContain.userScale == userScale",
         "R30HudContain.userScale == 1.0f"),
    )
    for a, b in mutants:
        assert a in renderer
        try:
            check_projection(renderer.replace(a, b, 1), semantic)
        except AssertionError:
            pass
        else:
            raise AssertionError("F11 scoped projection mutant survived: " + a)


def factor(source_w, source_h, eye_w, eye_h):
    if min(source_w, source_h, eye_w, eye_h) <= 0:
        return 1.0
    raw = (source_w / source_h) / (eye_w / eye_h)
    if not math.isfinite(raw) or raw <= 0:
        return 1.0
    return min(3.0, max(1.0, math.ceil(raw * 4.0) * 0.25))

def main():
    hook, font, header = (p.read_text(encoding="utf-8")
                          for p in (HOOK, FONT, HEADER))
    renderer = (ROOT / "src/vr/d3d9/stereo_renderer_r30.cpp").read_text(encoding="utf-8")
    semantic = (ROOT / "src/vr/game/render_semantics.hpp").read_text(encoding="utf-8")
    check(hook, font, header)
    check_projection(renderer, semantic)
    check_projection_mutations(renderer, semantic)
    # Default R26 and new R29 compile separate final TUs but share R23.
    common = COMMON.read_text(encoding="utf-8")
    api = EYE_API.read_text(encoding="utf-8")
    assert '#include "vr/core/r23_eye_extent_api.hpp"' in hook
    assert "R29OwnerRecommendedEyeExtent" not in hook
    assert "R23TryGetPublishedEyeExtent(" in common
    assert "bool R23TryGetPublishedEyeExtent(" in api
    assert "SharedState->structSize != sizeof(OutRunVR::SharedPoseState)" in common
    assert "SharedState->recommendedWidth[eye]" in common
    assert "SharedState->recommendedHeight[eye]" in common
    # Desktop 4:3 is unmodified; wide/portrait XR needs sharp larger glyphs.
    assert factor(1024, 768, 1024, 768) == 1.0
    assert factor(1920, 1080, 2496, 2688) == 2.0
    assert factor(3440, 1440, 2496, 2688) == 2.75
    assert factor(5120, 1440, 2496, 2688) == 3.0
    assert factor(0, 1440, 2496, 2688) == 1.0
    # Detect removal of either eye authority, desktop isolation or atlas rebuild.
    mutations = (
        (hook, "overlayActive && Game::is_vr_gameplay_presentation()",
         "overlayActive || Game::is_vr_gameplay_presentation()", font, header),
        (hook, "R23TryGetPublishedEyeExtent(1, rw, rh)",
         "true", font, header),
        (hook, "Overlay::FontsDirty = true;",
         "Overlay::FontsDirty = false;", font, header),
        (font, "std::clamp(VrFontMultiplier, 1.0f, 3.0f)",
         "1.0f", hook, header),
        (font, "1130.f * vrDensity", "1130.f", hook, header),
    )
    for index, (target, old, new, other, h) in enumerate(mutations):
        assert old in target
        if target is hook:
            broken = (target.replace(old, new, 1), font, header)
        else:
            broken = (hook, target.replace(old, new, 1), header)
        try:
            check(*broken)
        except AssertionError:
            continue
        raise AssertionError(f"F11 regression mutant {index} survived")
    # 3440x1440 desktop -> 2496x2688 XR eye. The source/eye
    # aspect compensation remains identical in both paths; only F11 escapes
    # the gameplay scale of 0.55. This is geometry, not headset optical PASS.
    aspect = (3440 / 1440) / (2496 / 2688)
    assert 2.5 < aspect < 2.6
    game_x, game_y = 0.55, 0.55 / aspect
    f11_x, f11_y = 1.0, 1.0 / aspect
    assert abs(f11_x / game_x - f11_y / game_y) < 1e-12
    assert abs(game_x / game_y - f11_x / f11_y) < 1e-12
    assert f11_y > game_y and f11_x > game_x
    print("VR F11 native atlas + independently sized stereo plane PASS; 10 negative mutants rejected")

if __name__ == "__main__":
    main()
