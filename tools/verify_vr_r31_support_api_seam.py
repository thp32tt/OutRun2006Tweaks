from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]

def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")

def function_body(source: str, marker: str) -> str:
    start = source.find(marker)
    if start < 0:
        raise ValueError(f"missing function marker: {marker}")
    brace = source.find("{", start)
    if brace < 0:
        raise ValueError(f"missing function body: {marker}")
    depth = 0
    for index in range(brace, len(source)):
        ch = source[index]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return source[brace:index + 1]
    raise ValueError(f"unterminated function body: {marker}")

header = read("src/vr/core/r31_support_api.hpp")
r31 = read("src/vr/d3d9/stereo_renderer_r31.cpp")
r30 = read("src/vr/d3d9/stereo_renderer_r30.cpp")
r29 = read("src/vr/d3d9/stereo_renderer_r29.cpp")
r29_api = read("src/vr/core/r29_owner_api.hpp")
r30_api = read("src/vr/core/r30_support_api.hpp")
r32 = read("src/vr/d3d9/stereo_renderer_r32.cpp")
workflow = read(".github/workflows/vr-dx9ex-active.yml")
errors = []

api = (
    "R31SupportTelemetryFrameSnapshot",
    "R31SupportTelemetryLiveWvpChecks",
    "R31SupportTelemetryLiveWvpRejects",
    "R31SupportResetFastPathState",
    "R31SupportGetSavedViewport",
    "R31SupportObserveDraw",
    "R31SupportDiscardUnreliableDrawCaches",
    "R31SupportNoteFallback",
    "R31SupportNoteFastWorld",
    "R31SupportNoteFragile",
    "R31SupportNoteHud",
    "R31SupportNoteUnstable",
    "R31SupportBuildFastWorldConstants",
    "R31SupportInstallStatus",
)
for marker in api:
    if marker not in header:
        errors.append(f"R31 support API missing declaration: {marker}")
    if marker not in r31:
        errors.append(f"R31 support API missing implementation: {marker}")
    if marker not in r32:
        errors.append(f"R32 missing R31 support API use: {marker}")

# Preserve original shader epoch semantics and deny a private R31 lower call.
epoch_api = "R30SupportCurrentShaderEpoch("
if epoch_api not in r30_api or epoch_api not in r30 or epoch_api not in r31:
    errors.append("R31 shader epoch support declaration/implementation/use missing")
else:
    try:
        body = function_body(r30, epoch_api)
        if "return R29OwnerCurrentShaderEpoch(identity, serial);" not in body:
            errors.append("R30 shader epoch facade lost lower owner delegation")
    except ValueError as exc:
        errors.append(str(exc))
if ("R29OwnerCurrentShaderEpoch(" not in r29_api or
        "return GetCurrentShaderEpoch(identity, serial);" not in function_body(
            r29, "R29OwnerCurrentShaderEpoch(")):
    errors.append("R29 independent shader epoch physical owner lost")
if "if (!GetCurrentShaderEpoch(" in r31:
    errors.append("R31 still uses private shader epoch textual dependency")
if "if (!R30SupportCurrentShaderEpoch(currentShader, currentShaderSerial) ||" not in r31:
    errors.append("R31 fast-world gate lacks explicit shader epoch API")

if '#include "../core/r31_support_api.hpp"' not in r31:
    errors.append("R31 implementation missing public support API header")
if '#include "../core/r31_support_api.hpp"' not in r32:
    errors.append("R32 missing explicit R31 support API boundary")

legacy_r32_calls = (
    "R31TelemetryFrameSnapshot(",
    "R31TelemetryLiveWvpChecks(",
    "R31TelemetryLiveWvpRejects(",
    "R31ResetFastPathState(",
    "R31GetSavedViewport(",
    "R31ObserveDraw(",
    "R31DiscardUnreliableDrawCaches(",
    "R31TelemetryNoteFallback(",
    "R31TelemetryNoteFastWorld(",
    "R31TelemetryNoteFragile(",
    "R31TelemetryNoteHud(",
    "R31TelemetryNoteUnstable(",
    "R31BuildFastWorldConstants(",
    "R31InstallStatus(",
)
for marker in legacy_r32_calls:
    if marker in r32:
        errors.append(f"R32 retained private R31 dependency: {marker}")

delegations = {
    "R31SupportTelemetryFrameSnapshot(": ("R31TelemetryFrameSnapshot()", "route.main", "route.unstable"),
    "R31SupportTelemetryLiveWvpChecks(": ("R31TelemetryLiveWvpChecks()",),
    "R31SupportTelemetryLiveWvpRejects(": ("R31TelemetryLiveWvpRejects()",),
    "R31SupportResetFastPathState(": ("R31ResetFastPathState()",),
    "R31SupportGetSavedViewport(": ("R31GetSavedViewport(device, viewport)",),
    "R31SupportObserveDraw(": ("R31ObserveDraw(device)",),
    "R31SupportDiscardUnreliableDrawCaches(": ("R31DiscardUnreliableDrawCaches()",),
    "R31SupportNoteFallback(": ("R31TelemetryNoteFallback()",),
    "R31SupportNoteFastWorld(": ("R31TelemetryNoteFastWorld()",),
    "R31SupportNoteFragile(": ("R31TelemetryNoteFragile()",),
    "R31SupportNoteHud(": ("R31TelemetryNoteHud()",),
    "R31SupportNoteUnstable(": ("R31TelemetryNoteUnstable()",),
    "R31SupportBuildFastWorldConstants(": (
        "return R31BuildFastWorldConstants(device, stereo, out);",
    ),
    "R31SupportInstallStatus(": ("R31InstallStatus()",),
}
for marker, required in delegations.items():
    try:
        body = function_body(r31, marker)
    except ValueError as exc:
        errors.append(str(exc))
        continue
    for expected in required:
        if expected not in body:
            errors.append(f"{marker.rstrip('(')} lost owner delegation: {expected}")

if "'tools/verify_vr_r31_support_api_seam.py'" not in workflow:
    errors.append("DX9Ex workflow does not execute the R31 support seam verifier")
if "'src/vr/core/r31_support_api.hpp'" not in workflow:
    errors.append("DX9Ex workflow path filter does not track the R31 support API")

if errors:
    for error in errors:
        print(f"R31 support API seam FAIL: {error}")
    sys.exit(1)

print("R31 support API seam PASS")
