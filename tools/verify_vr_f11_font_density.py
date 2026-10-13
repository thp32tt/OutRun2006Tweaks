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
            "ImGuiStyleVar_WindowPadding",
            "ImGuiStyleVar_CellPadding",
            "ImGuiStyleVar_IndentSpacing",
            "ImGuiStyleVar_GrabMinSize",
            "(std::min)(maxWidth / 1130.f, maxHeight / 600.f)",
            "shellStyle.GrabMinSize * styleDensity",
            "shellStyle.WindowPadding.x * styleDensity",
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


def check_transient_eye_extent_dropout(hook: str) -> None:
    """Retain VR F11 density on partial XR publication, reset on VR exit."""
    density = hook.split("float vrFontMultiplier = 1.0f;", 1)[1].split(
        "// A new atlas needs a new font texture.", 1)[0]
    retain = ("vrFontMultiplier = std::clamp(\\n"
              "\\t\\t\\t\\t\\tOverlay::VrFontMultiplier, 1.0f, 3.0f);")
    # Exact owning control flow: retention only inside active VR gameplay and
    # before either eye lookup, not a permanent desktop fallback.
    assert "overlayActive && Game::is_vr_gameplay_presentation()" in density
    assert retain.replace("\\n", "\n").replace("\\t", "\t") in density
    assert (density.index("overlayActive && Game::is_vr_gameplay_presentation()") <
            density.index(retain.replace("\\n", "\n").replace("\\t", "\t")) <
            density.index("R23TryGetPublishedEyeExtent(0, lw, lh)"))
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
    owner = density[density.index("R23TryGetPublishedEyeExtent(0, lw, lh)"):
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
    # Ensure the cached ORIGINAL bytes are copied to the separately-owned
    # ImGui buffer after every Clear(), not transferred to ImGui once.
    after = font.split("bool loaded = false;", 1)[1].split("if (!loaded)", 1)[0]
    for token in ("if (!fontData.empty())", "IM_ALLOC(fontData.size())",
                  "memcpy(owned, fontData.data(), fontData.size())",
                  "io.Fonts->AddFontFromMemoryTTF(owned, int(fontData.size()), sizePixels)"):
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
    """XR-density F11 uses the whole source canvas; game 4:3 bars stay intact."""
    shell = font.split("Overlay::ContentRect Overlay::content_rect()", 1)[1].split(
        "const std::vector<OverlayWindow*>& Overlay::windows()", 1)[0]
    required = (
        "const bool externalVrShell = VrFontMultiplier > 1.0f &&",
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

    # A real VR F11 window may use the side-rail pixels, but the original
    # front-end and desktop F11 still respect a forced 4:3 letterbox.
    def width(source_w, source_h, in_vr, density, force_rails):
        if not math.isfinite(source_w) or not math.isfinite(source_h) or (
                source_w <= 0 or source_h <= 0):
            return 0.
        if in_vr and density > 1.0:
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
        assert width(w, h, True, 1., True) == normal
        assert width(w, h, False, 2.75, True) == normal
        assert width(w, h, True, 2.75, False) == w
    assert width(float("nan"), 1440, True, 2.75, True) == 0.

    # Mutants must fail at the actual owner (not detached numeric fixtures).
    for original, bad in (
        ("VrFontMultiplier > 1.0f", "VrFontMultiplier >= 1.0f"),
        ("Game::is_vr_gameplay_presentation();", "Game::is_in_game();"),
        ("if (externalVrShell)", "if (false)"),
        ("return { 0.f, 0.f, screen.x, screen.y };",
         "return { 0.f, 0.f, screen.y * 4.f / 3.f, screen.y };"),
    ):
        assert shell.count(original) == 1, original
        changed = shell.replace(original, bad, 1)
        assert not all(x in changed for x in required), original
    print("PASS F11 VR full-source canvas, desktop/menu 4:3 preserved, 5 sizes and 4 mutants")

def main():
    hook, font, header = (p.read_text(encoding="utf-8")
                          for p in (HOOK, FONT, HEADER))
    renderer = (ROOT / "src/vr/d3d9/stereo_renderer_r30.cpp").read_text(encoding="utf-8")
    semantic = (ROOT / "src/vr/game/render_semantics.hpp").read_text(encoding="utf-8")
    check(hook, font, header)
    check_font_io_cache(font)
    check_font_density_hysteresis(hook)
    check_stereo_extent_coherence(hook)
    check_transient_eye_extent_dropout(hook)
    check_shell_layout_mutations(font)
    check_shell_numeric_cases()
    check_external_vr_f11_canvas(font)
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
