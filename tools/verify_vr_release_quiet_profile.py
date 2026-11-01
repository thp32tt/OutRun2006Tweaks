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

for token in (
    "bool FileLoggingEnabled() noexcept",
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

probe = r23.split("bool R23PixelDiagnosticsEnabled() noexcept", 1)[1].split(
    "constexpr UINT R23SourceSamples", 1)[0]
assert 'std::strcmp(value, "1") == 0' in probe
assert "return value != nullptr" in probe

print("PASS VR v0.01-beta: file writes, hot-path trace construction, telemetry and pixel probe are quiet by default; diagnostics explicitly opt in")
