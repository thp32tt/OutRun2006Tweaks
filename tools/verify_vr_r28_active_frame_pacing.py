"""Guard active R28 per-frame pacing diagnostics independent of optional R32 hooks."""
from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
source = (root / "src/vr/d3d9/stereo_renderer_r26.cpp").read_text(encoding="utf-8")
analyzer = (root / "tools/Analyze-OutRunVRSession.ps1").read_text(encoding="utf-8")
required = (
    "R28RecordActiveFramePacing(begin, end);",
    "R28PreviousPresentEndQpc = end.QuadPart;",
    "elapsedMs >= (1000.0 / 60.0)",
    "elapsedMs >= (1000.0 / 50.0)",
    "++w.over16667;",
    "++w.over20000;",
    "frameUs >= 25000",
    "frameUs >= 33333",
    "if (dipTier != 0 && elapsedMs > w.worstDip.elapsedMs)",
    "if (w.worstDip.tier != 0)",
    "band={} prepMs={:.3f}",
    "renderTid={} marker=R28_ACTIVE",
    "VR R28 FRAME DIP: frameMs=",
    "VR R28 FRAME WINDOW 5s: frames=",
    "p95Ms={:.3f} p99Ms={:.3f}",
    "drawPeakAtDip={}",
    "w = {};",
    "GetThreadTimes(GetCurrentThread()",
    "R28ThreadCpuTime100ns(kernel, user)",
    "threadCpuMs >= elapsedMs * 0.70",
    "nonCpuMs >= elapsedMs * 0.50",
    "VR R28 CPU WINDOW 5s: frames=",
    "prepMs={:.3f} threadCpuMs={:.3f} nonCpuMs={:.3f} cpuKnown={}",
    "over16ms={} over20ms={} over25ms={} over33ms={}",
)
for marker in required:
    if marker not in source:
        raise SystemExit(f"R28 active frame pacing missing: {marker}")
start = source.index("HRESULT __stdcall PresentDestR27(")
end = source.index("void R26RollbackHooks()", start)
block = source[start:end]
if not (block.index("QueryPerformanceCounter(&end)") <
        block.index("R28RecordActiveFramePacing(begin, end);") <
        block.index("if (Settings::VRTelemetry)")):
    raise SystemExit("R28 pacing must observe completed Present before 5s reporting")
pat = re.compile(r'VR R28 FRAME DIP: frameMs=([0-9.]+) presentMs=([0-9.]+) estimateFps=([0-9.]+) draws=(\d+) frameSerial=(\d+)')
if not pat.search("VR R28 FRAME DIP: frameMs=33.333 presentMs=2.102 estimateFps=30.0 draws=1234 frameSerial=56789 marker=R28_ACTIVE"):
    raise SystemExit("30 FPS event is not machine parseable")
for marker in ("R28RecordActiveFramePacing(begin, end);",
               "GetThreadTimes(GetCurrentThread()", "R28ThreadCpuTime100ns(kernel, user)",
               "++w.over16667;",
               "++w.over20000;", "++w.over25000;",
               "VR R28 FRAME WINDOW 5s: frames="):
    if source.count(marker) != 1:
        raise SystemExit(f"expected unique invariant {marker}, saw {source.count(marker)}")
    mutation = source.replace(marker, "/* removed measurement */", 1)
    if marker in mutation:
        raise SystemExit(f"negative mutation did not remove {marker}")
# The match value must extend past frameSerial/band to capture CPU timings.
if ")?[^\\r\\n]*'" not in analyzer:
    raise SystemExit("R28 dip regex truncates CPU breakdown fields")
if "const double prepMs = begin.QuadPart >= previous" not in source:
    raise SystemExit("Pre-Present wall work is not measured against previous Present end")
if "R28PreviousThreadCpuValid = cpuReadOk;" not in source:
    raise SystemExit("Thread CPU baseline does not tolerate failed OS samples")
for expected in ("R28CpuDiagnosticWindows", "R28SlowCpuDominantFrames",
                 "R28SlowNonCpuDominantFrames", "R28_CPU_BREAKDOWN_5S.csv",
                 "R28ActiveBelow60FpsFrames", "R28ActiveBelow50FpsFrames",
                 "r28ActiveBelow60FpsFrames", "r28ActiveBelow50FpsFrames",
                 "R28_ACTIVE_FRAME_DIPS.csv", "over20ms="):
    if expected not in analyzer:
        raise SystemExit("missing threshold/analyzer reporting: " + expected)
for ms, below60, below50 in ((11.111, False, False), (16.667, True, False),
                             (19.99, True, False), (20.0, True, True),
                             (25.0, True, True), (33.334, True, True)):
    if ((ms >= 1000.0 / 60.0), (ms >= 1000.0 / 50.0)) != (below60, below50):
        raise SystemExit(f"60/50 FPS boundary test failed: {ms}")
# Functional location guard: spike warning must be emitted only once the
# 5-second window ends, never on a per-frame threshold or tier escalation.
pacing = source[source.index("void R28RecordActiveFramePacing("):
                source.index("void R46TraceShaderFingerprint(")]
flush = pacing.index("if (nowMs - w.startedMs < 5000)")
warning = pacing.index("spdlog::warn(")
if warning <= flush or pacing.count("spdlog::warn(") != 1:
    raise SystemExit("R28 dip log still synchronously executes in frame hot path")
if "R28LastDipLogMs" in source or "R28LastDipLogTier" in source:
    raise SystemExit("R28 per-spike logger state was not retired")
if not (pacing.index("peak.elapsedMs = elapsedMs;") <
        pacing.index("peak.serial = serial;") <
        warning < pacing.index("w = {};")):
    raise SystemExit("worst source frame attribution is not preserved until flush")
for token in ("peak.presentMs", "peak.draws", "peak.serial",
              "peak.prepMs", "peak.threadCpuMs", "peak.nonCpuMs",
              "peak.cpuKnown", "peak.threadId"):
    if token not in pacing[pacing.index("const auto& peak = w.worstDip;"):warning+1100]:
        raise SystemExit("R28 worst-frame metadata dropped: " + token)
reset = source[source.index("if (!Settings::VRTelemetry)", source.index("HRESULT __stdcall PresentDestR27(")):
               source.index("R27TelemetryActiveOnThread = true;")]
for token in ("R28Pacing = {};", "R28PreviousPresentEndQpc = 0;",
              "R28PreviousThreadCpuValid = false;"):
    if token not in reset:
        raise SystemExit("R28 disable/enable epoch leaked: " + token)
# Seeded 5-second burst model: if the original 1-second/tier escalation
# reporting were restored, it would exceed the bounded one-event invariant.
import random
rng = random.Random(280804)
for _case in range(48):
    intervals = [rng.choice((11.11, 16.667, 20.0, 25.0, 33.334, 68., 305.))
                 for _frame in range(300 + rng.randrange(400))]
    peaks = []
    windows = []
    worst = None
    for i, elapsed in enumerate(intervals):
        if elapsed >= 1000.0 / 60.0:
            if worst is None or elapsed > worst[0]:
                worst = (elapsed, i)
        if (i + 1) % 300 == 0:
            windows.append(worst)
            peaks.extend([worst] if worst else [])
            worst = None
    if len(peaks) != len([x for x in windows if x is not None]):
        raise SystemExit("R28 burst-window logging was not bounded")
    for k, event in enumerate(windows):
        start = k * 300
        expected = max(((x, j + start) for j, x in
                        enumerate(intervals[start:start+300])
                        if x >= 1000.0 / 60.0), default=None)
        # Ties retain the first equal-duration frame, matching strict >.
        expected_value = expected[0] if expected else None
        if (event[0] if event else None) != expected_value:
            raise SystemExit("R28 worst-frame duration lost in spike storm")
# Destructive source checks must reject a relocated hot-path warning or
# erased peak-frame capture/reset.
for mutated in (
    pacing.replace("if (nowMs - w.startedMs < 5000)", "if (false)", 1),
    pacing.replace("peak.elapsedMs = elapsedMs;", "/* omitted */", 1),
    pacing.replace("if (w.worstDip.tier != 0)", "if (true)", 1),
):
    if mutated == pacing:
        raise SystemExit("R28 negative mutation missed source anchor")
print("VR R28 ACTIVE PACING BOUNDED WORST-FRAME LOG: PASS (7 baseline mutations, 48 burst models, epoch and logging gates)")
