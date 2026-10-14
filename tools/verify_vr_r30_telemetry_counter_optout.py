#!/usr/bin/env python3
"""R30 telemetry-off counter writes: all draw/stream paths, with destructive negatives."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/vr/d3d9/stereo_renderer_r30.cpp"

# A complete single-feature inventory: VB/IB shadow, XYZRHW draw/fallback,
# screen-space FOV/fallback and eye SkyGlow. These are diagnostic-only counters.
COUNTS = {
    "R30ScreenSpaceFovDraws": 2,
    "R30ScreenSpaceFallbacks": 1,
    "R30ScreenSpaceBuildFailures": 1,
    "R30XyzrhwHudDraws": 1,
    "R30XyzrhwWorldEffectDraws": 1,
    "R30XyzrhwRhwWorldPromotions": 1,
    "R30XyzrhwFallbacks": 9,
    "R30XyzrhwAtomicFallbacks": 1,
    "R30XyzrhwDepthPreserveFallbacks": 1,
    "R30XyzrhwBilateralFallbacks": 1,
    "R30ShadowWrites": 1,
    "R30ShadowReadHits": 6,
    "R30ShadowReadMisses": 4,
    "R30ShadowDiscardInvalidations": 1,
    "R30SkyGlowFrames": 1,
    "R30SkyGlowFailures": 1,
}

HELPER = """inline void R30RecordTelemetryCounter(std::uint64_t& counter) noexcept
        {
            if (Settings::VRTelemetry)
                ++counter;
        }"""


def errors(source: str) -> list[str]:
    faults: list[str] = []
    if HELPER not in source:
        faults.append("the opt-out helper must skip writes when telemetry is disabled")
    if "if (!Settings::VRTelemetry)\n                return;" not in source:
        faults.append("Present telemetry must retain its disabled early return")
    for counter, count in COUNTS.items():
        actual = source.count("R30RecordTelemetryCounter(" + counter + ");")
        if actual != count:
            faults.append(f"{counter}: expected {count} guarded writes, found {actual}")
        if re.search(r"\+\+\s*" + counter + r"\b|\b" + counter + r"\s*\+\+", source):
            faults.append(counter + ": unguarded increment")
        if not re.search(r"\bstd::uint64_t\s+" + counter + r"\s*=\s*0\s*;", source):
            faults.append(counter + ": diagnostic storage missing")
    return faults


def main() -> int:
    source = SOURCE.read_text(encoding="utf-8")
    failures = errors(source)
    if failures:
        print("R30 telemetry opt-out FAIL: " + "; ".join(failures))
        return 1

    # Destructive/mutation negatives must fail, not just restate a matched token.
    wrong_guard = source.replace(
        "if (Settings::VRTelemetry)\n                ++counter;",
        "if (true)\n                ++counter;", 1,
    )
    raw_hotpath = source.replace(
        "R30RecordTelemetryCounter(R30ShadowReadHits);",
        "++R30ShadowReadHits;", 1,
    )
    dropped_route = source.replace(
        "R30RecordTelemetryCounter(R30XyzrhwFallbacks);", ";", 1,
    )
    wrong_report = source.replace(
        "if (!Settings::VRTelemetry)\n                return;",
        "if (false)\n                return;", 1,
    )
    for label, mutant in (
        ("disabled opt-out", wrong_guard),
        ("raw shadow increment", raw_hotpath),
        ("lost XYZRHW route", dropped_route),
        ("disabled Present report", wrong_report),
    ):
        if mutant == source or not errors(mutant):
            print(f"R30 telemetry mutation FAIL: {label} escaped")
            return 1

    print("R30 telemetry opt-out PASS: 16 counters / 33 writes, 4 negative mutations")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
