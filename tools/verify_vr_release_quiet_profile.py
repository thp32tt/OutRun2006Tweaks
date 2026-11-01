#!/usr/bin/env python3
from pathlib import Path
import configparser

root = Path(__file__).resolve().parents[1]
p = configparser.ConfigParser(strict=True, interpolation=None)
p.read(root / "OutRun2006Tweaks.ini", encoding="utf-8")

assert p.getboolean("VR", "Telemetry") is False
assert p.getboolean("VR", "FileLogging") is False
assert p.getboolean("VR", "DirectGpuOnly") is True
assert abs(p.getfloat("Graphics", "ReflectionUpdateRate") - 0.25) < 1e-9
assert p.getboolean("Graphics", "TransparencySupersampling") is False
assert p.getboolean("VR", "TransparencySupersampling") is False

dll = (root / "src/dllmain.cpp").read_text(encoding="utf-8")
host = (root / "vrhost/src/main.cpp").read_text(encoding="utf-8")
r23 = (root / "vrhost/src/main_r23.cpp").read_text(encoding="utf-8")
focus = (root / "tools/Run-DX9ExFocusTest.ps1").read_text(encoding="utf-8")
official = (root / "tools/Run-FocusOfficialTest.ps1").read_text(encoding="utf-8")
selector = (root / "Start-OutRun.cmd").read_text(encoding="utf-8")
launcher = (root / "Start-OutRun-VR.cmd").read_text(encoding="utf-8")
cmake = (root / "CMakeLists.txt").read_text(encoding="utf-8")
wheel_build = (root / "src/hooks_wheel_ffb_build.cpp").read_text(encoding="utf-8")

for token in (
    "bool FileLoggingEnabled() noexcept",
    "bool ReleasePackageVrLaunchRequested() noexcept",
    'L"OUTRUN_VR_LAUNCH"',
    '"VR_RELEASE_VERSION.txt"',
    "Settings::VREnabled = false;",
    'L"OUTRUN_VR_FILE_LOG"',
    "if (Module::FileLoggingEnabled())",
    "spdlog::level::off",
):
    assert token in dll, token

for token in (
    "static bool OutRunVrFileLoggingEnabled() noexcept",
    'L"OUTRUN_VR_FILE_LOG"',
    "if (!OutRunVrFileLoggingEnabled())",
    "if (OutRunVrFileLoggingEnabled())",
):
    assert token in host, token

assert 'if (OutRunVrFileLoggingEnabled())\n            pipelineLog.open(' in r23
assert 'OutRunVR::Pacing::Enabled() && OutRunVrFileLoggingEnabled()' in r23
assert 'CheckXr(endResult, "xrEndFrame");\n            if (OutRunVrFileLoggingEnabled())' in r23
assert 'if (OutRunVrFileLoggingEnabled() &&\n                (lastPipelineTelemetryMs == 0 ||' in r23
assert 'if (OutRunVrFileLoggingEnabled())\n                timings.MaybeLog();' in r23
assert 'if (OutRunVrFileLoggingEnabled() &&\n            (R23LastTheaterRefreshLogMs == 0 ||' in r23
assert 'if (OutRunVrFileLoggingEnabled() &&\n                            (R23LastCachedProjectionLogMs == 0 ||' in r23
assert 'if (OutRunVrFileLoggingEnabled() &&\n                                (R23LastGameplayFallbackLogMs == 0 ||' in r23
assert 'if (OutRunVrFileLoggingEnabled() &&\n                (sessionEpoch_.lastLoggedXrHz <= 0.0 ||' in r23
assert 'Acquire(projection_, image);\n            if (OutRunVrFileLoggingEnabled())' in host

for script in (focus, official):
    assert "-VR.Telemetry=true" in script
    assert "OUTRUN_VR_FILE_LOG = '1'" in script

assert 'call "%~dp0Start-OutRun.cmd" vr' in launcher

for token in (
    'OUTRUN_VR_FORCE_DISABLED=1',
    'OUTRUN_VR_LAUNCH=1',
    'OUTRUN_VR_R23_PIXEL_PROBE=0',
    '-VR.Enabled=true',
    '-VR.AutoLaunchHost=true',
    '-FramerateUnlockExperimental=true',
    '-VR.FrameCadenceMode=1',
    '-VR.PreferD3D9Ex=true',
    '-VR.DirectGpuOnly=true',
    '-VR.AutoRenderResolution=true',
    '-VR.FollowGameResolution=false',
    '-VR.MirrorFitDesktop=true',
    '-VR.Hud1080pReference=true',
    '-VR.HudResponsiveLayout=true',
    '-VR.HudScale=0.55',
    '-VR.MenuScale=0.75',
    '-VR.CullingUnionMarginDegrees=8.0',
    '-VR.Telemetry=false',
    '-VR.FileLogging=false',
):
    assert token in selector, token

# The one shipped dinput8.dll is intentionally shared by 2D and VR and retains
# the current wheel FFB implementation rather than packaging a second DLL.
assert '"src/hooks_wheel_ffb_build.cpp"' in cmake
assert '#include "hooks_wheel_ffb.cpp"' in wheel_build

probe = r23.split("bool R23PixelDiagnosticsEnabled() noexcept", 1)[1].split(
    "constexpr UINT R23SourceSamples", 1)[0]
assert 'std::strcmp(value, "1") == 0' in probe
assert "return value != nullptr" in probe

print("PASS VR v0.01-beta: one shared FFB+VR dinput8.dll, direct EXE/selector 2D path disables only VR, CMD-only validated VR profile replaces PS1 dependency, publishing remains manual")
