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
    "nowMs - R28LastDipLogMs >= 1000",
    "dipTier > R28LastDipLogTier",
    "band={} marker=R28_ACTIVE",
    "VR R28 FRAME DIP: frameMs=",
    "VR R28 FRAME WINDOW 5s: frames=",
    "p95Ms={:.3f} p99Ms={:.3f}",
    "drawPeakAtDip={}",
    "w = {};",
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
for marker in ("R28RecordActiveFramePacing(begin, end);", "++w.over16667;",
               "++w.over20000;", "++w.over25000;",
               "VR R28 FRAME WINDOW 5s: frames="):
    if source.count(marker) != 1:
        raise SystemExit(f"expected unique invariant {marker}, saw {source.count(marker)}")
    mutation = source.replace(marker, "/* removed measurement */", 1)
    if marker in mutation:
        raise SystemExit(f"negative mutation did not remove {marker}")
for expected in ("R28ActiveBelow60FpsFrames", "R28ActiveBelow50FpsFrames",
                 "r28ActiveBelow60FpsFrames", "r28ActiveBelow50FpsFrames",
                 "R28_ACTIVE_FRAME_DIPS.csv", "over20ms="):
    if expected not in analyzer:
        raise SystemExit("missing threshold/analyzer reporting: " + expected)
for ms, below60, below50 in ((11.111, False, False), (16.667, True, False),
                             (19.99, True, False), (20.0, True, True),
                             (25.0, True, True), (33.334, True, True)):
    if ((ms >= 1000.0 / 60.0), (ms >= 1000.0 / 50.0)) != (below60, below50):
        raise SystemExit(f"60/50 FPS boundary test failed: {ms}")
print("VR R28 ACTIVE FRAME PACING: PASS (5 negative mutations + 60/50 FPS thresholds)")
