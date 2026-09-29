#!/usr/bin/env python3
"""Guard the first bounded R70 renderer-facade modularization step.

Set 01 F04 records that stable facades still hide historical .cpp include chains.
This verifier protects the first reduction: production R23 must compose the base
renderer plus the reusable R13 overlay directly instead of including
outrun_renderer_r13.cpp. Runtime behavior is intentionally unchanged.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    path = ROOT / rel
    if not path.is_file():
        raise SystemExit(f"renderer facade modularization missing file: {rel}")
    return path.read_text(encoding="utf-8")


def require(data: str, rel: str, *markers: str) -> None:
    for marker in markers:
        if marker not in data:
            raise SystemExit(
                f"renderer facade modularization invariant missing: {rel} :: {marker}"
            )


def require_order(data: str, rel: str, *markers: str) -> None:
    positions = []
    for marker in markers:
        pos = data.find(marker)
        if pos < 0:
            raise SystemExit(
                f"renderer facade modularization invariant missing: {rel} :: {marker}"
            )
        positions.append(pos)
    if positions != sorted(positions):
        raise SystemExit(
            f"renderer facade modularization include order drift: {rel} :: {markers}"
        )


wrapper_rel = "src/vr/game/outrun_renderer_r13.cpp"
overlay_rel = "src/vr/game/outrun_renderer_r13_overlay.inc"
r23_rel = "src/vr/game/outrun_renderer_r23.cpp"
r29_rel = "src/vr/game/outrun_renderer_r29.cpp"
facade_rel = "src/vr/d3d9/renderer_pipeline.cpp"

wrapper = read(wrapper_rel)
overlay = read(overlay_rel)
r23 = read(r23_rel)
r29 = read(r29_rel)
facade = read(facade_rel)
cmake_toml = read("cmake.toml")
cmake_generated = read("CMakeLists.txt")

require_order(
    wrapper,
    wrapper_rel,
    '#include "vr/d3d9/r13_bridge.hpp"',
    '#include "outrun_renderer.cpp"',
    '#include "outrun_renderer_r13_overlay.inc"',
)
if "namespace OutRunVRRenderer" in wrapper:
    raise SystemExit("R13 compatibility wrapper regained implementation body")

if '#include "outrun_renderer_r13.cpp"' in r23:
    raise SystemExit("R23 regressed to historical R13 .cpp inclusion")
require_order(
    r23,
    r23_rel,
    '#include "../runtime_eligibility.hpp"',
    '#include "../ipc/recenter_request.hpp"',
    '#include "vr/d3d9/r13_bridge.hpp"',
    '#include "outrun_renderer.cpp"',
    '#include "outrun_renderer_r13_overlay.inc"',
)

if '#include' in overlay:
    raise SystemExit("R13 overlay must remain include-free")
require(
    overlay,
    overlay_rel,
    "namespace OutRunVRRenderer",
    "R13CurrentRenderSemantic",
    "SetVertexShaderConstantFDestR13",
    "R13RendererInstallThread",
    "VRRendererR13HardeningHook",
)

require(r29, r29_rel, '#include "outrun_renderer_r23.cpp"')
require(
    facade,
    facade_rel,
    '#include "../game/outrun_renderer_r23.cpp"',
    '#include "../game/outrun_renderer_r29.cpp"',
)

for rel, data in (("cmake.toml", cmake_toml), ("CMakeLists.txt", cmake_generated)):
    require(
        data,
        rel,
        "src/vr/game/outrun_renderer_r13.cpp",
        "src/vr/game/outrun_renderer_r23.cpp",
        "src/vr/d3d9/renderer_pipeline.cpp",
        "OUTRUN_VR_R70_PRODUCTION_TUS",
    )

print("VR renderer facade modularization F04 phase 1: PASS")
