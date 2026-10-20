#!/usr/bin/env python3
"""DX9Ex draw-distance bounded policy: source contract and real C++ unit."""
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
source = (ROOT / "src/hooks_drawdistance.cpp").read_text(encoding="utf-8")
header = (ROOT / "src/vr/game/draw_distance_node_safety.hpp").read_text(encoding="utf-8")
unit = ROOT / "tools/tests/test_draw_distance_node_safety.cpp"

required = [
    '#include "vr/game/draw_distance_node_safety.hpp"',
    'DrawDistanceSafety::DrawListStorage',
    'DrawDistanceSafety::SeenNodeCount',
    'DrawDistanceSafety::IsKnownExclusionIndex',
    'DrawDistanceSafety::ShouldQueueNode',
    'DrawDistanceSafety::CanAppend',
    'SkipQuickSortHackStages[stageNum] = skip;',
    'std::free(newPtrs);',
    'std::free(newEntries);',
    'std::free(newUnknown);',
    'if (!newPtrs || !newEntries || !newUnknown)',
]
for token in required:
    assert token in source, f"Missing source safety contract: {token}"
assert source.index("if (!newPtrs || !newEntries || !newUnknown)") < source.index("buffer->MaxBuffers_4 = max_size;")
assert 'CollisionNodesToDisplay[nodeId] = true;' in source
assert 'if (DrawDistanceSafety::ShouldQueueNode(' in source
assert 'if (DrawDistanceSafety::CanAppend(' in source
assert 'DrawListCapacity + 1' in header

compiler = shutil.which("clang++") or shutil.which("g++")
if compiler:
    with tempfile.TemporaryDirectory() as tmp:
        executable = Path(tmp) / ("draw_distance_test.exe" if __import__("os").name == "nt" else "draw_distance_test")
        subprocess.run([compiler, "-std=c++20", "-O2", str(unit), "-o", str(executable)], check=True)
        subprocess.run([str(executable)], check=True)
    print("PASS: DX9Ex draw-distance C++ capacity/exclusion/seen-domain boundary tests")
else:
    print("PASS: DX9Ex draw-distance source contract (no standalone C++ compiler on PATH)")
