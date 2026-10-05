#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]

R7_PATH = ROOT / "src/vr/d3d9/stereo_renderer_r7.inc"
R13_PATH = ROOT / "src/vr/d3d9/stereo_renderer_r13.cpp"
R22_PATH = ROOT / "src/vr/d3d9/stereo_renderer_r22.cpp"
R32_PATH = ROOT / "src/vr/d3d9/stereo_renderer_r32.cpp"
HOST_CACHE_PATH = ROOT / "vrhost/src/runtime/d3d9ex_direct_passthrough_r32.hpp"
HOST_PASSTHROUGH_PATH = ROOT / "vrhost/src/runtime/d3d9ex_direct_passthrough.hpp"
HOST_R23_RUNTIME_PATH = ROOT / "vrhost/src/runtime/r23_runtime_hardening.hpp"
HOST_R24_PATH = ROOT / "vrhost/src/runtime/r24_black_screen_guard.hpp"
HOST_SUBMIT_PATH = ROOT / "vrhost/src/runtime/r32_direct_submit.hpp"


def load(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        print(
            f"DX9Ex reset/transport contract missing "
            f"{path.relative_to(ROOT)}: {exc}",
            file=sys.stderr,
        )
        raise SystemExit(1)


def fail(message: str) -> None:
    print(f"DX9Ex reset/transport contract FAILED: {message}", file=sys.stderr)
    raise SystemExit(1)


def body(source: str, marker: str) -> str:
    start = source.find(marker)
    if start < 0:
        fail(f"missing function marker: {marker}")
    brace = source.find("{", start)
    if brace < 0:
        fail(f"missing body for: {marker}")
    depth = 0
    for index in range(brace, len(source)):
        ch = source[index]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    fail(f"unterminated body for: {marker}")
    return ""


def require(source: str, label: str, *markers: str) -> None:
    for marker in markers:
        if marker not in source:
            fail(f"{label} missing: {marker}")


def forbid(source: str, label: str, *markers: str) -> None:
    for marker in markers:
        if marker in source:
            fail(f"{label} regained forbidden marker: {marker}")


def require_order(source: str, label: str, *markers: str) -> None:
    positions = [source.find(marker) for marker in markers]
    if min(positions) < 0:
        missing = [marker for marker, pos in zip(markers, positions) if pos < 0]
        fail(f"{label} missing ordered markers: {missing}")
    if positions != sorted(positions):
        fail(f"{label} order changed: {markers}")


r7 = load(R7_PATH)
r13 = load(R13_PATH)
r22 = load(R22_PATH)
r32 = load(R32_PATH)
host_cache = load(HOST_CACHE_PATH)
host_passthrough = load(HOST_PASSTHROUGH_PATH)
host_r23_runtime = load(HOST_R23_RUNTIME_PATH)
host_r24 = load(HOST_R24_PATH)
host_submit = load(HOST_SUBMIT_PATH)

# Reset must tear down every D3D9 DEFAULT-pool stereo/shared-eye/probe object
# before ResetEx. Preserve the generation counter itself so the next recreated
# ring cannot publish the same generation with new handles.
retire_probe = body(r7, "void RetireDirectInteropProbePublication() noexcept")
require_order(
    retire_probe,
    "D3D9 interop probe publication owner",
    "clientInteropProbeToken),0)",
    "clientInteropProbeHandle),0)",
)

release_probe = body(r7, "void ReleaseDirectInteropProbe() noexcept")
require_order(
    release_probe,
    "D3D9 interop probe teardown owner",
    "RetireDirectInteropProbePublication();",
    "ReleaseCom(DirectInteropProbeFence)",
    "ReleaseCom(DirectInteropProbeSurface)",
    "ReleaseCom(DirectInteropProbeTexture)",
    "DirectInteropProbeHandle=nullptr",
    "DirectInteropProbeToken=0",
    "DirectInteropVerified=false",
)

ensure_probe = body(r7, "bool EnsureDirectInteropProbe(IDirect3DDevice9* device)")
failure_pos = ensure_probe.find("++DirectInteropProbeFailures;")
release_pos = ensure_probe.find("ReleaseDirectInteropProbe();", failure_pos)
if failure_pos < 0 or release_pos < 0 or release_pos < failure_pos:
    fail("interop probe creation failure must route through teardown owner")
for marker in (
    "ReleaseCom(DirectInteropProbeFence)",
    "ReleaseCom(DirectInteropProbeSurface)",
    "ReleaseCom(DirectInteropProbeTexture)",
    "DirectInteropProbeHandle=nullptr",
    "DirectInteropProbeToken=0",
    "DirectInteropVerified=false",
):
    if marker in ensure_probe:
        fail(f"interop probe creation failure regained duplicate teardown: {marker}")


slot_release = body(r7, "void ReleaseDirectTransportSlotObjects() noexcept")
require(
    slot_release,
    "DirectGPU slot teardown owner",
    "ReleaseCom(slot.fence)",
    "ReleaseCom(slot.leftSurface)",
    "ReleaseCom(slot.leftTexture)",
    "ReleaseCom(slot.rightSurface)",
    "ReleaseCom(slot.rightTexture)",
    "slot={};",
)
for marker in (
    "ReleaseCom(slot.fence)",
    "ReleaseCom(slot.leftSurface)",
    "ReleaseCom(slot.leftTexture)",
    "ReleaseCom(slot.rightSurface)",
    "ReleaseCom(slot.rightTexture)",
):
    if r7.count(marker) != 1:
        fail(f"DirectGPU slot COM teardown must have one physical owner: {marker}")

retire_frames = body(r7, "void RetireDirectTransportFramePublications() noexcept")
require(
    retire_frames,
    "DirectGPU Frame.v2 retirement owner",
    "RenderFrameRingClaimed",
    "RenderFrameRing->publishSequence",
    "frame.sequence",
    "RenderFrameRunGenerationIndex",
    "RenderFrameDirectGpuTransport",
    "frame.frameId=0",
    "RenderFrameDirectLeftHandleIndex",
    "RenderFrameDirectRightHandleIndex",
    "RenderFrameDirectWidthIndex",
    "RenderFrameDirectHeightIndex",
    "RenderFrameDirectFormatIndex",
    "RenderFrameDirectGenerationIndex",
    "RenderFrameDirectSlotIndex",
)
if r7.count("RetireDirectTransportFramePublications();") != 2:
    fail("DirectGPU Frame.v2 retirement must be owned by both stereo-resource and direct-slot teardown wrappers")

release = body(r7, "void ReleaseStereoResources()")
require(
    release,
    "D3D9 reset resource release",
    "StereoResourcesReady=false;",
    "RetireDirectTransportFramePublications();",
    "DirectTransportResourcesReady=false;",
    "ReleaseDirectTransportSlotObjects();",
    "ReleaseDirectInteropProbe();",
    "DirectTransportFormat=D3DFMT_UNKNOWN",
)
require_order(
    release,
    "D3D9 reset DirectGPU publication retirement",
    "StereoResourcesReady=false;",
    "RetireDirectTransportFramePublications();",
    "DirectTransportResourcesReady=false;",
    "ReleaseDirectTransportSlotObjects();",
)
forbid(
    release,
    "reset path duplicate DirectGPU slot teardown ownership",
    "ReleaseCom(slot.fence)",
    "ReleaseCom(slot.leftSurface)",
    "ReleaseCom(slot.leftTexture)",
    "ReleaseCom(slot.rightSurface)",
    "ReleaseCom(slot.rightTexture)",
)
require_order(
    release,
    "D3D9 interop probe teardown routing",
    "ReleaseDirectInteropProbe();",
    "DirectTransportFormat=D3DFMT_UNKNOWN",
)
forbid(
    release,
    "reset path duplicate interop teardown ownership",
    "clientInteropProbeToken",
    "clientInteropProbeHandle",
    "ReleaseCom(DirectInteropProbeFence)",
    "ReleaseCom(DirectInteropProbeSurface)",
    "ReleaseCom(DirectInteropProbeTexture)",
    "DirectInteropProbeHandle=nullptr",
    "DirectInteropProbeToken=0",
    "DirectInteropVerified=false",
)
forbid(
    release,
    "monotonic DirectGPU generation across reset",
    "DirectTransportGeneration=0",
    "DirectTransportGeneration = 0",
)

release_slots = body(r7, "void ReleaseDirectTransportSlots()")
require_order(
    release_slots,
    "DirectGPU slot publication retirement and metadata reset",
    "RetireDirectTransportFramePublications();",
    "DirectTransportResourcesReady=false",
    "DirectTransportWidth=0",
    "DirectTransportHeight=0",
    "ReleaseDirectTransportSlotObjects();",
)
forbid(
    release_slots,
    "DirectGPU slot teardown wrapper duplicate COM ownership",
    "ReleaseCom(slot.fence)",
    "ReleaseCom(slot.leftSurface)",
    "ReleaseCom(slot.leftTexture)",
    "ReleaseCom(slot.rightSurface)",
    "ReleaseCom(slot.rightTexture)",
)

# The next ring recreation must bump generation before it becomes ready. The
# host cache key includes this generation plus both handles and dimensions.
ensure = body(r7, "bool EnsureDirectTransportResources(IDirect3DDevice9* device)")
require(
    ensure,
    "DirectGPU ring recreation",
    "if(DirectTransportResourcesReady&&DirectTransportWidth==targetWidth&&DirectTransportHeight==targetHeight)return true",
    "if(DirectTransportResourcesReady)ReleaseDirectTransportSlots()",
    "if(!DirectTransportGeneration)DirectTransportGeneration=RenderFrameRunGeneration",
    "if(++DirectTransportGeneration==0)++DirectTransportGeneration",
    "DirectTransportResourcesReady=true",
)
require_order(
    ensure,
    "DirectGPU generation publication",
    "if(DirectTransportResourcesReady)ReleaseDirectTransportSlots()",
    "for(auto&slot:DirectTransportSlots)",
    "if(!DirectTransportGeneration)DirectTransportGeneration=RenderFrameRunGeneration",
    "if(++DirectTransportGeneration==0)++DirectTransportGeneration",
    "DirectTransportResourcesReady=true",
)

claim_run = body(r7, "bool ClaimRenderFrameRingForCurrentRun() noexcept")
require(
    claim_run,
    "Frame.v2 cross-run legacy ACK reset",
    "EnsureSharedState()",
    "hostDirectConsumedFrameId",
    "InterlockedExchange(",
    "RenderFrameRingClaimed = true;",
)
require_order(
    claim_run,
    "Frame.v2 run claim legacy ACK reset ordering",
    "RenderFrameRing->reserved0 = RenderFrameRunGeneration;",
    "hostDirectConsumedFrameId",
    "RenderFrameRingClaimed = true;",
)

# R13 is the lower reset/resource owner. It releases shared resources and
# publishes a disabled frame before ResetEx; recreation occurs only on success.
reset_pre = body(r13, "void R13ResetCommonPre(IDirect3DDevice9*)")
require_order(
    reset_pre,
    "R13 reset preamble",
    "OutRunVRRenderer::NotifyGameReset();",
    "ReleaseStereoResources();",
    "PublishStereoState(OutRunVR::StereoDisabled",
    "PublishRenderFrame(OutRunVR::StereoDisabled",
)
reset_r13 = body(r13, "HRESULT __stdcall ResetDestR13(")
require_order(
    reset_r13,
    "R13 ResetEx ownership",
    "R13ResetCommonPre(device);",
    "ResetCompatDevice(device, params, hr)",
    "if (SUCCEEDED(hr))",
    "EnsureStereoResources(device)",
)

# Upper reset owners must fail close before calling down and only re-prime/rearm
# state after the lower reset succeeds.
reset_r22 = body(r22, "HRESULT __stdcall ResetDestR22(")
require_order(
    reset_r22,
    "R22 reset fail-close",
    "R22FailClosedEligibility();",
    "R22ResetBaselineTracking();",
    "R22ShadowState = {};",
    "R22ResetR13Hook.stdcall<HRESULT>",
    "if (gameDevice && SUCCEEDED(hr))",
    "R22PrimeShadowState(device)",
)

invalidate_direct_r32 = body(
    r32, "void R32InvalidateDirectInteropOnly() noexcept")
require(
    invalidate_direct_r32,
    "R32 host-identity interop invalidation",
    "R32ClearPendingProducerFences();",
    "ReleaseDirectTransportSlots();",
    "ReleaseDirectInteropProbe();",
    "R32ForgetDirectIdentity();",
)
require_order(
    invalidate_direct_r32,
    "R32 interop probe teardown routing",
    "ReleaseDirectInteropProbe();",
    "R32ForgetDirectIdentity();",
)
forbid(
    invalidate_direct_r32,
    "R32 duplicate interop teardown ownership",
    "clientInteropProbeToken",
    "clientInteropProbeHandle",
    "ReleaseCom(DirectInteropProbeFence);",
    "ReleaseCom(DirectInteropProbeSurface);",
    "ReleaseCom(DirectInteropProbeTexture);",
    "DirectInteropProbeHandle = nullptr;",
    "DirectInteropProbeToken = 0;",
    "DirectInteropVerified = false;",
)

invalidate_r32 = body(r32, "void R32InvalidateResetCaches() noexcept")
require(
    invalidate_r32,
    "R32 reset identity invalidation",
    "R32ForgetDirectIdentity();",
    "R32ClearPendingProducerFences();",
    "R32DirectCopyPathRejected = false;",
    "R32DirectCopyRejectHr = D3D_OK;",
)
reset_r32 = body(r32, "HRESULT __stdcall ResetDestR32(")
require_order(
    reset_r32,
    "R32 reset lifecycle",
    "if (gameDevice)",
    "R32ClearPendingProducerFences();",
    "R32ResetR22Hook.stdcall<HRESULT>",
    "if (SUCCEEDED(hr))",
    "R32ResetAfterGameReset();",
)
require(
    reset_r32,
    "R32 failed-reset cleanup",
    "R32InvalidateResetCaches();",
    "++R32ResetFailures;",
)

# Production R23 completion must update both ACK contracts. R13/R32 use the
# generation-scoped per-slot mapping, while the lower R7 fallback still consumes
# SharedPose.hostDirectConsumedFrameId. Keep the legacy bridge monotonic so late
# async completions cannot move the global ACK backwards.
require(
    load(ROOT / "src/vr/ipc/direct_ack_r13.hpp"),
    "dedicated ACK complete run-identity ABI fields",
    "DirectGpuAckRunGenerationIndex = 0",
    "DirectGpuAckGamePidIndex = 1",
    "std::uint32_t reserved[2]",
    "static_assert(sizeof(DirectGpuAckState) == 48)",
)
ensure_pose_host = body(host_passthrough, "inline bool EnsurePoseState() noexcept")
require(
    ensure_pose_host,
    "host writable legacy ACK mapping",
    "FILE_MAP_ALL_ACCESS",
    "OutRunVR::SharedMemoryName",
)
legacy_ack = body(host_passthrough, "inline void PublishLegacyConsumedFrame(")
require(
    legacy_ack,
    "host legacy global ACK bridge",
    "hostDirectConsumedFrameId",
    "GetCurrentProcessId()",
    "EnsureFrameRing()",
    "RenderFrameRunIdentityMatches(*FrameRing, frame)",
    "LegacyFrameAtOrAfter",
    "InterlockedCompareExchange",
)
require_order(
    legacy_ack,
    "legacy ACK live-run identity guard",
    "EnsureFrameRing()",
    "RenderFrameRunIdentityMatches(*FrameRing, frame)",
    "hostDirectConsumedFrameId",
    "InterlockedCompareExchange",
)
publish_completed = body(host_passthrough, "inline bool PublishCompletedFrame(")
require(
    publish_completed,
    "host dedicated ACK live-run identity guard",
    "EnsureFrameRing()",
    "RenderFrameRunIdentityMatches(*FrameRing, frame)",
    "EnsureDirectAckState()",
)
require_order(
    publish_completed,
    "host live-run guard before dedicated ACK write",
    "EnsureFrameRing()",
    "RenderFrameRunIdentityMatches(*FrameRing, frame)",
    "EnsureDirectAckState()",
    "BeginAckWrite();",
    "DirectAckState->completedFrameId[slot] = frame.frameId;",
)
require(
    publish_completed,
    "host dedicated ACK complete game-run scope",
    "RenderFrameRunGenerationIndex",
    "DirectGpuAckRunGenerationIndex",
    "DirectGpuAckGamePidIndex",
    "runGeneration",
    "gamePid",
)
require_order(
    publish_completed,
    "host dedicated ACK complete game-run publication",
    "const std::uint32_t runGeneration",
    "const std::uint32_t gamePid = frame.clientPid;",
    "BeginAckWrite();",
    "DirectGpuAckRunGenerationIndex] = runGeneration;",
    "DirectGpuAckGamePidIndex] = gamePid;",
    "DirectAckState->completedFrameId[slot] = frame.frameId;",
    "EndAckWrite();",
)
require_order(
    publish_completed,
    "host dual ACK publication",
    "DirectAckState->completedFrameId[slot] = frame.frameId;",
    "EndAckWrite();",
    "PublishLegacyConsumedFrame(frame);",
    "return true;",
)

# The game may only accept a dedicated ACK that belongs to its current Frame.v2
# game run as well as the current DirectGPU resource generation. This closes the
# remaining race where an old host completion lands after a fast game restart.
read_gpu_ack = body(r13, "bool R13ReadGpuCompletedFrame(")
require(
    read_gpu_ack,
    "game dedicated ACK complete run-identity validation",
    "DirectGpuAckRunGenerationIndex",
    "DirectGpuAckGamePidIndex",
    "RenderFrameRunGeneration",
    "GetCurrentProcessId()",
    "snapshot.transportGeneration != DirectTransportGeneration",
)
require_order(
    read_gpu_ack,
    "game dedicated ACK identity validation",
    "snapshot.hostPid != SharedState->hostPid",
    "snapshot.transportGeneration != DirectTransportGeneration",
    "!RenderFrameRunGeneration",
    "DirectGpuAckRunGenerationIndex",
    "DirectGpuAckGamePidIndex",
    "GetCurrentProcessId()",
    "completedFrame = snapshot.completedFrameId[slotIndex];",
)

# Host-owned SafeEye fallback cache must also be scoped to the complete
# Frame.v2 game-run identity. Keep one owner predicate for cache identity so
# legacy/R32 ensure paths and R23/R24 direct consumers cannot drift apart.
reset_safe_eyes = body(host_passthrough, "inline void ResetSafeEyes() noexcept")
require(
    reset_safe_eyes,
    "SafeEye complete identity reset",
    "SafeFrameId = 0;",
    "SafeTransportGeneration = 0;",
    "SafeRunGeneration = 0;",
    "SafeGamePid = 0;",
)

safe_eye_owner = body(host_passthrough, "inline bool SafeEyesOwnFrame(")
require(
    safe_eye_owner,
    "SafeEye owner complete run identity",
    "RenderFrameDirectGenerationIndex",
    "RenderFrameRunGenerationIndex",
    "const std::uint32_t gamePid = frame.clientPid;",
    "frame.frameId != 0",
    "generation != 0",
    "runGeneration != 0",
    "gamePid != 0",
    "SafeFrameId == frame.frameId",
    "SafeTransportGeneration == generation",
    "SafeRunGeneration == runGeneration",
    "SafeGamePid == gamePid",
    "SafeEyeSrv[0] && SafeEyeSrv[1]",
)

copy_safe = body(host_passthrough, "inline bool CopySharedFrameToSafeEyes(")
require_order(
    copy_safe,
    "SafeEye complete identity publication",
    "PublishCompletedFrame(frame)",
    "SafeFrameId = frame.frameId;",
    "RenderFrameDirectGenerationIndex",
    "SafeRunGeneration =",
    "RenderFrameRunGenerationIndex",
    "SafeGamePid = frame.clientPid;",
)

ensure_safe = body(host_passthrough, "inline bool EnsureSafeFrame(")
require(
    ensure_safe,
    "legacy SafeEye owner delegation",
    "if (SafeEyesOwnFrame(frame))",
    "return true;",
    "CopySharedFrameToSafeEyes(frame)",
)
forbid(
    ensure_safe,
    "legacy SafeEye identity duplication",
    "SafeFrameId ==",
    "SafeTransportGeneration ==",
    "SafeRunGeneration ==",
    "SafeGamePid ==",
)

r23_direct = body(host_r23_runtime, "inline XrResult RenderCommittedDirect(")
require(
    r23_direct,
    "R23 SafeEye owner delegation",
    "const bool safeAlreadyOwned = SafeEyesOwnFrame(frame);",
    "if (!safeAlreadyOwned && !EnsureSafeFrame(frame.frameId))",
)
forbid(
    r23_direct,
    "R23 SafeEye identity duplication",
    "SafeFrameId ==",
    "SafeTransportGeneration ==",
    "SafeRunGeneration ==",
    "SafeGamePid ==",
)

r24_direct = body(host_r24, "inline bool TryBuildDirectSafeProjection(")
require(
    r24_direct,
    "R24 SafeEye owner delegation",
    "const bool safeAlreadyOwned = SafeEyesOwnFrame(snapshot.frame);",
    "if (!safeAlreadyOwned && !EnsureSafeFrame(snapshot.frameId))",
)
forbid(
    r24_direct,
    "R24 SafeEye identity duplication",
    "SafeFrameId ==",
    "SafeTransportGeneration ==",
    "SafeRunGeneration ==",
    "SafeGamePid ==",
)

# Host opened-shared-resource caches must be scoped to the complete Frame.v2
# game run as well as resource generation and HANDLE values. Windows may recycle
# HANDLE numeric values after a fast producer-process restart.
open_slot = body(host_cache, "inline bool R32OpenSharedSlot(")
require(
    open_slot,
    "host shared-eye complete run cache identity",
    "RenderFrameRunGenerationIndex",
    "const std::uint32_t gamePid = frame.clientPid;",
    "cache.generation == generation",
    "cache.runGeneration == runGeneration",
    "cache.gamePid == gamePid",
    "cache.leftHandle == left && cache.rightHandle == right",
    "R32ReleaseSharedSlot(cache);",
    "OpenSharedResource(",
    "cache.generation = generation",
    "cache.runGeneration = runGeneration",
    "cache.gamePid = gamePid",
    "cache.leftHandle = left",
    "cache.rightHandle = right",
)
require_order(
    open_slot,
    "host shared-eye reopen with complete run identity",
    "const std::uint32_t generation",
    "const std::uint32_t runGeneration",
    "const std::uint32_t gamePid",
    "cache.generation == generation",
    "cache.runGeneration == runGeneration",
    "cache.gamePid == gamePid",
    "R32ReleaseSharedSlot(cache);",
    "OpenSharedResource(",
    "cache.generation = generation",
    "cache.runGeneration = runGeneration",
    "cache.gamePid = gamePid",
)

copy_safe_r32 = body(host_cache, "inline bool CopySharedFrameToSafeEyesR32(")
require_order(
    copy_safe_r32,
    "R32 SafeEye complete identity publication",
    "PublishCompletedFrame(frame)",
    "SafeFrameId = frame.frameId;",
    "SafeTransportGeneration =",
    "RenderFrameDirectGenerationIndex",
    "SafeRunGeneration =",
    "RenderFrameRunGenerationIndex",
    "SafeGamePid = frame.clientPid;",
)

ensure_safe_r32 = body(host_cache, "inline bool EnsureSafeFrameR32(")
require(
    ensure_safe_r32,
    "R32 SafeEye owner delegation",
    "if (SafeEyesOwnFrame(frame))",
    "return true;",
    "CopySharedFrameToSafeEyesR32(frame)",
)
forbid(
    ensure_safe_r32,
    "R32 SafeEye identity duplication",
    "SafeFrameId ==",
    "SafeTransportGeneration ==",
    "SafeRunGeneration ==",
    "SafeGamePid ==",
)

# Host ACK ownership may observe late completions from a pre-reset generation
# or a prior game run. Cache reuse, pending EVENT reuse and fault suppression
# must all be scoped to the complete Frame.v2 identity, not generation alone.
release_pending = body(host_submit, "inline void ReleasePending() noexcept")
require(
    release_pending,
    "host ACK identity reset",
    "AckFaultGeneration = 0;",
    "AckFaultRunGeneration = 0;",
    "AckFaultGamePid = 0;",
    "ActiveAckGeneration = 0;",
    "ActiveAckRunGeneration = 0;",
    "ActiveAckGamePid = 0;",
)

observe_identity = body(host_submit, "inline void ObserveAckIdentity(")
require(
    observe_identity,
    "host ACK complete run identity",
    "RenderFrameDirectGenerationIndex",
    "RenderFrameRunGenerationIndex",
    "frame.clientPid",
    "ActiveAckGeneration == generation",
    "ActiveAckRunGeneration == runGeneration",
    "ActiveAckGamePid == gamePid",
)
require_order(
    observe_identity,
    "host ACK identity transition cache reset",
    "ActiveAckGeneration = generation;",
    "ActiveAckRunGeneration = runGeneration;",
    "ActiveAckGamePid = gamePid;",
    "AckedFrame.fill(0);",
    "AckedGeneration.fill(0);",
)

poll_acks = body(host_submit, "inline void PollCompletedAcks()")
mismatch_start = poll_acks.find("if (ActiveAckGeneration != 0 &&")
publish_pos = poll_acks.find("PublishCompletedFrame(", mismatch_start)
continue_pos = poll_acks.find("continue;", mismatch_start)
if min(mismatch_start, publish_pos, continue_pos) < 0:
    fail("host late-run ACK branch missing")
if continue_pos > publish_pos:
    fail("late ACK from superseded generation/run may publish before discard")
require(
    poll_acks[mismatch_start:continue_pos + len("continue;")],
    "late generation/run ACK discard",
    "completedGeneration != ActiveAckGeneration",
    "completedRunGeneration != ActiveAckRunGeneration",
    "completedGamePid != ActiveAckGamePid",
    "pending.armed = false;",
    "pending.flushIssued = false;",
    "pending.frame = {};",
)
require(
    poll_acks,
    "host ACK query fault complete identity",
    "AckFaultGeneration = generation;",
    "AckFaultRunGeneration = runGeneration;",
    "AckFaultGamePid = gamePid;",
)

arm_ack = body(host_submit, "inline bool ArmConsumptionFence(")
arm_identity_prefix = """const std::uint32_t generation =
            frame.reserved[OutRunVR::RenderFrameDirectGenerationIndex];
        const std::uint32_t runGeneration =
            frame.reserved[OutRunVR::RenderFrameRunGenerationIndex];
        const std::uint32_t gamePid = frame.clientPid;
        if (slot >= Pending.size() || !generation || !runGeneration || !gamePid)
            return false;"""
require(
    arm_ack,
    "ArmConsumptionFence complete frame identity",
    arm_identity_prefix,
    "ObserveAckIdentity(frame);",
    "ActiveAckGeneration != generation",
    "ActiveAckRunGeneration != runGeneration",
    "ActiveAckGamePid != gamePid",
    "pending.frame.clientPid == frame.clientPid",
)
require_order(
    arm_ack[arm_ack.find(arm_identity_prefix):],
    "ArmConsumptionFence exact-frame identity before ACK cache read",
    arm_identity_prefix,
    "ObserveAckIdentity(frame);",
    "ActiveAckGeneration != generation",
    "ActiveAckRunGeneration != runGeneration",
    "ActiveAckGamePid != gamePid",
    "!EnsureFence(slot)",
    "AckedGeneration[slot] == generation",
)
pending_reuse = """if (pending.armed &&
            pending.frame.frameId == frame.frameId &&
            pending.frame.reserved[
                OutRunVR::RenderFrameDirectGenerationIndex] == generation &&
            pending.frame.reserved[
                OutRunVR::RenderFrameRunGenerationIndex] ==
                frame.reserved[OutRunVR::RenderFrameRunGenerationIndex] &&
            pending.frame.clientPid == frame.clientPid)"""
require(
    arm_ack,
    "pending EVENT complete identity reuse gate",
    pending_reuse,
)
require_order(
    arm_ack[arm_ack.find(pending_reuse):],
    "pending EVENT identity before reuse",
    pending_reuse,
    "++AckSameFramePendingReuse;",
)

can_fast = body(host_submit, "inline bool CanFastSubmit(")
require(
    can_fast,
    "host ACK fault complete run identity",
    "RenderFrameRunGenerationIndex",
    "verified.frame.clientPid",
    "AckFaultGeneration == generation",
    "AckFaultRunGeneration == runGeneration",
    "AckFaultGamePid == gamePid",
)

end_frame = body(host_submit, "inline XrResult XRAPI_CALL EndFrame(")
require_order(
    end_frame,
    "observe complete ACK identity before polling",
    "ObserveAckIdentity(observed.frame);",
    "PollCompletedAcks();",
    "CanFastSubmit(endInfo, verified, reject)",
)

print(
    "DX9Ex reset/transport contract PASS "
    "(resource teardown, monotonic generation, fail-close reset, "
    "host complete-run stale ACK rejection)"
)
