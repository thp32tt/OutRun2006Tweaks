#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]

R7_PATH = ROOT / "src/vr/d3d9/stereo_renderer_r7.inc"
R13_PATH = ROOT / "src/vr/d3d9/stereo_renderer_r13.cpp"
R22_PATH = ROOT / "src/vr/d3d9/stereo_renderer_r22.cpp"
R30_PATH = ROOT / "src/vr/d3d9/stereo_renderer_r30.cpp"
R32_PATH = ROOT / "src/vr/d3d9/stereo_renderer_r32.cpp"
HOST_BUNDLE_PATH = ROOT / "vrhost/src/runtime/r23_verified_bundle.hpp"
HOST_CACHE_PATH = ROOT / "vrhost/src/runtime/d3d9ex_direct_passthrough_r32.hpp"
HOST_PASSTHROUGH_PATH = ROOT / "vrhost/src/runtime/d3d9ex_direct_passthrough.hpp"
HOST_R23_RUNTIME_PATH = ROOT / "vrhost/src/runtime/r23_runtime_hardening.hpp"
HOST_R24_PATH = ROOT / "vrhost/src/runtime/r24_black_screen_guard.hpp"
HOST_R26_PATH = ROOT / "vrhost/src/runtime/r26_recenter_hardening.hpp"
HOST_REVIEW_PATH = ROOT / "vrhost/src/runtime/review_hardening.hpp"
HOST_SBS_PATH = ROOT / "vrhost/src/runtime/sbs_capture_override.hpp"
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
r30 = load(R30_PATH)
r32 = load(R32_PATH)
host_bundle = load(HOST_BUNDLE_PATH)
host_cache = load(HOST_CACHE_PATH)
host_passthrough = load(HOST_PASSTHROUGH_PATH)
host_r23_runtime = load(HOST_R23_RUNTIME_PATH)
host_r24 = load(HOST_R24_PATH)
host_r26 = load(HOST_R26_PATH)
host_review = load(HOST_REVIEW_PATH)
host_sbs = load(HOST_SBS_PATH)
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

# R13 owns the dedicated DirectGPU ACK mapping lifetime. The mapping must have
# one physical teardown owner, and ResetEx must drop the previous transport-run
# view/handle before lower D3D9 shared resources are released/recreated.
release_ack = body(r13, "void R13ReleaseAckState() noexcept")
require_order(
    release_ack,
    "R13 dedicated ACK mapping teardown owner",
    "UnmapViewOfFile(R13AckState);",
    "R13AckState = nullptr;",
    "CloseHandle(R13AckMapping);",
    "R13AckMapping = nullptr;",
)
if r13.count("UnmapViewOfFile(R13AckState);") != 1:
    fail("R13 dedicated ACK view teardown must have one physical owner")
if r13.count("CloseHandle(R13AckMapping);") != 1:
    fail("R13 dedicated ACK handle teardown must have one physical owner")

ensure_ack = body(r13, "bool R13EnsureAckState() noexcept")
require(
    ensure_ack,
    "R13 ACK mapping recovery routing",
    "R13ReleaseAckState();",
    "OpenFileMappingW(",
    "MapViewOfFile(",
)
for marker in (
    "UnmapViewOfFile(R13AckState);",
    "CloseHandle(R13AckMapping);",
):
    if marker in ensure_ack:
        fail(f"R13 ACK ensure path regained duplicate teardown: {marker}")

for marker in (
    "enum class R13GpuCompletionReadResult",
    "Unavailable",
    "Ready",
    "RetryAfterRebind",
):
    if marker not in r13:
        fail(f"R13 ACK snapshot result contract missing: {marker}")

read_ack = body(r13, "R13GpuCompletionReadResult R13ReadGpuCompletionSnapshot(")
require_order(
    read_ack,
    "R13 stale-host ACK mapping retirement",
    "const std::uint32_t expectedHostPid =",
    "if (!snapshot.hostPid || !expectedHostPid)",
    "if (snapshot.hostPid != expectedHostPid)",
    "R13ReleaseAckState();",
    "return R13GpuCompletionReadResult::RetryAfterRebind;",
    "snapshot.transportGeneration != DirectTransportGeneration",
    "completed.completedFrameId,",
    "snapshot.completedFrameId,",
    "return R13GpuCompletionReadResult::Ready;",
)
identity_pos = read_ack.find("snapshot.transportGeneration != DirectTransportGeneration")
copy_pos = read_ack.find("completed.completedFrameId,", identity_pos)
if min(identity_pos, copy_pos) < 0:
    fail("R13 ACK run-identity scope missing")
if "return R13GpuCompletionReadResult::Unavailable;" not in read_ack[identity_pos:copy_pos]:
    fail("R13 ACK run-identity mismatch must fail closed without requesting rebind")
if read_ack.count("R13ReleaseAckState();") != 1:
    fail("R13 ACK snapshot path must retire a stale host mapping exactly once")

read_ack_rebind = body(r13, "bool R13ReadGpuCompletionSnapshotWithRebind(")
require_order(
    read_ack_rebind,
    "R13 stale-only bounded ACK rebind owner",
    "const auto first = R13ReadGpuCompletionSnapshot(completed);",
    "if (first == R13GpuCompletionReadResult::Ready)",
    "return true;",
    "if (first != R13GpuCompletionReadResult::RetryAfterRebind)",
    "return false;",
    "return R13ReadGpuCompletionSnapshot(completed) ==",
    "R13GpuCompletionReadResult::Ready;",
)
if read_ack_rebind.count("R13ReadGpuCompletionSnapshot(completed)") != 2:
    fail("R13 ACK rebind owner must keep one initial read plus one stale-host recovery read")

# R13 is the lower reset/resource owner. It releases shared resources and
# publishes a disabled frame before ResetEx; recreation occurs only on success.
reset_pre = body(r13, "void R13ResetCommonPre(IDirect3DDevice9*)")
require_order(
    reset_pre,
    "R13 reset preamble",
    "OutRunVRRenderer::NotifyGameReset();",
    "R13ReleaseAckState();",
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
    "R30SupportReleaseDirectAckState();",
    "R30SupportReleaseDirectTransportInterop();",
    "R32ForgetDirectIdentity();",
)
require_order(
    invalidate_direct_r32,
    "R32 host-identity ACK/transport teardown routing",
    "R30SupportReleaseDirectAckState();",
    "R32DirectCopyPathRejected = false;",
    "R32DirectCopyRejectHr = D3D_OK;",
    "R30SupportReleaseDirectTransportInterop();",
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

# 00493: after the pre-Present wait was retired, the parallel R32-only
# producer-pending side table and its drain helper must disappear entirely.
# The canonical DirectTransportSlot::producerPending EVENT remains authoritative.
forbid(
    r32,
    "retired R32 duplicate producer-pending side state",
    "R32ProducerFencePending",
    "R32ProducerPendingFrame",
    "R32WaitProducerFence(",
    "R32DrainPendingProducerFence(",
)

resolve_direct_r32 = body(r32, "bool R32ResolveDirectTransport(")

require_order(
    resolve_direct_r32,
    "R32 DirectGPU source-surface owner facade",
    "R30SupportDirectTransportSourceSurfaces sourceSurfaces{};",
    "R30SupportTryGetDirectTransportSourceSurfaces(sourceSurfaces)",
    "const std::uint32_t preferred =",
)
forbid(
    resolve_direct_r32,
    "R32 DirectGPU raw lower source-surface dependency",
    "StretchRect(BackBuffer",
    "StretchRect(RightEyeSurface",
)
# R32 now selects/ACK-gates the slot, while the lower R30 API owns the
# physical copy/fence and internal-pass scope. Check BOTH sides of the seam.
require_order(
    resolve_direct_r32,
    "R32 lower-owned DirectGPU copy/fence dispatch",
    "R30SupportTryGetDirectTransportSourceSurfaces(sourceSurfaces)",
    "R30SupportCopyDirectTransportEyesAndIssueFence(",
    "if (FAILED(copy.hr))",
    "R32DirectCopyRejectHr = copy.hr;",
    "R30SupportMarkDirectTransportSlotPending(selected, frameId);",
)
forbid(
    resolve_direct_r32,
    "R32 regained lower DirectGPU slot or internal pass ownership",
    "DirectTransportSlots[",
    "InternalPassScope guard;",
    "slot.fence->Issue(",
)
copy_fence_owner_r30 = body(
    r30, "R30SupportCopyDirectTransportEyesAndIssueFence(")
require_order(
    copy_fence_owner_r30,
    "R30 lower-owned left/right source copy and EVENT issuance",
    "if (!device || !source.left || !source.right ||",
    "index >= OutRunVR::RenderFrameRingSize",
    "if (!slot.leftSurface || !slot.rightSurface || !slot.fence)",
    "InternalPassScope guard;",
    "source.left, nullptr, slot.leftSurface",
    "source.right, nullptr, slot.rightSurface",
    "if (FAILED(leftCopy) || FAILED(rightCopy))",
    "return {slot.fence->Issue(D3DISSUE_END), false};",
)
require_order(
    resolve_direct_r32,
    "R32 final-owner free-slot scan",
    "const std::uint32_t preferred =",
    "std::uint32_t selected = OutRunVR::RenderFrameRingSize;",
    "R30SupportGpuCompletionSnapshot ackSnapshot{};",
    "bool ackSnapshotRead = false;",
    "bool ackSnapshotValid = false;",
    "for (std::uint32_t offset = 0;",
    "R30SupportPollDirectTransportSlotProducer(index)",
    "if (!ackSnapshotRead)",
    "R30SupportTryGetGpuCompletionSnapshot(ackSnapshot)",
    "ackSnapshotRead = true;",
    "The host completed this exact published frame. Retire the",
    "selected = index;",
    "if (selected >= OutRunVR::RenderFrameRingSize)",
    "R30SupportNoteDirectTransportRingBackpressure();",
    "R30SupportCopyDirectTransportEyesAndIssueFence(",
    "if (FAILED(copy.hr))",
    "DirectTransportFrameReadyAfterPresent() is",
    "R30SupportMarkDirectTransportSlotPending(selected, frameId);",
    "R30SupportSetActiveDirectTransportSlot(selected);",
)
ack_retire_marker = "The host completed this exact published frame. Retire the"
ack_retire_pos = resolve_direct_r32.find(ack_retire_marker)
if ack_retire_pos < 0:
    fail("R32 ACK-completed publication retirement marker missing")
retire_publication_r30 = body(r30, "R30SupportRetireDirectTransportSlotPublication(")
require_order(
    retire_publication_r30,
    "R30 ACK-completed slot publication metadata owner",
    "auto& target = DirectTransportSlots[slot];",
    "target.frameId = 0;",
    "target.published = false;",
)
if resolve_direct_r32.count("R30SupportRetireDirectTransportSlotPublication(index)") != 1:
    fail("R32 ACK publication retirement must use one R30 owner call")
forbid(resolve_direct_r32, "R32 raw ACK publication retirement reintroduced",
       "candidate.frameId = 0;", "candidate.published = false;")
require_order(
    resolve_direct_r32[ack_retire_pos:],
    "R32 ACK-completed publication retirement",
    ack_retire_marker,
    "R30SupportRetireDirectTransportSlotPublication(index);",
    "selected = index;",
)

if resolve_direct_r32.count("R30SupportNoteDirectTransportRingBackpressure()") != 1:
    fail("R32 DirectGPU free-slot scan must count whole-ring backpressure once through the R30 owner facade")
if resolve_direct_r32.count("R30SupportMarkDirectTransportSlotPending(selected, frameId)") != 1:
    fail("R32 DirectGPU publish path must mark pending slot metadata exactly once through the R30 owner facade")
for raw_write in (
    "slot.producerPending = true;",
    "slot.pendingFrameId = frameId;",
    "slot.frameId = frameId;",
    "slot.published = false;",
):
    if raw_write in resolve_direct_r32:
        fail(f"R32 DirectGPU publish path regained raw lower pending-slot write: {raw_write}")
if resolve_direct_r32.count("R30SupportSetActiveDirectTransportSlot(selected)") != 1:
    fail("R32 DirectGPU publish path must set the active slot exactly once through the R30 owner facade")
if "ActiveDirectTransportSlot" in resolve_direct_r32.replace(
        "R30SupportSetActiveDirectTransportSlot", ""):
    fail("R32 DirectGPU publish path regained raw lower active-slot state")
if "++DirectTransportRingBackpressure;" in resolve_direct_r32:
    fail("R32 DirectGPU free-slot scan regained raw lower ring-backpressure state")

ack_snapshot_r13 = body(r13, "R13GpuCompletionReadResult R13ReadGpuCompletionSnapshot(")
require_order(
    ack_snapshot_r13,
    "R13 whole-ring ACK stable snapshot",
    "const std::uint32_t before = R13AckState->sequence;",
    "std::memcpy(&snapshot, R13AckState, sizeof(snapshot));",
    "const std::uint32_t after = R13AckState->sequence;",
    "if (before != after || (after & 1u))",
    "snapshot.transportGeneration != DirectTransportGeneration",
    "completed.completedFrameId,",
    "snapshot.completedFrameId,",
)
require(
    resolve_direct_r32,
    "R32 one-snapshot-per-resolve ACK fast path",
    "R30SupportGpuCompletionSnapshot ackSnapshot{};",
    "bool ackSnapshotRead = false;",
    "bool ackSnapshotValid = false;",
    "if (!ackSnapshotRead)",
    "R30SupportTryGetGpuCompletionSnapshot(ackSnapshot)",
    "ackSnapshotRead = true;",
    "const bool ackValid = ackSnapshotValid;",
    "ackSnapshot.completedFrameId[index]",
)
if resolve_direct_r32.count("R30SupportTryGetGpuCompletionSnapshot(ackSnapshot)") != 1:
    fail("R32 DirectGPU ring scan must delegate bounded ACK rebind policy to one R30 support snapshot call")
forbid(
    resolve_direct_r32,
    "R32 repeated per-slot ACK snapshot regression",
    "R13TryGetGpuCompletedFrame(index, gpuCompleted)",
)

resolve_direct_r13 = body(r13, "bool ResolveDirectTransportR13(")
require_order(
    resolve_direct_r13,
    "R13 base DirectGPU whole-ring ACK scan",
    "std::uint32_t selected = OutRunVR::RenderFrameRingSize;",
    "R13GpuCompletionSnapshot ackSnapshot{};",
    "bool ackSnapshotRead = false;",
    "bool ackSnapshotValid = false;",
    "for (std::uint32_t offset = 0;",
    "if (slot.published && slot.frameId)",
    "R13ReadGpuCompletionSnapshotWithRebind(ackSnapshot)",
    "ackSnapshotRead = true;",
    "ackSnapshot.completedFrameId[index]",
)
if resolve_direct_r13.count("R13ReadGpuCompletionSnapshotWithRebind(ackSnapshot)") != 1:
    fail("R13 base DirectGPU ring scan must read one owner-managed ACK snapshot per resolve")
r13_published_marker = "if (slot.published && slot.frameId)"
r13_published_pos = resolve_direct_r13.find(r13_published_marker)
if r13_published_pos < 0:
    fail("R13 base DirectGPU published-slot scope missing")
require_order(
    resolve_direct_r13[r13_published_pos:],
    "R13 base DirectGPU ACK-completed publication retirement",
    r13_published_marker,
    "R13ReadGpuCompletionSnapshotWithRebind(ackSnapshot)",
    "ackSnapshot.completedFrameId[index]",
    "slot.frameId = 0;",
    "slot.published = false;",
)

# The R13 physical fallback owns DirectGPU before the final R33/R32 owner is
# available. It must preserve the same fail-closed resource-lifetime invariant:
# an EVENT hard error, a partial shared-eye copy failure, or EVENT Issue failure
# cannot make an unproven shared slot reusable. Quarantine the fallback copy
# path until ResetEx recreates the transport resources.
require(
    r13,
    "R13 fallback DirectGPU rejection state",
    "bool R13DirectCopyPathRejected = false;",
    "HRESULT R13DirectCopyRejectHr = D3D_OK;",
)
r13_reject_gate = resolve_direct_r13.find("if (R13DirectCopyPathRejected)")
r13_resource_ensure = resolve_direct_r13.find("EnsureDirectTransportResources(device)")
if min(r13_reject_gate, r13_resource_ensure) < 0:
    fail("R13 fallback DirectGPU rejection/resource gate missing")
if r13_reject_gate > r13_resource_ensure:
    fail("R13 fallback rejected hot path must short-circuit before resource validation")
require_order(
    resolve_direct_r13[r13_reject_gate:],
    "R13 fallback DirectGPU rejected hot-path short-circuit",
    "if (R13DirectCopyPathRejected)",
    "return false;",
    "EnsureDirectTransportResources(device)",
    "const std::uint32_t preferred =",
)
r13_pending_start = resolve_direct_r13.find("if (slot.producerPending)")
r13_published_start = resolve_direct_r13.find(
    "if (slot.published && slot.frameId)", r13_pending_start
)
if min(r13_pending_start, r13_published_start) < 0:
    fail("R13 fallback producer EVENT poll scope missing")
r13_pending_poll = resolve_direct_r13[r13_pending_start:r13_published_start]
require_order(
    r13_pending_poll,
    "R13 fallback producer EVENT hard-error fail-closed",
    "else if (ready == S_FALSE)",
    "continue;",
    "R13DirectCopyPathRejected = true;",
    "R13DirectCopyRejectHr = ready;",
    "return false;",
)
r13_hard_error = r13_pending_poll.find("R13DirectCopyPathRejected = true;")
if r13_hard_error < 0:
    fail("R13 fallback producer EVENT hard-error branch missing")
forbid(
    r13_pending_poll[r13_hard_error:],
    "R13 fallback producer EVENT hard-error must retain quarantined slot",
    "slot.producerPending = false;",
    "slot.pendingFrameId = 0;",
    "slot.frameId = 0;",
    "slot.published = false;",
)

r13_copy_start = resolve_direct_r13.find("auto& slot = DirectTransportSlots[selected];")
r13_pending_publish = resolve_direct_r13.find(
    "slot.producerPending = true;", r13_copy_start
)
if min(r13_copy_start, r13_pending_publish) < 0:
    fail("R13 fallback copy/Issue scope missing")
r13_copy_issue = resolve_direct_r13[r13_copy_start:r13_pending_publish]
copy_fail_marker = "if (FAILED(leftCopy) || FAILED(rightCopy))"
issue_decl_marker = "const HRESULT issueHr = slot.fence->Issue(D3DISSUE_END);"
copy_fail_pos = r13_copy_issue.find(copy_fail_marker)
issue_decl_pos = r13_copy_issue.find(issue_decl_marker)
if min(copy_fail_pos, issue_decl_pos) < 0 or issue_decl_pos <= copy_fail_pos:
    fail("R13 fallback shared-eye copy failure scope missing")
require_order(
    r13_copy_issue[:issue_decl_pos],
    "R13 fallback shared-eye copy failure fail-closed",
    "const HRESULT leftCopy = StretchDirectEye(",
    "const HRESULT rightCopy = SUCCEEDED(leftCopy)",
    copy_fail_marker,
    "R13DirectCopyPathRejected = true;",
    "R13DirectCopyRejectHr = FAILED(leftCopy)",
    "return false;",
)
issue_fail_pos = r13_copy_issue.find("if (FAILED(issueHr))", issue_decl_pos)
if issue_fail_pos < 0:
    fail("R13 fallback EVENT Issue failure scope missing")
require_order(
    r13_copy_issue[issue_decl_pos:],
    "R13 fallback EVENT Issue failure fail-closed",
    issue_decl_marker,
    "if (FAILED(issueHr))",
    "R13DirectCopyPathRejected = true;",
    "R13DirectCopyRejectHr = issueHr;",
    "return false;",
)
reset_r13_common = body(r13, "void R13ResetCommonPre(IDirect3DDevice9*)")
require_order(
    reset_r13_common,
    "R13 fallback DirectGPU rejection reset",
    "R13DirectCopyPathRejected = false;",
    "R13DirectCopyRejectHr = D3D_OK;",
    "R13ReleaseAckState();",
    "ReleaseStereoResources();",
)

post_present_r7 = body(r7, "bool DirectTransportFrameReadyAfterPresent(")
require_order(
    post_present_r7,
    "DirectGPU bounded post-Present publication",
    "if(WaitForEventQuery(slot.fence,1))",
    "slot.producerPending=false;",
    "slot.pendingFrameId=0;",
    "slot.published=true;",
    "++DirectTransportFenceTimeouts;",
)
if post_present_r7.count("WaitForEventQuery(") != 1:
    fail("DirectGPU post-Present publication must keep exactly one bounded EVENT wait")
timeout_pos = post_present_r7.find("++DirectTransportFenceTimeouts;")
if timeout_pos < 0:
    fail("DirectGPU post-Present timeout quarantine scope missing")
timeout_tail = post_present_r7[timeout_pos:]
require_order(
    timeout_tail,
    "DirectGPU post-Present timeout return",
    "++DirectTransportFenceTimeouts;",
    "return false;",
)
forbid(
    post_present_r7[timeout_pos:],
    "DirectGPU post-Present unresolved EVENT must preserve producer ownership",
    "GetData(",
    "slot.producerPending=false;",
    "slot.pendingFrameId=0;",
    "slot.frameId=0;",
    "slot.published=false;",
)
forbid(
    post_present_r7,
    "DirectGPU post-Present publication wait",
    "D3DGETDATA_FLUSH",
    "Sleep(",
    "SwitchToThread(",
    "WaitForSingleObject(",
)

present_r7 = body(r7, "HRESULT __stdcall PresentDest(")
lower_present_marker = "const HRESULT hr=PresentHook.stdcall<HRESULT>"
lower_present_pos = present_r7.find(lower_present_marker)
if lower_present_pos < 0:
    fail("DirectGPU Present path lost lower Present boundary")
post_lower_present_r7 = present_r7[lower_present_pos:]
require_order(
    post_lower_present_r7,
    "DirectGPU post-Present publication ordering",
    lower_present_marker,
    "if(directTransport)",
    "if(SUCCEEDED(hr)&&DirectTransportFrameReadyAfterPresent(pendingFrameId))",
    "if(composedStereo&&SUCCEEDED(hr)&&!FrameStereoIncomplete)",
    "PublishStereoState(OutRunVR::StereoSbsActive,true,pendingPoseSequence,pendingFrameId);",
    "PublishRenderFrame(OutRunVR::StereoSbsActive,pendingFrameId,pendingPoseSequence,presentStart.QuadPart,OutRunVR::StereoFailureNone,&FrameStereoMetadata,false,directTransport);",
)
if post_lower_present_r7.count("DirectTransportFrameReadyAfterPresent(pendingFrameId)") != 1:
    fail("DirectGPU Present path must authorize publication through exactly one post-Present readiness gate")

forbid(
    resolve_direct_r32,
    "R32 final owner fixed-slot regression",
    "R13TryGetGpuCompletedFrame(slotIndex, gpuCompleted)",
)
require(
    resolve_direct_r32,
    "R32 non-blocking producer EVENT poll facade",
    "R30SupportPollDirectTransportSlotProducer(index)",
)
producer_poll_r30 = body(r30, "R30SupportPollDirectTransportSlotProducer(")
require_order(
    producer_poll_r30,
    "R30 producer EVENT poll owner semantics",
    "if (!target.producerPending)",
    "target.fence",
    "target.fence->GetData(nullptr, 0, 0)",
    "if (ready == S_OK)",
    "target.producerPending = false;",
    "target.pendingFrameId = 0;",
    "if (!target.published)",
    "target.frameId = 0;",
    "return ready;",
)

# A producer EVENT hard error is not equivalent to ordinary ring pressure.
# Once GetData can no longer prove completion, the shared-eye slot must not be
# recycled or silently cleared. Keep the final R32 owner fail-closed until a
# reset/interop identity transition revalidates the DirectGPU copy path.
pending_poll_marker = "const HRESULT ready ="
published_scan_marker = "if (candidate.published && candidate.frameId)"
pending_poll_pos = resolve_direct_r32.find(pending_poll_marker)
published_scan_pos = resolve_direct_r32.find(
    published_scan_marker, pending_poll_pos
)
if min(pending_poll_pos, published_scan_pos) < 0:
    fail("R32 producer EVENT poll scope missing")
producer_poll_r32 = resolve_direct_r32[pending_poll_pos:published_scan_pos]
require_order(
    producer_poll_r32,
    "R32 producer EVENT hard-error fail-closed",
    "R30SupportPollDirectTransportSlotProducer(index)",
    "if (ready == S_FALSE)",
    "continue;",
    "if (FAILED(ready))",
    "R32DirectCopyPathRejected = true;",
    "R32DirectCopyRejectHr = ready;",
    "if (R30SupportTelemetryEnabled()) ++R32PendingFenceErrors;",
    "return false;",
)
hard_error_pos = producer_poll_r32.find("R32DirectCopyPathRejected = true;")
if hard_error_pos < 0:
    fail("R32 producer EVENT hard-error branch missing")
forbid(
    resolve_direct_r32,
    "R32 producer EVENT poll must remain behind the R30 owner facade",
    "candidate.producerPending",
    "candidate.pendingFrameId",
    "candidate.fence->GetData",
)
forbid(
    producer_poll_r32[hard_error_pos:],
    "R32 producer EVENT hard-error must retain quarantined slot",
    "candidate.producerPending = false;",
    "candidate.pendingFrameId = 0;",
    "candidate.frameId = 0;",
    "candidate.published = false;",
)

issue_marker = "const HRESULT issueHr = slot.fence->Issue(D3DISSUE_END);"
issue_pos = resolve_direct_r32.find(issue_marker)
pending_publish_pos = resolve_direct_r32.find(
    "R30SupportMarkDirectTransportSlotPending(selected, frameId);", issue_pos
)
if min(issue_pos, pending_publish_pos) < 0:
    fail("R32 producer EVENT issue scope missing")
issue_r32 = resolve_direct_r32[issue_pos:pending_publish_pos]
require_order(
    issue_r32,
    "R32 producer EVENT issue failure fail-closed",
    issue_marker,
    "if (FAILED(issueHr))",
    "R32DirectCopyPathRejected = true;",
    "R32DirectCopyRejectHr = issueHr;",
    "if (R30SupportTelemetryEnabled()) ++R32PendingFenceErrors;",
    "return false;",
)

forbid(
    resolve_direct_r32,
    "R32 redundant pre-Present producer fence wait",
    "R32WaitProducerFence(slot.fence)",
    "R32ProducerFencePending[selected] = true;",
    "R32ProducerPendingFrame[selected] = frameId;",
    "D3DGETDATA_FLUSH",
    "SwitchToThread(",
    "Sleep(",
    "WaitForSingleObject(",
)

invalidate_r32 = body(r32, "void R32InvalidateResetCaches() noexcept")
require(
    invalidate_r32,
    "R32 reset identity invalidation",
    "R32ForgetDirectIdentity();",
    "R32DirectCopyPathRejected = false;",
    "R32DirectCopyRejectHr = D3D_OK;",
)
reset_r32 = body(r32, "HRESULT R32WithResetLifecycle(")
require_order(
    reset_r32,
    "R32 reset lifecycle owner helper",
    "const HRESULT hr = lowerReset();",
    "const bool gameDevice = R30SupportIsGameDevice(device);",
    "if (gameDevice)",
    "if (SUCCEEDED(hr))",
    "R32ResetAfterGameReset();",
)
require(
    reset_r32,
    "R32 failed-reset cleanup",
    "R32InvalidateResetCaches();",
    "++R32ResetFailures;",
)
forbid(
    r32,
    "retired R32 physical Reset ownership",
    "SafetyHookInline R32ResetR22Hook{};",
    "HRESULT __stdcall ResetDestR32(",
    "reinterpret_cast<void*>(&ResetDestR22), ResetDestR32",
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
read_gpu_ack = body(r13, "R13GpuCompletionReadResult R13ReadGpuCompletionSnapshot(")
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
    "snapshot.hostPid != expectedHostPid",
    "snapshot.transportGeneration != DirectTransportGeneration",
    "!RenderFrameRunGeneration",
    "DirectGpuAckRunGenerationIndex",
    "DirectGpuAckGamePidIndex",
    "GetCurrentProcessId()",
    "completed.completedFrameId,",
    "snapshot.completedFrameId,",
)
forbid(
    r13,
    "retired per-slot ACK compatibility surface",
    "R13ReadGpuCompletedFrame(",
    "R13TryGetGpuCompletedFrame(",
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

safe_eye_run_owner = body(
    host_passthrough, "inline bool SafeEyesBelongToTransportRun("
)
require(
    safe_eye_run_owner,
    "SafeEye transport-run owner complete identity",
    "RenderFrameDirectGenerationIndex",
    "RenderFrameRunGenerationIndex",
    "const std::uint32_t gamePid = frame.clientPid;",
    "generation != 0",
    "runGeneration != 0",
    "gamePid != 0",
    "SafeFrameId != 0",
    "SafeTransportGeneration == generation",
    "SafeRunGeneration == runGeneration",
    "SafeGamePid == gamePid",
    "SafeEyeSrv[0] && SafeEyeSrv[1]",
)

safe_eye_owner = body(host_passthrough, "inline bool SafeEyesOwnFrame(")
require(
    safe_eye_owner,
    "SafeEye exact-frame owner delegation",
    "frame.frameId != 0",
    "SafeFrameId == frame.frameId",
    "SafeEyesBelongToTransportRun(frame)",
)
forbid(
    safe_eye_owner,
    "SafeEye exact-frame owner duplicated transport identity",
    "SafeTransportGeneration ==",
    "SafeRunGeneration ==",
    "SafeGamePid ==",
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

# Classic fallback freshness must advance on a new Frame.v2 producer run even
# when the restarted game reuses the same low frameId. Otherwise the new run's
# first valid fallback can inherit an expired prior-run LastClassicAdvanceMs.
classic_fallback = body(host_review, "inline bool FreshClassicFallbackAvailable() noexcept")
require(
    classic_fallback,
    "classic fallback complete run freshness identity",
    "RenderFrameRunGenerationIndex",
    "const std::uint32_t gamePid = frame.clientPid;",
    "if (!runGeneration || !gamePid)",
    "frame.frameId != LastClassicFrameId",
    "runGeneration != LastClassicRunGeneration",
    "gamePid != LastClassicGamePid",
    "LastClassicRunGeneration = runGeneration;",
    "LastClassicGamePid = gamePid;",
    "LastClassicAdvanceMs = now;",
)
require_order(
    classic_fallback,
    "classic fallback run identity before freshness timestamp",
    "const std::uint32_t runGeneration",
    "const std::uint32_t gamePid",
    "runGeneration != LastClassicRunGeneration",
    "gamePid != LastClassicGamePid",
    "LastClassicRunGeneration = runGeneration;",
    "LastClassicGamePid = gamePid;",
    "LastClassicAdvanceMs = now;",
)

classic_destroy = body(host_review, "inline XrResult XRAPI_CALL DestroySession(")
require(
    classic_destroy,
    "classic fallback run identity reset",
    "LastClassicFrameId = 0;",
    "LastClassicRunGeneration = 0;",
    "LastClassicGamePid = 0;",
    "LastClassicAdvanceMs = 0;",
)

direct_host_destroy = body(
    host_passthrough, "inline XrResult XRAPI_CALL DestroySession("
)
require_order(
    direct_host_destroy,
    "D3D9Ex direct-host transactional session teardown",
    "const XrResult result =",
    "OutRunVrSbsCaptureOverride::DestroySession(session);",
    "if (XR_SUCCEEDED(result))",
    "ResetR13HostState();",
    "return result;",
)

r26_destroy = body(host_r26, "inline XrResult XRAPI_CALL DestroySession(")
require_order(
    r26_destroy,
    "R26 recenter transactional session teardown",
    "const XrResult result =",
    "OutRunVrR24BlackScreenGuard::DestroySession(session);",
    "if (XR_SUCCEEDED(result))",
    "ResetSessionState();",
    "return result;",
)

# R24 flat recovery may reuse an older SafeEye frame, but only inside the
# currently live DirectGPU transport/game run. This preserves same-run visual
# recovery without reviving prior-process or pre-reset eye content.
direct_flat = body(host_r24, "inline bool RenderDirectFlatFallback(")
require(
    direct_flat,
    "R24 direct-flat current transport-run guard",
    "OutRunVrR21RuntimeHardening::DirectTransportRequested()",
    "OutRunVrReviewHardening::LatestCompleteDirectFrame(latest)",
    "SafeEyesBelongToTransportRun(latest)",
)
require_order(
    direct_flat,
    "R24 direct-flat identity before SafeEye sampling",
    "LatestCompleteDirectFrame(latest)",
    "SafeEyesBelongToTransportRun(latest)",
    "SourceSrv = SafeEyeSrv[0];",
)

# A committed R23 presentation bundle may outlive newer frames from the same
# producer run, but it must never survive a game-process/run restart. Freshness
# therefore combines age/internal consistency with current producer identity.
bundle_run = body(host_bundle, "inline bool BelongsToCurrentProducerRun(")
require(
    bundle_run,
    "R23 verified bundle current producer-run identity",
    "RenderFrameRunGenerationIndex",
    "snapshot.frame.clientPid",
    "OutRunVrFinalTest::ReadLatestFrame(latest, publish)",
    "latest.reserved[OutRunVR::RenderFrameRunGenerationIndex]",
    "snapshotRunGeneration == latestRunGeneration",
    "snapshotGamePid == latest.clientPid",
)
bundle_fresh = body(host_bundle, "inline bool ReadFresh(")
require_order(
    bundle_fresh,
    "R23 verified bundle freshness includes producer-run ownership",
    "Read(out)",
    "IsFresh(out)",
    "BelongsToCurrentProducerRun(out)",
)

# R19's short-lived stereo fallback cache must be scoped to the producer run.
# The OpenXR host can survive a fast game restart, so observing any Frame.v2
# from a new run must invalidate the prior run's complete stereo frame before
# the new frame becomes stereo-complete.
stereo_cache = body(host_sbs, "inline void UpdateStereoFrameCache()")
require(
    host_sbs,
    "R19 stereo cache run identity helpers",
    "inline bool FrameRunIdentityValid(",
    "RenderFrameRunGenerationIndex",
    "inline bool SameProducerRun(",
    "inline void InvalidateStereoFrameCache() noexcept",
)
require(
    stereo_cache,
    "R19 stereo cache fail-closed run transition",
    "if (!OutRunVrFinalTest::ReadLatestFrame(frame, publish))",
    "if (!FrameRunIdentityValid(frame))",
    "InvalidateStereoFrameCache();",
    "if (LastStereoFrameValid && !SameProducerRun(frame, LastStereoFrame))",
    "if (!FrameComplete(frame))",
    "LastStereoFrame = frame;",
    "LastStereoFrameValid = true;",
)
require_order(
    stereo_cache,
    "R19 new-run invalidation before complete-frame reuse",
    "if (!FrameRunIdentityValid(frame))",
    "if (LastStereoFrameValid && !SameProducerRun(frame, LastStereoFrame))",
    "if (!FrameComplete(frame))",
    "LastStereoFrame = frame;",
)
sbs_reset = body(host_sbs, "inline void ResetAll(bool parentSessionDestroying = false)")
require(
    sbs_reset,
    "R19 stereo cache reset owner",
    "Projection.Destroy(parentSessionDestroying);",
    "Theater.Destroy(parentSessionDestroying);",
    "InvalidateStereoFrameCache();",
)

sbs_gpu_drain = body(host_sbs, "inline bool WaitForSwapchainGpuIdleBeforeDestroy() noexcept")
require(
    host_sbs,
    "R19 swapchain GPU drain budget",
    "SwapchainGpuDrainBudgetMs = 250",
)
require(
    sbs_gpu_drain,
    "R19 OpenXR swapchain destroy GPU completion fence",
    "D3D11_QUERY_EVENT",
    "CreateQuery(",
    "OutRunVrFinalTest::Context->End(completion);",
    "OutRunVrFinalTest::Context->Flush();",
    "OutRunVrFinalTest::Context->GetData(",
    "while (status == S_FALSE)",
    "const ULONGLONG start = GetTickCount64();",
    "GetDeviceRemovedReason()",
    "GetTickCount64() - start >= SwapchainGpuDrainBudgetMs",
    "ReleaseCom(completion);",
)
gpu_drain_completion = sbs_gpu_drain[
    sbs_gpu_drain.find("OutRunVrFinalTest::Context->End(completion);"):
]
require_order(
    gpu_drain_completion,
    "R19 swapchain GPU completion ordering",
    "OutRunVrFinalTest::Context->End(completion);",
    "OutRunVrFinalTest::Context->Flush();",
    "const ULONGLONG start = GetTickCount64();",
    "while (status == S_FALSE)",
    "OutRunVrFinalTest::Context->GetData(",
    "GetDeviceRemovedReason()",
    "GetTickCount64() - start >= SwapchainGpuDrainBudgetMs",
    "ReleaseCom(completion);",
)

ensure_source = body(host_sbs, "inline bool EnsureSource(")
require_order(
    ensure_source,
    "R19 capture source replacement is transactional",
    "ID3D11Texture2D* pendingSource = nullptr;",
    "CreateTexture2D(",
    "&d, nullptr, &pendingSource)",
    "ID3D11ShaderResourceView* pendingSourceSrv = nullptr;",
    "CreateShaderResourceView(",
    "pendingSource, &vd, &pendingSourceSrv)",
    "ReleaseCom(SourceSrv);",
    "ReleaseCom(Source);",
    "Source = pendingSource;",
    "SourceSrv = pendingSourceSrv;",
    "SourceWidth = d.Width;",
    "SourceHeight = d.Height;",
    "SourceFormat = d.Format;",
)
require(
    ensure_source,
    "R19 failed replacement releases only pending capture resources",
    "ReleaseCom(pendingSourceSrv);",
    "ReleaseCom(pendingSource);",
)
forbid(
    ensure_source,
    "R19 capture resource creation must not target published globals directly",
    "CreateTexture2D(&d, nullptr, &Source)",
    "CreateShaderResourceView(Source, &vd, &SourceSrv)",
)

create_shaders = body(host_sbs, "inline bool CreateShaders()")
require_order(
    create_shaders,
    "R19 shader resource staging precedes global publication",
    "ReleaseCom(ConstantBuffer);",
    "ReleaseCom(Sampler);",
    "ReleaseCom(Ps);",
    "ReleaseCom(Vs);",
    "ID3D11VertexShader* pendingVs = nullptr;",
    "ID3D11PixelShader* pendingPs = nullptr;",
    "ID3D11SamplerState* pendingSampler = nullptr;",
    "ID3D11Buffer* pendingConstantBuffer = nullptr;",
    "CreateVertexShader(vsCode->GetBufferPointer(),",
    "&pendingVs);",
    "CreatePixelShader(psCode->GetBufferPointer(),",
    "&pendingPs);",
    "CreateSamplerState(&sd, &pendingSampler)",
    "CreateBuffer(",
    "&bd, nullptr, &pendingConstantBuffer)",
    "Vs = pendingVs;",
    "Ps = pendingPs;",
    "Sampler = pendingSampler;",
    "ConstantBuffer = pendingConstantBuffer;",
)
publish_start = create_shaders.find("Vs = pendingVs;")
if publish_start < 0:
    fail("R19 shader publication start missing")
publish_path = create_shaders[publish_start:]
require_order(
    publish_path,
    "R19 complete shader bundle publishes before success",
    "Vs = pendingVs;",
    "Ps = pendingPs;",
    "Sampler = pendingSampler;",
    "ConstantBuffer = pendingConstantBuffer;",
    "return true;",
)
require(
    create_shaders,
    "R19 shader partial-creation rollback",
    "const auto rollbackPending = [&]() noexcept",
    "ReleaseCom(pendingConstantBuffer);",
    "ReleaseCom(pendingSampler);",
    "ReleaseCom(pendingPs);",
    "ReleaseCom(pendingVs);",
    "rollbackPending();",
)
forbid(
    create_shaders,
    "R19 shader creation must not publish directly into globals",
    "nullptr, &Vs);",
    "nullptr, &Ps);",
    "CreateSamplerState(&sd, &Sampler)",
    "&bd, nullptr, &ConstantBuffer)",
)

sbs_acquire = body(host_sbs, "inline bool Acquire(Swapchain& swapchain")
require(
    host_sbs,
    "R19 bounded swapchain image wait budget",
    "SwapchainImageWaitBudgetNs = 5'000'000",
)
require(
    sbs_acquire,
    "R19 bounded swapchain image wait",
    "wait.timeout = SwapchainImageWaitBudgetNs;",
    "const XrResult result = ::xrWaitSwapchainImage(swapchain.handle, &wait);",
    "if (result == XR_TIMEOUT_EXPIRED)",
    "return false;",
    "swapchain.waited = true;",
)
forbid(
    sbs_acquire,
    "R19 swapchain image wait must not block indefinitely",
    "XR_INFINITE_DURATION",
    "for (;;)",
)
require_order(
    sbs_acquire,
    "R19 bounded wait call ordering",
    "image = swapchain.acquiredImage;",
    "wait.timeout = SwapchainImageWaitBudgetNs;",
    "::xrWaitSwapchainImage(swapchain.handle, &wait);",
    "if (result == XR_TIMEOUT_EXPIRED)",
    "if (XR_FAILED(result))",
    "swapchain.waited = true;",
)
timeout_start = sbs_acquire.find("if (result == XR_TIMEOUT_EXPIRED)")
failed_start = sbs_acquire.find("if (XR_FAILED(result))", timeout_start)
timeout_path = sbs_acquire[timeout_start:failed_start]
require(
    timeout_path,
    "R19 timeout yields frame while preserving acquired image",
    "return false;",
)
forbid(
    timeout_path,
    "R19 timeout must retain acquired image ownership",
    "swapchain.acquired = false;",
    "swapchain.acquiredImage = 0;",
    "swapchain.waited = true;",
    "swapchain.waitFaulted = true;",
    "::xrReleaseSwapchainImage",
)
require(
    host_sbs,
    "R19 swapchain image-flow hard-fault state",
    "bool acquireFaulted = false;",
    "bool waitFaulted = false;",
    "bool releaseFaulted = false;",
)
require_order(
    sbs_acquire,
    "R19 prior image-flow hard fault fails closed before acquire",
    "if (swapchain.acquireFaulted || swapchain.waitFaulted ||",
    "swapchain.releaseFaulted)",
    "return false;",
    "if (!swapchain.acquired)",
)
require(
    sbs_acquire,
    "R19 hard acquire failure marks swapchain faulted",
    "const XrResult acquireResult = ::xrAcquireSwapchainImage(",
    "if (XR_FAILED(acquireResult))",
    "swapchain.acquireFaulted = true;",
    "return false;",
)
acquire_fail_start = sbs_acquire.find("if (XR_FAILED(acquireResult))")
acquire_success_start = sbs_acquire.find("swapchain.acquired = true;", acquire_fail_start)
acquire_fail_path = sbs_acquire[acquire_fail_start:acquire_success_start]
require_order(
    acquire_fail_path,
    "R19 hard acquire fault before frame yield",
    "swapchain.acquireFaulted = true;",
    "return false;",
)
forbid(
    acquire_fail_path,
    "R19 hard acquire failure must not claim image ownership",
    "swapchain.acquired = true;",
    "swapchain.waited = true;",
    "::xrWaitSwapchainImage",
    "::xrReleaseSwapchainImage",
)
hard_wait_start = sbs_acquire.find("if (XR_FAILED(result))")
wait_success_start = sbs_acquire.find("swapchain.waited = true;", hard_wait_start)
hard_wait_path = sbs_acquire[hard_wait_start:wait_success_start]
require(
    hard_wait_path,
    "R19 hard wait failure marks swapchain faulted",
    "swapchain.waitFaulted = true;",
    "return false;",
)
require_order(
    hard_wait_path,
    "R19 hard wait fault before frame yield",
    "swapchain.waitFaulted = true;",
    "return false;",
)

sbs_release = body(host_sbs, "inline bool Release(Swapchain& swapchain, bool contentComplete)")
require(
    sbs_release,
    "R19 hard release failure marks swapchain faulted",
    "const XrResult result = ::xrReleaseSwapchainImage(swapchain.handle, &release);",
    "if (XR_SUCCEEDED(result))",
    "swapchain.releaseFaulted = true;",
    "return false;",
)
require_order(
    sbs_release,
    "R19 release commit proof requires complete content",
    "swapchain.acquired = false;",
    "swapchain.waited = false;",
    "swapchain.acquiredImage = 0;",
    "swapchain.committedGeneration =",
    "contentComplete ? swapchain.generation : 0;",
    "return true;",
)
release_fail_start = sbs_release.find("swapchain.committedGeneration = 0;", sbs_release.find("if (XR_SUCCEEDED(result))"))
if release_fail_start < 0:
    fail("R19 hard release must invalidate committed generation")
release_fail_path = sbs_release[release_fail_start:]
forbid(
    release_fail_path,
    "R19 hard release failure must retain local image ownership for teardown",
    "swapchain.acquired = false;",
    "swapchain.waited = false;",
    "swapchain.acquiredImage = 0;",
    "swapchain.committedGeneration = swapchain.generation;",
)
require_order(
    release_fail_path,
    "R19 hard release invalidates cache proof before fault",
    "swapchain.committedGeneration = 0;",
    "swapchain.releaseFaulted = true;",
    "return false;",
)

projection_override = body(host_sbs, "inline bool RenderProjectionOverride(")
theater_override = body(host_sbs, "inline bool RenderTheaterOverride(")
require(
    projection_override,
    "R19 projection release commit ownership",
    "Release(Projection, false);",
    "const bool released = Release(Projection, ok);",
)
require(
    theater_override,
    "R19 theater release commit ownership",
    "Release(Theater, false);",
    "const bool released = Release(Theater, ok);",
)

direct_safe_projection = body(host_passthrough, "inline bool RenderSafeProjection(")
require(
    direct_safe_projection,
    "R23 direct projection explicit release content provenance",
    "Release(Projection, false);",
    "const bool released = Release(Projection, ok);",
    "if (!ok || !released)",
)
forbid(
    direct_safe_projection,
    "R23 direct projection must not use legacy one-argument Release",
    "Release(Projection);",
)

r24_direct_projection = body(host_r24, "inline bool RenderSafeProjectionChecked(")
r24_direct_flat = body(host_r24, "inline bool RenderDirectFlatFallback(")
r24_emergency = body(host_r24, "inline bool BuildEmergencyVisibleQuad(")
require(
    r24_direct_projection,
    "R24 projection content-complete release ownership",
    "Release(Projection, false);",
    "const bool released = Release(Projection, ok);",
)
require(
    r24_direct_projection,
    "R24 projection render carries swapchain GPU-work owner",
    "UvRect{ 0.f, 0.f, 1.f, 1.f }, &Projection",
)
require(
    r24_direct_flat,
    "R24 theater content-complete release ownership",
    "Release(Theater, false);",
    "const bool released = Release(Theater, ok);",
)
require(
    r24_direct_flat,
    "R24 direct-flat render carries swapchain GPU-work owner",
    "UvRect{ 0.f, 0.f, 1.f, 1.f }, &Theater",
)
require(
    r24_emergency,
    "R24 emergency clear release ownership",
    "Release(Theater, false);",
    "Release(Theater, true)",
)

sbs_swapchain_destroy = body(host_sbs, "bool Destroy(bool parentSessionDestroying = false)")
require(
    sbs_swapchain_destroy,
    "R19 swapchain image-flow hard-fault reset",
    "acquireFaulted = false;",
    "waitFaulted = false;",
    "releaseFaulted = false;",
)
require(
    host_sbs,
    "R19 swapchain GPU-work provenance",
    "bool gpuWorkSubmitted = false;",
)
require_order(
    sbs_swapchain_destroy,
    "R19 skip drain only for never-submitted swapchains",
    "const bool gpuDrained =",
    "!gpuWorkSubmitted || WaitForSwapchainGpuIdleBeforeDestroy();",
    "if (!gpuDrained)",
    "gpuWorkSubmitted = false;",
    "const XrResult result = ::xrDestroySwapchain(handle);",
)

render_to = body(host_sbs, "inline bool RenderTo(ID3D11RenderTargetView* rtv")
require(
    render_to,
    "R19 tracked render preserves four-argument compatibility",
    "Swapchain* swapchainOwner = nullptr",
)
require(
    host_sbs,
    "R19 swapchain owner exposes GPU-work provenance mutation",
    "void NoteGpuWorkSubmitted() noexcept",
    "gpuWorkSubmitted = true;",
)
require_order(
    render_to,
    "R19 marks submitted GPU work after draw",
    "OutRunVrFinalTest::Context->Draw(3, 0);",
    "if (swapchainOwner)",
    "swapchainOwner->NoteGpuWorkSubmitted();",
    "OutRunVrFinalTest::Context->OMSetRenderTargets(1, &nullRtv, nullptr);",
)
require(
    host_sbs,
    "R19 render paths pass swapchain provenance owner",
    "eyeUv[0], &Projection",
    "eyeUv[1], &Projection",
    "theaterUv, &Theater",
)

require(
    sbs_swapchain_destroy,
    "R19 fail-closed swapchain destruction",
    "if (!gpuDrained)",
    "if (!parentSessionDestroying)",
    "return false;",
    "handle = XR_NULL_HANDLE;",
    "const XrResult result = ::xrDestroySwapchain(handle);",
    "if (XR_FAILED(result) && !parentSessionDestroying)",
)
require_order(
    sbs_swapchain_destroy,
    "R19 live swapchain completion-before-destroy ordering",
    "WaitForSwapchainGpuIdleBeforeDestroy();",
    "if (!gpuDrained)",
    "if (!parentSessionDestroying)",
    "return false;",
    "gpuWorkSubmitted = false;",
    "const XrResult result = ::xrDestroySwapchain(handle);",
)
successful_drain_destroy = sbs_swapchain_destroy[
    sbs_swapchain_destroy.find("// The event-query fence proved"):
    sbs_swapchain_destroy.find("for (auto& pair : rtvs)")
]
require_order(
    successful_drain_destroy,
    "R19 successful drain proof survives transient live destroy failure",
    "gpuWorkSubmitted = false;",
    "const XrResult result = ::xrDestroySwapchain(handle);",
    "if (XR_FAILED(result) && !parentSessionDestroying)",
    "return false;",
)
require_order(
    sbs_swapchain_destroy,
    "R19 live destroy preserves local resources until ownership resolves",
    "WaitForSwapchainGpuIdleBeforeDestroy();",
    "if (!gpuDrained)",
    "const XrResult result = ::xrDestroySwapchain(handle);",
    "if (XR_FAILED(result) && !parentSessionDestroying)",
    "for (auto& pair : rtvs)",
    "rtvs.clear();",
    "images.clear();",
    "generation = 0;",
)
destroy_result_start = sbs_swapchain_destroy.find(
    "const XrResult result = ::xrDestroySwapchain(handle);"
)
resource_release_start = sbs_swapchain_destroy.find("for (auto& pair : rtvs)")
destroy_result_path = sbs_swapchain_destroy[
    destroy_result_start:resource_release_start
]
require(
    destroy_result_path,
    "R19 failed live destroy retains local resources",
    "if (XR_FAILED(result) && !parentSessionDestroying)",
    "return false;",
)
destroy_unproven = sbs_swapchain_destroy[
    sbs_swapchain_destroy.find("if (!gpuDrained)"):
    sbs_swapchain_destroy.find("else", sbs_swapchain_destroy.find("if (!gpuDrained)"))
]
forbid(
    destroy_unproven,
    "R19 unproven GPU completion path must not call xrDestroySwapchain",
    "::xrDestroySwapchain(handle);",
)

ensure_swapchain = body(host_sbs, "inline bool EnsureSwapchain(")
require(
    ensure_swapchain,
    "R19 image-flow hard fault bypasses swapchain reuse",
    "!swapchain.acquireFaulted",
    "!swapchain.waitFaulted",
    "!swapchain.releaseFaulted",
    "if (!swapchain.Destroy())",
)
require_order(
    ensure_swapchain,
    "R19 live recreate fail-closed destroy",
    "if (!swapchain.Destroy())",
    "return false;",
    "const DXGI_FORMAT format = ChooseSwapchainFormat(session);",
    "::xrCreateSwapchain(session, &create, &swapchain.handle)",
)

sbs_parent_prepare = body(host_sbs, "bool PrepareForParentSessionDestroy() noexcept")
require_order(
    sbs_parent_prepare,
    "R19 parent-session no-work fast path",
    "if (handle == XR_NULL_HANDLE || !gpuWorkSubmitted)",
    "return true;",
    "if (!WaitForSwapchainGpuIdleBeforeDestroy())",
)
parent_prepare_drain = sbs_parent_prepare[
    sbs_parent_prepare.find("if (!WaitForSwapchainGpuIdleBeforeDestroy())"):
]
require_order(
    parent_prepare_drain,
    "R19 parent-session GPU completion proof",
    "if (!WaitForSwapchainGpuIdleBeforeDestroy())",
    "return false;",
    "gpuWorkSubmitted = false;",
    "return true;",
)

sbs_parent_forget = body(host_sbs, "void ForgetAfterParentSessionDestroy() noexcept")
require(
    sbs_parent_forget,
    "R19 parent-success local ownership release",
    "handle = XR_NULL_HANDLE;",
    "rtvs.clear();",
    "images.clear();",
    "generation = 0;",
    "committedGeneration = 0;",
    "gpuWorkSubmitted = false;",
)

sbs_destroy_session = body(host_sbs, "inline XrResult XRAPI_CALL DestroySession(XrSession session)")
forbid(
    sbs_destroy_session,
    "R19 parent destroy must not discard local state before parent result",
    "ResetAll(true);",
)
require_order(
    sbs_destroy_session,
    "R19 transactional parent-session teardown",
    "Projection.PrepareForParentSessionDestroy();",
    "Theater.PrepareForParentSessionDestroy();",
    "const XrResult result = OutRunVrFinalTest::DestroySession(session);",
    "if (XR_SUCCEEDED(result))",
    "Projection.ForgetAfterParentSessionDestroy();",
    "Theater.ForgetAfterParentSessionDestroy();",
    "ViewSpace = XR_NULL_HANDLE;",
    "ResetCapture();",
    "return result;",
)

# R24's display-only soft grace intentionally reads the committed snapshot
# without R23's normal fresh-read path, but it must retain the same current
# producer-run ownership. Otherwise a prior-run bundle could be revived after
# a fast game restart through this raw Read() bypass.
display_grace = body(host_r24, "inline bool ReadDisplayGraceSnapshot(")
require(
    display_grace,
    "R24 display grace current producer-run guard",
    "Read(out)",
    "FrameComplete(out.frame)",
    "BelongsToCurrentProducerRun(out)",
)
require_order(
    display_grace,
    "R24 display grace validates bundle before current run",
    "Read(out)",
    "FrameComplete(out.frame)",
    "BelongsToCurrentProducerRun(out)",
    "GetTickCount64()",
)

# R24's released-image cache must not outlive the DirectGPU producer run that
# populated it. Swapchain generation proves release ownership only inside that
# swapchain creation; it does not distinguish a restarted game process/run.
cache_quad = body(host_r24, "inline bool BuildCachedVisibleQuad(")
require(
    host_r24,
    "R24 released-image direct run provenance",
    "struct DirectCacheRunIdentity",
    "ProjectionCommittedRun",
    "TheaterCommittedDirectRun",
    "DirectRunIdentityFor(",
    "DirectCacheRunMatchesLatest(",
)
require(
    cache_quad,
    "R24 cached projection current direct run guard",
    "DirectCacheRunMatchesLatest(ProjectionCommittedRun)",
    "(!TheaterCommittedDirectRun.Valid() ||",
    "DirectCacheRunMatchesLatest(TheaterCommittedDirectRun)",
)
require_order(
    cache_quad,
    "R24 cached projection ownership before theater fallback",
    "DirectCacheRunMatchesLatest(ProjectionCommittedRun)",
    "BuildViewQuad(Projection.handle",
    "TheaterCommittedDirectRun.Valid()",
    "BuildViewQuad(Theater.handle",
)

direct_projection = body(host_r24, "inline bool TryBuildDirectSafeProjection(")
require_order(
    direct_projection,
    "R24 projection provenance after successful release",
    "RenderSafeProjectionChecked(session, endInfo, projection, views)",
    "ProjectionCommittedRun = DirectRunIdentityFor(snapshot.frame);",
    "return ProjectionCommittedRun.Valid();",
)
require_order(
    direct_flat,
    "R24 direct-flat provenance after successful release",
    "TheaterCommittedGeneration = OutRunVrSbsCaptureOverride::Theater.generation;",
    "TheaterCommittedDirectRun = DirectRunIdentityFor(latest);",
    "if (!TheaterCommittedDirectRun.Valid())",
    "BuildViewQuad(Theater.handle",
)

emergency_quad = body(host_r24, "inline bool BuildEmergencyVisibleQuad(")
require_order(
    emergency_quad,
    "R24 emergency clear records swapchain GPU work before flush",
    "OutRunVrFinalTest::Context->ClearRenderTargetView(",
    "Theater.NoteGpuWorkSubmitted();",
    "OutRunVrFinalTest::Context->Flush();",
    "Release(Theater, true)",
)
require_order(
    emergency_quad,
    "R24 emergency theater clears direct provenance",
    "TheaterCommittedGeneration = OutRunVrSbsCaptureOverride::Theater.generation;",
    "TheaterCommittedDirectRun = {};",
    "BuildViewQuad(Theater.handle",
)

visible_fallback = body(host_r24, "inline XrResult SubmitVisibleFallback(")
require(
    visible_fallback,
    "R24 live theater clears direct provenance",
    "if (live)",
    "TheaterCommittedDirectRun = {};",
)

r32_destroy = body(host_submit, "inline XrResult XRAPI_CALL DestroySession(")
require_order(
    r32_destroy,
    "R32 transactional session teardown",
    "const XrResult result =",
    "OutRunVrR26RecenterHardening::DestroySession(session);",
    "if (XR_SUCCEEDED(result))",
    "ReleasePending();",
    "OutRunVrD3D9ExDirectPassthrough::R32ResetDirectCaches();",
    "return result;",
)
forbid(
    r32_destroy,
    "R32 destroy must not bypass R26 recenter owner",
    "OutRunVrR24BlackScreenGuard::DestroySession(session)",
)

review_destroy = body(host_review, "inline XrResult XRAPI_CALL DestroySession(")
require_order(
    review_destroy,
    "R15 transactional session teardown",
    "const XrResult result =",
    "OutRunVrD3D9ExDirectPassthrough::DestroySession(session);",
    "if (XR_SUCCEEDED(result))",
    "LastClassicFrameId = 0;",
    "LastClassicRunGeneration = 0;",
    "LastClassicGamePid = 0;",
    "LastClassicAdvanceMs = 0;",
    "return result;",
)

r23_destroy = body(host_r23_runtime, "inline XrResult XRAPI_CALL DestroySession(")
require_order(
    r23_destroy,
    "R23 transactional session teardown",
    "const XrResult result =",
    "OutRunVrR22RuntimeHardening::DestroySession(session);",
    "if (XR_SUCCEEDED(result))",
    "OutRunVrR23VerifiedBundle::Invalidate();",
    "RecordFinalSubmission(",
    "return result;",
)

r24_destroy = body(host_r24, "inline XrResult XRAPI_CALL DestroySession(")
require_order(
    r24_destroy,
    "R24 transactional session teardown",
    "const XrResult result =",
    "OutRunVrR23RuntimeHardening::DestroySession(session);",
    "if (XR_SUCCEEDED(result))",
    "ProjectionCommittedGeneration = 0;",
    "TheaterCommittedGeneration = 0;",
    "ProjectionCommittedRun = {};",
    "TheaterCommittedDirectRun = {};",
    "return result;",
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
    "(resource/ACK teardown, monotonic generation, fail-close reset, "
    "host complete-run stale ACK rejection)"
)
