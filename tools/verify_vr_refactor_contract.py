#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
errors = []

def read(rel: str) -> str:
    path = ROOT / rel
    if not path.is_file():
        errors.append(f"missing required file: {rel}")
        return ""
    return path.read_text(encoding="utf-8")

tracker = read("src/vr/state/state_block_tracker.hpp")
r22 = read("src/vr/d3d9/stereo_renderer_r22.cpp")
r31 = read("src/vr/d3d9/stereo_renderer_r31.cpp")
r33 = read("src/vr/d3d9/stereo_renderer_r33.cpp")

for marker in (
    "class StateBlockTracker final",
    "SetR22Reliable",
    "SetR31Reliable",
    "R22Reliable",
    "R31Reliable",
    "Reliable",
    "MarkCoverageLost",
    "ResetCoverageLoss",
    "CoverageLost",
    "RequireResync",
    "ConsumeResync",
):
    if marker not in tracker:
        errors.append(f"StateBlockTracker API missing marker: {marker}")

for rel, source in (
    ("src/vr/d3d9/stereo_renderer_r22.cpp", r22),
    ("src/vr/d3d9/stereo_renderer_r31.cpp", r31),
    ("src/vr/d3d9/stereo_renderer_r33.cpp", r33),
):
    if "state_block_tracker.hpp" not in source:
        errors.append(f"{rel}: StateBlockTracker include missing")

for legacy in (
    "R22StateBlockTrackingReliable",
    "R31StateBlockTrackingReliable",
    "R31StateBlockCoverageLost",
    "R31StateBlockResyncPending",
):
    for rel, source in (
        ("src/vr/d3d9/stereo_renderer_r22.cpp", r22),
        ("src/vr/d3d9/stereo_renderer_r31.cpp", r31),
        ("src/vr/d3d9/stereo_renderer_r33.cpp", r33),
    ):
        if legacy in source:
            errors.append(f"{rel}: legacy StateBlock authority reintroduced: {legacy}")

if "StateBlockTracker::Reliable()" not in r33:
    errors.append("R33: neutral aggregate StateBlock reliability query missing")

if errors:
    print("R84 refactor contract FAILED")
    for error in errors:
        print(f"- {error}")
    sys.exit(1)

print("R84 refactor contract OK")
