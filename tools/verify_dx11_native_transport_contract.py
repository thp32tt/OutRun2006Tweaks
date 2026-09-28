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
    require(
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
        ],
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
            "retire_acknowledged",
        ],
    )
    require(
        "src/vr/d3d11/native_shared_eye_ring.cpp",
        [
            "TransportIdentityValid(next)",
            "!all_slots_idle()",
            "D3D11_ASYNC_GETDATA_DONOTFLUSH",
            "context->End(entry.producer_fence.Get())",
            "entry.state = SharedEyeSlotState::ProducerPending",
            "entry.state = SharedEyeSlotState::Published",
            "TransportAckReleasesFrame",
            "reset_slot_lifetime(entry)",
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
    print("DX11 native transport lifetime contract: OK")


if __name__ == "__main__":
    main()
