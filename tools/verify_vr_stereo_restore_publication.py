#!/usr/bin/env python3
"""R84: failed per-eye submissions/restores must veto this Present.

Validate R30 left Draw/left c64 rollback as well as both R30/R33 right
restore paths. SkyGlow and unrelated failure sites cannot supply the proof.
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



def scoped_guard(source: str, signature: str) -> str:
    """Return the exact guard body, including nested state-restoration scopes."""
    start = source.index("{", source.index(signature))
    depth = 0
    for pos in range(start, len(source)):
        depth += (source[pos] == "{") - (source[pos] == "}")
        if depth == 0:
            return source[start:pos + 1]
    raise AssertionError(f"unterminated guard: {signature}")


def check_r30_left(source: str) -> bool:
    try:
        for signature in ("HRESULT R30ExecuteXyzrhwStereo(",
                          "HRESULT R30TryScreenSpaceFovDraw("):
            fn = function_block(source, signature)
            guard = scoped_guard(fn, "if (FAILED(leftHr))")
            required = (
                "R29OwnerMarkRightDrawFailed();",
                "R29OwnerInvalidateRightDepthStencilIfLeftMayWrite(device);",
                "R29OwnerReportStereoFailure(",
                "R29OwnerArmMonoSafety();",
                "return leftHr;",
            )
            position = -1
            for token in required:
                position = guard.index(token, position + 1)
        # A failed c64 upload may safely fall through to R29 only when
        # original c64 rollback succeeded. Failure must poison the same eye
        # frame rather than presenting it with an unknown game WVP.
        fov = function_block(source, "HRESULT R30TryScreenSpaceFovDraw(")
        upload = scoped_guard(fov, "if (!leftWvpOk)")
        rollback = scoped_guard(upload, "if (!restored)")
        required = ("R29OwnerMarkRightDrawFailed();",
                    "R29OwnerReportStereoFailure(",
                    "R29OwnerArmMonoSafety();", "return E_FAIL;")
        position = -1
        for token in required:
            position = rollback.index(token, position + 1)
        assert "return E_NOTIMPL;" in upload
        return True
    except (ValueError, AssertionError):
        return False


def check_left_mutations(source: str) -> None:
    functions = ("HRESULT R30ExecuteXyzrhwStereo(",
                 "HRESULT R30TryScreenSpaceFovDraw(")
    assert check_r30_left(source), "R30 left-eye publication veto is missing"
    cases = 0
    for signature in functions:
        fn = function_block(source, signature)
        guard = scoped_guard(fn, "if (FAILED(leftHr))")
        for token in ("R29OwnerMarkRightDrawFailed();",
                      "R29OwnerInvalidateRightDepthStencilIfLeftMayWrite(device);",
                      "R29OwnerReportStereoFailure("):
            mutant = source.replace(fn, fn.replace(
                guard, guard.replace(token, "/* removed */", 1), 1), 1)
            assert not check_r30_left(mutant), (signature, token)
            cases += 1
        mutant = source.replace(fn, fn.replace(
            "if (FAILED(leftHr))", "if (SUCCEEDED(leftHr))", 1), 1)
        assert not check_r30_left(mutant), (signature, "inverted guard")
        cases += 1
    fov = function_block(source, functions[1])
    upload = scoped_guard(fov, "if (!leftWvpOk)")
    rollback = scoped_guard(upload, "if (!restored)")
    mutant = source.replace(fov, fov.replace(
        rollback, rollback.replace(
            "R29OwnerMarkRightDrawFailed();", "/* removed */", 1), 1), 1)
    assert not check_r30_left(mutant), "failed c64 rollback mutation survived"
    cases += 1
    print(f"R84 R30 left draw + c64 rollback current-frame veto: PASS ({cases} negative mutations)")

def main() -> None:
    check_left_mutations((ROOT / "src/vr/d3d9/stereo_renderer_r30.cpp").read_text(encoding="utf-8"))
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
