#!/usr/bin/env python3
"""Static contract for the stock-DXVK host-owned shared-eye transport.

This verifier does not claim runtime success. It protects the synchronization
and lifetime invariants that the DXVK bridge must inherit from the established
DirectGPU path until Quest3/VDXR evidence proves the transport in hardware.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(rel: str) -> str:
    path = ROOT / rel
    if not path.is_file():
        raise SystemExit(f"DXVK host-owned transport contract missing file: {rel}")
    return path.read_text(encoding="utf-8")


def require(rel: str, *markers: str) -> str:
    data = load(rel)
    for marker in markers:
        if marker not in data:
            raise SystemExit(
                f"DXVK host-owned transport invariant missing: {rel} :: {marker}"
            )
    return data


def ordered(data: str, rel: str, *markers: str) -> None:
    cursor = -1
    for marker in markers:
        pos = data.find(marker, cursor + 1)
        if pos < 0:
            raise SystemExit(
                f"DXVK host-owned transport order marker missing: {rel} :: {marker}"
            )
        if pos <= cursor:
            raise SystemExit(
                f"DXVK host-owned transport ordering regressed: {rel} :: {marker}"
            )
        cursor = pos


bridge = require(
    "src/vr/ipc/dxvk_shared_eye_bridge.hpp",
    "MemoryName[]",
    "Version = 1",
    "HostAlive = 1u << 0",
    "ResourcesReady = 1u << 1",
    "std::uint64_t leftHandle",
    "std::uint64_t rightHandle",
    "Slot slots[OutRunVR::RenderFrameRingSize]",
    "static_assert(sizeof(Slot) == 16)",
    "static_assert(sizeof(State) == 136)",
)
if "std::uintptr_t leftHandle" in bridge or "std::uintptr_t rightHandle" in bridge:
    raise SystemExit("DXVK bridge reintroduced pointer-width shared-memory ABI")

host = require(
    "vrhost/src/main.cpp",
    "bool InitializeDxvkHostSharedBridge()",
    "ShutdownDxvkHostSharedBridge();",
    "D3D11_RESOURCE_MISC_SHARED",
    "GetSharedHandle(&handle)",
    "for (std::uint32_t slot = 0;",
    "slot < OutRunVR::RenderFrameRingSize",
    "dxvkBridgeState_->slots[slot].leftHandle",
    "dxvkBridgeState_->slots[slot].rightHandle",
    "dxvkBridgeState_->magic =",
    "OutRunVR::DxvkSharedEyeBridge::Magic",
    "PublishDxvkHostSharedBridge(true)",
)
host_init_start = host.find("bool InitializeDxvkHostSharedBridge()")
host_reset_start = host.find("void Reset()", host_init_start)
if host_init_start < 0 or host_reset_start < 0:
    raise SystemExit("could not isolate DXVK host-owned bridge initializer")
host_init = host[host_init_start:host_reset_start]
ordered(
    host_init,
    "vrhost/src/main.cpp::InitializeDxvkHostSharedBridge",
    "ShutdownDxvkHostSharedBridge();",
    "dxvkBridgeState_->generation = dxvkBridgeGeneration_;",
    "for (std::uint32_t slot = 0;",
    "MemoryBarrier();",
    "dxvkBridgeState_->magic =",
    "dxvkBridgeReady_ = true;",
    "PublishDxvkHostSharedBridge(true);",
)
for marker in (
    "&dxvkBridgeLeft_[slot]",
    "dxvkBridgeState_->slots[slot].leftHandle",
    "&dxvkBridgeRight_[slot]",
    "dxvkBridgeState_->slots[slot].rightHandle",
):
    if marker not in host_init:
        raise SystemExit(
            f"DXVK bridge must allocate both eyes for every ring slot before publish: {marker}"
        )

game = require(
    "src/vr/d3d9/stereo_renderer_r7.inc",
    "bool ReadDxvkHostBridgeState",
    "const std::uint32_t before=DxvkHostBridgeState->sequence",
    "std::memcpy(&out,DxvkHostBridgeState,sizeof(out))",
    "const std::uint32_t after=DxvkHostBridgeState->sequence",
    "before==after&&!(after&1u)",
    "out.magic==OutRunVR::DxvkSharedEyeBridge::Magic",
    "out.version==OutRunVR::DxvkSharedEyeBridge::Version",
    "out.structSize==sizeof(out)",
    "bool EnsureDxvkHostOwnedTransportResources",
    "HostAlive|OutRunVR::DxvkSharedEyeBridge::ResourcesReady",
    "bridge.hostPid!=SharedState->hostPid",
    "DirectTransportGeneration==bridge.generation",
    "DxvkHostBridgeFailedGeneration==bridge.generation",
    "ReleaseDirectTransportSlots();",
    "device->CreateTexture(bridge.width,bridge.height,1,D3DUSAGE_RENDERTARGET",
    "DxvkHostBridgeFailedGeneration=bridge.generation",
    "DirectTransportGeneration=bridge.generation",
    "DirectTransportResourcesReady=true",
    "DirectTransportHostOwnedDxvk=true",
)
read_start = game.find("bool ReadDxvkHostBridgeState")
ensure_start = game.find("bool EnsureDxvkHostOwnedTransportResources", read_start)
target_start = game.find("void DirectTransportTargetSize", ensure_start)
if min(read_start, ensure_start, target_start) < 0:
    raise SystemExit("could not isolate DXVK bridge read/import functions")
read_body = game[read_start:ensure_start]
ensure_body = game[ensure_start:target_start]
ordered(
    read_body,
    "src/vr/d3d9/stereo_renderer_r7.inc::ReadDxvkHostBridgeState",
    "const std::uint32_t before=DxvkHostBridgeState->sequence",
    "MemoryBarrier();",
    "std::memcpy(&out,DxvkHostBridgeState,sizeof(out))",
    "MemoryBarrier();",
    "const std::uint32_t after=DxvkHostBridgeState->sequence",
    "before==after&&!(after&1u)",
)
ordered(
    ensure_body,
    "src/vr/d3d9/stereo_renderer_r7.inc::EnsureDxvkHostOwnedTransportResources",
    "if(!DxvkNativeTransportCandidate)return false;",
    "if(!ReadDxvkHostBridgeState(bridge))return false;",
    "const std::uint32_t requiredFlags=",
    "if((bridge.flags&requiredFlags)!=requiredFlags",
    "if(DxvkHostBridgeFailedGeneration==bridge.generation)return false;",
    "if(DirectTransportResourcesReady)ReleaseDirectTransportSlots();",
    "for(std::uint32_t index=0;index<OutRunVR::RenderFrameRingSize;++index)",
    "DirectTransportGeneration=bridge.generation;",
    "DirectTransportResourcesReady=true;",
    "DirectTransportHostOwnedDxvk=true;",
)

# The host-owned bridge must feed the same producer slot state machine as the
# existing DirectGPU path. Publication occurs only after the producer EVENT,
# and published slots remain immutable until the R13 exact per-slot ACK.
require(
    "src/vr/d3d9/stereo_renderer_r7.inc",
    "bool ResolveDirectTransport",
    "slot.producerPending=true",
    "slot.published=false",
    "bool DirectTransportFrameReadyAfterPresent",
    "slot.published=true",
    "S_FALSE stays quarantined",
)
r13 = require(
    "src/vr/d3d9/stereo_renderer_r13_overlay.inc",
    "R13ReadGpuCompletedFrame",
    "DirectGpuAckIdentityMatches",
    "SharedState->hostPid",
    "GetCurrentProcessId()",
    "RenderFrameRunGeneration",
    "DirectTransportGeneration",
    "snapshot.completedFrameId[slotIndex]",
    "if (slot.published && slot.frameId)",
    "R13ReadGpuCompletedFrame(index, gpuCompleted)",
    "if (!ackValid ||",
    "!FrameIdAtOrAfter(gpuCompleted, slot.frameId)",
    "slot.frameId = 0;",
    "slot.published = false;",
)
ack_read_start = r13.find("bool R13ReadGpuCompletedFrame")
resolve_start = r13.find("bool ResolveDirectTransportR13", ack_read_start)
if min(ack_read_start, resolve_start) < 0:
    raise SystemExit("could not isolate R13 exact ACK path")
ack_body = r13[ack_read_start:resolve_start]
ordered(
    ack_body,
    "src/vr/d3d9/stereo_renderer_r13_overlay.inc::R13ReadGpuCompletedFrame",
    "const std::uint32_t before = R13AckState->sequence;",
    "std::memcpy(&snapshot, R13AckState, sizeof(snapshot));",
    "const std::uint32_t after = R13AckState->sequence;",
    "DirectGpuAckIdentityMatches(",
    "SharedState->hostPid",
    "GetCurrentProcessId()",
    "RenderFrameRunGeneration",
    "DirectTransportGeneration",
    "completedFrame = snapshot.completedFrameId[slotIndex];",
)

host_r23 = require(
    "vrhost/src/main_r23.cpp",
    "bool R23StageDirectHold",
    "c.context_->CopyResource(R23DirectHold.eye[0], c.directLeft_[slot])",
    "c.context_->CopyResource(R23DirectHold.eye[1], c.directRight_[slot])",
    "R23DirectHold.frameId = frame.frameId",
    "R23DirectHold.generation = generation",
    "R23DirectHold.valid = true",
    "PublishCompletedFrame(frame)",
    "older unsampled ring frames are ACKed immediately",
)
stage_start = host_r23.find("bool R23StageDirectHold")
source_kind_start = host_r23.find("const char* R23SourceKindName", stage_start)
if min(stage_start, source_kind_start) < 0:
    raise SystemExit("could not isolate R23 host-owned hold copy")
stage_body = host_r23[stage_start:source_kind_start]
ordered(
    stage_body,
    "vrhost/src/main_r23.cpp::R23StageDirectHold",
    "c.context_->CopyResource(R23DirectHold.eye[0], c.directLeft_[slot])",
    "c.context_->CopyResource(R23DirectHold.eye[1], c.directRight_[slot])",
    "R23DirectHold.frameId = frame.frameId;",
    "R23DirectHold.generation = generation;",
    "R23DirectHold.valid = true;",
)

# Set 08 F30 deliberately retains exactly one left/right CopyResource pair per
# accepted DirectGPU producer frame. Guard against accidental reintroduction of
# the legacy private snapshot/fence path or additional hold-copy amplification.
if stage_body.count("CopyResource(") != 2:
    raise SystemExit(
        "R23StageDirectHold must contain exactly one left/right CopyResource pair"
    )
for forbidden in (
    "directSnapshotLeft_",
    "directSnapshotRight_",
    "CommitDirectStereoSource(",
    "context_->Flush()",
    "c.context_->Flush()",
):
    if forbidden in stage_body:
        raise SystemExit(
            "R23StageDirectHold regressed into legacy snapshot/flush work: "
            + forbidden
        )

direct_commit_start = host_r23.find("bool R23CommitDirectAfterValidation")
classic_commit_start = host_r23.find(
    "bool R23CommitClassicAfterValidation", direct_commit_start
)
if min(direct_commit_start, classic_commit_start) < 0:
    raise SystemExit("could not isolate R23 production DirectGPU commit path")
direct_commit_body = host_r23[direct_commit_start:classic_commit_start]
ordered(
    direct_commit_body,
    "vrhost/src/main_r23.cpp::R23CommitDirectAfterValidation",
    "c.PrepareDirectStereoSource(frame)",
    "R23ValidateDirectResourceSize(c, frame)",
    "R23StageDirectHold(c, frame)",
    "c.directTransportReady_ = true;",
    "c.directFrameValid_ = true;",
)
for forbidden in (
    "CommitDirectStereoSource(",
    "directSnapshotLeft_",
    "directSnapshotRight_",
    "CopyResource(",
    "Flush()",
):
    if forbidden in direct_commit_body:
        raise SystemExit(
            "R23 production DirectGPU commit path bypasses the single-copy hold stage: "
            + forbidden
        )

# VR-HOST-002 post-review closure. The old reconciliation candidate is
# historical only; protect the current run-identity, stale-run rejection,
# verified handoff, loading/stall hold, and exact fallback contracts.
protocol = require(
    "src/vr/ipc/protocol.hpp",
    "RenderFrameRunGenerationIndex = 11",
    "bool RenderFrameRunIdentityMatches(",
    "ring.clientPid != 0",
    "ring.reserved0 != 0",
    "frame.clientPid == ring.clientPid",
    "frame.reserved[RenderFrameRunGenerationIndex] == ring.reserved0",
)

for marker in (
    "bool ClaimRenderFrameRingForCurrentRun() noexcept",
    "RenderFrameRing->clientPid = self;",
    "RenderFrameRing->reserved0 = RenderFrameRunGeneration;",
    "std::memset(&slot, 0, sizeof(slot));",
    "frame.reserved[OutRunVR::RenderFrameRunGenerationIndex]=RenderFrameRunGeneration",
    "const bool holdPreviousProjection=R67HoldPreviousProjectionThisPresent;",
):
    if marker not in game:
        raise SystemExit(
            f"VR-HOST-002 producer/run-hold invariant missing: {marker}"
        )

for marker in (
    "class RenderFrameReader",
    "bool ReadSlot(std::uint32_t index",
    "OutRunVR::RenderFrameRunIdentityMatches(*state_, out)",
):
    if marker not in host:
        raise SystemExit(
            f"VR-HOST-002 host stale-run rejection invariant missing: {marker}"
        )

for marker in (
    "const bool cachedHold = cachedProjectionValid;",
    'finalLayerKind = "projection-cached";',
    "pendingBundlePublish = true;",
    "OutRunVrR23VerifiedBundle::Publish(",
    'finalLayerKind = "direct-only-no-classic-fallback";',
    "generation != currentGeneration",
):
    if marker not in host_r23:
        raise SystemExit(
            f"VR-HOST-002 verified handoff/hold invariant missing: {marker}"
        )

r23_hardening = require(
    "vrhost/src/runtime/r23_runtime_hardening.hpp",
    "OutRunVrR23VerifiedBundle::ReadFresh(verified)",
    "OutRunVrSbsCaptureOverride::FrameComplete(verified.frame)",
    "RenderCommittedDirect(session, endInfo, verified)",
    "const bool exactClassicSource = verified.sourceCaptureQpc > 0",
    "OutRunVrSbsCaptureOverride::LastProductionPresentQpc ==",
    "verified.sourceCaptureQpc",
    "FreshClassicFallbackAvailable()",
    "classic fallback blocked: current production capture is not the committed bundle source",
)

frame_identity_smoke = require(
    "vrhost/tests/frame_run_identity_smoke.cpp",
    "RenderFrameRunIdentityMatches(ring, frame)",
    "frame.clientPid = 1002",
    "ring.reserved0 = 0",
    "Simulate a fast game restart",
)

ack_identity_smoke = require(
    "vrhost/tests/direct_ack_identity_smoke.cpp",
    "DirectGpuAckIdentityMatches(ack, 10, 20, 30, 40)",
    "DirectGpuAckIdentityMatches(ack, 10, 20, 31, 40)",
    "DirectGpuAckIdentityMatches(ack, 10, 20, 30, 41)",
)

cmake = require(
    "vrhost/CMakeLists.txt",
    "outrun-vr-frame-run-identity-smoke",
    "tests/frame_run_identity_smoke.cpp",
    "outrun-vr-direct-ack-identity-smoke",
)
workflow = require(
    ".github/workflows/vr-openxr.yml",
    "Run Frame.v2 producer-run identity regression",
    "outrun-vr-frame-run-identity-smoke.exe",
    "Run exact DirectGPU ACK identity regression",
    "outrun-vr-direct-ack-identity-smoke.exe",
)

# Keep the smoke target in the host build graph; it provides compile-time ABI
# checks in addition to this source-order/lifetime verifier.
require(
    "vrhost/CMakeLists.txt",
    "outrun-vr-dxvk-shared-eye-bridge-smoke",
    "tests/dxvk_shared_eye_bridge_smoke.cpp",
)

print("DXVK host-owned transport synchronization + VR-HOST-002 post-review contract: PASS")
