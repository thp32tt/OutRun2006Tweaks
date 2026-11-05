#!/usr/bin/env python3
"""Destructive source regression for native game camera -> stereo GPU transfers.

This does not substitute for Windows D3D11 compile or Quest 3 runtime evidence.
"""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
ring = (root / "src/vr/d3d11/native_shared_eye_ring.cpp").read_text(encoding="utf-8")
stereo = (root / "src/vr/d3d11/native_game_stereo_submission.cpp").read_text(encoding="utf-8")
helper = (root / "src/vr/d3d11/native_game_gpu_output_preserve.hpp").read_text(encoding="utf-8")

def integrated(ring_src: str, stereo_src: str, helper_src: str) -> bool:
    ring_begin = ring_src.find("} sourceOutputs{context};")
    ring_end = ring_src.find("if (!signal_producer_fence(context, slot, frame_id))", ring_begin)
    if min(ring_begin, ring_end) < 0:
        return False
    ring_transfer = ring_src[ring_begin:ring_end]
    camera_begin = stereo_src.find("ScopedNativePostpassOutputs restore{context_};")
    camera_end = stereo_src.find("return eye_targets_bound();", camera_begin)
    if min(camera_begin, camera_end) < 0:
        return False
    camera_transfer = stereo_src[camera_begin:camera_end]
    stretch_begin = stereo_src.find("if (sampled.Get() != source) {")
    stretch_end = stereo_src.find("ID3D11RenderTargetView* target = eyeTarget_;", stretch_begin)
    if min(stretch_begin, stretch_end) < 0:
        return False
    stretch_transfer = stereo_src[stretch_begin:stretch_end]
    ring_steps = (
        "ScopedNativeGameGpuTransferInputs leftInputs(",
        "ScopedNativeGameGpuTransferInputs rightInputs(",
        "entry.gpu_copy_queued = true;",
        "context->CopyResource(entry.eye[0].Get(), left_source);",
    )
    camera_steps = (
        "ScopedNativePostpassOutputs restore{context_};",
        "ScopedNativeGameGpuTransferInputs eyeCopyInputs(",
        "if (needsResolve) {",
        "context_->ResolveSubresource(",
    )
    stretch_steps = (
        "ScopedNativeGameGpuTransferInputs sampledCopyInputs(",
        "context_->CopySubresourceRegion(",
        "ID3D11RenderTargetView* target = eyeTarget_;",
    )
    def ordered(source: str, steps: tuple[str, ...]) -> bool:
        positions = [source.find(token) for token in steps]
        return all(p >= 0 for p in positions) and positions == sorted(positions)
    return (
        "native_game_gpu_output_preserve.hpp" in ring_src
        and "native_game_gpu_output_preserve.hpp" in stereo_src
        and ordered(ring_transfer, ring_steps)
        and ordered(camera_transfer, camera_steps)
        and ordered(stretch_transfer + "ID3D11RenderTargetView* target = eyeTarget_;",
                    stretch_steps)
        and all(token in helper_src for token in (
            "VSGetShaderResources", "PSGetShaderResources", "GSGetShaderResources",
            "HSGetShaderResources", "DSGetShaderResources", "CSGetShaderResources",
            "resource == destination_", "set(stage, slot, &empty);",
            "set(entry.stage, entry.slot, &entry.view);"
        ))
    )

assert integrated(ring, stereo, helper)
for mutation in (
    (ring.replace("ScopedNativeGameGpuTransferInputs leftInputs(", "REMOVED leftInputs(", 1), stereo, helper),
    (ring.replace("ScopedNativeGameGpuTransferInputs rightInputs(", "REMOVED rightInputs(", 1), stereo, helper),
    (ring, stereo.replace("ScopedNativeGameGpuTransferInputs eyeCopyInputs(", "REMOVED eyeCopyInputs(", 1), helper),
    (ring, stereo.replace("ScopedNativeGameGpuTransferInputs sampledCopyInputs(", "REMOVED sampledCopyInputs(", 1), helper),
    (ring, stereo, helper.replace("resource == destination_", "false", 1)),
):
    assert not integrated(*mutation), "destructive regression was not detected"
print("PASS native XR L/R eye, camera and stretch GPU transfer SRV preservation")
