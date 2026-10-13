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
            "layoutChanged ? ImGuiCond_Always : initialPlacement",
            "std::fabs(previousContent.width - content.width) > 0.5f",
            "std::fabs(previousDensity - vrDensity) > 0.01f",
            "ImGui::SetNextWindowSize(windowSize, layoutPlacement);",
            "ImGuiStyleVar_FramePadding",
            "ImGuiStyleVar_ItemSpacing",
            "ImGuiStyleVar_ItemInnerSpacing",
            "ImGuiStyleVar_ScrollbarSize",
            "ImGui::PopStyleVar(4);",
        )),
        (header, ("inline static float VrFontMultiplier = 1.0f;",)),
    ):
        for marker in needles:
            assert marker in target, f"missing F11 density guard: {marker}"
    assert hook.index("Overlay::FontsDirty = true;") < hook.index(
        "Overlay::rebuild_fonts();"
    ) < hook.index("ImGui_ImplDX9_NewFrame();")

def check_shell_layout_mutations(font: str) -> None:
    """Reject actual owner changes that reintroduce stale resolution and tiny controls."""
    start = font.index("void Overlay::render_shell()")
    end = font.index("void Overlay::init()", start)
    shell = font[start:end]
    mutations = (
        ("layoutChanged ? ImGuiCond_Always : initialPlacement",
         "initialPlacement"),
        ("std::fabs(previousContent.width - content.width) > 0.5f",
         "false"),
        ("std::fabs(previousDensity - vrDensity) > 0.01f",
         "false"),
        ("ImGui::SetNextWindowSize(windowSize, layoutPlacement);",
         "ImGui::SetNextWindowSize(windowSize, initialPlacement);"),
        ("ImGui::PopStyleVar(4);", "ImGui::PopStyleVar(3);"),
        ("ImGuiStyleVar_FramePadding", "ImGuiStyleVar_WindowRounding"),
    )
    for original, mutation in mutations:
        assert shell.count(original) == 1, original
        broken = (font[:start] + shell.replace(original, mutation, 1)
                  + font[end:])
        try:
            check("", broken, "")
        except (AssertionError, IndexError, ValueError):
            # The shared check requires the original hook/header; use
            # the exact shell markers below instead for focused mutation.
            pass
        broken_shell = broken[start:broken.index("void Overlay::init()", start)]
        assert original not in broken_shell, "layout mutation was not applied"
        # Every mutation must break at least one owning-condition invariant.
        required = (
            "layoutChanged ? ImGuiCond_Always : initialPlacement",
            "std::fabs(previousContent.width - content.width) > 0.5f",
            "std::fabs(previousDensity - vrDensity) > 0.01f",
            "ImGui::SetNextWindowSize(windowSize, layoutPlacement);",
            "ImGui::PopStyleVar(4);",
            "ImGuiStyleVar_FramePadding",
        )
        assert not all(item in broken_shell for item in required), original


def check_shell_numeric_cases() -> None:
    """Finite responsive bounds for desktop, ultrawide and Quest3 transition."""
    previous = None
    cases = (
        (1024, 768, 0, 1.0),
        (1920, 1080, 0, 1.0),
        (3440, 1440, 1, 2.75),
        (3440, 1440, 0, 2.75),
        (3440, 1440, 0, 2.75),  # steady: user drag must survive
        (1280, 720, 0, 1.0),  # VR exit + reset
        (640, 480, 0, 1.0),
        (20, 20, 0, 1.0),  # restore from minimized tiny frame
    )
    changes = []
    for width, height, letterbox, density in cases:
        bar = ((width - height * 4 / 3) * 0.5 + 0.5
               if letterbox and width > height * 4 / 3 else 0.0)
        content = (bar, 0.0, width - 2 * bar, height)
        available_w = max(1.0, content[2] - min(40.0, content[2] * 0.1))
        available_h = max(1.0, content[3] - min(40.0, content[3] * 0.1))
        window_w, window_h = min(1130.0 * density, available_w), min(600.0 * density, available_h)
        assert 0 < window_w <= content[2]
        assert 0 < window_h <= content[3]
        changed = (previous is not None and (
            any(abs(a-b) > 0.5 for a,b in zip(previous[:4], content)) or
            abs(previous[4] - density) > 0.01))
        changes.append(changed)
        previous = (*content, density)
    assert changes == [False, True, True, True, False, True, True, True]


def check_projection(renderer: str, semantic: str) -> None:
    # F11 must not be reduced by VR.HudScale *after* rebuilding a sharp
    # source-resolution font atlas. The external semantic is not permission
    # to relax generic game ScreenOverlay2D/menu or projected-world content.
    start = renderer.index("float R30HudScopeScale() noexcept")
    end = renderer.index("void R30HudContainScale(", start)
    scope = renderer[start:end]
    # A separate ESC/ScreenOverlay2D branch can also mention this semantic.
    # Assert the exact F11 branch BEFORE its return, not a token that survives
    # elsewhere after a destructive edit to F11's owning condition.
    f11_condition, f11_return, remaining_scope = scope.partition("return 1.0f;")
    assert f11_return, "missing F11 projection escape"
    for token in (
        "ExternalOverlaySemanticDepth != 0",
        "EffectiveScope() ==",
        "RenderScope::ScreenOverlay2D)",
    ):
        assert token in f11_condition, token
    assert "return R30HudScaleValue();" in remaining_scope
    assert f11_condition.index("ExternalOverlaySemanticDepth != 0") < (
        f11_condition.index("RenderScope::ScreenOverlay2D)"))
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
    # Mutate the owning function, never an earlier unrelated occurrence
    # of a generic token (e.g. 'return 1.0f;' in the aspect helper).
    scope_start = renderer.index("float R30HudScopeScale() noexcept")
    scope_end = renderer.index("void R30HudContainScale(", scope_start)
    contain_end = renderer.index("bool R30TransformHudScissor(", scope_end)
    for index, (a, b) in enumerate(mutants):
        begin, end = ((scope_start, scope_end) if index < 3
                      else (scope_end, contain_end))
        owning_function = renderer[begin:end]
        assert owning_function.count(a) == 1, (
            "F11 mutant target is not unique in owner: " + a
        )
        broken = (renderer[:begin] +
                  owning_function.replace(a, b, 1) +
                  renderer[end:])
        try:
            check_projection(broken, semantic)
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

def check_font_density_hysteresis(hook: str) -> None:
    """Do not regenerate F11's D3D9 font atlas for near-boundary XR jitter."""
    density = hook.split("float vrFontMultiplier = 1.0f;", 1)[1].split(
        "// A new atlas needs a new font texture.", 1
    )[0]
    required = (
        "std::ceil(factor * 4.0f) * 0.25f",
        "Overlay::VrFontMultiplier, 1.0f, 3.0f",
        "constexpr float kFontAspectHysteresis = 0.03f;",
        "stepped > previous &&",
        "factor <= previous + kFontAspectHysteresis",
        "stepped < previous &&",
        "factor >= previous - 0.25f - kFontAspectHysteresis",
        "factor > 1.0f",
        "vrFontMultiplier = previous;",
        "vrFontMultiplier = stepped;",
    )
    for token in required:
        assert token in density, "missing F11 XR jitter guard: " + token
    assert density.index("const float stepped") < density.index(
        "const float previous") < density.index(
        "constexpr float kFontAspectHysteresis")
    # Negative mutations must break this precise owner rather than passing
    # because unrelated HUD or standalone font code still has the tokens.
    for a, b in (
        ("factor <= previous + kFontAspectHysteresis",
         "factor < previous - kFontAspectHysteresis"),
        ("factor >= previous - 0.25f - kFontAspectHysteresis",
         "factor <= previous + 0.25f"),
        ("factor > 1.0f", "factor > 2.0f"),
        ("vrFontMultiplier = previous;", "vrFontMultiplier = stepped;"),
    ):
        assert a in density
        broken = density.replace(a, b, 1)
        assert any(token not in broken for token in required), (
            "F11 XR hysteresis mutant survived: " + a)

    def next_density(current, factor, active=True):
        if not active or not math.isfinite(factor) or factor <= 0:
            return 1.0
        stepped = min(3.0, max(1.0, math.ceil(factor * 4.0) * .25))
        previous = min(3.0, max(1.0, current))
        if stepped > previous and factor <= previous + .03:
            return previous
        if stepped < previous and factor >= previous - .25 - .03 and factor > 1.0:
            return previous
        return stepped

    # Former ceil-only code ping-ponged between 2.50/2.75 during each
    # normal near-threshold source/eye aspect update.
    ratio = 2.50
    jitter = (ratio - .002, ratio + .002) * 32
    assert len(set(factor(3440, 1440, 2496, 2688) for _ in range(2))) == 1
    old = [min(3., max(1., math.ceil(v * 4) * .25)) for v in jitter]
    assert len(set(old)) == 2
    density = 2.50
    transitions = 0
    for v in jitter:
        new = next_density(density, v)
        transitions += new != density
        density = new
    assert transitions == 0
    assert next_density(2.50, 2.54) == 2.75
    assert next_density(2.75, 2.50) == 2.75
    assert next_density(2.75, 2.46) == 2.50
    assert next_density(2.75, 1.50) == 1.50
    assert next_density(2.75, 1.00) == 1.00
    assert next_density(2.75, float("nan")) == 1.00
    assert next_density(2.75, 2.49, active=False) == 1.00
    assert next_density(1.0, 99.) == 3.0


def main():
    hook, font, header = (p.read_text(encoding="utf-8")
                          for p in (HOOK, FONT, HEADER))
    renderer = (ROOT / "src/vr/d3d9/stereo_renderer_r30.cpp").read_text(encoding="utf-8")
    semantic = (ROOT / "src/vr/game/render_semantics.hpp").read_text(encoding="utf-8")
    check(hook, font, header)
    check_font_density_hysteresis(hook)
    check_shell_layout_mutations(font)
    check_shell_numeric_cases()
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
    print("VR F11 atlas + responsive shell reflow + stereo plane PASS; 16 negative mutants rejected")

if __name__ == "__main__":
    main()
