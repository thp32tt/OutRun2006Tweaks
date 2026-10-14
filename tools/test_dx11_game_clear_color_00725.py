#!/usr/bin/env python3
"""Regression: successful game backbuffer Clear -> DX11 full-frame Draw color."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
src = (ROOT / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")
hdr = (ROOT / "src/vr/d3d11/live_game_frame_bridge.hpp").read_text(encoding="utf-8")
hook = (ROOT / "src/vr/d3d9/stereo_renderer.cpp").read_text(encoding="utf-8")
helper = (ROOT / "src/vr/d3d11/native_game_clear_color.hpp").read_text(encoding="utf-8")
wf = (ROOT / ".github/workflows/dx11-fast-structural.yml").read_text(encoding="utf-8")

def integrated(cpp: str, r9: str, clear: str) -> bool:
    callback = r9.split("HRESULT __stdcall ClearDestR9(", 1)[-1].split(
        "template <typename ActualDraw, typename LegacyDraw>", 1)[0]
    observe = cpp.split("void observe_game_clear(", 1)[-1].split(
        "void observe_unavailable_game_draw(", 1)[0]
    submit = cpp.split("bool submit(", 1)[-1].split("bool observe_source_device(", 1)[0]
    return all(x in callback for x in (
        "if (SUCCEEDED(result) && (flags & D3DCLEAR_TARGET))",
        "live_game_frame::observe_game_clear(",
        "return finishNativeClear(stereoHr);",
        "return finishNativeClear(hr);",
        "return finishNativeClear(ClearHook.stdcall<HRESULT>(",
        "return finishNativeClear(R9ClearCallbackHook.stdcall<HRESULT>(",
    )) and all(x in observe for x in (
        "s.clearColor.discard();", "if (count != 0u || rects != nullptr) return;",
        "game->GetRenderTarget(0,", "game->GetBackBuffer(0, 0, D3DBACKBUFFER_TYPE_MONO,",
        "targetIdentity.Get() == backbufferIdentity.Get()",
        "viewport.Width == bbDesc.Width && viewport.Height == bbDesc.Height",
        "s.clearColor.record(sourceDevice,",
    )) and all(x in submit for x in (
        "s.frameBatch.first_draw()",
        "s.clearColor.native_color(s.sourceGameDevice, output.targetIdentity, kBackground)",
        "env_full_game_opt_in()")) and all(x in cpp for x in (
        "output.targetIdentity = reinterpret_cast<std::uintptr_t>(sourceTargetIdentity.Get());",
        "s.clearColor.discard();\n        // Menu/car/race frames often",
    )) and all(x in clear for x in (
        "wholeBackbuffer && device != 0u && backbuffer != 0u",
        "sourceDevice == device && backbufferIdentity == backbuffer",
        "if (!matches(device, backbuffer)) return fallback;",
    ))

assert "void observe_game_clear(IDirect3DDevice9* gameDevice" in hdr
assert integrated(src, hook, helper), "R9 Clear -> native Draw integration disconnected"
for old, new in (
    ("if (SUCCEEDED(result) && (flags & D3DCLEAR_TARGET))",
     "if (FAILED(result) && (flags & D3DCLEAR_TARGET))"),
    ("return finishNativeClear(stereoHr);", "return stereoHr;"),
    ("return finishNativeClear(hr);", "return hr;"),
):
    mutant = hook.replace(old, new, 1)
    assert mutant != hook and not integrated(src, mutant, helper), old
for old, new in (
    ("if (count != 0u || rects != nullptr) return;", "if (count == 0u && rects == nullptr) return;"),
    ("targetIdentity.Get() == backbufferIdentity.Get()",
     "targetIdentity.Get() != backbufferIdentity.Get()"),
    ("s.clearColor.native_color(s.sourceGameDevice, output.targetIdentity, kBackground)",
     "kBackground"),
    ("s.clearColor.discard();\n        // Menu/car/race frames often",
     "// missing frame discard\n        // Menu/car/race frames often"),
):
    mutant = src.replace(old, new, 1)
    assert mutant != src and not integrated(mutant, hook, helper), old
mutant = helper.replace("if (!matches(device, backbuffer)) return fallback;",
                        "if (matches(device, backbuffer)) return fallback;")
assert mutant != helper and not integrated(src, hook, mutant)
assert "python tools/test_dx11_game_clear_color_00725.py" in wf
assert "tools/dx11_game_clear_color_probe_00725.cpp" in wf
print("DX11 00725 R9 Clear/native full-frame source color + fallback PASS")
