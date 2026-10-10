#!/usr/bin/env python3
"""Fail-closed contract for the R84 -> focus structural inventory."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
INV = ROOT / "docs/automation/r84-port/R84_TO_FOCUS_INVENTORY.json"

errors = []
if not INV.exists():
    errors.append("missing R84_TO_FOCUS_INVENTORY.json")
else:
    data = json.loads(INV.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1:
        errors.append("inventory schema_version must be 1")
    if data.get("task_id") != "CONVERSION-DX9EX-00506":
        errors.append("inventory must be owned by CONVERSION-DX9EX-00506")
    if data.get("focus_base_sha") != "cd94b8751540fce0a493374fc3e841dd8475aa32":
        errors.append("inventory focus base SHA drifted")
    if data.get("donor_sha") != "40e998500fc758dd3b078d9df2ecc2a57a19bc5d":
        errors.append("inventory donor SHA drifted")
    if data.get("gate0", {}).get("status") != "DONE":
        errors.append("R84 convergence Gate 0 must be DONE before inventory is authoritative")
    allowed = {"APPLIED_EQUIVALENT","PORT_REQUIRED","SUPERSEDED","DEFERRED_RUNTIME_RISK"}
    items = data.get("items") or []
    if not items:
        errors.append("inventory has no classified items")
    ids = [x.get("id") for x in items]
    if len(ids) != len(set(ids)):
        errors.append("inventory item ids must be unique")
    for item in items:
        if item.get("disposition") not in allowed:
            errors.append(f"invalid disposition for {item.get('id')}: {item.get('disposition')}")
        if not item.get("evidence"):
            errors.append(f"missing evidence for {item.get('id')}")
        if not item.get("next_action"):
            errors.append(f"missing next_action for {item.get('id')}")
    required = {
        "R84-R34-R33-FINAL-DISPATCH",
        "R84-R33-R32-REVIEW-DISPATCH",
        "R84-R32-R31-SUPPORT-STATE",
        "R84-R31-R30-SCREEN-SPACE",
        "R84-R30-R29-STEREO-BASE",
        "R84-HUD-XYZRHW-INTERFACES",
        "R84-STEREO-RUNTIME-MATH-FACADES",
        "R84-FRAME-LIFECYCLE-RECOVERY",
        "R84-STATEBLOCK-RASTER-DEPTH",
        "R84-DIRECTGPU-FACADES",
        "R84-PERF-DISPATCH-TELEMETRY",
        "R84-CMAKE-TEXTUAL-OWNERSHIP",
        "R84-REFACTOR-VERIFIER-COVERAGE",
        "R84-DEFERRED-RUNTIME-RISK",
    }
    missing = required - set(ids)
    if missing:
        errors.append("unclassified required units: " + ", ".join(sorted(missing)))
    dispositions = {x.get("id"): x.get("disposition") for x in items}
    if dispositions.get("R84-CMAKE-TEXTUAL-OWNERSHIP") != "PORT_REQUIRED":
        errors.append("remaining textual/CMake ownership debt must stay PORT_REQUIRED until independently compiled")
    if data.get("unclassified_count") != 0 or not data.get("classification_complete"):
        errors.append("inventory must explicitly close with zero unclassified units")

# This 00506 inventory captures HISTORICAL split debt. Retain its immutable
# dispositions, but validate the CURRENT R84 state once 00591 feature CI has
# accepted all five independent ownership/ABI/build/regression/bundle items.
# Otherwise (old branches), continue enforcing the original textual evidence.
r33 = (ROOT / "src/vr/d3d9/stereo_renderer_r33.cpp").read_text(encoding="utf-8")
r32 = (ROOT / "src/vr/d3d9/stereo_renderer_r32.cpp").read_text(encoding="utf-8")
r31 = (ROOT / "src/vr/d3d9/stereo_renderer_r31.cpp").read_text(encoding="utf-8")
r30 = (ROOT / "src/vr/d3d9/stereo_renderer_r30.cpp").read_text(encoding="utf-8")
cmake = (ROOT / "cmake.toml").read_text(encoding="utf-8")
generated = (ROOT / "CMakeLists.txt").read_text(encoding="utf-8")
if (ROOT / "src/vr/d3d9/stereo_renderer_r34.cpp").exists():
    errors.append("retired R34 physical source returned")
feature_path = ROOT / "docs/automation/runs/CONVERSION-DX9EX-00591.json"
feature = json.loads(feature_path.read_text(encoding="utf-8")) if feature_path.exists() else {}
accepted = {
    item.get("id") for item in feature.get("acceptance_results", [])
    if item.get("status") == "PASS_FEATURE_CI"
}
all_accepted = (
    feature.get("feature_id") == "DX9EX:R84_RENDERER_GRAPH"
    and feature.get("feature_status") == "FEATURE_READY"
    and accepted == {"R84-OWNERS", "R84-ABI", "R84-BUILD-GRAPH",
                     "R84-REGRESSION", "R84-TEST-BUNDLE"}
)
seams = (
    (r33, "R33_R32", "stereo_renderer_r32.cpp", "stereo_renderer_r32.cpp"),
    (r32, "R32_R31", "stereo_renderer_r31.cpp", "stereo_renderer_r31.cpp"),
    (r31, "R31_R30", "stereo_renderer_r30.cpp", "stereo_renderer_r30.cpp"),
    (r30, "R30_R29", "stereo_renderer_r29.cpp", "stereo_renderer_r29.cpp"),
)
if all_accepted:
    for source, gate, included, _ in seams:
        guard = "#ifndef OUTRUN_VR_REFACTOR_SPLIT_" + gate
        if guard not in source or '#include "' + included + '"' not in source:
            errors.append("R84 independently compiled source lost guarded fallback: " + gate)
    for label, build in (("cmake.toml", cmake), ("CMakeLists.txt", generated)):
        for _, gate, _, owner in seams:
            if "option(OUTRUN_VR_REFACTOR_SPLIT_" + gate not in build:
                errors.append(label + " missing R84 independent owner gate: " + gate)
            if ("src/vr/d3d9/" + owner + "\n        PROPERTIES HEADER_FILE_ONLY FALSE)") not in build:
                errors.append(label + " missing R84 independent compilation: " + owner)
    if cmake != generated and (
        cmake[cmake.find("option(OUTRUN_VR_REFACTOR_SPLIT_R33_R32"):cmake.find("set(OUTRUN_VR_COMPARE_COUNT")]
        != generated[generated.find("option(OUTRUN_VR_REFACTOR_SPLIT_R33_R32"):generated.find("set(OUTRUN_VR_COMPARE_COUNT")]
    ):
        errors.append("R84 CMake ownership gates differ from generated CMakeLists")
else:
    for source, gate, included, _ in seams:
        if '#include "' + included + '"' not in source:
            errors.append("historical R84 textual ownership changed before acceptance: " + gate)
    for marker in ("src/vr/d3d9/stereo_renderer_r29.cpp",
                   "src/vr/d3d9/stereo_renderer_r30.cpp",
                   "src/vr/d3d9/stereo_renderer_r31.cpp",
                   "src/vr/d3d9/stereo_renderer_r32.cpp",
                   "PROPERTIES HEADER_FILE_ONLY TRUE"):
        if marker not in cmake:
            errors.append("historical CMake ownership evidence missing: " + marker)

if errors:
    for error in errors:
        print(f"R84 inventory contract FAIL: {error}")
    sys.exit(1)
print("R84 inventory contract PASS")
