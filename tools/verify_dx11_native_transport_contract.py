#!/usr/bin/env python3
"""Fail closed if the dormant native DX11 shared-eye transport loses its lifetime gates."""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def require(path: str, needles: list[str]) -> str:
    text = (ROOT / path).read_text(encoding="utf-8")
    missing = [needle for needle in needles if needle not in text]
    if missing:
        raise SystemExit(f"{path}: missing native transport contract evidence: {missing}")
    return text


def verify_eye_pair_submission(body: str) -> None:
    """Validate both the historical 1x copy producer and the MSAA-capable
    two-eye transfer without requiring obsolete single-argument signatures.
    Every source/format/provenance check must precede *both* GPU writes.
    """
    common = [
        "same_producer_context(context) == false",
        "entry.state != SharedEyeSlotState::Acquired",
        "source->GetDevice(owner.GetAddressOf())",
        "context->CopyResource(entry.eye[0].Get(), left_source);",
        "context->CopyResource(entry.eye[1].Get(), right_source);",
        "entry.gpu_copy_queued = true;",
        "if (!signal_producer_fence(context, slot, frame_id)) {",
    ]
    for needle in common:
        if needle not in body:
            raise SystemExit(f"DX11 R306 native producer missing: {needle}")
    # The legacy one-line return cannot protect a submitted D3D11 GPU copy
    # if EVENT arming fails. The failure branch must quarantine the exact
    # generation; do not relax this contract to make a new eye transfer pass.
    failure_branch = re.search(
        r"if \(!signal_producer_fence\(context, slot, frame_id\)\)\s*\{"
        r"[^{}]*synchronization_faulted_ = true;\s*return false;\s*\}\s*return true;",
        body, re.DOTALL,
    )
    if not failure_branch or "reset_slot_lifetime(entry)" in body[failure_branch.start():]:
        raise SystemExit("DX11 submitted stereo eye copies must quarantine on failed EVENT arming")
    legacy = "!exact_source(left_source) || !exact_source(right_source)"
    msaa = [
        "!exact_source(left_source, leftDesc)",
        "!exact_source(right_source, rightDesc)",
        "desc.SampleDesc.Count == 0",
        "producer_device_->CheckFormatSupport(format_, &formatSupport)",
        "formatSupport & D3D11_FORMAT_SUPPORT_MULTISAMPLE_RESOLVE",
        "native_game_eye_transfer(",
        "transfer == NativeGameEyeTransfer::Reject",
        "native_game_eye_pair_sources_admitted(",
        "transfer == NativeGameEyeTransfer::Resolve",
        "context->ResolveSubresource(entry.eye[0].Get(), 0u, left_source, 0u, format_);",
        "context->ResolveSubresource(entry.eye[1].Get(), 0u, right_source, 0u, format_);",
    ]
    is_msaa = "native_game_eye_transfer(" in body or "ResolveSubresource(" in body
    if is_msaa:
        for needle in msaa:
            if needle not in body:
                raise SystemExit(f"DX11 MSAA producer missing preflight/resolve: {needle}")
        checkpoints = [
            "!exact_source(left_source, leftDesc)",
            "!exact_source(right_source, rightDesc)",
            "producer_device_->CheckFormatSupport(format_, &formatSupport)",
            "native_game_eye_transfer(",
            "transfer == NativeGameEyeTransfer::Reject",
            "native_game_eye_pair_sources_admitted(",
            "entry.gpu_copy_queued = true;",
            "context->ResolveSubresource(entry.eye[0].Get()",
            "context->ResolveSubresource(entry.eye[1].Get()",
            "context->CopyResource(entry.eye[0].Get()",
            "context->CopyResource(entry.eye[1].Get()",
            "if (!signal_producer_fence(",
        ]
        positions = [body.index(token) for token in checkpoints]
        # Resolve and Copy are mutually exclusive GPU paths. Every source
        # admission must complete before the slot is marked GPU-owned; each
        # eye write must then precede the guarded producer EVENT.
        preflight = positions[:6]
        queued = positions[6]
        eyes = positions[7:11]
        fence = positions[11]
        if preflight != sorted(preflight) or not (
            preflight[-1] < queued
            and all(queued < pos < fence for pos in eyes)
            and eyes[0] < eyes[1]
            and eyes[2] < eyes[3]
        ):
            raise SystemExit("DX11 MSAA admission/copy/resolve/GPU ownership must precede guarded fence")
        # 00842 actual game-camera texture arrays: two distinct physical
        # source slices, not two views of the same eye or stale ring alias.
        # This is a GPU transfer implementation contract, not fabricated
        # proof that the live R30 renderer has attached its camera callback.
        source_guards = (
            "left_array_slice >= leftDesc.ArraySize",
            "right_array_slice >= rightDesc.ArraySize",
            "leftIdentity.Get() == rightIdentity.Get()",
            "left_array_slice == right_array_slice",
        )
        slice_writes = (
            "context->CopySubresourceRegion(entry.eye[0].Get()",
            "context->CopySubresourceRegion(entry.eye[1].Get()",
            "D3D11CalcSubresource(0u, left_array_slice, leftDesc.MipLevels)",
            "D3D11CalcSubresource(0u, right_array_slice, rightDesc.MipLevels)",
        )
        for needle in source_guards + slice_writes:
            if needle not in body:
                raise SystemExit("DX11 00842 missing real array-slice mip-zero GPU path: " + needle)
        for needle in source_guards:
            if body.index(needle) >= queued:
                raise SystemExit("DX11 eye source slice and alias admission must precede GPU writes")
        for needle in slice_writes:
            if not queued < body.index(needle) < fence:
                raise SystemExit("DX11 eye array mip-zero copy must precede producer EVENT")
    elif legacy in body:
        if not (
            body.index(legacy) < body.index("entry.gpu_copy_queued = true;")
            < body.index("context->CopyResource(entry.eye[0]")
            < body.index("context->CopyResource(entry.eye[1]")
            < body.index("if (!signal_producer_fence(")
        ):
            raise SystemExit("DX11 legacy eye pair must validate before both GPU copies")
    else:
        raise SystemExit("DX11 stereo source validation missing or obsolete signature")


def verify_direct_eye_render(body: str) -> None:
    """Verify direct native left/right Draw recording cannot publish or
    recycle a partial pair when callback work or EVENT arming fails.
    """
    required = [
        "!activation_ready()",
        "!same_producer_context(context)",
        "!recorder",
        "entry.state != SharedEyeSlotState::Acquired",
        "entry.frame_id != frame_id",
        "entry.gpu_copy_queued",
        "!entry.rtv[0] || !entry.rtv[1] || !entry.producer_fence",
        "entry.gpu_copy_queued = true;",
        "recorder(user, context, entry.rtv[0].Get(), entry.rtv[1].Get())",
        "if (!signal_producer_fence(context, slot, frame_id))",
    ]
    for needle in required:
        if needle not in body:
            raise SystemExit("DX11 direct native game-eye GPU producer missing: " + needle)
    queued = body.index("entry.gpu_copy_queued = true;")
    recorded = body.index("recorder(user, context, entry.rtv[0].Get(), entry.rtv[1].Get())")
    signal = body.index("if (!signal_producer_fence(context, slot, frame_id))")
    if not queued < recorded < signal:
        raise SystemExit("DX11 direct eye draw must reserve GPU ownership before both draws")
    if len(re.findall(r"synchronization_faulted_\s*=\s*true;", body)) != 2:
        raise SystemExit("DX11 direct eye recorder and EVENT failures must BOTH quarantine")
    if not re.search(
        r"if\s*\(!recorder\(user, context, entry\.rtv\[0\]\.Get\(\),"
        r" entry\.rtv\[1\]\.Get\(\)\)\)\s*\{"
        r"\s*synchronization_faulted_ = true;\s*return false;\s*\}",
        body,
    ):
        raise SystemExit("DX11 direct eye partial render must quarantine")
    if not re.search(
        r"if\s*\(!signal_producer_fence\(context, slot, frame_id\)\)\s*\{"
        r"\s*synchronization_faulted_ = true;\s*return false;\s*\}",
        body,
    ):
        raise SystemExit("DX11 direct eye producer EVENT failure must quarantine")
    if "reset_slot_lifetime(entry)" in body:
        raise SystemExit("DX11 direct native GPU recorder must never reuse partial eyes")

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
    # Both native production paths must validate the exact immediate owner:
    # the copy/resolve source and the direct two-eye Draw recorder. Do not
    # depend on a frozen string count that omits new context-bearing methods.
    contexts = (
        ("refresh_unpublished_fence", "try_acquire_slot"),
        ("try_acquire_slot", "cancel_acquired_slot"),
        ("submit_eye_pair", "render_eye_pair"),
        ("render_eye_pair", "signal_producer_fence"),
        ("signal_producer_fence", "publish_if_fence_complete"),
        ("publish_if_fence_complete", "snapshot_published_frame"),
    )
    for before, after in contexts:
        start = ring_cpp.find("NativeSharedEyeRing::" + before + "(")
        end = ring_cpp.find("NativeSharedEyeRing::" + after + "(", start)
        if start < 0 or end <= start:
            raise SystemExit("DX11 native ring context owner boundary missing: " + before)
        body = ring_cpp[start:end]
        if before == "submit_eye_pair":
            if "same_producer_context(context) == false" not in body:
                raise SystemExit("DX11 copy/resolve must verify immediate device context")
        elif "!same_producer_context(context)" not in body:
            raise SystemExit("DX11 producer context owner guard missing: " + before)
    copy_start = ring_cpp.find("bool NativeSharedEyeRing::submit_eye_pair(")
    direct_start = ring_cpp.find("bool NativeSharedEyeRing::render_eye_pair(", copy_start)
    signal_start = ring_cpp.find("bool NativeSharedEyeRing::signal_producer_fence(", direct_start)
    if copy_start < 0 or direct_start <= copy_start or signal_start <= direct_start:
        raise SystemExit("DX11 both native stereo GPU producer paths must be connected")
    verify_eye_pair_submission(ring_cpp[copy_start:direct_start])
    verify_direct_eye_render(ring_cpp[direct_start:signal_start])
    probe_source = (ROOT / "tools/dx11_native_transport_probe.cpp").read_text(
        encoding="utf-8")
    if "R306 left/right GPU pixel copy identity" not in probe_source:
        raise SystemExit("DX11 R306 two-eye GPU pixel validation missing")
    for needle in (
        "00842 aliased same slice and invalid slice reject before GPU",
        "00842 native producer submits two independent GPU array-slice eyes",
        "00842 independent mip-zero L/R GPU pixel identity",
        "00842 stereo GPU host handoff and exact ACK retirement",
    ):
        if needle not in probe_source:
            raise SystemExit("DX11 00842 WARP native game stereo array regression missing: " + needle)
    for needle in [
        "foreign.device->OpenSharedResource(",
        "foreign.context->CopyResource(hostReadback, hostEyes[eyeIndex]);",
        "R306 foreign host shared handle preserves both eye colors",
    ]:
        if needle not in probe_source:
            raise SystemExit(f"DX11 R306 host GPU consumer evidence missing: {needle}")


    # EVENT completion must not depend on an unrelated game Present or
    # test-side Flush: production submits immediately after End, while
    # consumer polling remains DONOTFLUSH and non-blocking.
    signal_start = ring_cpp.find("bool NativeSharedEyeRing::signal_producer_fence(")
    publish_start = ring_cpp.find("bool NativeSharedEyeRing::publish_if_fence_complete(", signal_start)
    if signal_start < 0 or publish_start <= signal_start:
        raise SystemExit("DX11 producer EVENT submission boundary missing")
    signal_body = ring_cpp[signal_start:publish_start]
    end_pos = signal_body.find("context->End(entry.producer_fence.Get());")
    flush_pos = signal_body.find("context->Flush();")
    pending_pos = signal_body.find("entry.state = SharedEyeSlotState::ProducerPending;")
    if not (0 <= end_pos < flush_pos < pending_pos) or signal_body.count("context->Flush();") != 1:
        raise SystemExit("DX11 producer must flush EVENT before entering ProducerPending")
    if "D3D11_ASYNC_GETDATA_DONOTFLUSH" not in publish_body:
        raise SystemExit("DX11 producer fence polling must remain nonblocking")
    probe_cpp = (ROOT / "tools/dx11_native_transport_probe.cpp").read_text(
        encoding="utf-8"
    )
    probe_start = probe_cpp.find("void publish_bounded(")
    probe_end = probe_cpp.find("int main()", probe_start)
    if probe_start < 0 or probe_end <= probe_start or (
        "context->Flush();" in probe_cpp[probe_start:probe_end]
    ):
        raise SystemExit("DX11 WARP probe must not hide a missing producer Flush")

    # R178: the acquired slot must remain quarantined after invalidation.
    # This path does not query a GPU fence, so an invalidated generation
    # cannot safely cancel and reuse it.
    cancel_start = ring_cpp.find("bool NativeSharedEyeRing::cancel_acquired_slot(")
    signal_start = ring_cpp.find(
        "bool NativeSharedEyeRing::signal_producer_fence(", cancel_start)
    if cancel_start < 0 or signal_start <= cancel_start:
        raise SystemExit("DX11 R178 cancel/producer fence boundary missing")
    cancel_body = ring_cpp[cancel_start:signal_start]
    copy_guard = "!native_game_eye_copy_cancelable(entry.gpu_copy_queued)"
    if copy_guard not in cancel_body or (
        cancel_body.index(copy_guard) > cancel_body.index("reset_slot_lifetime(entry);")
    ):
        raise SystemExit("DX11 acquired eye slot with GPU copy queued must not be cancelled")
    lifetime_guard = "if (!activation_ready() || slot >= slots_.size())"
    if lifetime_guard not in cancel_body or (
        cancel_body.index(lifetime_guard) >
        cancel_body.index("reset_slot_lifetime(entry);")
    ):
        raise SystemExit("DX11 R178 invalidated acquired slot may be recycled")
    for needle in [
        "R178 invalidated acquired slot cannot be cancelled or recycled",
        "R178 invalidated acquired slot blocks generation retag",
    ]:
        if needle not in probe_cpp:
            raise SystemExit(f"DX11 R178 WARP negative control missing: {needle}")
    print("DX11 R178 invalidated acquired-slot cancel guard: OK")
    print("DX11 native transport lifetime contract: OK")


if __name__ == "__main__":
    main()
