#!/usr/bin/env python3
"""Source integration and negative mutation proof for live same-Present full-size output."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
CPP = (ROOT / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
HDR = (ROOT / "src/vr/d3d11/native_game_readback_provenance.hpp").read_text()
WF = (ROOT / ".github/workflows/dx11-fast-structural.yml").read_text()

def integrated(src: str, provenance: str) -> bool:
    a = src.find("void before_game_present(")
    b = src.find("void before_game_reset(IDirect3DDevice9* game) noexcept {", a)
    if a < 0 or b < a:
        return False
    section = src[a:b]
    capture = section.find("if (fullMode) {")
    # The full-resolution source must enqueue first and poll its own fence.
    queue = section.find("ctx->CopyResource(next.staging.Get(), s.backend.color_texture());", capture)
    poll = section.find("auto& oldest = s.readbacks[fullMode ? fullSlot : s.readSlot];")
    getdata = section.find("HRESULT ready = ctx->GetData(", poll)
    fallback = section.find("if (complete && outputWritable &&", getdata)
    return all((
        0 <= capture < queue < poll < getdata < fallback,
        "fullQueued = true;" in section[queue:poll],
        "if (oldest.busy && (!fullMode || fullQueued))" in section[poll:getdata],
        "!oldest.provenance.may_present(s.presents, fullMode)" in section,
        "s.sourceGameDevice == presentDevice && !fullMode" in section[fallback:],
        "if (!fullMode) s.readSlot = (s.readSlot + 1u) % kReadbackSlots;" in section,
        "prior.provenance.capturedAtPresent >= s.presents" in section,
        "D3D11_ASYNC_GETDATA_DONOTFLUSH" in section,
        "capturedAtPresent == currentPresent" in provenance,
        "fullMode ? capturedAtPresent == currentPresent" in provenance,
        "may_overlay(currentPresent)" in provenance,
        "s.frameBatch.publishable_full(s.pending, s.sourceDrawsThisFrame)" in section,
        "GameReadbackProvenance::quarantine_full_frame(" in section,
    ))

assert integrated(CPP, HDR), "live full-native Draw -> same-Present fence -> fallback disconnected"
for old, new in (
    ("oldest.provenance.may_present(s.presents, fullMode)", "oldest.provenance.may_overlay(s.presents)"),
    ("fullMode ? fullSlot : s.readSlot", "s.readSlot"),
    ("fullQueued = true;", "fullQueued = false;"),
    ("s.sourceGameDevice == presentDevice && !fullMode", "s.sourceGameDevice == presentDevice"),
):
    mutant = CPP.replace(old, new, 1)
    assert mutant != CPP and not integrated(mutant, HDR), old
assert not integrated(CPP, HDR.replace("capturedAtPresent == currentPresent",
                                       "capturedAtPresent < currentPresent"))
assert "python tools/test_dx11_full_frame_same_present_00726.py" in WF
assert "tools/dx11_full_frame_same_present_probe_00726.cpp" in WF
print("00726 full-frame same-Present native producer/consumer and D3D9 fallback PASS")
