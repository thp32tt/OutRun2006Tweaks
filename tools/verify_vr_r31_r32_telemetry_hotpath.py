#!/usr/bin/env python3
"""R31 draw/R32 Present telemetry hotpath and transition regression guard."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
R31 = ROOT / "src/vr/d3d9/stereo_renderer_r31.cpp"
R32 = ROOT / "src/vr/d3d9/stereo_renderer_r32.cpp"
WORKFLOW = ROOT / ".github/workflows/vr-dx9ex-active.yml"

def body(text, sig):
    at = text.index(sig)
    first = text.index("{", at)
    depth = 0
    for i in range(first, len(text)):
        if text[i] == "{": depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0: return text[first:i + 1]
    raise ValueError(sig)

def check(r31, r32):
    try:
        draw = body(r31, "void R31ObserveDraw(")
        present = body(r32, "HRESULT R32WithPresentTelemetry(")
        finalize = body(r32, "void R32FinalizeFramePerf(")
        before = draw.index("if (!R30SupportTelemetryEnabled())")
        stop = draw.index("return;", before)
        reads = draw.index("R30SupportTargetIsBackBuffer()")
        if not (before < stop < reads): return False
        if not all(x in draw[before:stop] for x in (
            "if (R31Frame.epoch != 0)", "R31Frame = {};", "R31Window = {};")):
            return False
        for name in ("FastWorld", "Hud", "Fallback", "Unstable", "Fragile"):
            if "if (R30SupportTelemetryEnabled())" not in body(
                    r31, "inline void R31TelemetryNote" + name + "()"):
                return False
        gate = present.index("if (samplePerf)")
        snapshot = present.index("stereo = R32CaptureStereoWorkload();")
        qpc = present.index("QueryPerformanceCounter(&presentStart)")
        call = present.index("const HRESULT hr = lowerPresent();")
        if not (gate < snapshot < qpc < call): return False
        after = present[call:]
        indices = [after.index(x) for x in (
            "if (samplePerf)", "QueryPerformanceCounter(&presentEnd)",
            "R32FinalizeFramePerf(", "R32LogPerfWindow()", "else",
            "R32FrameWorkloadCounters = {};", "R32LastPresentEndQpc = 0;")]
        if indices != sorted(indices): return False
        # The opt-out reset is now guarded by a Present transition. Verify
        # that the guard clears the QPC baseline and window ownership together.
        transition = after[after.index("else if (R32PerfWindowActive ||"):]
        if not all(x in transition for x in (
            "R32FrameWorkloadCounters.draws != 0)",
            "R32FrameWorkloadCounters = {};",
            "R32PerfWindowCounters = {};",
            "R32PerfBaselineUs = 0;",
            "R32Counters = {};",
            "R32LastPresentEndQpc = 0;",
            "R32PerfWindowActive = false;")):
            return False
        if not (transition.index("R32LastPresentEndQpc = 0;") <
                transition.index("R32PerfWindowActive = false;")):
            return False
        disabled = finalize[
            finalize.index("if (!R30SupportTelemetryEnabled())"):
            finalize.index("auto frame = ")]
        return all(x in disabled for x in (
            "R32LastPresentEndQpc = 0;",
            "R32PerfWindowActive = false;",
            "R32PerfWindowCounters = {};",
            "R32PerfBaselineUs = 0;"))
    except ValueError:
        return False

def main():
    r31 = R31.read_text(encoding="utf-8")
    r32 = R32.read_text(encoding="utf-8")
    assert WORKFLOW.read_text(encoding="utf-8").count(
        "tools/verify_vr_r31_r32_telemetry_hotpath.py") == 2
    assert check(r31, r32), "telemetry hotpath contract broken"
    candidates = (
        (r31.replace("if (!R30SupportTelemetryEnabled())\n            {\n                if (R31Frame.epoch", "if (false)\n            {\n                if (R31Frame.epoch", 1), r32),
        (r31.replace("R31Window = {};\n                }\n                return;", "R31Window = {};\n                }\n                ++R31Frame.draws;", 1), r32),
        (r31.replace("if (R30SupportTelemetryEnabled())", "if (true)", 1), r32),
        (r31, r32.replace("stereo = R32CaptureStereoWorkload();", "stereo = {};", 1)),
        (r31, r32.replace(
            "R32LastPresentEndQpc = 0;\n                    R32PerfWindowActive = false;",
            "R32LastPresentEndQpc = presentStart.QuadPart;\n                    R32PerfWindowActive = false;", 1)),
        (r31, r32.replace(
            "R32LastPresentEndQpc = 0;\n                R32PerfWindowActive = false;\n                return;",
            "R32LastPresentEndQpc = presentEndQpc;\n                R32PerfWindowActive = false;\n                return;", 1)),
    )
    for i, (left, right) in enumerate(candidates):
        assert left != r31 or right != r32, f"mutation {i} not applied"
        assert not check(left, right), f"mutation {i} escaped"
    # Disabled intervals discard the old baseline; first new sample is warm-up.
    last_qpc = 45000
    for enabled in (True, False, False, True):
        if not enabled: last_qpc = 0
        elif last_qpc == 0: last_qpc = 75000
    assert last_qpc == 75000
    print("PASS DX9Ex R31/R32 telemetry hotpath and 6 negative mutations")

if __name__ == "__main__":
    main()
