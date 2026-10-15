#!/usr/bin/env python3
"""R84: failed right-eye state restoration must poison the current Present.

Validate both R30 and both R33 *physical* per-eye submission functions.
Other restore paths (e.g. SkyGlow) have distinct ownership and must not be
mistaken for these four current-frame draw guards.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
GUARDS = (
    ("src/vr/d3d9/stereo_renderer_r30.cpp",
     ("HRESULT R30ExecuteXyzrhwStereo(", "HRESULT R30TryScreenSpaceFovDraw("),
     "R29OwnerMarkRightDrawFailed();",
     "R29OwnerInvalidateRightDepthStencilIfLeftMayWrite(device);",
     "R29OwnerArmMonoSafety();"),
    ("src/vr/d3d9/stereo_renderer_r33.cpp",
     ("R32ReviewOwnedResult R33TryFastWorld(", "R32ReviewOwnedResult R33TryHud("),
     "R32ReviewMarkFrameRightDrawFailed();",
     "R33InvalidateRightForLeftWrite(",
     "R32ReviewArmStereoRecoverySafety();"),
)
RESTORE = re.compile(r"if\s*\(\s*!restoreOk\s*\)\s*\{([^{}]*)\}", re.S)


def function_block(source: str, signature: str) -> str:
    start = source.index("{", source.index(signature))
    depth = 0
    for pos in range(start, len(source)):
        depth += (source[pos] == "{") - (source[pos] == "}")
        if depth == 0:
            return source[start:pos + 1]
    raise AssertionError(f"unterminated source function: {signature}")


def check(source: str, functions: tuple[str, ...],
          marker: str, invalidate: str, arm: str) -> bool:
    try:
        blocks = [
            [m.group(1) for m in RESTORE.finditer(function_block(source, name))]
            for name in functions
        ]
    except (ValueError, AssertionError):
        return False
    return all(len(guards) == 1 and all(
        key in guards[0] for key in (marker, invalidate, arm)
    ) and guards[0].index(marker) < guards[0].index(invalidate) <
           guards[0].index(arm) for guards in blocks)


def main() -> None:
    for path, functions, marker, invalidate, arm in GUARDS:
        source = (ROOT / path).read_text(encoding="utf-8")
        assert check(source, functions, marker, invalidate, arm), path
        # Mutate each physical draw independently: a previously unrelated
        # SkyGlow restore block can neither hide nor cause this failure.
        for name in functions:
            fn = function_block(source, name)
            owned = RESTORE.search(fn)
            assert owned is not None and marker in owned.group(1), (path, name)
            # The right-eye Draw failure already marks the frame earlier in
            # this same function. Mutate only the *restore* branch, never the
            # earlier working rightHr failure marker.
            restore_guard = owned.group(0)
            mutated_guard = restore_guard.replace(
                marker, "/* omitted current-frame failure veto */", 1)
            mutant = source.replace(
                fn, fn.replace(restore_guard, mutated_guard, 1), 1)
            assert not check(mutant, functions, marker, invalidate, arm), (path, name)
        # A condition inversion must fail even if a later function still has
        # a valid failure branch and the same frame marker.
        for name in functions:
            fn = function_block(source, name)
            owned = RESTORE.search(fn)
            assert owned is not None, (path, name)
            restore_guard = owned.group(0)
            mutated_guard = restore_guard.replace(
                "if (!restoreOk)", "if (restoreOk)", 1)
            mutant = source.replace(
                fn, fn.replace(restore_guard, mutated_guard, 1), 1)
            assert not check(mutant, functions, marker, invalidate, arm), (path, name)
    print("R84 restore failure publication veto: PASS (4 paths, 8 scoped mutations)")


if __name__ == "__main__":
    main()
