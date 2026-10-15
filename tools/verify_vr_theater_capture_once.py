#!/usr/bin/env python3
"""Same-tick DXGI acquisition elision, with negative policy mutations."""
from pathlib import Path

root = Path(__file__).resolve().parents[1]
cpp = (root / "vrhost/src/main_r23.cpp").read_text(encoding="utf-8")
policy = (root / "vrhost/src/runtime/theater_capture_reuse.hpp").read_text(encoding="utf-8")

def check(text):
    flat = " ".join(text.split())
    return ("return attemptedClassicCapture && available && freshPixels;" in flat
            and "static_assert(!MayReuseCapture(false, true, true)" in text
            and "static_assert(!MayReuseCapture(true, false, true)" in text
            and "static_assert(!MayReuseCapture(true, true, false)" in text)

assert check(policy), "policy and safety guards must all be present"
for invalid in [
    "attemptedClassicCapture || available || freshPixels",
    "attemptedClassicCapture && available",
    "attemptedClassicCapture && freshPixels",
    "available && freshPixels",
]:
    mutated = policy.replace(
        "attemptedClassicCapture && available && freshPixels", invalid)
    assert not check(mutated), "negative mutation was not rejected"

assert '#include "runtime/theater_capture_reuse.hpp"' in cpp
assert "CaptureStatus capturedForTheater{};" in cpp
assert "capturedForTheater = capture;" in cpp
assert "OutRunVrTheaterCaptureReuse::MayReuseCapture(" in cpp
assert "? capturedForTheater" in cpp
assert ": R23RefreshTheaterFallbackCapture(compositor);" in cpp
assert cpp.count("R23RefreshTheaterFallbackCapture(compositor);") == 1
print("PASS same-tick theater capture reuse: four negative policy mutations")
