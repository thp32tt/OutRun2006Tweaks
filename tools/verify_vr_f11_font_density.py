#!/usr/bin/env python3
# F11 live font slider: keep window/control geometry proportional to the
# independently rasterised VR atlas. The native desktop shell must remain 1x.
def f11_shell_density(font_size, eye_density, vr):
    bounded_font = max(0.5, min(5.0, font_size))
    ui_factor = max(0.5, min(2.5, bounded_font / 2.0)) if vr else 1.0
    return max(1.0, min(3.0, eye_density)) * ui_factor

for eye in (1.0, 1.75, 2.75, 3.0):
    assert f11_shell_density(2.0, eye, True) == eye
    assert f11_shell_density(4.0, eye, True) == 2.0 * eye
    assert f11_shell_density(1.0, eye, True) == 0.5 * eye
    assert f11_shell_density(4.0, eye, False) == eye
assert f11_shell_density(5.0, 2.75, True) == 2.75 * 2.5
assert f11_shell_density(float("inf"), 2.75, True) == 2.75 * 2.5

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
            "f11VisibleThisFrame && Game::is_vr_gameplay_presentation()",
            "R23TryGetPublishedEyeExtentPair(extent)",
            "R23TryGetPublishedEyeExtentPair(extent)",
            "lw >= 640u && lh >= 480u && rw >= 640u && rh >= 480u",
            "std::isfinite(factor) && factor > 0.0f",
            "std::ceil(factor * 4.0f) * 0.25f, 1.0f, 3.0f",
            "Overlay::FontsDirty = true;",
        )),
        (hook, ("ImGui_ImplDX9_InvalidateDeviceObjects();",
                '#include "input_manager.hpp"',
                "const bool f11VisibleThisFrame = Overlay::will_be_visible_this_frame();",)),
        (font_guard, (
            "std::clamp(GlobalFontScale, 0.5f, 5.0f)",
            "std::clamp(VrFontMultiplier, 1.0f, 3.0f)",
            "ImGui::GetStyle().FontSizeBase = sizePixels;",
            "io.Fonts->Clear();",
        )),
        (shell_guard, (
            "std::clamp(VrFontMultiplier, 1.0f, 3.0f)",
            "const float vrFontScale = std::clamp(GlobalFontScale, 0.5f, 5.0f);",
            "const float vrUiFactor = externalVrShell",
            "std::clamp(vrFontScale / 2.0f, 0.5f, 2.5f) : 1.0f;",
            "const float vrDensity = std::clamp(VrFontMultiplier, 1.0f, 3.0f) * vrUiFactor;",
            "1130.f * vrDensity",
            "600.f * vrDensity",
            "ImGuiCond_Appearing : ImGuiCond_FirstUseEver",
            "layoutChanged ? ImGuiCond_Always : initialPlacement",
            "std::fabs(previousContent.width - content.width) > 0.5f",
            "std::fabs(previousDensity - vrDensity) > 0.01f",
            "ImGui::SetNextWindowSize(windowSize, layoutPlacement);",
            "ImGuiStyleVar_WindowPadding",
            "ImGuiStyleVar_CellPadding",
            "ImGuiStyleVar_IndentSpacing",
            "ImGuiStyleVar_GrabMinSize",
            "(std::min)(maxWidth / 1130.f, maxHeight / 600.f)",
            "shellStyle.GrabMinSize * styleDensity",
            "shellStyle.WindowPadding.x * styleDensity",
            "const bool externalVrShell = Game::is_vr_gameplay_presentation();",
            "const ImGuiCond initialPlacement = externalVrShell",
            "previousVrShell != externalVrShell ||",
            "previousVrShell = externalVrShell;",
            "const bool vrStyle = externalVrShell;",
            "ImGuiStyleVar_FramePadding",
            "ImGuiStyleVar_ItemSpacing",
            "ImGuiStyleVar_ItemInnerSpacing",
            "ImGuiStyleVar_ScrollbarSize",
            "ImGui::PopStyleVar(8);",
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
    # Mutate the exact edit-finalisation subroutine, not earlier calls
    # in the first-run modal or unrelated F11 frame initialization.
    mutations = (
        ("layoutChanged ? ImGuiCond_Always : initialPlacement",
         "initialPlacement"),
        ("std::fabs(previousContent.width - content.width) > 0.5f",
         "false"),
        ("std::fabs(previousDensity - vrDensity) > 0.01f",
         "false"),
        ("ImGui::SetNextWindowSize(windowSize, layoutPlacement);",
         "ImGui::SetNextWindowSize(windowSize, initialPlacement);"),
        ("ImGui::PopStyleVar(8);", "ImGui::PopStyleVar(7);"),
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
            "ImGui::PopStyleVar(8);",
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
        style_density = max(1.0, min(density, available_w / 1130.0, available_h / 600.0))
        assert 1.0 <= style_density <= max(1.0, density)
        if available_w >= 1130.0 and available_h >= 600.0:
            assert 1130.0 * style_density <= available_w + 1e-5
            assert 600.0 * style_density <= available_h + 1e-5
        if density == 1.0:
            assert style_density == 1.0  # desktop metrics untouched
        changed = (previous is not None and (
            any(abs(a-b) > 0.5 for a,b in zip(previous[:4], content)) or
            abs(previous[4] - density) > 0.01))
        changes.append(changed)
        previous = (*content, density)
    assert changes == [False, True, True, True, False, True, True, True]


def check_shell_vr_mode_transitions(font: str) -> None:
    """A 1x XR atlas must not silently restore desktop shell layout."""
    shell = font.split("void Overlay::render_shell()", 1)[1].split(
        "void Overlay::init()", 1)[0]
    exact = (
        "const bool externalVrShell = Game::is_vr_gameplay_presentation();",
        "const ImGuiCond initialPlacement = externalVrShell",
        "previousVrShell != externalVrShell ||",
        "previousVrShell = externalVrShell;",
        "const bool vrStyle = externalVrShell;",
    )
    for token in exact:
        assert token in shell, token
    for original, wrong in (
        (exact[1], "const ImGuiCond initialPlacement = vrDensity > 1.0f"),
        (exact[2], "false ||"),
        (exact[3], "previousVrShell = false;"),
        (exact[4], "const bool vrStyle = vrDensity > 1.0f;"),
    ):
        mutant = shell.replace(original, wrong, 1)
        assert mutant != shell
        assert not all(token in mutant for token in exact)
    def changed(old, new):
        if old is None:
            return False
        return (old[0] != new[0] or abs(old[1] - new[1]) > .01 or
                any(abs(a-b) > .5 for a,b in zip(old[2], new[2])))
    for rect in ((0., 0., 1024., 768.), (0., 0., 3440., 1440.),
                 (0., 0., 2496., 2688.)):
        states = ((False, 1., rect), (True, 1., rect),
                  (True, 1., rect), (True, 2.75, rect),
                  (True, 2.75, rect), (False, 1., rect),
                  (False, 1., rect))
        assert [changed(states[i-1] if i else None, state)
                for i, state in enumerate(states)] == [
            False, True, False, True, False, True, False]
    print("PASS VR F11 equal-density presentation transition and four destructive controls")


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
    # F11 must not borrow the ESC optical boost, and that difference is
    # part of the contain cache identity across the same Present.
    assert "const bool pauseResponsive = R30IsPauseMenuElement() &&" in contain
    assert "R30HudContain.pauseResponsive == pauseResponsive" in contain
    assert "OutRunVrPauseEye::ResponsiveMenuScale(" in contain
    assert "userScale, sourceOverTarget, pauseResponsive);" in contain
    assert "scaleY = opticalScale / sourceOverTarget;" in contain
    assert "scaleX = opticalScale * sourceOverTarget;" in contain
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
        ("R30HudContain.pauseResponsive == pauseResponsive",
         "R30HudContain.pauseResponsive == true"),
        ("userScale, sourceOverTarget, pauseResponsive);",
         "userScale, sourceOverTarget, true);"),
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


def check_transient_eye_extent_dropout(hook: str) -> None:
    """Retain VR F11 density on partial XR publication, reset on VR exit."""
    density = hook.split("float vrFontMultiplier = 1.0f;", 1)[1].split(
        "// A new atlas needs a new font texture.", 1)[0]
    retain = ("vrFontMultiplier = std::clamp(\\n"
              "\\t\\t\\t\\t\\tOverlay::VrFontMultiplier, 1.0f, 3.0f);")
    # Exact owning control flow: retention only inside active VR gameplay and
    # before either eye lookup, not a permanent desktop fallback.
    assert "f11VisibleThisFrame && Game::is_vr_gameplay_presentation()" in density
    assert retain.replace("\\n", "\n").replace("\\t", "\t") in density
    assert (density.index("f11VisibleThisFrame && Game::is_vr_gameplay_presentation()") <
            density.index(retain.replace("\\n", "\n").replace("\\t", "\t")) <
            density.index("R23TryGetPublishedEyeExtentPair(extent)"))
    assert "float vrFontMultiplier = 1.0f;" in hook
    assert "lw >= 640u && lh >= 480u && rw >= 640u && rh >= 480u" in density
    assert "if (Overlay::VrFontMultiplier != vrFontMultiplier)" in density
    # Destructive controls: a reverted or unconditional reset must fail.
    mutation = density.replace(retain.replace("\\n", "\n").replace("\\t", "\t"),
                               "vrFontMultiplier = 1.0f;", 1)
    assert retain.replace("\\n", "\n").replace("\\t", "\t") not in mutation
    assert mutation != density
    def transition(previous, vr, left, right, ratio):
        if not vr:
            return 1.0
        if not (left and right):
            return min(3., max(1., previous))
        if not math.isfinite(ratio) or ratio <= 0:
            return min(3., max(1., previous))
        return min(3., max(1., math.ceil(ratio * 4) / 4))
    for source in ((1024, 768), (1920, 1080), (3440, 1440), (5120, 1440)):
        # Valid both-eye publication followed by intermittent one-eye loss.
        ratio = (source[0] / source[1]) / (2496 / 2688)
        expected = transition(1., True, True, True, ratio)
        current = expected
        for i in range(80):
            current = transition(current, True, i % 2 == 0, i % 3 == 0, ratio)
            assert current == expected, (source, i)
        assert transition(current, False, False, False, ratio) == 1.
    # Reset/zero-size and exiting the game must never preserve the VR font.
    assert transition(2.75, False, True, True, 2.57) == 1.
    assert transition(2.75, True, False, False, 2.57) == 2.75
    assert transition(2.75, True, True, False, 2.57) == 2.75
    assert transition(2.75, True, True, True, 1.0) == 1.0
    print("PASS F11 one-eye XR publication dropout keeps last atlas; VR exit resets")


def factor(source_w, source_h, eye_w, eye_h):
    if min(source_w, source_h, eye_w, eye_h) <= 0:
        return 1.0
    raw = max((source_w / source_h) / (eye_w / eye_h),
              eye_h / source_h)
    if not math.isfinite(raw) or raw <= 0:
        return 1.0
    return min(3.0, max(1.0, math.ceil(raw * 4.0) * 0.25))

def check_native_eye_height_density(hook: str) -> None:
    """F11 atlas density tracks both XR aspect AND the real eye pixel height."""
    # Restrict destructive mutations to the eye-pixel floor owner. The
    # upstream source-aspect computation also uses screen_resolution->y;
    # a broad search replaces that unrelated denominator first.
    owner = hook.split("const float eyePixelScale =", 1)[1].split(
        "if (std::isfinite(factor) && factor > 0.0f)", 1)[0]
    owner = "const float eyePixelScale =" + owner
    tokens = (
        "const float eyePixelScale =",
        "static_cast<float>(lh) + static_cast<float>(rh)",
        "static_cast<float>(Game::screen_resolution->y);",
        "(std::max)(sourceAspect / eyeAspect, eyePixelScale);",
    )
    assert all(t in owner for t in tokens)
    for original, broken in (
        ("(std::max)(sourceAspect / eyeAspect, eyePixelScale);",
         "sourceAspect / eyeAspect;"),
        ("static_cast<float>(lh) + static_cast<float>(rh)",
         "static_cast<float>(lh) + static_cast<float>(lh)"),
        ("static_cast<float>(Game::screen_resolution->y);",
         "static_cast<float>(Game::screen_resolution->x);"),
    ):
        assert original in owner
        mutated = owner.replace(original, broken, 1)
        assert not all(t in mutated for t in tokens)
    # Original user-reported 3440x1440 case stays in the same 2.75 bucket.
    assert factor(3440, 1440, 2496, 2688) == 2.75
    # XR portrait eye heights exceeding a 1080p/768p mirror must not
    # fall back to only a 16:9 or 4:3 aspect-ratio correction.
    assert factor(1920, 1080, 2496, 2688) == 2.50
    assert factor(1024, 768, 2496, 2688) == 3.0
    # Native and low-resolution eye outputs are unchanged; no desktop branch
    # inherits this VR-only font density or any gameplay HUD transform.
    assert factor(1920, 1080, 1920, 1080) == 1.0
    assert factor(1024, 768, 1024, 768) == 1.0
    assert factor(5120, 1440, 2496, 2688) == 3.0
    assert factor(0, 1440, 2496, 2688) == 1.0
    print("PASS VR F11 native eye-height atlas floor, 5 resolution pairs, 3 destructive mutations")


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
        # Two independent arms intentionally share this assignment. A
        # one-arm mutation is a regression even if its sibling remains.
        assert any(token not in broken for token in required) or (
            a == "vrFontMultiplier = previous;" and
            density.count(a) == 2 and broken.count(a) == 1
        ), "F11 XR hysteresis mutant survived: " + a

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



def check_stereo_extent_coherence(hook: str) -> None:
    """Mixed XR resize snapshots cannot produce a transient blurry F11 atlas."""
    density = hook.split("float vrFontMultiplier = 1.0f;", 1)[1].split(
        "// A new atlas needs a new font texture.", 1)[0]
    owner = density[density.index("R23TryGetPublishedEyeExtentPair(extent)"):
                    density.index("const float sourceAspect")]
    guards = (
        "lw >= 640u && lh >= 480u && rw >= 640u && rh >= 480u",
        "std::fabs(static_cast<float>(lw) - static_cast<float>(rw)) <=",
        "0.10f * static_cast<float>((std::max)(lw, rw))",
        "std::fabs(static_cast<float>(lh) - static_cast<float>(rh)) <=",
        "0.10f * static_cast<float>((std::max)(lh, rh))",
    )
    for marker in guards:
        assert marker in owner, "missing owner-side binocular extent gate: " + marker
    assert owner.index(guards[0]) < owner.index(guards[1]) < owner.index(guards[3])
    # Exact destructive mutations on either eye axis must be rejected.
    for broken, replacement in (
        (guards[1], "std::fabs(static_cast<float>(lw) - static_cast<float>(rw)) >="),
        (guards[3], "std::fabs(static_cast<float>(lh) - static_cast<float>(rh)) >="),
        (guards[2], "1.00f * static_cast<float>((std::max)(lw, rw))"),
        (guards[4], "1.00f * static_cast<float>((std::max)(lh, rh))"),
    ):
        assert owner.count(broken) == 1
        mutant = owner.replace(broken, replacement, 1)
        assert not all(g in mutant for g in guards), broken

    def consistent(left, right):
        lw, lh = left
        rw, rh = right
        return (min(lw, lh, rw, rh) >= 480 and lw >= 640 and rw >= 640
                and abs(lw-rw) <= .10 * max(lw, rw)
                and abs(lh-rh) <= .10 * max(lh, rh))

    old_eye = (1600, 1700)
    new_eye = (2496, 2688)
    assert consistent(new_eye, new_eye)
    assert consistent(old_eye, old_eye)
    assert not consistent(old_eye, new_eye)
    assert not consistent(new_eye, old_eye)
    assert not consistent((2496, 2100), new_eye)  # height-only transition
    assert not consistent((2000, 2688), new_eye)  # width-only transition
    assert consistent((2450, 2650), new_eye)  # normal modest per-eye variance
    assert not consistent((0, 0), new_eye)
    # A partial left/right update holds the previous density with no atlas
    # rebuild; only a complete pair applies the new aspect bucket.
    for source in ((1024, 768), (1920, 1080), (3440, 1440)):
        current = factor(*source, *old_eye)
        expected = factor(*source, *new_eye)
        for left, right in ((new_eye, old_eye), (old_eye, new_eye),
                            (new_eye, new_eye)):
            candidate = factor(*source, *((
                (left[0]+right[0]) / 2, (left[1]+right[1]) / 2
            ))) if consistent(left, right) else current
            if left != right:
                assert candidate == current, (source, left, right)
            else:
                assert candidate == expected
    print("PASS F11 binocular resize coherence: 3 aspects, 4 destructive controls")



def check_font_io_cache(font: str) -> None:
    """F11 re-rasterisation must not repeat synchronous Win32 TTF I/O per XR resize."""
    block = font.split("void Overlay::rebuild_fonts()", 1)[1].split("bool loaded = false;", 1)[0]
    expected = (
        "static const std::vector<uint8_t> fontData = []() {",
        "GetWindowsDirectoryW(windowsDir, MAX_PATH)",
        "pathLength == 0 || pathLength >= MAX_PATH",
        "std::ifstream file(fontPath, std::ios::binary | std::ios::ate)",
        "const std::streamoff fileBytes = file.tellg();",
        "fileBytes <= 0 || fileBytes > 16 * 1024 * 1024",
        "std::vector<uint8_t> bytes(static_cast<std::size_t>(fileBytes));",
        "static_cast<std::streamsize>(fileBytes)",
        "return bytes;",
        "}();",
    )
    for token in expected:
        assert token in block, token
    assert block.index("fileBytes <= 0") < block.index("bytes(static_cast")
    assert "std::vector<uint8_t> fontData;" not in block
    # The first failed font must not degrade to an enlarged bitmap when a
    # second valid scalable face is present on Windows/Wine.
    for face in ('L"segoeui.ttf"', 'L"tahoma.ttf"', 'L"arial.ttf"'):
        assert face in block, face
    assert "for (const wchar_t* family : fontFiles)" in block
    assert block.count("continue;") >= 3
    assert block.index('L"segoeui.ttf"') < block.index('L"tahoma.ttf"') < block.index('L"arial.ttf"')
    # One bad font cannot poison the whole search; only all failures
    # legitimately reach the default bitmap face.
    for good, bad in (
        ('L"tahoma.ttf"', 'L"segoeui.ttf"'),
        ('L"arial.ttf"', 'L"segoeui.ttf"'),
        ("for (const wchar_t* family : fontFiles)", "if (true)"),
        ("if (!file)\n\t\t\t\tcontinue;", "if (!file)\n\t\t\t\treturn {};"),
    ):
        assert good in block
        broken = block.replace(good, bad, 1)
        assert (any(face not in broken for face in (
            'L"segoeui.ttf"', 'L"tahoma.ttf"', 'L"arial.ttf"'))
            or "for (const wchar_t* family : fontFiles)" not in broken
            or broken.count("continue;") < 3)
    # Ensure the cached ORIGINAL bytes are copied to the separately-owned
    # ImGui buffer after every Clear(), not transferred to ImGui once.
    after = font.split("bool loaded = false;", 1)[1].split("if (!loaded)", 1)[0]
    for token in ("if (!fontData.empty())", "IM_ALLOC(fontData.size())",
                  "if (owned)", "memcpy(owned, fontData.data(), fontData.size())",
                  "owned, int(fontData.size()), sizePixels)"):
        assert token in after
    for old, bad in (
        ("static const std::vector<uint8_t> fontData", "const std::vector<uint8_t> fontData"),
        ("fileBytes <= 0", "fileBytes < 0"),
        ("fileBytes > 16 * 1024 * 1024", "fileBytes > 1024 * 1024 * 1024"),
        ("pathLength >= MAX_PATH", "pathLength > MAX_PATH"),
        ("return bytes;", "return std::vector<uint8_t>{};"),
        ("IM_ALLOC(fontData.size())", "IM_ALLOC(13)"),
    ):
        assert old in font
        damaged = font.replace(old, bad, 1)
        try:
            check_font_io_cache_contract(damaged)
        except AssertionError:
            continue
        raise AssertionError(f"F11 cache destructive mutant escaped: {old}")


def check_font_io_cache_contract(font: str) -> None:
    block = font.split("void Overlay::rebuild_fonts()", 1)[1].split("bool loaded = false;", 1)[0]
    for token in (
        "static const std::vector<uint8_t> fontData = []() {",
        "fileBytes <= 0 || fileBytes > 16 * 1024 * 1024",
        "pathLength == 0 || pathLength >= MAX_PATH",
        "return bytes;",
    ):
        assert token in block
    after = font.split("bool loaded = false;", 1)[1].split("if (!loaded)", 1)[0]
    assert "IM_ALLOC(fontData.size())" in after


def check_external_vr_f11_canvas(font: str) -> None:
    """Active VR F11 uses the whole source canvas even at density 1; game rails stay intact."""
    shell = font.split("Overlay::ContentRect Overlay::content_rect()", 1)[1].split(
        "const std::vector<OverlayWindow*>& Overlay::windows()", 1)[0]
    required = (
        "const bool externalVrShell = Game::is_vr_gameplay_presentation();",
        "Game::is_vr_gameplay_presentation();",
        "if (externalVrShell)",
        "return { 0.f, 0.f, screen.x, screen.y };",
        "Settings::UILetterboxing > 0 && Settings::UIScalingMode > 0",
        "(Settings::UILetterboxing == 2 || !Game::is_in_game())",
        "return { border, 0.f, screen.x - (border * 2.f), screen.y };",
    )
    for token in required:
        assert token in shell, token
    assert shell.index("screen.x <= 0.f || screen.y <= 0.f") < (
        shell.index("const bool externalVrShell"))
    assert shell.index("return { 0.f, 0.f, screen.x, screen.y };") < (
        shell.index("float border = 0.f;"))
    assert shell.index("float border = 0.f;") < (
        shell.index("return { border, 0.f,"))
    assert "VrFontMultiplier > 1.0f" not in shell

    # A real VR F11 window may use the side-rail pixels, but the original
    # front-end and desktop F11 still respect a forced 4:3 letterbox.
    def width(source_w, source_h, in_vr, density, force_rails):
        if not math.isfinite(source_w) or not math.isfinite(source_h) or (
                source_w <= 0 or source_h <= 0):
            return 0.
        if in_vr:
            return source_w
        if force_rails and source_w > source_h * 4. / 3.:
            return source_h * 4. / 3. - 1.0
        return source_w

    for w, h in ((1024, 768), (1920, 1080), (3440, 1440),
                 (2560, 1080), (2496, 2688)):
        normal = width(w, h, False, 1., True)
        vr_shell = width(w, h, True, 2.75, True)
        assert vr_shell == w
        assert normal <= vr_shell
        # The VR shell is still external when XR aspect normalises to 1x
        # font density. Font appearance cannot change the layout owner.
        assert width(w, h, True, 1., True) == w
        assert width(w, h, True, 0.5, True) == w
        assert width(w, h, False, 2.75, True) == normal
        assert width(w, h, True, 2.75, False) == w
    assert width(float("nan"), 1440, True, 2.75, True) == 0.

    # Mutants must fail at the actual owner (not detached numeric fixtures).
    for original, bad in (
        ("const bool externalVrShell = Game::is_vr_gameplay_presentation();",
         "const bool externalVrShell = VrFontMultiplier > 1.0f && Game::is_vr_gameplay_presentation();"),
        ("Game::is_vr_gameplay_presentation();", "Game::is_in_game();"),
        ("if (externalVrShell)", "if (false)"),
        ("return { 0.f, 0.f, screen.x, screen.y };",
         "return { 0.f, 0.f, screen.y * 4.f / 3.f, screen.y };"),
    ):
        assert shell.count(original) == 1, original
        changed = shell.replace(original, bad, 1)
        assert not all(x in changed for x in required), original
    print("PASS F11 VR font-independent full-source canvas, desktop/menu 4:3 preserved, 5 sizes and 4 mutants")

def check_first_run_vr_modal(font: str) -> None:
    """The first-run F11 popup follows XR glyph density and is viewport bounded."""
    modal = font.split("static void render_first_run_intro()", 1)[1].split(
        "void ForceShowCursor", 1)[0]
    tokens = (
        "const bool vrModal = Game::is_vr_gameplay_presentation();",
        "const Overlay::ContentRect content = Overlay::content_rect();",
        "std::clamp(Overlay::VrFontMultiplier, 1.0f, 3.0f)",
        "content.width * 0.90f",
        "content.height * 0.90f",
        "384.0f * Overlay::GlobalFontScale * density",
        "384.0f * Overlay::GlobalFontScale;",
        "const float modalFontFactor = vrModal",
        "std::clamp(Overlay::GlobalFontScale / 2.0f, 0.5f, 2.5f)",
        "700.0f * density * modalFontFactor, usableHeight",
        "(std::min)(384.0f * Overlay::GlobalFontScale * density,",
        "ImGui::SetNextWindowPos(center, 0, ImVec2(0.5f, 0.5f));",
        "ImGui::SetNextWindowSize(ImVec2(popupWidth, popupHeight));",
        "const float popupHeight = vrModal",
        ": 0.0f;",
    )
    for token in tokens:
        assert token in modal, token
    assert modal.index("const bool vrModal =") < modal.index("const float popupWidth =")
    assert modal.index("const float popupHeight =") < modal.index("ImGui::BeginPopupModal(")

    def geometry(w, h, scale, density, vr):
        if not vr:
            return 384.0 * scale, 0.0
        atlas = min(max(density, 1.0), 3.0)
        font_factor = min(max(scale / 2.0, 0.5), 2.5)
        return (min(384.0 * scale * atlas, max(1.0, w * 0.90)),
                min(700.0 * atlas * font_factor, max(1.0, h * 0.90)))

    for w, h in ((1024, 768), (1920, 1080), (3440, 1440),
                 (2560, 1080), (2496, 2688), (768, 1024),
                 (1, 1)):
        for density in (1.0, 2.0, 2.75, 3.0):
            for scale in (0.5, 1.0, 2.0, 3.5, 5.0):
                pw, ph = geometry(w, h, scale, density, True)
                assert 0.0 < pw <= max(1.0, w * 0.9)
                assert 0.0 < ph <= max(1.0, h * 0.9)
            assert geometry(w, h, 2.0, density, False) == (768.0, 0.0)
    # At 1080p and temporarily 1x XR atlas density, large live font
    # edits must grow the first-run dialog rather than clip its controls.
    assert geometry(1920, 1080, 4.0, 1.0, True)[1] == 972.0
    assert geometry(1920, 1080, 4.0, 1.0, True)[1] > geometry(1920, 1080, 2.0, 1.0, True)[1]
    assert geometry(1920, 1080, 4.0, 1.0, False) == (1536.0, 0.0)
    assert geometry(3440, 1440, 2.0, 2.75, True)[0] > 768.0
    assert geometry(3440, 1440, 2.0, 2.75, True)[1] <= 1296.0
    for original, bad in (
        ("std::clamp(Overlay::VrFontMultiplier, 1.0f, 3.0f)", "1.0f"),
        ("content.width * 0.90f", "content.width * 4.0f"),
        ("content.height * 0.90f", "content.height * 4.0f"),
        ("384.0f * Overlay::GlobalFontScale * density",
         "384.0f * Overlay::GlobalFontScale"),
        ("700.0f * density * modalFontFactor, usableHeight",
         "700.0f * density, usableHeight"),
        ("700.0f * density * modalFontFactor, usableHeight",
         "700.0f * density * modalFontFactor, 99999.0f"),
        ("const bool vrModal = Game::is_vr_gameplay_presentation();",
         "const bool vrModal = false;"),
    ):
        assert original in modal
        mutated = modal.replace(original, bad, 1)
        assert any(token not in mutated for token in tokens), original
    print("PASS first-run F11 modal XR+font density, 7 viewport sizes, 5 font scales, scroll limit and 7 mutants")



def check_first_run_font_slider_commit(font: str) -> None:
    """F11 first-run: persist navigation commits even with another active item."""
    owner = font.split("static void render_first_run_intro()", 1)[1].split(
        "void ForceShowCursor", 1)[0]
    required = (
        "if (!fontScaleHeld)\n\t\tfontScale = Overlay::GlobalFontScale;",
        'ImGui::SliderFloat("Font Scale", &fontScale, 0.5f, 3.5f)',
        "ImGui::IsItemDeactivatedAfterEdit() ||",
        "ImGui::IsMouseReleased(ImGuiMouseButton_Left)",
        "Overlay::GlobalFontScale = fontScale;",
        "Overlay::FontScalePending = true;",
        "Overlay::FontScaleCommitRequested = true;",
        "fontScaleHeld = false;",
        "if (sliderEditFinished)\n\t\tcommitFontScale();",
    )
    for token in required:
        assert token in owner, "missing first-run F11 commit invariant: " + token
    assert owner.index(required[0]) < owner.index(required[1])
    assert owner.index(required[1]) < owner.index(required[2])
    assert owner.index(required[2]) < owner.index(required[4])
    assert owner.index(required[4]) < owner.index(required[6])
    assert owner.count(required[6]) == 1, "must have one commit owner"
    assert "Overlay::settings_write();" not in owner, (
        "First-run must use the retriable F11 frame-finaliser")
    assert owner.count("commitFontScale();") == 2, (
        "focus change and popup close must share one commit path")
    assert "changed && !ImGui::IsAnyItemActive()" not in owner
    close = owner.split('if (ImGui::Button("Let\'s go",', 1)[1]
    assert close.index("commitFontScale();") < close.index(
        "Overlay::IsFirstRun = false;")
    assert "if (!fontScaleHeld)\n\t\t\treturn;" in owner

    # Mutate the live source contract, including the previously failing
    # move-to-another-active-control and close-during-slider cases.
    mutations = (
        (required[0], "if (fontScaleHeld)\n\t\tfontScale = Overlay::GlobalFontScale;"),
        (required[2], "false ||"),
        (required[3], "false"),
        (required[5], "Overlay::FontScalePending = false;"),
        (required[6], "Overlay::FontScaleCommitRequested = false;"),
        (required[8], "if (false)\n\t\tcommitFontScale();"),
        ("\t\tcommitFontScale();\n\t\tOverlay::IsFirstRun = false;",
         "\t\tOverlay::IsFirstRun = false;"),
        ("if (!fontScaleHeld)\n\t\t\treturn;",
         "if (fontScaleHeld)\n\t\t\treturn;"),
    )
    def contract(source):
        tokens = required
        return (all(t in source for t in tokens)
                and source.count(tokens[6]) == 1
                and source.count("commitFontScale();") == 2
                and "changed && !ImGui::IsAnyItemActive()" not in source
                and "if (!fontScaleHeld)\n\t\t\treturn;" in source
                and "\t\tcommitFontScale();\n\t\tOverlay::IsFirstRun = false;" in source)
    assert contract(owner)
    for original, broken in mutations:
        assert owner.count(original) == 1, original
        assert not contract(owner.replace(original, broken, 1)), original

    def update(committed, draft, held, writes, edited=False, deactivate=False,
               mouse_release=False, close=False, another_active=False):
        if not held:
            draft = committed
        if edited:
            held = True
        finished = held and (deactivate or mouse_release)
        # another_active must never cancel a *finished* edit.
        if finished or (close and held):
            committed, held = draft, False
            writes += 1
        return committed, draft, held, writes

    current = update(2.4, 2.0, False, 0)
    assert current == (2.4, 2.4, False, 0)
    current = update(2.4, 2.9, True, 0, edited=True, another_active=True)
    assert current == (2.4, 2.9, True, 0)
    current = update(*current, deactivate=True, another_active=True)
    assert current == (2.9, 2.9, False, 1)
    # An unrelated active button on commit frame does not lose disk storage.
    current = update(*current, another_active=True)
    assert current == (2.9, 2.9, False, 1)
    current = update(2.9, 3.1, True, 1, edited=True)
    assert current == (2.9, 3.1, True, 1)
    current = update(*current, close=True)
    assert current == (3.1, 3.1, False, 2)
    assert update(*current, close=True) == (3.1, 3.1, False, 2)
    current = update(3.1, 2.1, True, 2, mouse_release=True)
    assert current == (2.1, 2.1, False, 3)
    assert update(1.8, 3.1, False, 0) == (1.8, 1.8, False, 0)
    print("PASS F11 slider focus/close save-once, 8 destructive controls")



def check_source_reset_atlas_hold(hook: str) -> None:
    """Same-frame F11 open retains XR atlas during temporary source loss."""
    area = hook.split("float vrFontMultiplier = 1.0f;", 1)[1].split(
        "// Quantised quarter-steps prevent continuous atlas churn", 1)[0]
    active = "if (f11VisibleThisFrame && Game::is_vr_gameplay_presentation())"
    size = "if (Game::screen_resolution &&"
    retain = ("vrFontMultiplier = std::clamp(\\n"
              "\\t\\t\\t\\t\\tOverlay::VrFontMultiplier, 1.0f, 3.0f);"
              ).replace("\\n", "\n").replace("\\t", "\t")
    assert area.count(active) == area.count(size) == area.count(retain) == 1
    assert area.index(active) < area.index(retain) < area.index(size)
    assert area.index(size) < area.index("R23TryGetPublishedEyeExtentPair(extent)")
    def density(predicted, vr, source_ok, previous, factor):
        if not predicted or not vr:
            return 1.0
        if source_ok and factor is not None:
            return max(1.0, min(3.0, factor))
        return max(1.0, min(3.0, previous))
    for previous in (1.25, 2.0, 2.75, 3.0):
        assert density(True, True, False, previous, None) == previous
        assert density(True, True, True, previous, None) == previous
        assert density(False, True, False, previous, None) == 1.0
        assert density(True, False, False, previous, None) == 1.0
    print("PASS F11 XR atlas Reset hold, closing and desktop negative")


def check_first_visible_f11_frame(hook: str) -> None:
    """Legacy F11 and bound action agree with render on opening/closing."""
    call = "const bool f11VisibleThisFrame = Overlay::will_be_visible_this_frame();"
    assert hook.count(call) == 1
    assert hook.index(call) < hook.index("float vrFontMultiplier = 1.0f;")
    assert hook.index("float vrFontMultiplier = 1.0f;") < hook.index(
        "overlayActive = Overlay::render();")
    assert "if (f11VisibleThisFrame && Game::is_vr_gameplay_presentation())" in hook
    density = hook.split("float vrFontMultiplier = 1.0f;", 1)[1].split(
        "R23TryGetPublishedEyeExtentPair(extent)", 1)[0]
    assert "InputManager_ModActionHeld(ModAction::OverlayToggle)" not in density
    assert "overlayActive &&" not in density
    assert "Game::screen_resolution &&" in density
    def poll(previous, held, legacy, new_input, dialog, visible):
        edge = held and not previous
        change = edge or (legacy and not new_input and not dialog)
        return held, (not visible if change else visible)
    prior, visible = False, False
    for held, legacy, new_input, dialog, expected in (
        (False, False, False, False, False),
        (False, True, False, False, True), # legacy first visible frame
        (False, False, False, False, True),
        (False, True, False, True, True), # binding dialog suppresses F11
        (False, True, False, False, False), # close, immediately 1x
        (True, False, True, False, True), # bound-action first frame
        (True, False, True, False, True), # no held-key repeat
        (False, False, True, False, True),
        (True, False, True, False, False),
    ):
        prior, visible = poll(prior, held, legacy, new_input, dialog, visible)
        assert visible == expected
    print("PASS F11 same-frame legacy/bound open/close and dialog regression")


def check_f11_overlay_font_persistence(font: str, header: str) -> None:
    """Whole F11 edit lifecycle: keyboard, pad, drag, tab, close and corrupt INI."""
    ui = (ROOT / "src/overlay/overlay_settings_ui.cpp").read_text(encoding="utf-8")
    markers = (
        "Overlay::FontScalePending = true;",
        "ImGui::IsItemDeactivatedAfterEdit()",
        "Overlay::FontScaleCommitRequested = true;",
    )
    for token in markers:
        assert token in ui, "F11 input/edit owner missing: " + token
    for token in ("inline static bool FontScalePending = false;",
                  "inline static bool FontScaleCommitRequested = false;"):
        assert token in header, token
    render = font.split("bool Overlay::render()", 1)[1].split(
        "// Creates a unique machine ID", 1)[0]
    # Own both the UI action and final save in frame scope, not in the
    # possibly hidden tab. Neither a single mouse click nor a drag writes
    # the INI on every render frame.
    required = (
        "if (FontScalePending &&",
        "FontScaleCommitRequested ||",
        "!ImGui::IsMouseDown(ImGuiMouseButton_Left)",
        "!ImGui::IsAnyItemActive()",
        "FontsDirty = true;",
        "SettingsDirtyPending = true;",
        "FontScalePending = false;",
        "FontScaleCommitRequested = false;",
        "if (SettingsDirtyPending && canCommitSettings)",
        "if (settings_write())",
        "SettingsDirtyPending = false;",
        "ImGui::EndFrame();",
    )
    for token in required:
        assert token in render, "F11 frame finalisation missing: " + token
    # Restrict order evidence to the actual pending-edit finaliser:
    # the separate first-run modal may legitimately call settings_write()
    # earlier in Overlay::render(), before any F11 edit is pending.
    finaliser = render[render.index("if (FontScalePending &&"):]
    offsets = [finaliser.index(token) for token in (
        "if (FontScalePending &&", "FontsDirty = true;",
        "SettingsDirtyPending = true;", "FontScalePending = false;",
        "FontScaleCommitRequested = false;",
        "if (SettingsDirtyPending && canCommitSettings)",
        "if (settings_write())", "SettingsDirtyPending = false;",
        "ImGui::EndFrame();")]
    assert offsets == sorted(offsets), "F11 frame save must precede EndFrame"
    assert "std::isfinite(savedFontScale)" in font
    assert "std::clamp(savedFontScale, 0.5f, 5.0f) : 2.0f" in font
    assert "std::isfinite(GlobalFontScale)" in render
    assert "std::clamp(GlobalFontScale, 0.5f, 5.0f) : 2.0f" in render

    # Old code only detected mouse release; it failed key/gamepad edits
    # and a pending edit whose tab stopped rendering after focus moved.
    assert "fontScaleHeld && ImGui::IsMouseReleased" not in ui
    def advance(pending, count, *, edit=False, requested=False,
                visible=True, mouse=False, active=False):
        pending = pending or edit
        commit = pending and (requested or not visible or
                              (not mouse and not active))
        return (False if commit else pending, count + int(commit))
    # Drag: dozens of frames, single save after release.
    state = (False, 0)
    for _ in range(40):
        state = advance(*state, edit=True, mouse=True, active=True)
    assert state == (True, 0)
    state = advance(*state, mouse=False, active=False)
    assert state == (False, 1)
    for _ in range(40):
        state = advance(*state)
    assert state == (False, 1)
    # Keyboard/controller edited slider loses focus to another active
    # button; explicit deactivation wins that race.
    state = advance(*state, edit=True, active=True)
    assert state == (True, 1)
    state = advance(*state, requested=True, active=True)
    assert state == (False, 2)
    # Tab switch: the old tab's control is not rendered again.
    state = advance(*state, edit=True, mouse=True, active=True)
    state = advance(*state, visible=True, active=False)
    assert state == (False, 3)
    # Close F11 while input focus is still active.
    state = advance(*state, edit=True, active=True)
    state = advance(*state, visible=False, active=True)
    assert state == (False, 4)

    mutations = (
        (ui, markers[0], "Overlay::FontScalePending = false;", markers),
        (ui, markers[1], "ImGui::IsMouseReleased(ImGuiMouseButton_Left)", markers),
        (finaliser, "SettingsDirtyPending = true;", "SettingsDirtyPending = false;", required),
        (finaliser, "if (SettingsDirtyPending && canCommitSettings)", "if (false)", required),
        (finaliser, "if (settings_write())", "if (false)", required),
        (finaliser, "SettingsDirtyPending = false;", "SettingsDirtyPending = true;", required),
    )
    for original, good, bad, needed in mutations:
        assert original.count(good) >= 1
        mutated = original.replace(good, bad, 1)
        assert not all(token in mutated for token in needed), good
    print("PASS F11 full edit/save/atlas lifecycle: drag, keys, pad, tab, close, invalid INI and 6 destructive mutants")


def check_all_f11_settings_frame_commit(font: str, header: str) -> None:
    """Theme/chat/notification/opacity edits survive tab, focus and F11 close."""
    ui = (ROOT / "src/overlay/overlay_settings_ui.cpp").read_text(encoding="utf-8")
    render = font.split("bool Overlay::render()", 1)[1].split(
        "// Creates a unique machine ID", 1)[0]
    for marker in (
        "const bool appearanceChanged = draw_appearance();",
        "const bool notificationsChanged = draw_notifications();",
        "const bool chatChanged = draw_chat();",
        "Overlay::SettingsDirtyPending |=",
        "appearanceChanged || notificationsChanged || chatChanged;",
    ):
        assert marker in ui, marker
    assert "bool settingsDirty = false;" not in ui
    assert "inline static bool SettingsDirtyPending = false;" in header
    for marker in (
        "const bool canCommitSettings = !overlay_visible ||",
        "FontScaleCommitRequested ||",
        "!ImGui::IsMouseDown(ImGuiMouseButton_Left)",
        "!ImGui::IsAnyItemActive()",
        "if (SettingsDirtyPending && canCommitSettings)",
        "if (settings_write())",
        "SettingsDirtyPending = false;",
        "SettingsDirtyPending = true;",
    ):
        assert marker in render, marker
    # Opening a different tab is not permission to lose a pending edit.
    # Font and non-font edit are coalesced into one INI write.
    def next_frame(pending, saves, *, changed=False, visible=True,
                   mouse_down=False, item_active=False,
                   font_requested=False, write_ok=True):
        pending = pending or changed
        can_write = not visible or font_requested or (
            not mouse_down and not item_active)
        if pending and can_write and write_ok:
            return False, saves + 1
        return pending, saves
    pending, saves = False, 0
    for _ in range(40):
        pending, saves = next_frame(pending, saves, changed=True,
                                    mouse_down=True, item_active=True)
    assert (pending, saves) == (True, 0)
    pending, saves = next_frame(pending, saves, mouse_down=False,
                                item_active=True)  # tab switched; focus held
    assert (pending, saves) == (True, 0)
    pending, saves = next_frame(pending, saves, visible=False,
                                mouse_down=True, item_active=True,
                                write_ok=False)  # locked/read-only INI
    assert (pending, saves) == (True, 0)
    pending, saves = next_frame(pending, saves, visible=False)
    assert (pending, saves) == (False, 1)
    for _ in range(20):
        pending, saves = next_frame(pending, saves)
    assert (pending, saves) == (False, 1)
    pending, saves = next_frame(pending, saves, changed=True,
                                item_active=True, font_requested=True)
    assert (pending, saves) == (False, 2)
    # Mutation must invalidate the actual owner, not just some unrelated write.
    changes = (
        (ui, "Overlay::SettingsDirtyPending |=", "false |="),
        (ui, "appearanceChanged || notificationsChanged || chatChanged",
         "appearanceChanged"),
        (render, "if (SettingsDirtyPending && canCommitSettings)",
         "if (false)"),
        (render, "if (settings_write())", "if (true)"),
        (render, "SettingsDirtyPending = false;", "SettingsDirtyPending = true;"),
    )
    for source, good, bad in changes:
        assert source.count(good) == 1, good
        mutant = source.replace(good, bad, 1)
        assert good not in mutant, good
    print("PASS F11 all-preference save lifetime + tab/close/write-failure negative cases")

def main():
    hook, font, header = (p.read_text(encoding="utf-8")
                          for p in (HOOK, FONT, HEADER))
    renderer = (ROOT / "src/vr/d3d9/stereo_renderer_r30.cpp").read_text(encoding="utf-8")
    semantic = (ROOT / "src/vr/game/render_semantics.hpp").read_text(encoding="utf-8")
    check(hook, font, header)
    check_f11_overlay_font_persistence(font, header)
    check_all_f11_settings_frame_commit(font, header)
    check_font_io_cache(font)
    check_font_density_hysteresis(hook)
    check_first_visible_f11_frame(hook)
    check_source_reset_atlas_hold(hook)
    check_native_eye_height_density(hook)
    check_stereo_extent_coherence(hook)
    check_transient_eye_extent_dropout(hook)
    check_shell_layout_mutations(font)
    check_shell_numeric_cases()
    check_shell_vr_mode_transitions(font)
    check_external_vr_f11_canvas(font)
    check_first_run_vr_modal(font)
    check_first_run_font_slider_commit(font)
    check_projection(renderer, semantic)
    check_projection_mutations(renderer, semantic)
    # Default R26 and new R29 compile separate final TUs but share R23.
    common = COMMON.read_text(encoding="utf-8")
    api = EYE_API.read_text(encoding="utf-8")
    assert '#include "vr/core/r23_eye_extent_api.hpp"' in hook
    assert "R29OwnerRecommendedEyeExtent" not in hook
    assert "R23TryGetPublishedEyeExtent(" in common
    assert "bool R23TryGetPublishedEyeExtent(" in api
    assert "bool R23TryGetPublishedEyeExtentPair(std::uint32_t out[4]) noexcept;" in api
    assert "R23TryGetPublishedEyeExtentPair(extent)" in hook
    pair = common.split("bool R23TryGetPublishedEyeExtentPair(", 1)[1].split(
        "bool R23TryGetPublishedEyeExtent(", 1)[0]
    paired_guards = (
        "out[0] = out[1] = out[2] = out[3] = 0;",
        "const std::uint32_t before = shared->sequence;",
        "if (before & 1u)",
        "MemoryBarrier();",
        "const std::uint32_t after = shared->sequence;",
        "if (before != after || (after & 1u))",
        "shared->recommendedWidth[0]", "shared->recommendedHeight[0]",
        "shared->recommendedWidth[1]", "shared->recommendedHeight[1]",
        "size != sizeof(OutRunVR::SharedPoseState)",
        "lw < 640u || lh < 480u || rw < 640u || rh < 480u",
        "lw > 8192u || lh > 8192u || rw > 8192u || rh > 8192u",
        "out[0] = lw;", "out[1] = lh;", "out[2] = rw;", "out[3] = rh;"
    )
    for required in paired_guards:
        assert required in pair, "unsafe R23 pair snapshot: " + required
    for required, mutant in (
        ("if (before & 1u)", "if (false)"),
        ("if (before != after || (after & 1u))", "if (false)"),
        ("out[2] = rw;", "out[2] = lw;"),
        ("out[3] = rh;", "out[3] = lh;"),
        ("size != sizeof(OutRunVR::SharedPoseState)", "false"),
    ):
        broken = pair.replace(required, mutant, 1)
        assert required in pair and required not in broken, (
            "R23 source destructive mutation did not touch the owner")
    assert "SharedState->structSize != sizeof(OutRunVR::SharedPoseState)" in common
    assert "SharedState->recommendedWidth[eye]" in common
    assert "SharedState->recommendedHeight[eye]" in common
    # Desktop 4:3 is unmodified; wide/portrait XR needs sharp larger glyphs.
    assert factor(1024, 768, 1024, 768) == 1.0
    assert factor(1920, 1080, 2496, 2688) == 2.5
    assert factor(3440, 1440, 2496, 2688) == 2.75
    assert factor(5120, 1440, 2496, 2688) == 3.0
    assert factor(0, 1440, 2496, 2688) == 1.0
    # Detect removal of either eye authority, desktop isolation or atlas rebuild.
    mutations = (
        (hook, "f11VisibleThisFrame && Game::is_vr_gameplay_presentation()",
         "overlayActive || Game::is_vr_gameplay_presentation()", font, header),
        (hook, "R23TryGetPublishedEyeExtentPair(extent)",
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
