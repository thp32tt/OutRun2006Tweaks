#!/usr/bin/env python3
"""R23 QPC host freshness correctness: overflow, invalid samples, and fallback."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R23 = (ROOT / "src/vr/d3d9/stereo_renderer_r23.cpp").read_text(encoding="utf-8")
HELPER = (ROOT / "src/vr/ipc/qpc_freshness.hpp").read_text(encoding="utf-8")
SMOKE = (ROOT / "vrhost/tests/qpc_freshness_smoke.cpp").read_text(encoding="utf-8")

def check(source: str, helper: str, smoke: str) -> None:
    start = source.index("const char* R23DiagnoseHostFreshness(")
    end = source.index("void R23MaybeLogSummary()", start)
    function = source[start:end]
    assert '#include "../ipc/qpc_freshness.hpp"' in source
    assert "OutRunVR::Ipc::ElapsedQpcMilliseconds(" in function
    assert "snap.sampleQpc, now.QuadPart, frequency);" in function
    assert 'if (ageMs < 0)' in function
    assert 'return "qpc-invalid";' in function
    assert "((now.QuadPart - snap.sampleQpc) * 1000)" not in function
    for token in ("wholeSeconds = elapsed / frequency",
                  "remainder = elapsed % frequency",
                  "wholeSeconds > limit / 1000",
                  "remainder <= limit / 1000",
                  "wrapThreshold = frequency - remainder",
                  "for (int step = 0; step < 1000; ++step)",
                  "residual -= wrapThreshold",
                  "residual += remainder",
                  "base > limit - partial ? limit : base + partial",
                  "if (sample <= 0 || now < sample || frequency <= 0)"):
        assert token in helper, token
    for token in ("ghz * 40LL * 86400LL",
                  "sample + ghz * 3 / 2",
                  "sample - 1", "sample, sample, 0",
                  "max)(), 1", "high / 2, high",
                  "huge / 500 - 1", "huge / 500, huge"):
        assert token in smoke, token

check(R23, HELPER, SMOKE)
for source, helper, smoke in (
    (R23.replace("OutRunVR::Ipc::ElapsedQpcMilliseconds(",
                 "OldUnsafeQpcMilliseconds(", 1), HELPER, SMOKE),
    (R23, HELPER.replace("wholeSeconds > limit / 1000",
                         "wholeSeconds < limit / 1000", 1), SMOKE),
    (R23, HELPER.replace("remainder <= limit / 1000",
                         "remainder >= limit / 1000", 1), SMOKE),
    (R23, HELPER.replace("wrapThreshold = frequency - remainder",
                         "wrapThreshold = frequency + remainder", 1), SMOKE),
    (R23, HELPER, SMOKE.replace("ghz * 40LL * 86400LL",
                               "ghz * 2LL", 1)),
):
    try:
        check(source, helper, smoke)
    except AssertionError:
        continue
    raise AssertionError("QPC freshness destructive mutation escaped")
print("DX9Ex R23 QPC host freshness overflow/mutation PASS")
