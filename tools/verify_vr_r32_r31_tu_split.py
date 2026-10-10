from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]

def read(path):
    return (ROOT / path).read_text(encoding="utf-8")

r32 = read("src/vr/d3d9/stereo_renderer_r32.cpp")
cmake = read("CMakeLists.txt")
cmkr = read("cmake.toml")
workflow = read(".github/workflows/vr-dx9ex-active.yml")
preflight = json.loads(read("docs/automation/r84-port/R32_R31_SPLIT_PREFLIGHT.json"))
errors = []

guard = "#ifndef OUTRUN_VR_REFACTOR_SPLIT_R32_R31"
include = '#include "stereo_renderer_r31.cpp"'
guard_pos = r32.find(guard)
include_pos = r32.find(include)
endif_pos = r32.find("#endif", guard_pos if guard_pos >= 0 else 0)
if min(guard_pos, include_pos, endif_pos) < 0 or not (guard_pos < include_pos < endif_pos):
    errors.append("R32 textual R31 include is not isolated behind the future split guard")

# The previously blocked split now has explicit R30 and R31 owner services.
# Protect the active integrated build graph rather than retaining a stale
# FATAL_ERROR that prevents the supported four-TU configuration.
for label, body in (("CMakeLists.txt", cmake), ("cmake.toml", cmkr)):
    for option, source in (
        ("R32_R31", "stereo_renderer_r31.cpp"),
        ("R31_R30", "stereo_renderer_r30.cpp"),
    ):
        if f"option(OUTRUN_VR_REFACTOR_SPLIT_{option}" not in body:
            errors.append(f"{label} missing {option} split option")
        marker = f"if(OUTRUN_VR_REFACTOR_SPLIT_{option})"
        block_start = body.find(marker)
        block_end = body.find("\nendif()", block_start)
        if min(block_start, block_end) < 0 or (
            f"src/vr/d3d9/{source}" not in body[block_start:block_end] or
            "PROPERTIES HEADER_FILE_ONLY FALSE" not in body[block_start:block_end]
        ):
            errors.append(f"{label} {option} does not compile {source} as an independent TU")
        if "add_compile_definitions(OUTRUN_VR_REFACTOR_SPLIT_" + option + "=1)" not in body[block_start:block_end]:
            errors.append(f"{label} {option} missing compile-definition isolation")
    if "R32/R31 split is blocked until" in body:
        errors.append(f"{label} retained obsolete R32/R31 FATAL gate")
    if "Combined R33/R32/R31/R30 ownership" not in body:
        errors.append(f"{label} lacks integrated TU ownership constraint")

for feature in ("OUTRUN_VR_REFACTOR_SPLIT_R33_R32", "OUTRUN_VR_REFACTOR_SPLIT_R32_R31", "OUTRUN_VR_REFACTOR_SPLIT_R31_R30"):
    if "-D" + feature + "=ON" not in workflow:
        errors.append(f"canonical Win32 full-chain gate does not enable {feature}")
if "'tools/verify_vr_r32_r31_tu_split.py'" not in workflow:
    errors.append("DX9Ex workflow does not execute active split guard")

if preflight.get("status") != "BLOCKED_BY_LOWER_OWNER_API_EXTRACTION":
    errors.append("R32/R31 preflight blocker status is not durable")
if preflight.get("failed_run_id") != 37594186807:
    errors.append("R32/R31 preflight does not pin the exact failed compile run")
if preflight.get("failed_result_sha") != "b4353c37f2b760ce25be7230a4ca4797cbab2c7d":
    errors.append("R32/R31 preflight does not pin the exact failed result SHA")
required = set(preflight.get("required_predecessor_boundaries", []))
for boundary in ("R31_R30", "R30_R29", "RESET_PRESENT_DIRECTGPU"):
    if boundary not in required:
        errors.append(f"R32/R31 preflight missing predecessor boundary: {boundary}")

r30_api = read("src/vr/core/r30_support_api.hpp")
r30 = read("src/vr/d3d9/stereo_renderer_r30.cpp")
if "R30SupportSetStereoRecoverySafetyThroughEpoch(" not in r30_api:
    errors.append("R30 lower recovery epoch facade declaration missing")
if "SetStereoRecoverySafetyThroughEpoch(throughEpoch);" not in r30:
    errors.append("R30 lower recovery epoch delegation missing")
if "R30SupportSetStereoRecoverySafetyThroughEpoch(" not in r32:
    errors.append("R32 Reset lifecycle still uses transitive R29 recovery function")
if "            SetStereoRecoverySafetyThroughEpoch(" in r32:
    errors.append("R32 regained private R29 recovery linkage")
if '#include "vr_pass_policy.hpp"' not in r32:
    errors.append("R32 standalone translation unit lacks shared effect policy")
for public, lower in (
    ("FrameIdAtOrAfter", "return FrameIdAtOrAfter(candidate, reference);"),
    ("FailClosedResetBaselineState", "FailClosedResetBaselineState();"),
    ("ArmStereoRecoverySafety", "ArmStereoRecoverySafety(extraPresents);"),
    ("NoteRestoreFailure", "NoteRestoreFailure(what);"),
):
    facade = "R30Support" + public + "("
    if facade not in r30_api or facade not in r30 or facade not in r32:
        errors.append("missing isolated lower-owner facade: " + facade)
    if lower not in r30:
        errors.append("R30 lower-owner delegation drifted: " + lower)
for old in (
    "!FrameIdAtOrAfter(gpuCompleted, candidate.frameId)",
    "{ FailClosedResetBaselineState(); }",
    "{ ArmStereoRecoverySafety(n); }",
    "{ NoteRestoreFailure(what); }",
):
    if old in r32:
        errors.append("R32 retains private R9/R29 imported identifier: " + old)

legacy_r31_calls = (
    "R31TelemetryFrameSnapshot(", "R31TelemetryLiveWvpChecks(",
    "R31TelemetryLiveWvpRejects(", "R31ResetFastPathState(",
    "R31GetSavedViewport(", "R31ObserveDraw(",
    "R31DiscardUnreliableDrawCaches(", "R31TelemetryNoteFallback(",
    "R31TelemetryNoteFastWorld(", "R31TelemetryNoteFragile(",
    "R31TelemetryNoteHud(", "R31TelemetryNoteUnstable(",
    "R31BuildFastWorldConstants(", "R31InstallStatus(",
)
for marker in legacy_r31_calls:
    if marker in r32:
        errors.append(f"R32 regressed to private R31 support dependency: {marker}")

if errors:
    for error in errors:
        print(f"R32/R31 split preflight FAIL: {error}")
    sys.exit(1)

print("R32/R31 split preflight PASS")
