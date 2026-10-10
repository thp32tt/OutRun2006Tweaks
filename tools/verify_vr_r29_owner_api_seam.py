#!/usr/bin/env python3
"""Guard the R29 -> R30 owner seam against accidental private-state reuse.

Includes mutation checks: replacing each real R29 owner delegation with a
no-op/wrong result must cause verification failure. This is an interim static
check; Win32 compile/link and HMD acceptance remain separate gates.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src/vr/d3d9"
CORE = ROOT / "src/vr/core"


def body(source: str, signature: str) -> str:
    pos = source.find(signature)
    if pos < 0:
        raise AssertionError(f"definition missing: {signature}")
    start = source.find("{", pos)
    if start < 0:
        raise AssertionError(f"body missing: {signature}")
    depth = 0
    for idx in range(start, len(source)):
        if source[idx] == "{":
            depth += 1
        elif source[idx] == "}":
            depth -= 1
            if depth == 0:
                return source[start + 1:idx]
    raise AssertionError(f"unclosed body: {signature}")


OWNER_CALLS = {
    "bool R29OwnerStableStereoBase(": "return R29StableStereoBase(device);",
    "bool R29OwnerFragileEffectCached(": "return R29FragileEffectCached(device, fragile);",
    "void R29OwnerArmMonoSafety(": "R29ArmMonoSafety(extraPresents);",
    "void R29OwnerNoteStableTwoEyeDraw(": "R29TelemetryNoteStableTwoEyeDraw();",
    "R29OwnerInstallStatus() noexcept": "R29StereoInstallState.load(std::memory_order_acquire);",
}


def check(r29: str, r30: str, header: str) -> None:
    for signature, delegation in OWNER_CALLS.items():
        implementation = body(r29, signature)
        assert delegation in implementation, f"R29 delegation changed: {signature}"
        exported = signature.split("R29Owner", 1)[1].split("(", 1)[0]
        assert "R29Owner" + exported in header, f"header missing {exported}"
    assert '#include "../core/r29_owner_api.hpp"' in r29
    assert '#include "../core/r29_owner_api.hpp"' in r30
    for pattern in (
        r"(?<!Owner)\bR29StableStereoBase\(",
        r"(?<!Owner)\bR29FragileEffectCached\(",
        r"(?<!Owner)\bR29ArmMonoSafety\(",
        r"\bR29TelemetryNoteStableTwoEyeDraw\(",
        r"\bR29StereoInstallState\b",
        r"\bR29StableTwoEyeDraws\b",
    ):
        assert not re.search(pattern, r30), f"R30 private R29 leak: {pattern}"
    for interface in (
        "R29OwnerStableStereoBase", "R29OwnerFragileEffectCached",
        "R29OwnerArmMonoSafety", "R29OwnerNoteStableTwoEyeDraw",
        "R29OwnerInstallStatus",
    ):
        assert interface + "(" in r30, f"R30 does not use {interface}"


def main() -> None:
    r29 = (SRC / "stereo_renderer_r29.cpp").read_text(encoding="utf-8")
    r30 = (SRC / "stereo_renderer_r30.cpp").read_text(encoding="utf-8")
    header = (CORE / "r29_owner_api.hpp").read_text(encoding="utf-8")
    check(r29, r30, header)
    for signature, delegation in OWNER_CALLS.items():
        # Mutate the exported owner definition, not an earlier lower-owner
        # call with the same spelling elsewhere in the R29 translation unit.
        pos = r29.find(signature)
        assert pos >= 0
        mutated = r29[:pos] + r29[pos:].replace(
            delegation, "/* poisoned delegation */", 1
        )
        try:
            check(mutated, r30, header)
        except AssertionError:
            pass
        else:
            raise AssertionError(f"negative mutation unexpectedly PASS: {signature}")
    print("R29/R30 owner ABI regression PASS (5 negative mutations)")


if __name__ == "__main__":
    main()
