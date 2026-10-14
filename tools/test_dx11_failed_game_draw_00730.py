#!/usr/bin/env python3
"""00730: original failed game Draw cannot publish a speculative native full frame."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
hook = (root / "src/vr/d3d9/stereo_renderer_r30.cpp").read_text(encoding="utf-8")
safe_hook = (root / "src/vr/d3d9/stereo_renderer_r30_r26_safe.cpp").read_text(encoding="utf-8")
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

# 00738: R26-safe game hooks also draw speculatively before D3D9 completes.
# Failure on the XYZRHW direct path OR R29/R26 delegated path must revoke
# the full native menu/vehicle/race batch without replacing the HRESULT.
def safe_integrated(source: str) -> bool:
    start = source.find("void R30CompleteNativeGameSourceR26Safe(")
    end = source.find("HRESULT __stdcall DrawPrimitiveDestR30(", start)
    if start < 0 or end < 0:
        return False
    helper = source[start:end]
    if "if (FAILED(gameHr))" not in helper or "observe_failed_game_draw(device);" not in helper:
        return False
    expected = (
        ("DrawPrimitive", "R30ObserveNativeLinearVB("),
        ("DrawIndexedPrimitive", "R30ObserveNativeIndexedVB("),
        ("DrawPrimitiveUP", "live_game_frame::observe_linear("),
        ("DrawIndexedPrimitiveUP", "R30ObserveNativeIndexedUP("),
    )
    for name, observed in expected:
        begin = source.find("HRESULT __stdcall " + name + "DestR30(", end)
        if begin < 0:
            return False
        finish = source.find("HRESULT __stdcall ", begin + 10)
        if finish < 0:
            finish = source.find("void R30RollbackHooks()", begin)
        if finish <= begin:
            return False
        block = source[begin:finish]
        observed_at = block.find(observed)
        native_at = block.find("const HRESULT xyzrhw =")
        early_at = block.find("R30CompleteNativeGameSourceR26Safe(device, xyzrhw);")
        fallback_at = block.find("const HRESULT gameHr = R30GuardScreenSpace(")
        complete_at = block.find("R30CompleteNativeGameSourceR26Safe(device, gameHr);")
        if not (0 <= observed_at < native_at < early_at < fallback_at < complete_at):
            return False
        if "if (xyzrhw != E_NOTIMPL) {" not in block or "return xyzrhw;" not in block[early_at:fallback_at]:
            return False
        if "return gameHr;" not in block[complete_at:]:
            return False
    # The sprite-specialized indexed Draw returns before XYZRHW and R29.
    # That original HRESULT is equally authoritative for native publication.
    indexed_begin = source.find("HRESULT __stdcall DrawIndexedPrimitiveDestR30(", helper_end)
    indexed_end = source.find("HRESULT __stdcall DrawPrimitiveUPDestR30(", indexed_begin)
    if indexed_begin < 0 or indexed_end < 0:
        return False
    indexed = source[indexed_begin:indexed_end]
    sprite = indexed.find("const HRESULT fixedFnSprite =")
    sprite_check = indexed.find("R30CompleteNativeGameSourceR26Safe(device, fixedFnSprite);")
    xyz = indexed.find("const HRESULT xyzrhw =")
    if not (0 <= sprite < sprite_check < xyz):
        return False
    if "if (fixedFnSprite != E_NOTIMPL) {" not in indexed or "return fixedFnSprite;" not in indexed[sprite_check:xyz]:
        return False
    return True

assert safe_integrated(safe_hook), "R26-safe failed game Draw must quarantine native frame"
for old, new in (
    ("if (FAILED(gameHr))", "if (SUCCEEDED(gameHr))"),
    ("observe_failed_game_draw(device);", "observe_unavailable_game_draw(device);"),
):
    damaged = safe_hook.replace(old, new, 1)
    assert damaged != safe_hook and not safe_integrated(damaged), old
sprite_mutated = safe_hook.replace(
    "R30CompleteNativeGameSourceR26Safe(device, fixedFnSprite);",
    "/* lost fixed-function sprite failure */", 1)
assert sprite_mutated != safe_hook and not safe_integrated(sprite_mutated)
for name in ("DrawPrimitive", "DrawIndexedPrimitive", "DrawPrimitiveUP", "DrawIndexedPrimitiveUP"):
    begin = safe_hook.index("HRESULT __stdcall " + name + "DestR30(")
    finish = safe_hook.find("HRESULT __stdcall ", begin + 10)
    if finish < 0:
        finish = safe_hook.index("void R30RollbackHooks()", begin)
    block = safe_hook[begin:finish]
    for call in ("R30CompleteNativeGameSourceR26Safe(device, xyzrhw);",
                 "R30CompleteNativeGameSourceR26Safe(device, gameHr);"):
        damaged = block.replace(call, "/* dropped original failure result */", 1)
        assert damaged != block
        assert not safe_integrated(safe_hook[:begin] + damaged + safe_hook[finish:]), (name, call)

assert "python tools/test_dx11_failed_game_draw_00730.py" in workflow
assert "tools/dx11_failed_game_draw_probe_00730.cpp" in workflow
print("PASS 00730/00738: both R30 and R26-safe VB/IB/UP failure paths quarantine native full frame; original gamepad/fallback preserved")
