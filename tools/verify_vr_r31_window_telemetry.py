#!/usr/bin/env python3
"""R31 disabled telemetry cannot leak old frame sums into a new enabled window.

Run once per source change; independent negative mutation controls. No HMD claims.
"""
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "src/vr/d3d9/stereo_renderer_r31.cpp"


def body(text: str) -> str:
    start = text.index("void R31FinalizePerfFrame() noexcept")
    end = text.index("void R31ObserveDraw(", start)
    return text[start:end]


def violations(text: str) -> list[str]:
    part = body(text)
    gate = "if (!R30SupportTelemetryEnabled())"
    clear = "R31Window = {};"
    early = "return;"
    take = "++R31Window.presents;"
    if part.count(gate) != 1:
        return ["missing disabled-telemetry gate"]
    if part.count(clear) != 2:
        return ["missing disabled reset or timed-window reset"]
    sub = part[part.index(gate):part.index(take)]
    if not (sub.count(clear) == 1 and sub.count(early) == 1):
        return ["disabled gate does not clear and exit"]
    if not part.index(gate) < part.index(take):
        return ["disabled gate follows accumulation"]
    if "R31Frame = {};" in sub or "R31TelemetryResetFrameWindow();" in sub:
        return ["diagnostic disable altered per-frame counters"]
    if "now - R31Window.lastLogMs >= 5000" not in part:
        return ["five-second window flush missing"]
    return []


def fixture() -> None:
    # Model only the accum/reset contract, not rendering or per-frame counters.
    presents = 0
    for enabled, frames in ((True, 12), (True, 8), (False, 99), (True, 5)):
        if not enabled:
            presents = 0
        else:
            presents += frames
    assert presents == 5, "old diagnostic frames leaked after disable"


def main() -> None:
    source = SOURCE.read_text(encoding="utf-8")
    assert not violations(source), violations(source)
    mutations = (
        ("if (!R30SupportTelemetryEnabled())", "if (R30SupportTelemetryEnabled())"),
        ("R31Window = {};\n                return;", "R31Window = {};\n                ++R31Window.presents;"),
        ("R31Window = {};\n                return;", "return;"),
        ("if (!R30SupportTelemetryEnabled())", "if (false)"),
    )
    for old, new in mutations:
        assert source.count(old) >= 1, "mutation anchor missing: " + old
        mutated = source.replace(old, new, 1)
        # The unconditional/falsified guards must also be rejected syntactically.
        assert violations(mutated), "mutation escaped: " + old
    fixture()
    print("R31 telemetry window PASS: disabled reset, clean re-enable, 4 mutations")


if __name__ == "__main__":
    main()
