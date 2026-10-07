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

# Pin the focus-side structural facts that justify the dispositions.
r33 = (ROOT / "src/vr/d3d9/stereo_renderer_r33.cpp").read_text(encoding="utf-8")
r32 = (ROOT / "src/vr/d3d9/stereo_renderer_r32.cpp").read_text(encoding="utf-8")
r31 = (ROOT / "src/vr/d3d9/stereo_renderer_r31.cpp").read_text(encoding="utf-8")
r30 = (ROOT / "src/vr/d3d9/stereo_renderer_r30.cpp").read_text(encoding="utf-8")
cmake = (ROOT / "cmake.toml").read_text(encoding="utf-8")
if (ROOT / "src/vr/d3d9/stereo_renderer_r34.cpp").exists():
    errors.append("retired R34 physical source returned")
for source, marker, label in (
    (r33, '#include "stereo_renderer_r32.cpp"', "R33->R32 textual ownership"),
    (r32, '#include "stereo_renderer_r31.cpp"', "R32->R31 textual ownership"),
    (r31, '#include "stereo_renderer_r30.cpp"', "R31->R30 textual ownership"),
    (r30, '#include "stereo_renderer_r29.cpp"', "R30->R29 textual ownership"),
):
    if marker not in source:
        errors.append(f"{label} changed; reclassify inventory before proceeding")
for marker in (
    "src/vr/d3d9/stereo_renderer_r29.cpp",
    "src/vr/d3d9/stereo_renderer_r30.cpp",
    "src/vr/d3d9/stereo_renderer_r31.cpp",
    "src/vr/d3d9/stereo_renderer_r32.cpp",
    "PROPERTIES HEADER_FILE_ONLY TRUE",
):
    if marker not in cmake:
        errors.append(f"CMake textual-ownership evidence missing: {marker}")

if errors:
    for error in errors:
        print(f"R84 inventory contract FAIL: {error}")
    sys.exit(1)
print("R84 inventory contract PASS")
