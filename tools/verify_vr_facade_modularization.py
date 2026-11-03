#!/usr/bin/env python3
"""Guard bounded R70 facade modularization.

Set 01 F04 records that stable facades still hide historical .cpp include chains.
Phase 1 extracted renderer R13 into an include-free overlay. Phase 2 did the same
for renderer R23/R27/R28. Phases 3-5 flattened the production D3D9Ex R15/R14/R13
wrapper edges. Phases 6-17 flatten the default stereo R34/R33/R32/R31/R30/R29/R26/R23/R22/R21/R20/R13 wrapper edges
into include-free overlays while preserving the historical translation-unit
wrappers for compatibility/build-graph ownership. Phase 18 closes F04 by
pinning the production facade floor at the canonical R9/R7 stereo_renderer.cpp
base and rejecting any reintroduced versioned stereo wrapper below that floor.
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
stereo_base_rel = "src/vr/d3d9/stereo_renderer.cpp"
stereo_r13_wrapper_rel = "src/vr/d3d9/stereo_renderer_r13.cpp"
stereo_r13_overlay_rel = "src/vr/d3d9/stereo_renderer_r13_overlay.inc"
stereo_r20_wrapper_rel = "src/vr/d3d9/stereo_renderer_r20.cpp"
stereo_r20_overlay_rel = "src/vr/d3d9/stereo_renderer_r20_overlay.inc"
stereo_r21_wrapper_rel = "src/vr/d3d9/stereo_renderer_r21.cpp"
stereo_r21_overlay_rel = "src/vr/d3d9/stereo_renderer_r21_overlay.inc"
stereo_r22_wrapper_rel = "src/vr/d3d9/stereo_renderer_r22.cpp"
stereo_r22_overlay_rel = "src/vr/d3d9/stereo_renderer_r22_overlay.inc"
stereo_r23_wrapper_rel = "src/vr/d3d9/stereo_renderer_r23.cpp"
stereo_r23_overlay_rel = "src/vr/d3d9/stereo_renderer_r23_overlay.inc"
stereo_r26_wrapper_rel = "src/vr/d3d9/stereo_renderer_r26.cpp"
stereo_r26_overlay_rel = "src/vr/d3d9/stereo_renderer_r26_overlay.inc"
stereo_r29_wrapper_rel = "src/vr/d3d9/stereo_renderer_r29.cpp"
stereo_r29_overlay_rel = "src/vr/d3d9/stereo_renderer_r29_overlay.inc"
stereo_r30_wrapper_rel = "src/vr/d3d9/stereo_renderer_r30.cpp"
stereo_r30_overlay_rel = "src/vr/d3d9/stereo_renderer_r30_overlay.inc"
stereo_r31_wrapper_rel = "src/vr/d3d9/stereo_renderer_r31.cpp"
stereo_r31_overlay_rel = "src/vr/d3d9/stereo_renderer_r31_overlay.inc"
stereo_r32_wrapper_rel = "src/vr/d3d9/stereo_renderer_r32.cpp"
stereo_r32_overlay_rel = "src/vr/d3d9/stereo_renderer_r32_overlay.inc"
stereo_r33_wrapper_rel = "src/vr/d3d9/stereo_renderer_r33.cpp"
stereo_r33_overlay_rel = "src/vr/d3d9/stereo_renderer_r33_overlay.inc"
stereo_r34_wrapper_rel = "src/vr/d3d9/stereo_renderer_r34.cpp"
stereo_r34_overlay_rel = "src/vr/d3d9/stereo_renderer_r34_overlay.inc"
stereo_facade_rel = "src/vr/d3d9/stereo_pipeline.cpp"

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
stereo_base = read(stereo_base_rel)
stereo_r13_wrapper = read(stereo_r13_wrapper_rel)
stereo_r13_overlay = read(stereo_r13_overlay_rel)
stereo_r20_wrapper = read(stereo_r20_wrapper_rel)
stereo_r20_overlay = read(stereo_r20_overlay_rel)
stereo_r21_wrapper = read(stereo_r21_wrapper_rel)
stereo_r21_overlay = read(stereo_r21_overlay_rel)
stereo_r22_wrapper = read(stereo_r22_wrapper_rel)
stereo_r22_overlay = read(stereo_r22_overlay_rel)
stereo_r23_wrapper = read(stereo_r23_wrapper_rel)
stereo_r23_overlay = read(stereo_r23_overlay_rel)
stereo_r26_wrapper = read(stereo_r26_wrapper_rel)
stereo_r26_overlay = read(stereo_r26_overlay_rel)
stereo_r29_wrapper = read(stereo_r29_wrapper_rel)
stereo_r29_overlay = read(stereo_r29_overlay_rel)
stereo_r30_wrapper = read(stereo_r30_wrapper_rel)
stereo_r30_overlay = read(stereo_r30_overlay_rel)
stereo_r31_wrapper = read(stereo_r31_wrapper_rel)
stereo_r31_overlay = read(stereo_r31_overlay_rel)
stereo_r32_wrapper = read(stereo_r32_wrapper_rel)
stereo_r32_overlay = read(stereo_r32_overlay_rel)
stereo_r33_wrapper = read(stereo_r33_wrapper_rel)
stereo_r33_overlay = read(stereo_r33_overlay_rel)
stereo_r34_wrapper = read(stereo_r34_wrapper_rel)
stereo_r34_overlay = read(stereo_r34_overlay_rel)
stereo_facade = read(stereo_facade_rel)
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

require_order(
    stereo_r13_wrapper,
    stereo_r13_wrapper_rel,
    '#include "r13_bridge.hpp"',
    '#include "stereo_renderer.cpp"',
    '#include "stereo_renderer_r13_overlay.inc"',
)
if "namespace OutRunVRStereo" in stereo_r13_wrapper:
    raise SystemExit("Stereo R13 compatibility wrapper regained implementation body")
if "#include" in stereo_r13_overlay:
    raise SystemExit("Stereo R13 overlay must remain include-free")
require(
    stereo_r13_overlay,
    stereo_r13_overlay_rel,
    "namespace OutRunVRStereo",
    "R13InstallState",
    "R13OverlayReady",
    "R13EnsureAckState",
    "R13ReadGpuCompletedFrame",
    "R13ForceMonoShadow",
    "R13CaptureDrawTimeEffect",
    "R13UnsafeTransitionFrames",
    "InlineHook::StartDisabled",
    "VR R13: stereo hardening ACTIVE",
    "single-execution MRT/occlusion fallback",
)

require_order(
    stereo_r20_wrapper,
    stereo_r20_wrapper_rel,
    '#include "stereo_renderer_r13.cpp"',
    '#include "../runtime_eligibility.hpp"',
    '#include "stereo_renderer_r20_overlay.inc"',
)
if "namespace OutRunVRStereo" in stereo_r20_wrapper:
    raise SystemExit("Stereo R20 compatibility wrapper regained implementation body")
if "#include" in stereo_r20_overlay:
    raise SystemExit("Stereo R20 overlay must remain include-free")
require(
    stereo_r20_overlay,
    stereo_r20_overlay_rel,
    "namespace OutRunVRStereo",
    "R20InstallState",
    "R20StereoEligibilityGate",
    "R20ObserveFullDepthSeed",
    "R20DepthHistorySafeForInitialSeed",
    "R20CancelInitialSeed",
    "R20AcceptVerifiedBaseline",
    "BaselineVerified",
    "RecoveryPending",
    "R20BaselineCopyFailures",
    "R20DepthGateRejects",
    "InlineHook::StartDisabled",
    "VR R20 PRODUCTION: first stereo seed requires current-generation Z/stencil clears; disabled-first bootstrap transaction READY",
)

require_order(
    stereo_r21_wrapper,
    stereo_r21_wrapper_rel,
    '#include "stereo_renderer_r20.cpp"',
    '#include "stereo_renderer_r21_overlay.inc"',
)
if "namespace OutRunVRStereo" in stereo_r21_wrapper:
    raise SystemExit("Stereo R21 compatibility wrapper regained implementation body")
if "#include" in stereo_r21_overlay:
    raise SystemExit("Stereo R21 overlay must remain include-free")
require(
    stereo_r21_overlay,
    stereo_r21_overlay_rel,
    "namespace OutRunVRStereo",
    "R21HostStaleMs",
    "R21InstallState",
    "R21HostStatus::SoftSuspend",
    "R21ReadHostFreshness",
    "R21ApplyHostFailClosedAtPresent",
    "ObserveSoftHostSuspend",
    "without baseline reset",
    "R21HostFailClosed",
    "IsFailed(R20InstallState)",
    "InlineHook::StartDisabled",
    "VR R21 FAIL-CLOSED",
)

require_order(
    stereo_r22_wrapper,
    stereo_r22_wrapper_rel,
    '#include "stereo_renderer_r21.cpp"',
    '#include "stereo_renderer_r22_overlay.inc"',
)
if "namespace OutRunVRStereo" in stereo_r22_wrapper:
    raise SystemExit("Stereo R22 compatibility wrapper regained implementation body")
if "#include" in stereo_r22_overlay:
    raise SystemExit("Stereo R22 overlay must remain include-free")
require(
    stereo_r22_overlay,
    stereo_r22_overlay_rel,
    "namespace OutRunVRStereo",
    "R22InstallState",
    "R22ShadowState",
    "R22StateBlockTrackingReliable",
    "R22SetScissorRectHook",
    "R22SetRenderStateHook",
    "R22PrimeShadowState",
    "R22ResetBaselineTracking",
    "IsFailed(R21InstallState)",
    "per-draw GetViewport/GetScissorRect/GetRenderState eliminated",
    "VR R22 GAME: shadow-tracked viewport/scissor replay + common initial depth baseline + R21 eligibility gate ACTIVE",
)

require_order(
    stereo_r23_wrapper,
    stereo_r23_wrapper_rel,
    '#include "stereo_renderer_r22.cpp"',
    '#include "stereo_renderer_r23_overlay.inc"',
)
if "namespace OutRunVRStereo" in stereo_r23_wrapper:
    raise SystemExit("Stereo R23 compatibility wrapper regained implementation body")
if "#include" in stereo_r23_overlay:
    raise SystemExit("Stereo R23 overlay must remain include-free")
require(
    stereo_r23_overlay,
    stereo_r23_overlay_rel,
    "namespace OutRunVRStereo",
    "R23InstallState",
    "R23RecoveryNeedsBaseline",
    "R23CaptureActualGameState",
    "R23GameDrawSerial",
    "R23DiagnoseHostFreshness",
    "passive original Clear only",
    "authoritative first seed",
    "R23 is the final effective Present owner in the layered hook chain.",
    "VR R23 INIT: private eye/backbuffer resources initialized after final game Present",
)

require_order(
    stereo_r26_wrapper,
    stereo_r26_wrapper_rel,
    '#include "stereo_renderer_r23.cpp"',
    '#include "shader_fingerprint_gpl.hpp"',
    '#include "../game/render_semantics.hpp"',
    '#include "stereo_renderer_r26_overlay.inc"',
)
if "namespace OutRunVRRenderer" in stereo_r26_wrapper or "namespace OutRunVRStereo" in stereo_r26_wrapper:
    raise SystemExit("Stereo R26 compatibility wrapper regained implementation body")
if "#include" in stereo_r26_overlay:
    raise SystemExit("Stereo R26 overlay must remain include-free")
require(
    stereo_r26_overlay,
    stereo_r26_overlay_rel,
    "namespace OutRunVRRenderer",
    "R28PerspectiveWorldSemantic",
    "namespace OutRunVRStereo",
    "R26InstallState",
    "R37DepthDisabledFragileOverlay",
    "R13CaptureDrawTimeEffect",
    "unknown state fails closed",
    "VR R26/R28 GAME: verified-world shader-epoch recovery",
)

require_order(
    stereo_r29_wrapper,
    stereo_r29_wrapper_rel,
    '#include "stereo_renderer_r26.cpp"',
    '#include "vr/game/render_semantics.hpp"',
    '#include "stereo_renderer_r29_overlay.inc"',
)
if "namespace OutRunVRRenderer" in stereo_r29_wrapper or "namespace OutRunVRStereo" in stereo_r29_wrapper:
    raise SystemExit("Stereo R29 compatibility wrapper regained implementation body")
if "#include" in stereo_r29_overlay:
    raise SystemExit("Stereo R29 overlay must remain include-free")
require(
    stereo_r29_overlay,
    stereo_r29_overlay_rel,
    "namespace OutRunVRRenderer",
    "R29InvalidateRawWvpGeneration",
    "namespace OutRunVRStereo",
    "R29StableStereoBase",
    "R29FragileEffectCached",
    "R29MonoSafetyThroughEpoch",
    "VR R29 PERF: stable main-backbuffer draws now execute LEFT+RIGHT only",
)

require_order(
    stereo_r30_wrapper,
    stereo_r30_wrapper_rel,
    '#include "stereo_renderer_r29.cpp"',
    "#include <d3dcompiler.h>",
    "#include <algorithm>",
    "#include <array>",
    "#include <memory>",
    "#include <mutex>",
    "#include <unordered_map>",
    "#include <vector>",
    '#include "stereo_renderer_r30_overlay.inc"',
)
if "namespace Settings" in stereo_r30_wrapper or "namespace OutRunVRStereo" in stereo_r30_wrapper:
    raise SystemExit("R30 compatibility wrapper regained implementation body")
if "#include" in stereo_r30_overlay:
    raise SystemExit("R30 overlay must remain include-free")
require(
    stereo_r30_overlay,
    stereo_r30_overlay_rel,
    "namespace Settings",
    "VRHudScale",
    "namespace OutRunVRStereo",
    "R30DrawPrimitiveR29Hook",
    "state.depthTestEnabled &&",
    "state.rhwDepthEvidence",
    "R30CompositeSkyGlowBeforeHud",
    "VR R30 HUD: ScreenSpace2D correction READY",
)

require_order(
    stereo_r31_wrapper,
    stereo_r31_wrapper_rel,
    '#include "stereo_renderer_r30.cpp"',
    '#include "stereo_renderer_r31_overlay.inc"',
)
if "namespace OutRunVRStereo" in stereo_r31_wrapper:
    raise SystemExit("R31 compatibility wrapper regained implementation body")
if "#include" in stereo_r31_overlay:
    raise SystemExit("R31 overlay must remain include-free")
require(
    stereo_r31_overlay,
    stereo_r31_overlay_rel,
    "namespace OutRunVRStereo",
    "R31StateBlockTrackingReliable",
    "GetR28VerifiedProjection",
    "R31 fast left-eye c64 rollback",
    "R31 HUD left-eye c64 rollback",
    "R31StateBlockResyncPending",
    "R31FlushPendingStateBlockResync",
    "VR R31 PERF: cached world stereo + draw-route telemetry READY",
)

require_order(
    stereo_r32_wrapper,
    stereo_r32_wrapper_rel,
    '#include "r32_policy.hpp"',
    '#include "stereo_renderer_r31.cpp"',
    '#include "stereo_renderer_r32_overlay.inc"',
)
if "namespace OutRunVRStereo" in stereo_r32_wrapper:
    raise SystemExit("R32 compatibility wrapper regained implementation body")
if "#include" in stereo_r32_overlay:
    raise SystemExit("R32 overlay must remain include-free")
require(
    stereo_r32_overlay,
    stereo_r32_overlay_rel,
    "namespace OutRunVRStereo",
    "R32ResetR22Hook",
    "R32ResetAfterGameReset",
    "R32SetWvpBatch",
    "R32WaitProducerFence",
    "R32DrainPendingProducerFence",
    "R32ProducerFencePending",
    "draw is forced to stock-WVP zero disparity",
    "VR R32 REVIEW2",
)

require_order(
    stereo_r33_wrapper,
    stereo_r33_wrapper_rel,
    '#include "stereo_renderer_r32.cpp"',
    '#include "stereo_renderer_r33_overlay.inc"',
)
if "namespace OutRunVRStereo" in stereo_r33_wrapper:
    raise SystemExit("R33 compatibility wrapper regained implementation body")
if "#include" in stereo_r33_overlay:
    raise SystemExit("R33 overlay must remain include-free")
require(
    stereo_r33_overlay,
    stereo_r33_overlay_rel,
    "namespace OutRunVRStereo",
    "R31OwnedResult R33TryFastWorld",
    "R31OwnedResult R33TryHud",
    "R32LowerFailClosed",
    "R30DrawPrimitiveR29Hook",
    "R33ResetR32Hook.stdcall<HRESULT>",
    "top-level telemetry counted once",
)

require_order(
    stereo_r34_wrapper,
    stereo_r34_wrapper_rel,
    '#include "stereo_renderer_r33.cpp"',
    '#include "vr/game/render_semantics.hpp"',
    "namespace OutRunVRD3D9ExUpgradeR13",
    '#include "stereo_renderer_r34_overlay.inc"',
)
if "namespace OutRunVRStereo" in stereo_r34_wrapper:
    raise SystemExit("R34 compatibility wrapper regained implementation body")
if "#include" in stereo_r34_overlay:
    raise SystemExit("R34 overlay must remain include-free")
require(
    stereo_r34_overlay,
    stereo_r34_overlay_rel,
    "namespace OutRunVRStereo",
    "R34ResetReplayBlocked",
    "LastResetStateReplaySucceeded",
    "Present/pre",
    "R34PresentR33Hook.stdcall<HRESULT>",
    "stereo remains fail-closed",
)
# F04 closure floor: the production facade intentionally bottoms out at the
# canonical R9/R7 renderer. Historical R13-R34 wrappers remain available only
# to compatibility/diagnostic paths and must never re-enter the default branch.
require(
    stereo_base,
    stereo_base_rel,
    '#include "stereo_renderer_r7.inc"',
    'R9BuildId',
    'R9InstallState',
    'R9PresentCallbackHook',
)
if stereo_base.count('#include "stereo_renderer_r7.inc"') != 1:
    raise SystemExit("canonical stereo base must include stereo_renderer_r7.inc exactly once")
for stale_base_owner in (
    '#include "stereo_renderer_r13.cpp"',
    '#include "stereo_renderer_r20.cpp"',
    '#include "stereo_renderer_r21.cpp"',
    '#include "stereo_renderer_r22.cpp"',
    '#include "stereo_renderer_r23.cpp"',
    '#include "stereo_renderer_r26.cpp"',
    '#include "stereo_renderer_r29.cpp"',
    '#include "stereo_renderer_r30.cpp"',
    '#include "stereo_renderer_r31.cpp"',
    '#include "stereo_renderer_r32.cpp"',
    '#include "stereo_renderer_r33.cpp"',
    '#include "stereo_renderer_r34.cpp"',
):
    if stale_base_owner in stereo_base:
        raise SystemExit(
            f"canonical stereo base regressed to historical wrapper inclusion: {stale_base_owner}"
        )

production_marker = '#else\n#include "r32_policy.hpp"'
production_start = stereo_facade.find(production_marker)
production_end = stereo_facade.rfind("#endif")
if production_start < 0 or production_end <= production_start:
    raise SystemExit("could not isolate production stereo facade branch")
production_stereo = stereo_facade[production_start:production_end]
if production_stereo.count('#include "stereo_renderer.cpp"') != 1:
    raise SystemExit("production stereo facade must include canonical stereo_renderer.cpp exactly once")
for diagnostic_owner in (
    '#include "stereo_renderer_r26_compare.cpp"',
    '#include "stereo_renderer_r29_c1_compare.cpp"',
    '#include "stereo_renderer_r30_c2_compare.cpp"',
    '#include "stereo_renderer_r30_r26_safe.cpp"',
):
    if diagnostic_owner in production_stereo:
        raise SystemExit(
            f"production stereo facade leaked diagnostic comparison owner: {diagnostic_owner}"
        )

for stale_stereo_owner in (
    '#include "stereo_renderer_r13.cpp"',
    '#include "stereo_renderer_r20.cpp"',
    '#include "stereo_renderer_r21.cpp"',
    '#include "stereo_renderer_r22.cpp"',
    '#include "stereo_renderer_r23.cpp"',
    '#include "stereo_renderer_r26.cpp"',
    '#include "stereo_renderer_r29.cpp"',
    '#include "stereo_renderer_r30.cpp"',
    '#include "stereo_renderer_r31.cpp"',
    '#include "stereo_renderer_r32.cpp"',
    '#include "stereo_renderer_r33.cpp"',
    '#include "stereo_renderer_r34.cpp"',
):
    if stale_stereo_owner in stereo_facade:
        raise SystemExit(
            f"production stereo facade regressed to historical wrapper inclusion: {stale_stereo_owner}"
        )
require_order(
    stereo_facade,
    stereo_facade_rel,
    '#include "stereo_renderer_r26_compare.cpp"',
    '#include "stereo_renderer_r29_c1_compare.cpp"',
    '#include "stereo_renderer_r30_c2_compare.cpp"',
    '#include "stereo_renderer_r30_r26_safe.cpp"',
    '#include "r32_policy.hpp"',
    '#include "r13_bridge.hpp"',
    '#include "stereo_renderer.cpp"',
    '#include "stereo_renderer_r13_overlay.inc"',
    '#include "../runtime_eligibility.hpp"',
    '#include "stereo_renderer_r20_overlay.inc"',
    '#include "stereo_renderer_r21_overlay.inc"',
    '#include "stereo_renderer_r22_overlay.inc"',
    '#include "stereo_renderer_r23_overlay.inc"',
    '#include "shader_fingerprint_gpl.hpp"',
    '#include "../game/render_semantics.hpp"',
    '#include "stereo_renderer_r26_overlay.inc"',
    '#include "stereo_renderer_r29_overlay.inc"',
    "#include <d3dcompiler.h>",
    "#include <algorithm>",
    "#include <array>",
    "#include <memory>",
    "#include <mutex>",
    "#include <unordered_map>",
    "#include <vector>",
    '#include "stereo_renderer_r30_overlay.inc"',
    '#include "stereo_renderer_r31_overlay.inc"',
    '#include "stereo_renderer_r32_overlay.inc"',
    '#include "stereo_renderer_r33_overlay.inc"',
    "namespace OutRunVRD3D9ExUpgradeR13",
    '#include "stereo_renderer_r34_overlay.inc"',
)

r13_bridge_pos = stereo_facade.find('#include "r13_bridge.hpp"')
r9_base_pos = stereo_facade.find('#include "stereo_renderer.cpp"')
r13_overlay_pos = stereo_facade.find('#include "stereo_renderer_r13_overlay.inc"')
r20_runtime_pos = stereo_facade.find('#include "../runtime_eligibility.hpp"', r13_overlay_pos)
r20_overlay_pos = stereo_facade.find('#include "stereo_renderer_r20_overlay.inc"')
r21_overlay_pos = stereo_facade.find('#include "stereo_renderer_r21_overlay.inc"')
r22_overlay_pos = stereo_facade.find('#include "stereo_renderer_r22_overlay.inc"')
r23_overlay_pos = stereo_facade.find('#include "stereo_renderer_r23_overlay.inc"')
r26_semantics_pos = stereo_facade.find('#include "../game/render_semantics.hpp"', r23_overlay_pos)
r26_overlay_pos = stereo_facade.find('#include "stereo_renderer_r26_overlay.inc"')
r29_semantics_pos = stereo_facade.find('#include "vr/game/render_semantics.hpp"', r26_overlay_pos)
r29_overlay_pos = stereo_facade.find('#include "stereo_renderer_r29_overlay.inc"')
r33_overlay_pos = stereo_facade.find('#include "stereo_renderer_r33_overlay.inc"')
r34_semantics_pos = stereo_facade.rfind('#include "vr/game/render_semantics.hpp"')
r34_namespace_pos = stereo_facade.find("namespace OutRunVRD3D9ExUpgradeR13")
if min(r13_bridge_pos, r9_base_pos, r13_overlay_pos, r20_runtime_pos, r20_overlay_pos,
       r21_overlay_pos, r22_overlay_pos, r23_overlay_pos, r26_semantics_pos,
       r26_overlay_pos, r29_semantics_pos, r29_overlay_pos, r33_overlay_pos,
       r34_semantics_pos, r34_namespace_pos) < 0:
    raise SystemExit("production stereo facade semantic include boundary missing")
if not (r13_bridge_pos < r9_base_pos < r13_overlay_pos < r20_runtime_pos < r20_overlay_pos < r21_overlay_pos < r22_overlay_pos < r23_overlay_pos < r26_semantics_pos < r26_overlay_pos):
    raise SystemExit("R13/R20/R21/R22/R23/R26 production ownership boundary moved outside r13_bridge -> R9 base -> R13 -> runtime eligibility -> R20 -> R21 -> R22 -> R23 -> R26 order")
if not (r26_overlay_pos < r29_semantics_pos < r29_overlay_pos):
    raise SystemExit("R29 semantic prelude moved outside the R26 -> R29 overlay boundary")
if not (r33_overlay_pos < r34_semantics_pos < r34_namespace_pos):
    raise SystemExit("R34 render-semantics include moved outside the R33 -> R34 boundary")
if stereo_facade.count('#include "vr/game/render_semantics.hpp"') < 2:
    raise SystemExit("production stereo facade lost one of the historical semantic include boundaries")

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
        "src/vr/d3d9/stereo_renderer_r34.cpp",
        "src/vr/d3d9/ex_device_pipeline.cpp",
        "src/vr/d3d9/stereo_pipeline.cpp",
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
    "'src/vr/d3d9/stereo_renderer_r13_overlay.inc' = @(",
    "R13InstallState",
    "R13OverlayReady",
    "R13EnsureAckState",
    "R13ForceMonoShadow",
    "single-execution MRT/occlusion fallback",
    "'src/vr/d3d9/stereo_renderer_r20_overlay.inc' = @(",
    "R20InstallState",
    "R20StereoEligibilityGate",
    "R20DepthHistorySafeForInitialSeed",
    "R20AcceptVerifiedBaseline",
    "'src/vr/d3d9/stereo_renderer_r21_overlay.inc' = @(",
    "R21InstallState",
    "R21HostStatus::SoftSuspend",
    "R21ApplyHostFailClosedAtPresent",
    "without baseline reset",
    "'src/vr/d3d9/stereo_renderer_r22_overlay.inc' = @(",
    "R22InstallState",
    "R22ShadowState",
    "R22StateBlockTrackingReliable",
    "R22PrimeShadowState",
    "per-draw GetViewport/GetScissorRect/GetRenderState eliminated",
    "'src/vr/d3d9/stereo_renderer_r23_overlay.inc' = @(",
    "R23InstallState",
    "R23CaptureActualGameState",
    "authoritative first seed",
    "'src/vr/d3d9/stereo_renderer_r26_overlay.inc' = @(",
    "R26InstallState",
    "R37DepthDisabledFragileOverlay",
    "unknown state fails closed",
    "'src/vr/d3d9/stereo_renderer_r29_overlay.inc' = @(",
    "R29StableStereoBase",
    "R29FragileEffectCached",
    "R29MonoSafetyThroughEpoch",
    "'src/vr/d3d9/stereo_renderer_r30_overlay.inc' = @(",
    "R30DrawPrimitiveR29Hook",
    "state.depthTestEnabled &&",
    "state.rhwDepthEvidence",
    "'src/vr/d3d9/stereo_renderer_r31_overlay.inc' = @(",
    "R31StateBlockTrackingReliable",
    "GetR28VerifiedProjection",
    "R31 fast left-eye c64 rollback",
    "'src/vr/d3d9/stereo_renderer_r32_overlay.inc' = @(",
    "R32ResetR22Hook",
    "R32WaitProducerFence",
    "VR R32 REVIEW2",
    "'src/vr/d3d9/stereo_renderer_r33_overlay.inc' = @(",
    "R31OwnedResult R33TryFastWorld",
    "R33ResetR32Hook.stdcall<HRESULT>",
    "'src/vr/d3d9/stereo_renderer_r34_overlay.inc' = @(",
    "R34ResetReplayBlocked",
    "LastResetStateReplaySucceeded",
    "stereo remains fail-closed",
)
for stale_guard in (
    "'src/vr/game/outrun_renderer_r13.cpp' = @(",
    "'src/vr/game/outrun_renderer_r23.cpp' = @(",
    "'src/vr/d3d9/ex_device_upgrade_r13.cpp' = @(",
    "'src/vr/d3d9/ex_device_upgrade_r14.cpp' = @(",
    "'src/vr/d3d9/ex_device_upgrade_r15.cpp' = @(",
    "'src/vr/d3d9/stereo_renderer_r13.cpp' = @(",
    "'src/vr/d3d9/stereo_renderer_r20.cpp' = @(",
    "'src/vr/d3d9/stereo_renderer_r21.cpp' = @(",
    "'src/vr/d3d9/stereo_renderer_r22.cpp' = @(",
    "'src/vr/d3d9/stereo_renderer_r23.cpp' = @(",
    "'src/vr/d3d9/stereo_renderer_r26.cpp' = @(",
    "'src/vr/d3d9/stereo_renderer_r29.cpp' = @(",
    "'src/vr/d3d9/stereo_renderer_r30.cpp' = @(",
    "'src/vr/d3d9/stereo_renderer_r31.cpp' = @(",
    "'src/vr/d3d9/stereo_renderer_r32.cpp' = @(",
    "'src/vr/d3d9/stereo_renderer_r33.cpp' = @(",
    "'src/vr/d3d9/stereo_renderer_r34.cpp' = @(",
):
    if stale_guard in openxr_workflow:
        raise SystemExit(
            f"OpenXR hardening guard regressed to compatibility wrapper: {stale_guard}"
        )

print("VR facade modularization F04 phase 18 closure: PASS")
