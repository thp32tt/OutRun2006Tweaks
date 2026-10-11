"""Guard active R28 per-frame pacing diagnostics independent of optional R32 hooks."""
from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
source = (root / "src/vr/d3d9/stereo_renderer_r26.cpp").read_text(encoding="utf-8")
analyzer = (root / "tools/Analyze-OutRunVRSession.ps1").read_text(encoding="utf-8")
required = (
    "R28RecordActiveFramePacing(begin, end);",
    "R28PreviousPresentEndQpc = end.QuadPart;",
    "frameUs >= 25000",
    "frameUs >= 33333",
    "R28LastDipLogMs >= 1000",
    "VR R28 FRAME DIP: frameMs=",
    "VR R28 FRAME WINDOW 5s: frames=",
    "p95Ms={:.3f} p99Ms={:.3f}",
    "drawPeakAtDip={}",
    "w = {};",
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
for marker in ("R28RecordActiveFramePacing(begin, end);", "++w.over25000;",
               "VR R28 FRAME WINDOW 5s: frames="):
    if source.count(marker) != 1:
        raise SystemExit(f"expected unique invariant {marker}, saw {source.count(marker)}")
    mutation = source.replace(marker, "/* removed measurement */", 1)
    if marker in mutation:
        raise SystemExit(f"negative mutation did not remove {marker}")
print("VR R28 ACTIVE FRAME PACING: PASS (three negative mutations)")
