from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    path = ROOT / rel
    if not path.is_file():
        raise SystemExit(f"missing required file: {rel}")
    return path.read_text(encoding="utf-8")


def require(text: str, literal: str, meaning: str) -> None:
    if literal not in text:
        raise SystemExit(f"{meaning}: missing {literal!r}")


runner = read("tools/Run-OutRunVRTest.ps1")
hooks_misc = read("src/hooks_misc.cpp")
vr_settings = read("src/vr/settings.cpp")
graphics = read("src/hooks_graphics.cpp")

require(
    runner,
    "[ValidateSet('Desktop','XR_NATIVE_2496X2688')]",
    "DX11 source-resolution A/B selector",
)
require(
    runner,
    "[string]$DX11SourceResolution = 'Desktop'",
    "Desktop must remain the default A path",
)
candidate_start = "if($DX11SourceResolution -eq 'XR_NATIVE_2496X2688'){"
require(runner, candidate_start, "runtime-rejected XR-native request gate")
start = runner.index(candidate_start)
end = runner.index("    $profile=[ordered]@{", start)
candidate = runner[start:end]

for forbidden, meaning in (
    ("'-width','2496'", "portrait game-source width override"),
    ("'-height','2688'", "portrait game-source height override"),
    ("'-MirrorFitDesktop=true'", "portrait mirror-fit workaround"),
):
    if forbidden in candidate:
        raise SystemExit(f"runtime-rejected {meaning} must not be launched")

for literal, meaning in (
    ("DESKTOP_ASPECT_SAFE_AFTER_XR_NATIVE_REJECT", "safe fallback identity"),
    ("per-eye OpenXR target, not a valid game logical canvas", "runtime rejection rationale"),
    ("OpenXR keeps its native eye swapchain", "XR/game resolution separation"),
):
    require(candidate, literal, meaning)

for literal, meaning in (
    ('"dx11SourceResolutionProfile=$dx11SourceResolutionProfile"', "A/B identity log"),
    ('"dx11SourceWidth=$dx11SourceWidth"', "effective source width log"),
    ('"dx11SourceHeight=$dx11SourceHeight"', "effective source height log"),
):
    require(runner, literal, meaning)

for literal, meaning in (
    ('!wcsicmp(argv[i], L"-width")', "post-config width override hook"),
    ("Game::screen_resolution->x = std::stol(argv[++i], 0, 0);", "internal width target"),
    ('!wcsicmp(argv[i], L"-height")', "post-config height override hook"),
    ("Game::screen_resolution->y = std::stol(argv[++i], 0, 0);", "internal height target"),
):
    require(hooks_misc, literal, meaning)

require(
    vr_settings,
    'Setting<bool> VRMirrorFitDesktop{ "VR", "MirrorFitDesktop", false,',
    "MirrorFitDesktop must stay opt-in by default",
)
require(
    graphics,
    "VR PC MIRROR: fitting borderless window to monitor",
    "monitor-fit mirror path",
)
require(
    graphics,
    "while internal backbuffer remains",
    "internal backbuffer preservation",
)

print("DX11 XR source-resolution A/B launch policy: PASS")
