#!/usr/bin/env python3
"""Fail closed if the dormant native DX11 shared-eye transport loses its lifetime gates."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def require(path: str, needles: list[str]) -> str:
    text = (ROOT / path).read_text(encoding="utf-8")
    missing = [needle for needle in needles if needle not in text]
    if missing:
        raise SystemExit(f"{path}: missing native transport contract evidence: {missing}")
    return text


def main() -> None:
    transport = require(
        "src/vr/core/transport.hpp",
        [
            "D3D11NativeShared = 4",
            "struct TransportIdentity",
            "producerPid",
            "consumerPid",
            "runGeneration",
            "generation",
            "struct FrameAck",
            "TransportIdentityValid",
            "TransportAckIdentityMatches",
            "TransportAckReleasesFrame",
            "ack.slot == slot",
            "ack.frameId >= frameId",
            "class IFrameConsumer",
            "virtual void acknowledge(const FrameAck& ack) noexcept = 0;",
        ],
    )
    if "acknowledge(std::uint64_t frameId)" in transport:
        raise SystemExit(
            "DX11 R117 frameId-only consumer ACK contract must not reappear"
        )
    require(
        "src/vr/d3d11/native_shared_eye_ring.hpp",
        [
            "SharedEyeSlotState",
            "Acquired",
            "ProducerPending",
            "Published",
            "bind_lifetime",
            "activation_ready",
            "try_acquire_slot",
            "signal_producer_fence",
            "publish_if_fence_complete",
            "NativeSharedEyePublication",
            "snapshot_published_frame",
            "validate_publication_snapshot",
            "retire_acknowledged",
            "synchronization_faulted",
            "same_producer_context",
            "producer_device_",
        ],
    )
    require(
        "src/vr/d3d11/native_shared_eye_ring.cpp",
        [
            "TransportIdentityValid(next)",
            "observedDevice.Get() == producer_device_.Get()",
            "context->GetType() != D3D11_DEVICE_CONTEXT_IMMEDIATE",
            "!same_producer_context(context)",
            "!all_slots_idle()",
            "D3D11_ASYNC_GETDATA_DONOTFLUSH",
            "context->End(entry.producer_fence.Get())",
            "entry.state = SharedEyeSlotState::ProducerPending",
            "entry.state = SharedEyeSlotState::Published",
            "NativeSharedEyeRing::snapshot_published_frame",
            "publication.identity != identity_",
            "current.left_handle == publication.left_handle",
            "TransportAckReleasesFrame",
            "A query error does not prove GPU completion",
            "synchronization_faulted_ = true",
        ],
    )
    require(
        "CMakeLists.txt",
        [
            '"src/vr/d3d11/native_shared_eye_ring.cpp"',
            '"src/vr/d3d11/native_shared_eye_ring.hpp"',
        ],
    )
    require(
        "tools/analyze_dx11_census.py",
        [
            '"NativeDrawPathActivationAllowed": False',
        ],
    )
    require(
        "tools/dx11_native_transport_probe.cpp",
        [
            "D3D_DRIVER_TYPE_WARP",
            "ConsumerAckSignature",
            "IFrameConsumer::acknowledge",
            "ring.initialize(",
            "ring.bind_lifetime(",
            "in-flight allocation must reject generation retag",
            "signal_producer_fence",
            "publish_bounded",
            "published frame must produce exact handoff snapshot",
            "fresh published handoff snapshot validates",
            "wrong frame cannot snapshot published handles",
            "ACK retirement invalidates published handoff snapshot",
            "lifetime invalidation rejects stale handoff snapshot",
            "DX11 native shared-eye publication handoff R118: PASS",
            "stale generation ACK cannot retire published slot",
            "foreign-device context cannot acquire a producer slot",
            "foreign-device context cannot signal producer EVENT",
            "foreign-device context cannot publish producer EVENT",
            "foreign-device context cannot recycle pending producer fence",
            "older frame ACK cannot retire newer publication",
            "exact identity/frame ACK retires publication",
            "invalidated lifetime cannot manufacture retirement",
            "fresh allocation accepts next generation",
            "DX11 native shared-eye transport behavior R116: PASS",
        ],
    )
    require(
        "vrhost/tests/direct_ack_identity_smoke.cpp",
        [
            "ConsumerAckSignature",
            "IFrameConsumer::acknowledge",
            "TransportAckReleasesFrame",
        ],
    )

    require(
        "cmake.toml",
        [
            "[target.dx11_native_transport_probe]",
            '"tools/dx11_native_transport_probe.cpp"',
            '"src/vr/d3d11/native_shared_eye_ring.cpp"',
        ],
    )
    require(
        "CMakeLists.txt",
        [
            "# Target: dx11_native_transport_probe",
            "add_executable(dx11_native_transport_probe)",
            '"tools/dx11_native_transport_probe.cpp"',
            '"src/vr/d3d11/native_shared_eye_ring.cpp"',
        ],
    )
    require(
        ".github/workflows/backend-conversion-gate.yml",
        [
            "Build DX11 native transport probe",
            "--target dx11_native_transport_probe",
            "Run DX11 native transport probe",
            "dx11_native_transport_probe.exe",
        ],
    )

    ring_cpp = (ROOT / "src/vr/d3d11/native_shared_eye_ring.cpp").read_text(
        encoding="utf-8"
    )
    refresh_start = ring_cpp.find("bool NativeSharedEyeRing::refresh_unpublished_fence")
    acquire_start = ring_cpp.find("bool NativeSharedEyeRing::try_acquire_slot", refresh_start)
    publish_start = ring_cpp.find("bool NativeSharedEyeRing::publish_if_fence_complete")
    retire_start = ring_cpp.find("bool NativeSharedEyeRing::retire_acknowledged", publish_start)
    if min(refresh_start, acquire_start, publish_start, retire_start) < 0:
        raise SystemExit("DX11 native transport fence lifecycle functions not found")
    refresh_body = ring_cpp[refresh_start:acquire_start]
    publish_body = ring_cpp[publish_start:retire_start]
    if "synchronization_faulted_ = true" not in refresh_body or \
            "A query error does not prove GPU completion" not in refresh_body:
        raise SystemExit("DX11 pending-fence query errors must quarantine the ring")
    if "synchronization_faulted_ = true" not in publish_body:
        raise SystemExit("DX11 publish query errors must quarantine the ring")
    error_tail = refresh_body[refresh_body.find("A query error does not prove GPU completion"):]
    if "reset_slot_lifetime(slot)" in error_tail:
        raise SystemExit("DX11 query-error path must not mark pending GPU work reusable")
    publish_error = publish_body[publish_body.find("if (status != S_OK)"):]
    if "reset_slot_lifetime(entry)" in publish_error:
        raise SystemExit("DX11 publish query-error path must preserve ProducerPending")

    snapshot_start = ring_cpp.find(
        "bool NativeSharedEyeRing::snapshot_published_frame", publish_start
    )
    validate_start = ring_cpp.find(
        "bool NativeSharedEyeRing::validate_publication_snapshot", snapshot_start
    )
    if min(snapshot_start, validate_start) < 0:
        raise SystemExit("DX11 R118 publication snapshot functions not found")
    snapshot_body = ring_cpp[snapshot_start:validate_start]
    validate_body = ring_cpp[validate_start:retire_start]
    for needle in [
        "SharedEyeSlotState::Published",
        "entry.frame_id != frame_id",
        "out.identity = identity_",
        "out.left_handle = entry.shared_handle[0]",
        "out.right_handle = entry.shared_handle[1]",
    ]:
        if needle not in snapshot_body:
            raise SystemExit(
                f"DX11 R118 publication snapshot missing fail-closed evidence: {needle}"
            )
    for needle in [
        "publication.identity != identity_",
        "snapshot_published_frame(",
        "current.left_handle == publication.left_handle",
        "current.right_handle == publication.right_handle",
    ]:
        if needle not in validate_body:
            raise SystemExit(
                f"DX11 R118 publication validation missing stale-snapshot evidence: {needle}"
            )
    if ring_cpp.count("!same_producer_context(context)") != 4:
        raise SystemExit("DX11 native ring must check all four context-bearing paths")
    print("DX11 native transport lifetime contract: OK")


if __name__ == "__main__":
    main()
