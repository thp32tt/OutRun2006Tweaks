#!/usr/bin/env python3
"""00730: original failed game Draw cannot publish a speculative native full frame."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
hook = (root / "src/vr/d3d9/stereo_renderer_r30.cpp").read_text(encoding="utf-8")
api = (root / "src/vr/d3d11/live_game_frame_bridge.hpp").read_text(encoding="utf-8")
bridge = (root / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")
workflow = (root / ".github/workflows/dx11-fast-structural.yml").read_text(encoding="utf-8")

def integrated(hook_source: str, header: str, source: str) -> bool:
    helper_start = hook_source.find("void R30CompleteNativeGameSource(")
    helper_end = hook_source.find("HRESULT __stdcall DrawPrimitiveDestR30(", helper_start)
    if helper_start < 0 or helper_end < 0:
        return False
    helper = hook_source[helper_start:helper_end]
    if "if (FAILED(gameHr))" not in helper or "observe_failed_game_draw(device);" not in helper:
        return False
    for name, observed in (
        ("DrawPrimitive", "R30ObserveNativeLinearVB("),
        ("DrawIndexedPrimitive", "R30ObserveNativeIndexedVB("),
        ("DrawPrimitiveUP", "live_game_frame::observe_linear("),
        ("DrawIndexedPrimitiveUP", "R30ObserveNativeIndexedUP("),
    ):
        marker = "HRESULT __stdcall " + name + "DestR30("
        begin = hook_source.find(marker, helper_end)
        if begin < 0:
            return False
        end = hook_source.find("HRESULT __stdcall ", begin + len(marker))
        if end < 0:
            end = hook_source.find("void R30RollbackHooks()", begin)
        block = hook_source[begin:end]
        native = block.find(observed)
        call = block.find("const HRESULT xyzrhw =")
        fallback = block.find("const HRESULT gameHr = R30GuardScreenSpace(")
        after = block.find("R30CompleteNativeGameSource(device, gameHr);")
        if not (0 <= native < call < fallback < after):
            return False
        if "if (xyzrhw != E_NOTIMPL) {\n                R30CompleteNativeGameSource(device, xyzrhw);\n                return xyzrhw;" not in block:
            return False
        if "return gameHr;" not in block[after:]:
            return False
    if "void observe_failed_game_draw(IDirect3DDevice9* gameDevice) noexcept;" not in header:
        return False
    start = source.find("void observe_failed_game_draw(IDirect3DDevice9* game)")
    end = source.find("void before_game_present(", start)
    if not (0 <= start < end):
        return False
    failure = source[start:end]
    return all((
        "if (!diagnostic_enabled() || !game) return;" in failure,
        "if (s.sourceGameDevice != reinterpret_cast<std::uintptr_t>(game)) return;" in failure,
        "s.frameBatch.abort();" in failure,
        "s.pending = false;" in failure,
        "++s.sourceDrawsThisFrame" not in failure,
        "s.frameBatch.publishable_full(s.pending, s.sourceDrawsThisFrame)" in source[end:],
    ))

assert integrated(hook, api, bridge), "failed original game Draw must quarantine full native scene"
for original, mutant in (
    ("if (FAILED(gameHr))", "if (SUCCEEDED(gameHr))"),
    ("observe_failed_game_draw(device);", "observe_unavailable_game_draw(device);"),
    ("R30CompleteNativeGameSource(device, xyzrhw);", "/* ignored game failure */"),
    ("R30CompleteNativeGameSource(device, gameHr);", "/* ignored game failure */"),
):
    altered = hook.replace(original, mutant, 1)
    assert altered != hook and not integrated(altered, api, bridge), original
for original, mutant in (
    ("s.frameBatch.abort();", "/* failed game draw accepted */"),
    ("s.pending = false;", "s.pending = true;"),
    ("if (s.sourceGameDevice != reinterpret_cast<std::uintptr_t>(game)) return;", "/* foreign device accepted */"),
):
    start = bridge.index("void observe_failed_game_draw(")
    end = bridge.index("void before_game_present(", start)
    fragment = bridge[start:end]
    mutated = fragment.replace(original, mutant, 1)
    assert mutated != fragment
    assert not integrated(hook, api, bridge[:start] + mutated + bridge[end:]), original
assert "python tools/test_dx11_failed_game_draw_00730.py" in workflow
assert "tools/dx11_failed_game_draw_probe_00730.cpp" in workflow
print("PASS 00730: failed original D3D9 VB/IB/UP Draw quarantines native full frame without altering gamepad/fallback")
