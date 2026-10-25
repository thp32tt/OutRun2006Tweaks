#!/usr/bin/env python3
"""01064: sequential authentic game-camera RTVs reach the native OpenXR GPU ring."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
header = (root / "src/vr/d3d11/native_game_stereo_submission.hpp").read_text()
source = (root / "src/vr/d3d11/native_game_stereo_submission.cpp").read_text()
ring = (root / "src/vr/d3d11/native_shared_eye_ring.cpp").read_text()
ring_header = (root / "src/vr/d3d11/native_shared_eye_ring.hpp").read_text()
admission = (root / "src/vr/d3d11/native_game_eye_pair_sources.hpp").read_text()
workflow = (root / ".github/workflows/dx11-fast-structural.yml").read_text()

def integrated(s, r, h=header, rh=ring_header, helper=admission):
    capture = s.split("bool NativeGameStereoSubmission::capture_eye(", 1)[1].split(
        "// Source camera TYPELESS", 1)[0]
    submit = s.split("bool NativeGameStereoSubmission::submit()", 1)[1].split(
        "bool NativeGameStereoSubmission::try_publish(", 1)[0]
    exact = r.split("const auto exact_source =", 1)[1].split(
        "// Validate both resource descriptors", 1)[0]
    capture_header = h.split("bool capture_eye(", 1)[1].split(
        "// Copy both genuine", 1)[0]
    encoder_copy_header = h.split("[[nodiscard]] bool copy_game_surface(", 1)[1].split(
        "// Per-eye native GPU replay", 1)[0]
    # The old C++ helper shares the same three-argument shape as the new
    # source_is_live entrypoint; never accidentally rewrite that helper
    # instead of NativeGameStereoSubmission's actual method declaration.
    expected_source_signature = (
        "bool NativeGameStereoSubmission::source_is_live(\n"
        "    ID3D11Texture2D* source, UINT arraySlice, UINT mipSlice,\n"
        "    ID3D11RenderTargetView* gameCapturedRtv,\n"
        "    bool requireCurrentlyBound) const noexcept"
    )
    expected_existing_signature = (
        "DXGI_FORMAT NativeGameEyeDrawEncoder::offscreen_color_view_format(\n"
        "    ID3D11Texture2D* source, UINT arraySlice, UINT mipSlice) const noexcept"
    )
    return all((
        expected_source_signature in s,
        expected_existing_signature in s,
        "ID3D11RenderTargetView* gameCapturedRtv = nullptr" in capture_header,
        "gameCapturedRtv" not in encoder_copy_header,
        "UINT sourceMipSlice = 0u) noexcept;" in encoder_copy_header,
        "capturedRtvs_[2]" in h,
        "gameCapturedRtv, true" in capture,
        "capturedRtvs_[eyeIndex] = gameCapturedRtv;" in capture,
        "capturedRtvs_[0].Get(), false" in submit,
        "capturedRtvs_[1].Get(), false" in submit,
        "capturedRtvs_[0].Get(), capturedRtvs_[1].Get()" in submit,
        "native_game_eye_captured_rtv_admitted(" in s,
        "context_->OMGetRenderTargets(" in s,
        "if (view == gameCapturedRtv) boundAtCapture = true;" in s,
        "sourceIdentity.Get() == viewIdentity.Get()" in s,
        "ID3D11RenderTargetView* captured_left_rtv" in rh,
        "ID3D11RenderTargetView* captured_right_rtv" in rh,
        "if (capturedRtv)" in exact,
        "native_game_eye_captured_rtv_admitted(" in exact,
        "viewIdentity.Get() == sourceIdentity.Get()" in exact,
        "left_mip_slice, left_array_slice, captured_left_rtv" in r,
        "right_mip_slice, right_array_slice, captured_right_rtv" in r,
        "native_game_eye_rtv_subresource_matches(" in helper,
        "observedFormat == ringFormat" in helper,
        "viewSliceCount == 1u" in helper,
    ))

assert integrated(source, ring)
# Public C++ declarations must match the correct member, not another
# three-argument texture helper accidentally selected by an edit script.
assert not integrated(source, ring, h=header.replace(
    "ID3D11RenderTargetView* gameCapturedRtv = nullptr",
    "/* missing real camera RTV */", 1))
assert not integrated(source, ring, h=header.replace(
    "UINT sourceMipSlice = 0u) noexcept;",
    "UINT sourceMipSlice = 0u, ID3D11RenderTargetView* gameCapturedRtv = nullptr) noexcept;", 1))
for needle in (
    "capturedRtvs_[eyeIndex] = gameCapturedRtv;",
    "if (view == gameCapturedRtv) boundAtCapture = true;",
    "capturedRtvs_[0].Get(), capturedRtvs_[1].Get()",
):
    mutant = source.replace(needle, "/* erased camera ownership */", 1)
    assert mutant != source and not integrated(mutant, ring), needle
for needle in (
    "if (capturedRtv)",
    "right_mip_slice, right_array_slice, captured_right_rtv",
):
    mutant = ring.replace(needle, "/* erased GPU transfer */", 1)
    assert mutant != ring and not integrated(source, mutant), needle
assert "tests/vr/dx11_native_stereo_captured_views_01064.cpp" in workflow
assert "python tools/test_dx11_native_stereo_captured_views_01064.py" in workflow
print("PASS 01064 native sequential L/R camera provenance and GPU transfer contract")
