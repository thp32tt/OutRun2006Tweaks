#!/usr/bin/env python3
"""DX11 live stereo GPU copy -> fence -> cancellation lifetime regression."""
from pathlib import Path
import subprocess
import tempfile
from verify_dx11_native_transport_contract import (
    verify_eye_pair_submission,
    verify_direct_eye_render,
)

ROOT = Path(__file__).resolve().parent.parent
ring = (ROOT / "src/vr/d3d11/native_shared_eye_ring.cpp").read_text(encoding="utf-8")
slot = (ROOT / "src/vr/d3d11/native_shared_eye_ring.hpp").read_text(encoding="utf-8")
probe = ROOT / "tools/dx11_eye_copy_lifetime_probe_00721.cpp"

def linked(source: str, header: str) -> bool:
    copy_start = source.find("bool NativeSharedEyeRing::submit_eye_pair(")
    copy_end = source.find("bool NativeSharedEyeRing::render_eye_pair(", copy_start)
    cancel_start = source.find("bool NativeSharedEyeRing::cancel_acquired_slot(")
    cancel_end = source.find("bool NativeSharedEyeRing::submit_eye_pair(", cancel_start)
    reset_start = source.find("void NativeSharedEyeRing::reset_slot_lifetime(")
    reset_end = source.find("bool NativeSharedEyeRing::refresh_unpublished_fence(", reset_start)
    if min(copy_start, copy_end, cancel_start, cancel_end, reset_start, reset_end) < 0:
        return False
    submit = source[copy_start:copy_end]
    cancel = source[cancel_start:cancel_end]
    reset = source[reset_start:reset_end]
    queued = submit.find("entry.gpu_copy_queued = true;")
    first_copy = submit.find("context->CopyResource(entry.eye[0].Get(), left_source);")
    first_resolve = submit.find("context->ResolveSubresource(entry.eye[0].Get()")
    signal = submit.find("if (!signal_producer_fence(context, slot, frame_id))")
    fault = submit.find("synchronization_faulted_ = true;", signal)
    return (
        "bool gpu_copy_queued{};" in header
        and "slot.gpu_copy_queued = false;" in reset
        and "!native_game_eye_copy_cancelable(entry.gpu_copy_queued)" in cancel
        and "entry.gpu_copy_queued || !entry.eye[0]" in submit
        and queued >= 0 and first_copy > queued and first_resolve > queued
        and signal > first_copy and fault > signal
    )

# Real menu/car/race pixel UAV state must survive native L/R GPU eye copy.
# Two OM calls are needed: detach writable source aliases, then restore
# MRT/depth/pixel UAV prefix with -1 counter preservation.
def preserves_game_pixel_uavs(source: str) -> bool:
    begin = source.find("struct ScopedStereoSourceOutputs final {")
    end = source.find("} sourceOutputs{context};", begin)
    if begin < 0 or end < 0:
        return False
    portion = source[begin:end]
    return (
        "OMGetRenderTargetsAndUnorderedAccessViews(" in portion
        and portion.count("OMSetRenderTargetsAndUnorderedAccessViews(") == 2
        and "pixelOutputs + rtCount" in portion
        and "D3D11_PS_CS_UAV_REGISTER_COUNT - rtCount" in portion
        and "counter = UINT(-1)" in portion
        and "for (auto* output : pixelOutputs)" in portion
        and portion.count("CSSetUnorderedAccessViews(") == 2
    )

submit = ring[ring.index("bool NativeSharedEyeRing::submit_eye_pair("):
              ring.index("bool NativeSharedEyeRing::render_eye_pair(")]
assert preserves_game_pixel_uavs(submit), "native eye copy lost OM/CS UAV restoration"
for old, replacement in [
    ("OMGetRenderTargetsAndUnorderedAccessViews(", "OMGetRenderTargets("),
    ("OMSetRenderTargetsAndUnorderedAccessViews(", "OMSetRenderTargets("),
    ("pixelOutputs + rtCount", "computeOutputs + rtCount"),
    ("counter = UINT(-1)", "counter = 0u"),
]:
    assert old in submit
    assert not preserves_game_pixel_uavs(submit.replace(old, replacement))

assert linked(ring, slot), "native stereo GPU command or cancellation link missing"
# The mandatory Backend Conversion verifier must accept the guarded EVENT
# producer and reject destructive changes to GPU ownership/fence semantics.
verify_eye_pair_submission(submit)
for label, before, after in [
    ("missing GPU-queued ownership", "entry.gpu_copy_queued = true;", "/* unsafe */"),
    ("missing second eye copy", "context->CopyResource(entry.eye[1].Get(), right_source);", "/* unsafe */"),
    ("missing fence quarantine", "synchronization_faulted_ = true;", "/* unsafe */"),
    ("inverted EVENT failure", "if (!signal_producer_fence(context, slot, frame_id)) {",
     "if (signal_producer_fence(context, slot, frame_id)) {"),
]:
    assert before in submit, label
    try:
        verify_eye_pair_submission(submit.replace(before, after, 1))
    except SystemExit:
        pass
    else:
        raise AssertionError("native transport verifier accepted unsafe mutant: " + label)
# New native Draw producer must preserve the exact same GPU ownership and
# fail-closed transport guarantees, not borrow unrelated copy-path tokens.
direct = ring[ring.index("bool NativeSharedEyeRing::render_eye_pair("):
              ring.index("bool NativeSharedEyeRing::signal_producer_fence(")]
verify_direct_eye_render(direct)
for label, old, new in [
    ("direct missing ownership", "entry.gpu_copy_queued = true;", "/* unsafe */"),
    ("direct eye aliased", "entry.rtv[1].Get()", "entry.rtv[0].Get()"),
    ("direct missing callback quarantine", "synchronization_faulted_ = true;", "/* unsafe */"),
    ("direct wrong EVENT polarity",
     "if (!signal_producer_fence(context, slot, frame_id))",
     "if (signal_producer_fence(context, slot, frame_id))"),
]:
    assert old in direct, label
    try:
        verify_direct_eye_render(direct.replace(old, new, 1))
    except SystemExit:
        pass
    else:
        raise AssertionError("direct native-eye verifier accepted unsafe mutant: " + label)

# Destructive regression: dropping the cancellation veto or GPU-queued mark
# must fail the checker, not merely compile an unused helper.
assert not linked(ring.replace("!native_game_eye_copy_cancelable(entry.gpu_copy_queued)", "false"), slot)
assert not linked(ring.replace("entry.gpu_copy_queued = true;", "/* removed */"), slot)
assert not linked(ring.replace("synchronization_faulted_ = true;\n            return false;\n        }\n        return true;", "return false;\n        }\n        return true;"), slot)
with tempfile.TemporaryDirectory(prefix="dx11_eye_copy_00721_") as folder:
    binary = Path(folder) / "eye_copy"
    subprocess.run(["g++", "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror",
                    "-pedantic", str(probe), "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
print("DX11 stereo GPU eye submission lifetime: PASS (portable/static; Quest3 UNTESTED)")
