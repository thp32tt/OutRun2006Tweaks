#!/usr/bin/env python3
"""00741: source-owned D3D9 Reset must not disrupt full-frame GPU Draw/Present."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
BRIDGE = (ROOT / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
BATCH = (ROOT / "src/vr/d3d11/native_game_frame_batch.hpp").read_text()
API = (ROOT / "src/vr/d3d11/live_game_frame_bridge.hpp").read_text()
HOOKS = [(ROOT / p).read_text() for p in (
    "src/vr/d3d9/stereo_renderer_r30.cpp",
    "src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp",
)]
WF = (ROOT / ".github/workflows/dx11-fast-structural.yml").read_text()

def connected(bridge=BRIDGE, batch=BATCH, api=API, hooks=HOOKS, wf=WF):
    pos = bridge.find("void before_game_reset(IDirect3DDevice9* game) noexcept {")
    if pos < 0: return False
    reset = bridge[pos:]
    gate = "if (!GameNativeFrameBatch::reset_belongs_to_game_source("
    if gate not in reset or "s.pending = false;" not in reset: return False
    if reset.index(gate) >= reset.index("s.pending = false;"): return False
    if "s.previousOutput.valid() ? s.previousOutput.device : 0u" not in reset[:reset.index("s.pending = false;")]: return False
    if "return;" not in reset[reset.index(gate):reset.index("s.pending = false;")]: return False
    if "s.backend.shutdown();" not in reset: return False
    if "static constexpr bool reset_belongs_to_game_source(" not in batch: return False
    if "sourceOwner != 0u ? resettingDevice == sourceOwner" not in batch: return False
    if "lastPresentOwner == 0u ||" not in batch: return False
    if "resettingDevice == lastPresentOwner" not in batch: return False
    if "void before_game_reset(IDirect3DDevice9* gameDevice) noexcept;" not in api: return False
    for hook in hooks:
        part = hook[hook.index("HRESULT __stdcall ResetDestR30("):]
        if part.count("live_game_frame::before_game_reset(device);") < 1: return False
        if "live_game_frame::before_game_reset();" in part: return False
        original = "R30ResetR29Hook.stdcall<HRESULT>(device, params);"
        if part.count(original) != 1: return False
        if part.index("before_game_reset(device);") >= part.index(original): return False
        # The native owner cleanup must never replace the original D3D9 Reset.
        if "return hr;" not in part[part.index(original):]: return False
    return ("python tools/test_dx11_source_reset_00741.py" in wf and
            "tools/dx11_source_reset_probe_00741.cpp" in wf)

def in_reset(source: str, original: str, replacement: str) -> str:
    # Several earlier source-owner checks use the same Present expression.
    # Change the Reset body itself or this negative case would be a false PASS.
    start = source.index("void before_game_reset(IDirect3DDevice9* game) noexcept {")
    assert original in source[start:], "Reset mutation target missing"
    return source[:start] + source[start:].replace(original, replacement, 1)

assert connected(), "game device->Reset ownership->native scene fallback disconnected"
# Mutations: each change must fail, so the probe rejects a bookkeeping-only edit.
mutants = [
    dict(bridge=BRIDGE.replace("if (!GameNativeFrameBatch::reset_belongs_to_game_source(",
                               "if (GameNativeFrameBatch::reset_belongs_to_game_source(", 1)),
    dict(bridge=in_reset(BRIDGE,
                         "s.previousOutput.valid() ? s.previousOutput.device : 0u",
                         "0u")),
    dict(batch=BATCH.replace("sourceOwner != 0u ? resettingDevice == sourceOwner",
                             "sourceOwner != 0u ? resettingDevice != sourceOwner", 1)),
    dict(batch=BATCH.replace("resettingDevice == lastPresentOwner",
                             "resettingDevice != lastPresentOwner", 1)),
    dict(api=API.replace("before_game_reset(IDirect3DDevice9* gameDevice)",
                         "before_game_reset()")),
    dict(hooks=[HOOKS[0].replace("before_game_reset(device);",
                                "before_game_reset();", 1), HOOKS[1]]),
    dict(hooks=[HOOKS[0], HOOKS[1].replace("before_game_reset(device);",
                                         "before_game_reset();", 1)]),
    dict(hooks=[HOOKS[0].replace("R30ResetR29Hook.stdcall<HRESULT>(device, params);",
                                "E_FAIL;", 1), HOOKS[1]]),
    dict(hooks=[HOOKS[0], HOOKS[1].replace(
        "R30ResetR29Hook.stdcall<HRESULT>(device, params);", "E_FAIL;", 1)]),
    dict(wf=WF.replace("python tools/test_dx11_source_reset_00741.py", "")),
]
for i, mutation in enumerate(mutants):
    assert not connected(**mutation), f"Reset ownership regression mutation {i} escaped"
print("PASS: game/aux Reset source continuity, native readback fallback, 10 destructive mutations")
