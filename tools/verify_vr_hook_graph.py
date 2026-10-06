#!/usr/bin/env python3
"""Guard the legacy R-series hook graph while it is incrementally flattened.

This verifier is intentionally conservative: it pins the currently approved
include chain and an upper bound on SafetyHookInline declarations. Refactor
commits may reduce these counts, but may not silently grow another overlay.
"""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]

CHAIN = {
    "src/vr/d3d9/stereo_renderer_r13.cpp": "stereo_renderer.cpp",
    "src/vr/d3d9/stereo_renderer_r20.cpp": "stereo_renderer_r13.cpp",
    "src/vr/d3d9/stereo_renderer_r21.cpp": "stereo_renderer_r20.cpp",
    "src/vr/d3d9/stereo_renderer_r22.cpp": "stereo_renderer_r21.cpp",
    "src/vr/d3d9/stereo_renderer_r23.cpp": "stereo_renderer_r22.cpp",
    "src/vr/d3d9/stereo_renderer_r26.cpp": "stereo_renderer_r23.cpp",
    "src/vr/d3d9/stereo_renderer_r29.cpp": "stereo_renderer_r26.cpp",
    "src/vr/d3d9/stereo_renderer_r30.cpp": "stereo_renderer_r29.cpp",
    "src/vr/d3d9/stereo_renderer_r31.cpp": "stereo_renderer_r30.cpp",
    "src/vr/d3d9/stereo_renderer_r32.cpp": "stereo_renderer_r31.cpp",
    "src/vr/d3d9/stereo_renderer_r33.cpp": "stereo_renderer_r32.cpp",
}

MAX_HOOKS = {
    "src/vr/d3d9/stereo_renderer.cpp": 9,
    "src/vr/d3d9/stereo_renderer_r13.cpp": 7,
    "src/vr/d3d9/stereo_renderer_r20.cpp": 1,
    "src/vr/d3d9/stereo_renderer_r21.cpp": 1,
    "src/vr/d3d9/stereo_renderer_r22.cpp": 13,
    "src/vr/d3d9/stereo_renderer_r23.cpp": 7,
    "src/vr/d3d9/stereo_renderer_r26.cpp": 9,
    "src/vr/d3d9/stereo_renderer_r29.cpp": 5,
    "src/vr/d3d9/stereo_renderer_r30.cpp": 14,
    "src/vr/d3d9/stereo_renderer_r31.cpp": 0,
    "src/vr/d3d9/stereo_renderer_r32.cpp": 3,
    "src/vr/d3d9/stereo_renderer_r33.cpp": 7,
}

errors = []
for rel, parent in CHAIN.items():
    text = (ROOT / rel).read_text(encoding="utf-8")
    if f'#include "{parent}"' not in text:
        errors.append(f"{rel}: expected legacy parent include {parent}")

hook_re = re.compile(r"\bSafetyHookInline\s+[A-Za-z0-9_]+\s*\{\s*\}")
for rel, ceiling in MAX_HOOKS.items():
    text = (ROOT / rel).read_text(encoding="utf-8")
    count = len(hook_re.findall(text))
    if count > ceiling:
        errors.append(f"{rel}: hook declarations grew {count}>{ceiling}")
    print(f"{rel}: SafetyHookInline={count}/{ceiling}")

if errors:
    print("VR hook graph guard FAILED", file=sys.stderr)
    for error in errors:
        print(f" - {error}", file=sys.stderr)
    raise SystemExit(1)

print("VR hook graph guard PASS (counts may shrink during flattening; growth is blocked)")
