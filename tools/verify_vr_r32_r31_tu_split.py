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

blocked_message = (
    "R32/R31 split is blocked until lower R30/R29/Reset/Present/DirectGPU "
    "owner APIs replace R32 private textual-chain dependencies"
)
for label, body in (("CMakeLists.txt", cmake), ("cmake.toml", cmkr)):
    if 'option(OUTRUN_VR_REFACTOR_SPLIT_R32_R31' not in body:
        errors.append(f"{label} missing R32/R31 preflight option")
    if blocked_message not in body:
        errors.append(f"{label} does not fail closed on premature R32/R31 split")
    if "PROPERTIES HEADER_FILE_ONLY FALSE" in body[
        body.find("if(OUTRUN_VR_REFACTOR_SPLIT_R32_R31)"):
        body.find("endif()", body.find("if(OUTRUN_VR_REFACTOR_SPLIT_R32_R31)"))
    ]:
        errors.append(f"{label} prematurely enables independent R31 compilation")

if "-DOUTRUN_VR_REFACTOR_SPLIT_R32_R31=ON" in workflow:
    errors.append("canonical DX9Ex full-chain gate must not enable blocked R32/R31 split")
if "-DOUTRUN_VR_REFACTOR_SPLIT_R33_R32=ON" not in workflow:
    errors.append("canonical DX9Ex full-chain gate lost verified R33/R32 split")
if "'tools/verify_vr_r32_r31_tu_split.py'" not in workflow:
    errors.append("DX9Ex workflow does not execute R32/R31 preflight verifier")

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
