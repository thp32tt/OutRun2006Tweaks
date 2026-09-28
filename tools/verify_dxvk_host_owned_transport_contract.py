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
if host_init.count("createSharedEye(") < 3:
    raise SystemExit("DXVK bridge must allocate both eyes for every ring slot before publish")

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
    "src/vr/d3d9/stereo_renderer_r13.cpp",
    "R13ReadGpuCompletedFrame",
    "DirectGpuAckIdentityMatches",
    "SharedState->hostPid",
    "GetCurrentProcessId()",
    "RenderFrameRunGeneration",
    "DirectTransportGeneration",
    "snapshot.completedFrameId[slotIndex]",
    "Published shared eyes remain immutable",
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
    "src/vr/d3d9/stereo_renderer_r13.cpp::R13ReadGpuCompletedFrame",
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

# Keep the smoke target in the host build graph; it provides compile-time ABI
# checks in addition to this source-order/lifetime verifier.
require(
    "vrhost/CMakeLists.txt",
    "outrun-vr-dxvk-shared-eye-bridge-smoke",
    "tests/dxvk_shared_eye_bridge_smoke.cpp",
)

print("DXVK host-owned transport synchronization contract: PASS")
