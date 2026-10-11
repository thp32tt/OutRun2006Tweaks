#!/usr/bin/env python3
"""DX9Ex R13 five-field effect policy: remove redundant tracked D3D getter churn.

When R22/R31 StateBlock lifecycle coverage is complete, tracked setters and Apply
invalidate the state cache. With unproven coverage, preserve the historical
16-read live revalidation. HMD/FPS verification remains separate.
"""
from pathlib import Path

R = Path(__file__).resolve().parents[1]
SRC = R / "src/vr/d3d9/stereo_renderer_r7.inc"
TRACKER = R / "src/vr/state/state_block_tracker.hpp"
R22 = R / "src/vr/d3d9/stereo_renderer_r22.cpp"
R13 = R / "src/vr/d3d9/stereo_renderer_r13.cpp"


def verify(source: str) -> None:
    block = source.split("\t\tbool ReadTrackedRenderState(IDirect3DDevice9* device,\n", 1)[1]
    block = block.split("\n\t\tvoid PrimeTrackedRenderStates(", 1)[0]
    required = (
        '#include "vr/state/state_block_tracker.hpp"',
        "TrackedRenderStateValid[index]",
        "auto& reads = TrackedRenderStateReads[index];",
        "const bool trusted = OutRunVR::State::StateBlockTracker::Reliable() &&",
        "!OutRunVR::State::StateBlockTracker::Recording() &&",
        "!InternalStereoPass;",
        "if (trusted || ++reads < 16)",
        "++TrackedRenderStateCacheHits;",
        "out = TrackedRenderStateValue[index];",
        "reads = 0;",
        "device->GetRenderState(state, &live)",
        "if (!TrackedRenderStateValid[index])",
        "TrackedRenderStateValid[index] = true;",
        "TrackedRenderStateValue[index] = live;",
    )
    assert required[0] in source
    for value in required[1:]:
        assert value in block, value
    assert block.index("if (TrackedRenderStateValid[index])") < block.index(
        "const bool trusted =") < block.index(
        "if (trusted || ++reads < 16)") < block.index(
        "reads = 0;") < block.index(
        "device->GetRenderState(state, &live)")
    assert "if (trusted || ++reads < 16)" in block
    cache_hit = block.split("if (trusted || ++reads < 16)", 1)[1].split("reads = 0;", 1)[0]
    assert "out = TrackedRenderStateValue[index];" in cache_hit
    assert "if (!device || index >= TrackedRenderStateValue.size())" in block
    assert "if (FAILED(device->GetRenderState(state, &live)))" in block


if __name__ == "__main__":
    source = SRC.read_text(encoding="utf-8")
    tracker = TRACKER.read_text(encoding="utf-8")
    r22 = R22.read_text(encoding="utf-8")
    r13 = R13.read_text(encoding="utf-8")
    verify(source)
    assert all(v in tracker for v in (
        "static bool Reliable() noexcept",
        "EventConsumerReady()",
        "!CoverageLost()",
        "static bool Recording() noexcept",
    ))
    assert "InvalidateTrackedRenderStates();" in r22
    assert "void R22InvalidateAfterStateBlockApply(" in r22
    assert "OutRunVR::State::StateBlockEvents::NotifyBegin" in r22
    assert "OutRunVR::State::StateBlockEvents::NotifyEnd" in r22
    assert "ReadTrackedRenderState(device, D3DRS_ALPHABLENDENABLE" in r13
    assert "ReadTrackedRenderState(device, D3DRS_CULLMODE" in r13

    mutations = (
        ('"vr/state_block_tracker.hpp"', '"broken.hpp"'), 
        ('#include "vr/state/state_block_tracker.hpp"', "// no tracker"),
        ("StateBlockTracker::Reliable() &&", "StateBlockTracker::R22Reliable() &&"),
        ("!OutRunVR::State::StateBlockTracker::Recording() &&", "true &&"),
        ("!InternalStereoPass;", "true;"),
        ("if (trusted || ++reads < 16)", "if (++reads < 16)"),
        ("if (trusted || ++reads < 16)", "if (trusted)"),
        ("if (trusted || ++reads < 16)", "if (trusted || true)"),
        ("if (trusted || ++reads < 16)", "if (trusted && ++reads < 16)"),
        ("reads = 0;", "// no fallback reset"),
        ("device->GetRenderState(state, &live)", "D3D_OK"),
        ("TrackedRenderStateValid[index] = true;", "TrackedRenderStateValid[index] = false;"),
        ("out = TrackedRenderStateValue[index];", "out = 0;"),
    )
    tested = 0
    for old, new in mutations:
        if old not in source:
            if "broken.hpp" in new:
                continue
            raise AssertionError("missing mutation fixture: " + old)
        broken = source.replace(old, new, 1)
        try:
            verify(broken)
        except (AssertionError, IndexError):
            tested += 1
        else:
            raise AssertionError("negative mutation survived: " + old)
    assert tested == 12, tested
    print("PASS R13 tracked effect-state fast path, legacy live fallback and 12 negative mutations")
