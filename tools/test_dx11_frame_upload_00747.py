#!/usr/bin/env python3
"""00747 native D3D11 Map -> D3D9 backbuffer upload and safe unlock failure."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")
HDR = (ROOT / "src/vr/d3d11/native_game_frame_upload.hpp").read_text(encoding="utf-8")
WF = (ROOT / ".github/workflows/dx11-fast-structural.yml").read_text(encoding="utf-8")

def integrated(src, hdr):
    a = src.find("void before_game_present(")
    b = src.find("void before_game_reset(", a)
    if not 0 <= a < b: return False
    code = src[a:b]
    lock = code.find("s.insetSurface->LockRect(&lockRect, nullptr, 0)")
    copy = code.find("GameNativeFrameUpload::copy_rows(", lock)
    unlk = code.find("const HRESULT unlockStatus = s.insetSurface->UnlockRect();", copy)
    fail = code.find("if (!copied || FAILED(unlockStatus))", unlk)
    discard = code.find("s.insetSurface.Reset();", fail)
    good = code.find("} else {", discard)
    upload = code.find("game->UpdateSurface(", good)
    upload_error = code.find("} else {", upload)
    retry_cache = code.find("s.insetSurface.Reset();", upload_error)
    unmap = code.find("ctx->Unmap(oldest.staging.Get(), 0);", upload)
    return all((
        '#include "native_game_frame_upload.hpp"' in src,
        0 <= lock < copy < unlk < fail < discard < good < upload < upload_error < retry_cache < unmap,
        "if (fullMode) {" in code[upload_error:retry_cache],
        "s.insetFormat = D3DFMT_UNKNOWN;" in code[retry_cache:unmap],
        "lockRect.pBits, lockRect.Pitch," in code[copy:unlk],
        "mapped.pData, mapped.RowPitch," in code[copy:unlk],
        "surfaceWidth, surfaceHeight" in code[copy:unlk],
        "GameNativeFramePublication::valid_upload_pitch(" in code[lock:copy],
        "if (FAILED(unlockStatus))" in code[fail:discard],
        "s.insetFormat = D3DFMT_UNKNOWN;" in code[discard:good],
        "!destination || !source || height == 0u" in hdr,
        "valid_readback_pitch(width, sourcePitch)" in hdr,
        "valid_upload_pitch(width, destinationPitch)" in hdr,
        "std::memcpy(dst + row * dstStride, src + row * srcStride, rowBytes)" in hdr,
    ))
assert integrated(SRC, HDR), "native upload must copy full frame and fail closed"
for old, new in (
    ("if (!copied || FAILED(unlockStatus))", "if (!copied && FAILED(unlockStatus))"),
    ("const HRESULT unlockStatus = s.insetSurface->UnlockRect();", "const HRESULT unlockStatus = S_OK;"),
    ("GameNativeFrameUpload::copy_rows(", "/* missing native copy */("),
    # The cropped fast path precedes copy_rows in the same callsite.
    # Mutate the *legacy full-backbuffer* branch so this test still proves
    # uncropped D3D9 publication fails closed independently of crop tests.
    ("GameNativeFrameUpload::copy_rows(\\n                                                lockRect.pBits, lockRect.Pitch,",
     "GameNativeFrameUpload::copy_rows(\\n                                                mapped.pData, lockRect.Pitch,"),
    ("if (FAILED(unlockStatus))", "if (false /* ignore unlock */)"),
    ("if (fullMode) {\n                                                s.insetSurface.Reset();", "if (false) {\n                                                s.insetSurface.Reset();"),
):
    mutant = SRC.replace(old, new, 1)
    assert mutant != SRC and not integrated(mutant, HDR), old
for old, new in (
    ("!destination || !source || height == 0u", "height == 0u"),
    ("valid_readback_pitch(width, sourcePitch)", "true"),
    ("valid_upload_pitch(width, destinationPitch)", "true"),
    ("std::memcpy(dst + row * dstStride, src + row * srcStride, rowBytes)", "/* no pixels */"),
):
    mutant = HDR.replace(old, new, 1)
    assert mutant != HDR and not integrated(SRC, mutant), old
assert "python tools/test_dx11_frame_upload_00747.py" in WF
assert "tools/dx11_frame_upload_probe_00747.cpp" in WF
print("00747 full native BGRA output row transfer and DX9Ex failure fallback PASS")
