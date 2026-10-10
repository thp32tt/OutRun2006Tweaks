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
ui_scaling = read("src/hooks_uiscaling.cpp")
r30_safe = read("src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp")
r30_full = read("src/vr/d3d9/stereo_renderer_r30.cpp")
ini = read("OutRun2006Tweaks.ini")

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



# The game's existing UI Scaling path is the DX11/VR layout SSOT. It already
# converts OutRun's canonical 640x480 UI into the game canvas without stretching.
# VR may world-lock/project that result, but must not apply a hidden second
# default scale that pulls edge HUD/menu elements back toward the centre.
for literal, meaning in (
    ("UIScalingMode = 1", "OutRun Online Arcade UI scaling default"),
    ("HudScale = 0.55", "Quest 3 HUD size trim default"),
):
    require(ini, literal, meaning)

require(
    vr_settings,
    'Setting<float> VRHudScale{ "VR", "HudScale", 0.55f,',
    "VR HUD default must restore the prior Quest 3 size trim",
)
for literal, meaning in (
    ("float scale = min(Game::screen_scale->x, Game::screen_scale->y);", "canonical UI contain scale"),
    ("Game::screen_resolution->x - (Game::original_resolution.x * scale)", "canonical UI horizontal centering"),
):
    require(ui_scaling, literal, meaning)

contain_start = "        void R30HudContainScale("
contain_end = "        enum class R30ScreenSpaceKind"
for renderer, label in (
    (r30_safe, "R26-safe"),
    (r30_full, "full R30"),
):
    require(renderer, contain_start, f"{label} VR HUD contain transform")
    start = renderer.index(contain_start)
    end = renderer.index(contain_end, start)
    contain = renderer[start:end]
    if "R30HudAspectCompensation(" in contain:
        raise SystemExit(
            f"{label} VR HUD contain path must not add a second automatic aspect correction"
        )
require(
    r30_safe,
    "already-scaled game UI coordinates remain the layout SSOT",
    "explicit safe-path game UI layout ownership contract",
)
require(
    r30_full,
    "Do not \"contain\" it",
    "explicit full-path game UI layout ownership contract",
)


# Normal CORRECTNESS sessions must not pay diagnostic per-draw/stack-walk costs.
for literal, meaning in (
    ("$hudInspectorProfiles=@('HUD_SCREEN','HUD_MENU','HUD_WORLD','STAGE_DIAGNOSTIC')", "HUD inspector diagnostic opt-in"),
    ("$env:OUTRUN_VR_DX11_CENSUS='0'", "DX11 census disabled outside explicit diagnostic"),
    ("$env:OUTRUN_VR_DX11_CENSUS_EXHAUSTIVE='0'", "DX11 exhaustive census disabled for runtime tests"),
    ("$TestProfile -eq 'STAGE_DIAGNOSTIC'", "diagnostic-only shader/census gate"),
):
    require(runner, literal, meaning)

if "if($backend -ne '2d'){\n    $gameArgs += '-HudInspector=true'\n}" in runner:
    raise SystemExit("HUD inspector must not be forced on for every VR run")

print("DX11 XR source-resolution + UI-scaling SSOT policy: PASS")
