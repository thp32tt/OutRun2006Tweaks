#!/usr/bin/env python3
"""00727 live full-frame publication positive/negative source integration."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CPP = (ROOT / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")
HDR = (ROOT / "src/vr/d3d11/native_game_frame_publication.hpp").read_text(encoding="utf-8")
WF = (ROOT / ".github/workflows/dx11-fast-structural.yml").read_text(encoding="utf-8")


def integrated(src: str, header: str) -> bool:
    a = src.find("void before_game_present(")
    b = src.find("void before_game_reset(IDirect3DDevice9* game) noexcept {", a)
    if a < 0 or b <= a:
        return False
    body = src[a:b]
    probe = body.find("if (sourcePitchValid && !fullMode) {")
    publish = body.find("GameNativeFramePublication::should_upload(", probe)
    copy = body.find("GameNativeFrameUpload::copy_rows(", publish)
    update = body.find("uploaded = SUCCEEDED(game->UpdateSurface(", copy)
    reset = body.find("s.frameBatch.reset();", update)
    return all((
        '#include "native_game_frame_publication.hpp"' in src,
        0 <= probe < publish < copy < update < reset,
        "const HRESULT unlockStatus = s.insetSurface->UnlockRect();" in body[copy:update],
        "FAILED(unlockStatus)" in body[copy:update],
        "valid_readback_pitch(" in body[:publish],
        "valid_upload_pitch(" in body[publish:copy],
        "fullMode, !fullMode || complete, outputWritable," in body[publish:],
        "s.frameBatch.publishable_full(s.pending, s.sourceDrawsThisFrame)" in body,
        "oldest.provenance.may_present(s.presents, fullMode)" in body,
        "if (sourcePitchValid && !fullMode)" in body[probe:publish],
        'fullMode ? "full-frame" : "inset"' in body,
        "return complete && outputWritable && (fullMode || changedPixels != 0u);" in header,
        "rowPitch >= width * 4u" in header,
        "rowPitch > 0" in header,
    ))


assert integrated(CPP, HDR), "Same-Present native menu/race publication must keep fallback"
for old, new in (
    ("if (sourcePitchValid && !fullMode)", "if (sourcePitchValid)"),
    ("fullMode, !fullMode || complete, outputWritable,", "fullMode, true, outputWritable,"),
    ("GameNativeFramePublication::valid_readback_pitch(", "true /* bypassed */ ("),
    ("GameNativeFramePublication::valid_upload_pitch(", "true /* bypassed */ ("),
    ("game->UpdateSurface(", "/* no game backbuffer publication */ ("),
    ("GameNativeFrameUpload::copy_rows(", "/* no native pixel transfer */ ("),
):
    mutant = CPP.replace(old, new, 1)
    assert mutant != CPP and not integrated(mutant, HDR), old
for old, new in (
    ("fullMode || changedPixels != 0u", "changedPixels != 0u"),
    ("complete && outputWritable", "complete || outputWritable"),
    ("rowPitch >= width * 4u", "true"),
    ("rowPitch > 0", "rowPitch >= 0"),
):
    mutant = HDR.replace(old, new, 1)
    assert mutant != HDR and not integrated(CPP, mutant), old
assert "python tools/test_dx11_game_frame_publication_00727.py" in WF
assert "tools/dx11_game_frame_publication_probe_00727.cpp" in WF
print("00727 complete native menu/race frame + diagnostic inset fallback integration PASS")
