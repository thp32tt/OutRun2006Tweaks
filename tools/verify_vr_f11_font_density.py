#!/usr/bin/env python3
"""F11 Quest3 eye-aspect raster-density regression (static + numeric/destructive)."""
from pathlib import Path
import math

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "src/overlay/hooks_overlay.cpp"
FONT = ROOT / "src/overlay/overlay.cpp"
HEADER = ROOT / "src/overlay/overlay.hpp"

def check(hook: str, font: str, header: str) -> None:
    # Pin actual owning scopes. Searching whole files misses destructive
    # mutations when a second valid-looking token remains in a separate
    # ImGui draw call or VR shell sizing path.
    font_guard = font.split("void Overlay::rebuild_fonts()", 1)[1].split(
        "// Read the file rather than handing", 1
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
            "R29OwnerRecommendedEyeExtent(0, lw, lh)",
            "R29OwnerRecommendedEyeExtent(1, rw, rh)",
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
    check(hook, font, header)
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
        (hook, "R29OwnerRecommendedEyeExtent(1, rw, rh)",
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
    print("VR F11 native font-density guard PASS; 5 negative mutants rejected")

if __name__ == "__main__":
    main()
