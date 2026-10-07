from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]

def read(path):
    return (ROOT / path).read_text(encoding="utf-8")

r32 = read("src/vr/d3d9/stereo_renderer_r32.cpp")
cmake = read("CMakeLists.txt")
cmkr = read("cmake.toml")
workflow = read(".github/workflows/vr-dx9ex-active.yml")
errors = []

guard = "#ifndef OUTRUN_VR_REFACTOR_SPLIT_R32_R31"
include = '#include "stereo_renderer_r31.cpp"'
guard_pos = r32.find(guard)
include_pos = r32.find(include)
endif_pos = r32.find("#endif", guard_pos if guard_pos >= 0 else 0)
if min(guard_pos, include_pos, endif_pos) < 0 or not (guard_pos < include_pos < endif_pos):
    errors.append("R32 textual R31 include is not isolated behind the split gate")

for label, body in (("CMakeLists.txt", cmake), ("cmake.toml", cmkr)):
    if 'option(OUTRUN_VR_REFACTOR_SPLIT_R32_R31' not in body:
        errors.append(f"{label} missing R32/R31 split option")
    if not re.search(
        r"if\(OUTRUN_VR_REFACTOR_SPLIT_R32_R31\).*?"
        r"set_source_files_properties\(\s*"
        r"src/vr/d3d9/stereo_renderer_r31\.cpp\s*"
        r"PROPERTIES HEADER_FILE_ONLY FALSE\).*?"
        r"add_compile_definitions\(OUTRUN_VR_REFACTOR_SPLIT_R32_R31=1\)",
        body,
        re.S,
    ):
        errors.append(f"{label} split gate does not compile R31 independently")
    if 'if(NOT OUTRUN_VR_REFACTOR_SPLIT_R33_R32)' not in body:
        errors.append(f"{label} R32/R31 split does not require the verified R33/R32 split")
    included_start = body.find("set(OUTRUN_VR_INCLUDED_IMPL_TUS")
    included_end = body.find("set_source_files_properties(", included_start + 1)
    if min(included_start, included_end) < 0:
        errors.append(f"{label} missing included implementation ownership block")
    elif "src/vr/d3d9/stereo_renderer_r31.cpp" not in body[included_start:included_end]:
        errors.append(f"{label} default graph must keep R31 include-only until Gate 3 cleanup")

if '#include "../core/r31_support_api.hpp"' not in r32:
    errors.append("R32 missing explicit R31 support API boundary")

legacy_r31_calls = (
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
for marker in legacy_r31_calls:
    if marker in r32:
        errors.append(f"R32 still consumes private R31 implementation symbol: {marker}")

if "'tools/verify_vr_r32_r31_tu_split.py'" not in workflow:
    errors.append("DX9Ex workflow does not execute the R32/R31 split verifier")
if "-DOUTRUN_VR_REFACTOR_SPLIT_R32_R31=ON" not in workflow:
    errors.append("DX9Ex full-chain compile does not exercise the R32/R31 split gate")

if errors:
    for error in errors:
        print(f"R32/R31 TU split FAIL: {error}")
    sys.exit(1)

print("R32/R31 TU split PASS")
