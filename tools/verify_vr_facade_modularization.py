#!/usr/bin/env python3
"""Guard bounded R70 facade modularization.

Set 01 F04 records that stable facades still hide historical .cpp include chains.
Phase 1 extracted renderer R13 into an include-free overlay. Phase 2 did the same
for renderer R23/R27/R28. Phase 3 extracted the final D3D9Ex R15 layer. Phase 4
extracts R14 so the production Ex facade composes R13/base plus R14/R15 overlays
without nesting the historical R14 or R15 translation-unit wrappers.
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
ex_r13_wrapper_rel = "src/vr/d3d9/ex_device_upgrade_r13.cpp"
ex_r13_overlay_rel = "src/vr/d3d9/ex_device_upgrade_r13_overlay.inc"
ex_r14_wrapper_rel = "src/vr/d3d9/ex_device_upgrade_r14.cpp"
ex_r14_overlay_rel = "src/vr/d3d9/ex_device_upgrade_r14_overlay.inc"
ex_r15_wrapper_rel = "src/vr/d3d9/ex_device_upgrade_r15.cpp"
ex_r15_overlay_rel = "src/vr/d3d9/ex_device_upgrade_r15_overlay.inc"
ex_facade_rel = "src/vr/d3d9/ex_device_pipeline.cpp"

r13_wrapper = read(r13_wrapper_rel)
r13_overlay = read(r13_overlay_rel)
r23_wrapper = read(r23_wrapper_rel)
r23_overlay = read(r23_overlay_rel)
r29 = read(r29_rel)
facade = read(facade_rel)
ex_r13_wrapper = read(ex_r13_wrapper_rel)
ex_r13_overlay = read(ex_r13_overlay_rel)
ex_r14_wrapper = read(ex_r14_wrapper_rel)
ex_r14_overlay = read(ex_r14_overlay_rel)
ex_r15_wrapper = read(ex_r15_wrapper_rel)
ex_r15_overlay = read(ex_r15_overlay_rel)
ex_facade = read(ex_facade_rel)
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

require_order(
    ex_r13_wrapper,
    ex_r13_wrapper_rel,
    "#include <array>",
    "#include <atomic>",
    "#include <cstdint>",
    '#include "r13_bridge.hpp"',
    '#pragma optimize("", off)',
    '#include "ex_device_upgrade.cpp"',
    '#pragma optimize("", on)',
    '#include "ex_device_upgrade_r13_overlay.inc"',
)
if "namespace OutRunVRD3D9ExUpgradeR13" in ex_r13_wrapper:
    raise SystemExit("Ex R13 compatibility wrapper regained implementation body")
if "#include" in ex_r13_overlay:
    raise SystemExit("Ex R13 overlay must remain include-free")
require(
    ex_r13_overlay,
    ex_r13_overlay_rel,
    "namespace OutRunVRD3D9ExUpgradeR13",
    "TextureLockRectR13",
    "InstallManagedResourceCompatR13",
    "OpenXRVRD3D9ExR13Hardening",
    "ResetCompatDevice",
    "NormalizeLegacyPresentResult",
    "legacy ResetEx shim retained through final R15 validation",
)

require_order(
    ex_r14_wrapper,
    ex_r14_wrapper_rel,
    "#include <algorithm>",
    "#include <memory>",
    "#include <mutex>",
    "#include <unordered_map>",
    "#include <vector>",
    '#include "ex_device_upgrade_r13.cpp"',
    '#include "ex_device_upgrade_r14_overlay.inc"',
)
if "namespace OutRunVRD3D9ExUpgradeR13" in ex_r14_wrapper:
    raise SystemExit("R14 compatibility wrapper regained implementation body")
if "#include" in ex_r14_overlay:
    raise SystemExit("R14 overlay must remain include-free")
require(
    ex_r14_overlay,
    ex_r14_overlay_rel,
    "namespace OutRunVRD3D9ExUpgradeR13",
    "std::unordered_map<IDirect3DTexture9*, R14EntryPtr>",
    "R69IsSelectorAtlasReserveCandidate",
    "R14CopyWholeLevelByLock",
    "InstallManagedResourceCompatR14",
    "exact mip CPU-shadow upload failed",
)

require_order(
    ex_r15_wrapper,
    ex_r15_wrapper_rel,
    "#include <algorithm>",
    "#include <array>",
    "#include <atomic>",
    "#include <cstdint>",
    "#include <mutex>",
    '#include "ex_device_upgrade_r14.cpp"',
    '#include "../runtime_eligibility.hpp"',
    '#include "ex_device_upgrade_r15_overlay.inc"',
)
if "namespace OutRunVRStereo" in ex_r15_wrapper or "namespace OutRunVRD3D9ExUpgradeR13" in ex_r15_wrapper:
    raise SystemExit("R15 compatibility wrapper regained implementation body")
if "#include" in ex_r15_overlay:
    raise SystemExit("R15 overlay must remain include-free")
require(
    ex_r15_overlay,
    ex_r15_overlay_rel,
    "namespace OutRunVRStereo",
    "namespace OutRunVRD3D9ExUpgradeR13",
    "R15ResetStateHealthy",
    "R15CaptureClassicExtraBaseline",
    "D3DSBT_ALL",
    "Ex promotion rolled back transactionally",
    "LastResetStateReplaySucceeded",
)
for stale_ex_owner in (
    '#include "ex_device_upgrade_r13.cpp"',
    '#include "ex_device_upgrade_r14.cpp"',
    '#include "ex_device_upgrade_r15.cpp"',
):
    if stale_ex_owner in ex_facade:
        raise SystemExit(
            f"production Ex facade regressed to historical wrapper inclusion: {stale_ex_owner}"
        )
require_order(
    ex_facade,
    ex_facade_rel,
    "#include <algorithm>",
    "#include <array>",
    "#include <atomic>",
    "#include <cstdint>",
    "#include <memory>",
    "#include <mutex>",
    "#include <unordered_map>",
    "#include <vector>",
    '#include "r13_bridge.hpp"',
    '#pragma optimize("", off)',
    '#include "ex_device_upgrade.cpp"',
    '#pragma optimize("", on)',
    '#include "ex_device_upgrade_r13_overlay.inc"',
    '#include "ex_device_upgrade_r14_overlay.inc"',
    '#include "../runtime_eligibility.hpp"',
    '#include "ex_device_upgrade_r15_overlay.inc"',
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
        "src/vr/d3d9/ex_device_upgrade_r15.cpp",
        "src/vr/d3d9/ex_device_pipeline.cpp",
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
    "'src/vr/d3d9/ex_device_upgrade_r13_overlay.inc' = @(",
    "TextureLockRectR13",
    "ResetCompatDevice",
    "legacy ResetEx shim retained through final R15 validation",
    "'src/vr/d3d9/ex_device_upgrade_r14_overlay.inc' = @(",
    "std::unordered_map<IDirect3DTexture9*, R14EntryPtr>",
    "R14CopyWholeLevelByLock",
    "exact mip CPU-shadow upload failed",
    "'src/vr/d3d9/ex_device_upgrade_r15_overlay.inc' = @(",
    "D3DSBT_ALL",
    "Ex promotion rolled back transactionally",
)
for stale_guard in (
    "'src/vr/game/outrun_renderer_r13.cpp' = @(",
    "'src/vr/game/outrun_renderer_r23.cpp' = @(",
    "'src/vr/d3d9/ex_device_upgrade_r13.cpp' = @(",
    "'src/vr/d3d9/ex_device_upgrade_r14.cpp' = @(",
    "'src/vr/d3d9/ex_device_upgrade_r15.cpp' = @(",
):
    if stale_guard in openxr_workflow:
        raise SystemExit(
            f"OpenXR hardening guard regressed to compatibility wrapper: {stale_guard}"
        )

print("VR facade modularization F04 phase 5: PASS")
