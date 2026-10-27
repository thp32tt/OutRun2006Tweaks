#!/usr/bin/env python3
"""Review 01490: host menu optical cache must include accepted crop policy.

Static source regression with destructive mutants and conditional truth cases;
not an OpenXR/Quest3 runtime or 120-fps performance measurement.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "vrhost/src/main_r23.cpp"
source = SOURCE.read_text(encoding="utf-8-sig")


def verify(text: str) -> None:
    assert "float cachedMenuScale = -1.0f;" in text
    assert "bool cachedMenuLetterbox = false;" in text
    menu = text.split(
        "const std::uint32_t clientGameState = shared.GameState();", 1
    )[1].split("if (cachedMenuProjectionValid)\n", 1)[0]
    required = (
        "const bool currentMenuLetterbox =",
        "R23GameMenuIsLetterboxed(compositor.hwnd_);",
        "cachedMenuGameState != clientGameState ||",
        "cachedMenuScale != R23ConfiguredMenuScale",
        "cachedMenuProjectionValid = false;",
        "const bool letterboxPolicyChanged =",
        "cachedMenuProjectionValid &&",
        "cachedMenuLetterbox != currentMenuLetterbox;",
        "if (capture.available &&",
        "menuProjectionAnchorValid &&",
        "(!cachedMenuProjectionValid || capture.fresh ||",
        "letterboxPolicyChanged))",
        "if (R23RenderWorldLockedMenuProjection(",
        "cachedMenuProjectionViews = refreshed;",
        "cachedMenuLetterbox = currentMenuLetterbox;",
        "cachedMenuProjectionValid = true;",
    )
    for requirement in required:
        assert requirement in menu, "missing cache key: " + requirement
    assert menu.index("R23GameMenuIsLetterboxed(") < menu.index(
        "const bool letterboxPolicyChanged =") < menu.index(
        "if (capture.available &&") < menu.index(
        "cachedMenuLetterbox = currentMenuLetterbox;")
    # Do not invalidate a successful old pair on policy change if the next
    # desktop source/anchor is unavailable: retry on later available capture.
    policy = menu.split("const bool letterboxPolicyChanged =", 1)[1].split(
        "if (capture.available &&", 1)[0]
    assert "cachedMenuProjectionValid = false;" not in policy
    refresh = menu.split("if (R23RenderWorldLockedMenuProjection(", 1)[1]
    assert refresh.index("cachedMenuProjectionViews = refreshed;") < refresh.index(
        "cachedMenuLetterbox = currentMenuLetterbox;") < refresh.index(
        "cachedMenuProjectionValid = true;")
    config = text.split("bool R23GameMenuIsLetterboxed(", 1)[1].split(
        "constexpr ULONGLONG R23PixelIntervalMs", 1)[0]
    assert "if (!foundConfig)\n            return cachedLetterbox;" in config
    assert "const bool sameOwner =" in config
    assert "cachedLetterbox = OutRunVrMenuAspect::ShouldCropConfiguredMenu(" in config


verify(source)


def needs_redraw(available: bool, anchored: bool, valid: bool,
                 fresh: bool, old_crop: bool, accepted_crop: bool) -> bool:
    return available and anchored and (
        not valid or fresh or (valid and old_crop != accepted_crop))


fixtures = (
    (True, True, True, False, True, False, True),   # letterbox toggled; stale image
    (True, True, True, False, False, True, True),
    (True, True, True, False, True, True, False),   # no unnecessary recomposition
    (True, True, True, True, True, True, True),     # normal fresh source
    (True, True, False, False, False, False, True), # first frame/new state
    (False, True, True, False, True, False, False), # preserve old when no capture
    (True, False, True, False, True, False, False), # preserve old when unanchored
)
for available, anchored, valid, fresh, old, new, expected in fixtures:
    assert needs_redraw(available, anchored, valid, fresh, old, new) == expected

mutations = (
    ("cachedMenuLetterbox != currentMenuLetterbox;",
     "cachedMenuLetterbox == currentMenuLetterbox;"),
    ("(!cachedMenuProjectionValid || capture.fresh ||\n                         letterboxPolicyChanged)",
     "(!cachedMenuProjectionValid || capture.fresh)"),
    ("cachedMenuLetterbox = currentMenuLetterbox;",
     "cachedMenuLetterbox = !currentMenuLetterbox;"),
    ("if (capture.available &&", "if (true &&"),
    ("menuProjectionAnchorValid &&", "false &&"),
    ("if (!foundConfig)\n            return cachedLetterbox;",
     "if (!foundConfig)\n            return false;"),
)
for old, bad in mutations:
    assert old in source, "mutation fixture missing: " + old
    altered = source.replace(old, bad, 1)
    try:
        verify(altered)
    except (AssertionError, IndexError, ValueError):
        continue
    raise AssertionError("unsafe menu cache mutation escaped: " + old)

print("PASS R23 menu letterbox cache key; seven refresh cases; six destructive mutants")
print("RUNTIME_VALIDATION=UNTESTED")
