#!/usr/bin/env python3
"""00751 native full-size D3D11 crop upload is source-wired and fail-closed."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")
HDR = (ROOT / "src/vr/d3d11/native_game_frame_upload.hpp").read_text(encoding="utf-8")
WF = (ROOT / ".github/workflows/dx11-fast-structural.yml").read_text(encoding="utf-8")

def integrated(source, header):
    a = source.find("void before_game_present(")
    b = source.find("void before_game_reset(", a)
    if a < 0 or b <= a:
        return False
    code = source[a:b]
    admission = code.find("const bool croppedNativeUpload =")
    bound = code.find("const bool outputWritable =", admission)
    copy = code.find("const bool copied =", bound)
    crop = code.find("GameNativeFrameUpload::copy_rect(", copy)
    rows = code.find("GameNativeFrameUpload::copy_rows(", crop)
    unlock = code.find("const HRESULT unlockStatus", rows)
    surface = code.find("game->UpdateSurface(", unlock)
    return all((
        0 <= admission < bound < copy < crop < rows < unlock < surface,
        "croppedNativeUpload\n                                            ? GameNativeFrameUpload::copy_rect(" in code[copy:crop+70],
        "static_cast<std::uint32_t>(presentRegion.left)" in code[crop:rows],
        "static_cast<std::uint32_t>(presentRegion.bottom)" in code[crop:rows],
        "croppedNativeUpload ? &uploadSourceCrop : nullptr" in code[surface:surface+250],
        "const bool copied =" in code[copy:unlock],
        "!copied || FAILED(unlockStatus)" in code[unlock:surface],
        "left >= right || top >= bottom || right > frameWidth || bottom > frameHeight" in header,
        "valid_readback_pitch(frameWidth, sourcePitch)" in header,
        "valid_upload_pitch(frameWidth, destinationPitch)" in header,
        "lastRow > (maxSize - rightBytes) / srcStride" in header,
        "lastRow > (maxSize - rightBytes) / dstStride" in header,
        "row * dstStride + leftBytes" in header,
        "row * srcStride + leftBytes" in header,
    ))

assert integrated(SRC, HDR), "native cropped upload must bind to D3D9 output crop and fallback"
for old, new in (
    ("? GameNativeFrameUpload::copy_rect(", "? GameNativeFrameUpload::copy_rows("),
    ("static_cast<std::uint32_t>(presentRegion.left)", "0u /* wrong source x */"),
    ("static_cast<std::uint32_t>(presentRegion.bottom)", "0u /* empty height */"),
    ("croppedNativeUpload ? &uploadSourceCrop : nullptr", "nullptr /* overwrite full backbuffer */"),
    ("!copied || FAILED(unlockStatus)", "FAILED(unlockStatus) /* publish after failed copy */"),
):
    mutant = SRC.replace(old, new, 1)
    assert mutant != SRC and not integrated(mutant, HDR), old
for old, new in (
    ("right > frameWidth", "false /* OOB crop x */"),
    ("bottom > frameHeight", "false /* OOB crop y */"),
    ("valid_upload_pitch(frameWidth, destinationPitch)", "true /* invalid dst pitch */"),
    ("lastRow > (maxSize - rightBytes) / srcStride", "false /* source overflow */"),
):
    mutant = HDR.replace(old, new, 1)
    assert mutant != HDR and not integrated(SRC, mutant), old
assert "python tools/test_dx11_cropped_cpu_upload_00751.py" in WF
assert "tools/dx11_cropped_cpu_upload_probe_00751.cpp" in WF
print("00751 cropped full-frame BGRA upload and input-preserving D3D9 fallback PASS")
