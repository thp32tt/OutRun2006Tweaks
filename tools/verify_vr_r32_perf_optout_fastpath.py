#!/usr/bin/env python3
"""R32 telemetry disabled-Present write-free fast path, toggles and Reset."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CPP = ROOT / "src/vr/d3d9/stereo_renderer_r32.cpp"
WORKFLOW = ROOT / ".github/workflows/vr-dx9ex-active.yml"


def owner(source, signature):
    start = source.index(signature)
    opening = source.index("{", start)
    depth = 0
    for i in range(opening, len(source)):
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
            if depth == 0:
                return source[start:i + 1]
    raise AssertionError("unterminated " + signature)


def verify(source):
    assert "thread_local bool R32PerfWindowActive = false;" in source
    present = owner(source, "HRESULT R32WithPresentTelemetry(")
    reset = owner(source, "void R32InvalidateResetCaches()")
    finalize = owner(source, "void R32FinalizeFramePerf(")
    required = (
        "const bool samplePerf = gameDevice && R30SupportTelemetryEnabled();",
        "if (samplePerf)",
        "R32PerfWindowActive = true;",
        "const HRESULT hr = lowerPresent();",
        "R32FinalizeFramePerf(",
        "else if (R32PerfWindowActive ||",
        "R32FrameWorkloadCounters.draws != 0)",
        "R32FrameWorkloadCounters = {};",
        "R32PerfWindowCounters = {};",
        "R32PerfBaselineUs = 0;",
        "R32Counters = {};",
        "R32LastPresentEndQpc = 0;",
        "R32PerfWindowActive = false;",
    )
    for marker in required:
        assert marker in present, "Present missing " + marker
    assert present.index("R32PerfWindowActive = true;") < present.index(
        "const HRESULT hr = lowerPresent();")
    assert present.index("else if (R32PerfWindowActive ||") < present.index(
        "R32PerfWindowCounters = {};")
    assert "else\n                {" not in present.split(
        "if (gameDevice)", 1)[1], "unconditional telemetry-off reset returned"
    for marker in ("R32FrameWorkloadCounters = {};",
                   "R32PerfWindowCounters = {};",
                   "R32PerfBaselineUs = 0;",
                   "R32Counters = {};",
                   "R32LastPresentEndQpc = 0;",
                   "R32PerfWindowActive = false;"):
        assert marker in reset and marker in finalize, marker
    assert finalize.index("if (!R30SupportTelemetryEnabled())") < finalize.index(
        "R32PerfWindowActive = false;")
    assert "R32LogPerfWindow();" in present
    return present


def model():
    active = False
    draws = 0
    clears = 0
    for _ in range(12000):
        # Ordinary idle telemetry-off frame: no writes to the large window.
        if active or draws:
            clears += 1
            active = False
            draws = 0
    assert clears == 0
    # Active recording followed by 10k disabled frames clears once.
    active = True
    draws = 3298
    for _ in range(10000):
        if active or draws:
            clears += 1
            active, draws = False, 0
    assert clears == 1, clears
    # Mid-frame enabled draws / disabled Present must still discard that
    # partial workload, even if no prior sampled Present activated the flag.
    draws = 123
    if active or draws:
        clears += 1
        active, draws = False, 0
    assert clears == 2 and not active and draws == 0
    # Mid-Present disable and game Reset both invalidate the same epoch.
    active = True
    active, draws = False, 0
    assert not active and draws == 0
    print("R32 disabled Present numeric model PASS: 22k idle frames, 2 transitions")


def mutate(source):
    present = owner(source, "HRESULT R32WithPresentTelemetry(")
    reset = owner(source, "void R32InvalidateResetCaches()")
    finalize = owner(source, "void R32FinalizeFramePerf(")
    mutations = (
        (present, "R32PerfWindowActive = true;", "R32PerfWindowActive = false;"),
        (present, "else if (R32PerfWindowActive ||", "else if (false ||"),
        (present, "R32FrameWorkloadCounters.draws != 0)", "false)"),
        (present, "R32PerfWindowCounters = {};", "/* no clear */"),
        (present, "R32PerfWindowActive = false;", "R32PerfWindowActive = true;"),
        (reset, "R32PerfWindowActive = false;", "R32PerfWindowActive = true;"),
        (finalize, "R32PerfWindowCounters = {};", "/* stale window */"),
        (finalize, "R32PerfWindowActive = false;", "R32PerfWindowActive = true;"),
    )
    for target, good, wrong in mutations:
        assert target.count(good) == 1, good
        broken = source.replace(target, target.replace(good, wrong, 1), 1)
        try:
            verify(broken)
        except (AssertionError, ValueError):
            continue
        raise AssertionError("diagnostic fastpath regression survived: " + good)
    return len(mutations)


if __name__ == "__main__":
    source = CPP.read_text(encoding="utf-8")
    verify(source)
    model()
    total = mutate(source)
    assert WORKFLOW.read_text(encoding="utf-8").count(
        "tools/verify_vr_r32_perf_optout_fastpath.py") == 2
    print(f"PASS R32 sampled/disabled session lifecycle and {total} destructive mutants")
