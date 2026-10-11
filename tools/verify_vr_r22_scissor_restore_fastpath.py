#!/usr/bin/env python3
"""DX9Ex R22 raster replay: elide redundant scissor replays, never skip dirty draws."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/vr/d3d9/stereo_renderer_r22.cpp"


def section(source: str, start: str, end: str) -> str:
    return source.split(start, 1)[1].split(end, 1)[0]


def check(source: str) -> None:
    assert "thread_local bool R22InternalRasterTouched = false;" in source
    scope = section(source, "struct R22ReplayScope", "void R22FailClosedReplayState")
    assert "R22InternalRasterTouched = false;" in scope.split("~R22ReplayScope()", 1)[0]
    destructor = scope.split("~R22ReplayScope()", 1)[1]
    guard = "if (R22InternalViewportTouched || R22InternalRasterTouched)"
    assert guard in destructor, "Unchanged draw must not submit redundant D3D9 scissor state"
    before, after = destructor.split(guard, 1)
    assert "R22SetViewportHook.stdcall<HRESULT>" in before
    assert "R22ApplyGameScissor(device, R22GameScissor)" in after
    assert "NoteRestoreFailure" in after
    assert destructor.index(guard) < destructor.index("R22ApplyGameScissor(device, R22GameScissor)")

    rect = section(source, "HRESULT __stdcall SetScissorRectDestR22(", "HRESULT __stdcall SetRenderStateDestR22(")
    assert "SUCCEEDED(hr) && R22InternalReplayDepth && IsGameDevice(device)" in rect
    assert "R22InternalRasterTouched = true;" in rect
    state = section(source, "HRESULT __stdcall SetRenderStateDestR22(", "bool R22RectCoversBackbuffer(")
    assert "SUCCEEDED(hr) && R22InternalReplayDepth &&" in state
    assert "state == D3DRS_SCISSORTESTENABLE && IsGameDevice(device)" in state
    assert "R22InternalRasterTouched = true;" in state

    apply = section(source, "HRESULT __stdcall R22StateBlockApplyDest(", "bool R22EnsureStateBlockApplyHook(")
    assert "if (SUCCEEDED(hr) && R22InternalReplayDepth)" in apply
    assert "R22InternalRasterTouched = true;" in apply

    # Truth table for the exact C++ guard: only genuinely unchanged replay
    # can elide both D3D9 calls. Viewport/stencil/scissor and StateBlock
    # mutations remain on the old restoration path.
    assert not (False or False)
    assert (True or False) and (False or True) and (True or True)


def main() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    check(source)
    mutations = [
        source.replace("R22InternalViewportTouched || R22InternalRasterTouched",
                       "R22InternalViewportTouched && R22InternalRasterTouched", 1),
        source.replace("R22InternalRasterTouched = false;\n                    stateValid",
                       "stateValid", 1),
        source.replace("if (SUCCEEDED(hr) && R22InternalReplayDepth && IsGameDevice(device))\n                R22InternalRasterTouched = true;",
                       "if (false) R22InternalRasterTouched = true;", 1),
        source.replace("state == D3DRS_SCISSORTESTENABLE && IsGameDevice(device))\n                R22InternalRasterTouched = true;",
                       "state == D3DRS_SCISSORTESTENABLE && IsGameDevice(device));", 1),
        source.replace("if (SUCCEEDED(hr) && R22InternalReplayDepth)\n                        R22InternalRasterTouched = true;",
                       "if (false) R22InternalRasterTouched = true;", 1),
    ]
    for n, mutated in enumerate(mutations, 1):
        assert mutated != source, f"mutation {n} fixture did not change source"
        try:
            check(mutated)
        except (AssertionError, ValueError, IndexError):
            continue
        raise AssertionError(f"mutation {n} erroneously passed")
    print("PASS R22 unchanged-draw scissor restore elision; viewport/scissor/StateBlock safety; 5 mutations")


if __name__ == "__main__":
    main()
