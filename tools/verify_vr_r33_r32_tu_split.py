from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]

def read(path):
    return (ROOT / path).read_text(encoding="utf-8")

r33 = read("src/vr/d3d9/stereo_renderer_r33.cpp")
cmake = read("CMakeLists.txt")
cmkr = read("cmake.toml")
workflow = read(".github/workflows/vr-dx9ex-active.yml")
errors = []

guard = "#ifndef OUTRUN_VR_REFACTOR_SPLIT_R33_R32"
include = '#include "stereo_renderer_r32.cpp"'
guard_pos = r33.find(guard)
include_pos = r33.find(include)
endif_pos = r33.find("#endif", guard_pos if guard_pos >= 0 else 0)
if min(guard_pos, include_pos, endif_pos) < 0 or not (guard_pos < include_pos < endif_pos):
    errors.append("R33 textual R32 include is not isolated behind the split gate")

for label, body in (("CMakeLists.txt", cmake), ("cmake.toml", cmkr)):
    if 'option(OUTRUN_VR_REFACTOR_SPLIT_R33_R32' not in body:
        errors.append(f"{label} missing R33/R32 split option")
    if not re.search(
        r"if\(OUTRUN_VR_REFACTOR_SPLIT_R33_R32\).*?"
        r"set_source_files_properties\(\s*"
        r"src/vr/d3d9/stereo_renderer_r32\.cpp\s*"
        r"PROPERTIES HEADER_FILE_ONLY FALSE\).*?"
        r"add_compile_definitions\(OUTRUN_VR_REFACTOR_SPLIT_R33_R32=1\)",
        body,
        re.S,
    ):
        errors.append(f"{label} split gate does not compile R32 independently")
    included_start = body.find("set(OUTRUN_VR_INCLUDED_IMPL_TUS")
    included_end = body.find(
        "set_source_files_properties(${OUTRUN_VR_INCLUDED_IMPL_TUS}",
        included_start,
    )
    if min(included_start, included_end) < 0:
        errors.append(f"{label} missing included implementation ownership block")
    elif "src/vr/d3d9/stereo_renderer_r32.cpp" not in body[included_start:included_end]:
        errors.append(f"{label} default graph must keep R32 include-only until Gate 3 cleanup")

if "'tools/verify_vr_r33_r32_tu_split.py'" not in workflow:
    errors.append("DX9Ex workflow does not execute the R33/R32 split verifier")
if "-DOUTRUN_VR_REFACTOR_SPLIT_R33_R32=ON" not in workflow:
    errors.append("DX9Ex full-chain compile does not exercise the R33/R32 split gate")

if errors:
    for error in errors:
        print(f"R33/R32 TU split FAIL: {error}")
    sys.exit(1)

print("R33/R32 TU split PASS")
