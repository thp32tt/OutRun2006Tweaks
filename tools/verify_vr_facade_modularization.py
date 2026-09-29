#!/usr/bin/env python3
"""Guard bounded R70 renderer-facade modularization.

Set 01 F04 records that stable facades still hide historical .cpp include chains.
Phase 1 extracted R13 into an include-free overlay. Phase 2 does the same for
R23/R27/R28 so production R29 no longer includes outrun_renderer_r23.cpp.
These steps change source ownership only; runtime policy must remain unchanged.
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


r13_wrapper_rel = "src/vr/game/outrun_renderer_r13.cpp"
r13_overlay_rel = "src/vr/game/outrun_renderer_r13_overlay.inc"
r23_wrapper_rel = "src/vr/game/outrun_renderer_r23.cpp"
r23_overlay_rel = "src/vr/game/outrun_renderer_r23_overlay.inc"
r29_rel = "src/vr/game/outrun_renderer_r29.cpp"
facade_rel = "src/vr/d3d9/renderer_pipeline.cpp"

r13_wrapper = read(r13_wrapper_rel)
r13_overlay = read(r13_overlay_rel)
r23_wrapper = read(r23_wrapper_rel)
r23_overlay = read(r23_overlay_rel)
r29 = read(r29_rel)
facade = read(facade_rel)
cmake_toml = read("cmake.toml")
cmake_generated = read("CMakeLists.txt")
openxr_workflow = read(".github/workflows/vr-openxr.yml")

require_order(
    r13_wrapper,
    r13_wrapper_rel,
    '#include "vr/d3d9/r13_bridge.hpp"',
    '#include "outrun_renderer.cpp"',
    '#include "outrun_renderer_r13_overlay.inc"',
)
if "namespace OutRunVRRenderer" in r13_wrapper:
    raise SystemExit("R13 compatibility wrapper regained implementation body")
if "#include" in r13_overlay:
    raise SystemExit("R13 overlay must remain include-free")
require(
    r13_overlay,
    r13_overlay_rel,
    "namespace OutRunVRRenderer",
    "R13CurrentRenderSemantic",
    "SetVertexShaderConstantFDestR13",
    "R13RendererInstallThread",
    "VRRendererR13HardeningHook",
)

if '#include "outrun_renderer_r13.cpp"' in r23_wrapper:
    raise SystemExit("R23 regressed to historical R13 .cpp inclusion")
require_order(
    r23_wrapper,
    r23_wrapper_rel,
    '#include "../runtime_eligibility.hpp"',
    '#include "../ipc/recenter_request.hpp"',
    '#include "vr/d3d9/r13_bridge.hpp"',
    '#include "outrun_renderer.cpp"',
    '#include "outrun_renderer_r13_overlay.inc"',
    '#include "outrun_renderer_r23_overlay.inc"',
)
if "namespace OutRunVRRenderer" in r23_wrapper:
    raise SystemExit("R23 compatibility wrapper regained implementation body")
if "#include" in r23_overlay:
    raise SystemExit("R23 overlay must remain include-free")
require(
    r23_overlay,
    r23_overlay_rel,
    "namespace OutRunVRRenderer",
    "R23RendererInstallState",
    "R23ServiceRenderThreadCleanup",
    "R28TrackRawWvpWrite",
    "R23RendererInstallThread",
    "VRRendererR23EligibilityHook",
    "GetR28VerifiedProjection",
)

if '#include "outrun_renderer_r23.cpp"' in r29:
    raise SystemExit("R29 regressed to historical R23 .cpp inclusion")
require_order(
    r29,
    r29_rel,
    "#include <limits>",
    '#include "../runtime_eligibility.hpp"',
    '#include "../ipc/recenter_request.hpp"',
    '#include "vr/d3d9/r13_bridge.hpp"',
    '#include "outrun_renderer.cpp"',
    '#include "outrun_renderer_r13_overlay.inc"',
    '#include "outrun_renderer_r23_overlay.inc"',
)
require(
    r29,
    r29_rel,
    "R29BuildCoherentUploadEnvelope",
    "R29InvalidateRendererStateAfterExternalRestore",
)

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

require(
    openxr_workflow,
    ".github/workflows/vr-openxr.yml",
    "'src/vr/game/outrun_renderer_r13_overlay.inc' = @(",
    "R13FragileEffectNeedsZeroDisparity",
    "shadow/billboard/panel pass kept stock",
    "'src/vr/game/outrun_renderer_r23_overlay.inc' = @(",
    "R23RenderThreadCleanupRequested",
    "R23ServiceRenderThreadCleanup",
    "recovery pose warmup is stock-visible",
)
for stale_guard in (
    "'src/vr/game/outrun_renderer_r13.cpp' = @(",
    "'src/vr/game/outrun_renderer_r23.cpp' = @(",
):
    if stale_guard in openxr_workflow:
        raise SystemExit(
            f"OpenXR hardening guard regressed to compatibility wrapper: {stale_guard}"
        )

print("VR renderer facade modularization F04 phase 2: PASS")
