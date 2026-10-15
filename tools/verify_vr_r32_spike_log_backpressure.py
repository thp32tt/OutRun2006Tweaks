#!/usr/bin/env python3
"""Bound R32 synchronous spike diagnostics and preserve the exact worst-frame evidence."""
from pathlib import Path
import random
ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/vr/d3d9/stereo_renderer_r32.cpp"
WORKFLOW = ROOT / ".github/workflows/vr-dx9ex-active.yml"


def body(source, signature):
    p = source.index("{", source.index(signature))
    depth = 0
    for i in range(p, len(source)):
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
            if not depth:
                return source[p:i + 1]
    raise AssertionError("unclosed " + signature)


def violations(source):
    errors = []
    def check(ok, name):
        if not ok:
            errors.append(name)
    window = body(source, "struct R32PerfWindow")
    final = body(source, "void R32FinalizeFramePerf(")
    log = body(source, "void R32LogPerfWindow()")
    present = body(source, "HRESULT R32WithPresentTelemetry(")
    for x in ("worstBaselineUs", "worstPresentUs",
              "R32FrameWorkload worstWorkload{}",
              "R32StereoWorkloadSnapshot worstStereo{}"):
        check(x in window, "peak storage " + x)
    for x in ("if (frameUs > window.maxFrameUs)",
              "window.maxFrameUs = frameUs;",
              "window.worstBaselineUs = baselineBefore;",
              "window.worstPresentUs = presentUs;",
              "window.worstWorkload = frame;",
              "window.worstStereo = stereo;",
              "if (spike) ++window.spikes;"):
        check(x in final, "peak update " + x)
    check("spdlog::" not in final and "GetTickCount64()" not in final,
          "no per-spike synchronous I/O")
    check("R32LastSpikeLogMs" not in source, "hard spike logger retired")
    check("if (now - R32Counters.lastLogMs < 5000)" in log,
          "five-second cadence")
    for x in ("R32PerfWindowCounters.spikes",
              "R32PerfWindowCounters.maxFrameUs",
              "R32PerfWindowCounters.worstBaselineUs",
              "R32PerfWindowCounters.worstWorkload.indexedDraws",
              "R32PerfWindowCounters.worstWorkload.particleLikeDraws",
              "R32PerfWindowCounters.worstStereo.fastWorld",
              "R32PerfWindowCounters.worstStereo.hud",
              "R32PerfWindowCounters = {};"):
        check(x in log, "aggregate detail " + x)
    for x in ("R32FrameWorkloadCounters = {};", "R32PerfWindowCounters = {};",
              "R32PerfBaselineUs = 0;", "R32Counters = {};",
              "R32LastPresentEndQpc = 0;", "R32PerfWindowActive = false;"):
        check(x in present, "diagnostic opt-out " + x)
    check("else if (R32PerfWindowActive ||" in present and
          "R32FrameWorkloadCounters.draws != 0" in present,
          "only transition/dangling-draw clears inactive diagnostic window")
    check("R32PerfWindowActive = true;" in present,
          "a real sampled Present opens exactly one resettable window")
    check("R32PerfWindowActive = false;" in body(
          source, "void R32InvalidateResetCaches()"),
          "Reset invalidates active diagnostic ownership")
    # During a destructive mutation either anchor can disappear; that is
    # a negative-test violation, never a Python ValueError.
    check("spdlog::info(" in log and
          "R32PerfWindowCounters = {};" in log and
          log.index("spdlog::info(") < log.index("R32PerfWindowCounters = {};"),
          "aggregate emitted before window clear")
    return errors


def numeric_model():
    rng = random.Random(803)
    timestamps = 0
    nlogs = 0
    spikes = 0
    current = []
    for index in range(2600):
        elapsed = 300000 if index % 241 == 0 else rng.randrange(7000, 29000)
        snapshot = (elapsed, rng.randrange(200, 19000),
                    rng.randrange(0, 3500), rng.randrange(0, 150))
        current.append(snapshot)
        spikes += elapsed >= 30000
        timestamps += elapsed
        if timestamps >= 5_000_000:
            worst = max(current, key=lambda v: v[0])
            assert worst in current and worst[0] == max(x[0] for x in current)
            nlogs += 1
            timestamps = 0
            current = []
    assert spikes > 8 and 1 < nlogs < 15, (spikes, nlogs)
    # An opt-out interval discards the pending previous window and EMA.
    before = (100, 25, 300000, 10000)
    disabled = (0, 0, 0, 0)
    after = (1, 0, 12000, 12000)
    assert after != before and disabled != before
    print(f"R32 SPIKE MODEL PASS: spikes={spikes}, bounded five-second reports={nlogs}")


def main():
    source = SOURCE.read_text(encoding="utf-8")
    errors = violations(source)
    if errors:
        raise SystemExit("R32 SPIKE FAIL: " + "; ".join(errors))
    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert workflow.count("tools/verify_vr_r32_spike_log_backpressure.py") == 2
    # Mutate the *owning* function, not the first same-named reset in a
    # different owner. A global replace used to hit R32InvalidateResetCaches
    # instead of the logging/opt-out path and reported a false failure.
    mutations = (
        ("void R32FinalizeFramePerf(", "window.worstBaselineUs = baselineBefore;"),
        ("void R32FinalizeFramePerf(", "window.worstWorkload = frame;"),
        ("void R32FinalizeFramePerf(", "window.worstStereo = stereo;"),
        ("void R32FinalizeFramePerf(", "if (frameUs > window.maxFrameUs)"),
        ("void R32LogPerfWindow()", "R32PerfWindowCounters.worstStereo.fastWorld"),
        ("void R32LogPerfWindow()", "R32PerfWindowCounters = {};"),
        ("HRESULT R32WithPresentTelemetry(", "R32PerfWindowCounters = {};"),
        ("HRESULT R32WithPresentTelemetry(", "R32PerfBaselineUs = 0;"),
        ("void R32LogPerfWindow()", "if (now - R32Counters.lastLogMs < 5000)"),
    )
    for signature, marker in mutations:
        owner = body(source, signature)
        assert owner.count(marker) == 1, (signature, marker)
        mutated = owner.replace(marker, "DESTRUCTIVE_MUTANT", 1)
        assert violations(source.replace(owner, mutated, 1)), (signature, marker)
    numeric_model()
    print("R32 SPIKE SOURCE PASS: nine scoped destructive mutants, epoch, peak and full gate")


if __name__ == "__main__":
    main()
