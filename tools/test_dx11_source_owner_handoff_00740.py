#!/usr/bin/env python3
"""00740: integrated live Draw source-owner continuity, full-clear recovery, fallback."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
BRIDGE = (ROOT / "src/vr/d3d11/live_game_frame_bridge.cpp").read_text()
BATCH = (ROOT / "src/vr/d3d11/native_game_frame_batch.hpp").read_text()
WF = (ROOT / ".github/workflows/dx11-fast-structural.yml").read_text()

def connected(source: str, header: str) -> bool:
    owner_begin = source.find("bool observe_source_device(")
    mode_begin = source.find("bool observe_source_frame_mode(", owner_begin)
    clear_begin = source.find("void observe_game_clear(")
    unavailable_begin = source.find("void observe_unavailable_game_draw(", clear_begin)
    present_begin = source.find("void before_game_present(", unavailable_begin)
    reset_begin = source.find("void before_game_reset()", present_begin)
    if min(owner_begin, mode_begin, clear_begin, unavailable_begin, present_begin, reset_begin) < 0:
        return False
    owner = source[owner_begin:mode_begin]
    clear = source[clear_begin:unavailable_begin]
    present = source[present_begin:reset_begin]
    return all((
        "GameNativeFrameBatch::admits_game_source(" in owner,
        "s.previousOutput.valid()" in owner,
        "s.previousOutput.device : 0u" in owner,
        "if (s.sourceGameDevice == 0u) s.sourceGameDevice = current;" in owner,
        "const bool foreignSource =" in clear,
        "if (foreignSource && !env_full_game_opt_in()) return;" in clear,
        "if (!foreignSource) s.clearColor.discard();" in clear,
        "GameNativeFrameBatch::can_reacquire_full_clear(" in clear,
        "if (foreignSource && !sourceReacquired) return;" in clear,
        "if (foreignSource) s.clearColor.discard();" in clear,
        clear.index("if (foreignSource && !sourceReacquired) return;") <
            clear.index("s.clearColor.record("),
        "if (sourceReacquired || s.sourceGameDevice == 0u)" in clear,
        "s.sourceGameDevice = sourceDevice;" in clear,
        "if (++s.outputGeneration == 0u) ++s.outputGeneration;" in clear,
        "s.frameBatch.reset();" in clear,
        "s.sourceDrawsThisFrame = 0u;" in clear,
        "if (GameNativeFrameBatch::foreign_present(" in present,
        "GameNativeFrameBatch::admits_game_source(" not in present,
        "s.frameBatch.publishable_full(s.pending, s.sourceDrawsThisFrame)" in present,
        "bool admits_game_source(" in header,
        "bool can_reacquire_full_clear(" in header,
        "!nativeSubmitted && !nativePending" in header,
        "fullMode && wholeBackbuffer && candidate != 0u" in header,
    ))

assert connected(BRIDGE, BATCH), "00740 source Draw/full Clear/Present/fallback linkage"
for old, new in (
    ("s.previousOutput.device : 0u", "0u : 0u"),
    ("if (foreignSource && !sourceReacquired) return;", "if (false) return;"),
    ("if (sourceReacquired || s.sourceGameDevice == 0u)", "if (false)"),
    ("s.sourceDevice = sourceDevice;", "s.sourceDevice = 0u;"),
    ("if (!foreignSource) s.clearColor.discard();", "if (false) s.clearColor.discard();"),
):
    changed = BRIDGE.replace(old, new, 1)
    if changed != BRIDGE:
        assert not connected(changed, BATCH), old
for old, new in (
    ("!nativeSubmitted && !nativePending", "true"),
    ("fullMode && wholeBackbuffer && candidate != 0u", "true"),
):
    assert not connected(BRIDGE, BATCH.replace(old, new, 1)), old
assert "python tools/test_dx11_source_owner_handoff_00740.py" in WF
assert "tools/dx11_source_owner_handoff_probe_00740.cpp" in WF
print("00740 live source owner/whole-Clear handoff and input-safe fallback PASS")
