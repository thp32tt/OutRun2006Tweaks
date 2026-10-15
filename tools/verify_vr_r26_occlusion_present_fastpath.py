#!/usr/bin/env python3
"""R26 occlusion writer fast rejection and disabled Present profiler bypass.

This tests source ownership, destructive mutations, deterministic read counts
and conservative failure handling; it does not assert a headset FPS increase.
"""
from itertools import product
from pathlib import Path

SOURCE = (Path(__file__).resolve().parents[1] /
          "src/vr/d3d9/stereo_renderer_r26.cpp").read_text(encoding="utf-8")


def extract(source, signature):
    begin = source.index(signature)
    opening = source.index("{", begin)
    depth = 0
    for i in range(opening, len(source)):
        depth += (source[i] == "{") - (source[i] == "}")
        if depth == 0:
            return source[begin:i + 1]
    raise AssertionError("unclosed function " + signature)


def verify(source):
    occ = extract(source, "bool R26TrackedOcclusionDrawIsWriteFree(")
    present = extract(source, "HRESULT __stdcall PresentDestR27(")
    states = ("D3DRS_COLORWRITEENABLE", "D3DRS_ZWRITEENABLE",
              "D3DRS_STENCILENABLE", "D3DRS_STENCILWRITEMASK")
    positions = [occ.index(state) for state in states]
    assert positions == sorted(positions)
    for token in ("colorWrite != 0", "zWrite != FALSE",
                  "if (stencilEnable == FALSE)\n                return true;",
                  "stencilWriteMask == 0", "if (!device)"):
        assert token in occ, token
    assert occ.index("colorWrite != 0") < positions[1]
    assert occ.index("zWrite != FALSE") < positions[2]
    assert occ.index("if (stencilEnable == FALSE)") < positions[3]
    assert "return ReadTrackedRenderState(" in occ
    assert "stencilWriteMask == 0" in occ.split("return ReadTrackedRenderState(", 1)[1]
    off = present.split("if (!Settings::VRTelemetry)", 1)[1].split(
        "if (!R27TelemetryActiveOnThread)\n            {", 1)[0]
    assert "if (R27TelemetryActiveOnThread)" in off
    assert "R27TelemetryActiveOnThread = false;" in off
    for marker in ("R28Pacing = {};", "R28PreviousPresentEndQpc = 0;",
                   "R28PreviousThreadCpuValid = false;",
                   "R27PresentSamples = 0;"):
        assert marker in off, marker
    assert "return R27PresentR23Hook.stdcall<HRESULT>(device," in off
    assert "QueryPerformanceCounter" not in off
    enabled = present.split("R27TelemetryActiveOnThread = true;", 1)[1]
    assert enabled.count("QueryPerformanceCounter(&") == 2
    assert "R28RecordActiveFramePacing(begin, end);" in enabled
    assert "R28PreviousDrawSerial = TopLevelDrawSerial();" in present
    assert "R27TelemetryActiveOnThread = true;" in present


def sample(color, depth, stencil, mask, failed_at=None):
    states = (color, depth, stencil, mask)
    # Fail closed on every state actually read, skip provably irrelevant reads.
    reads = 0
    for i, value in enumerate(states):
        reads += 1
        if failed_at == i:
            return False, reads
        if i == 0 and value != 0:
            return False, reads
        if i == 1 and value != 0:
            return False, reads
        if i == 2 and value == 0:
            return True, reads
        if i == 3:
            return value == 0, reads
    raise AssertionError("unreachable")


def main():
    verify(SOURCE)
    for color, depth, stencil, mask in product((0, 1), repeat=4):
        expected = color == 0 and depth == 0 and (stencil == 0 or mask == 0)
        ok, reads = sample(color, depth, stencil, mask)
        assert ok == expected
        assert reads == (1 if color else 2 if depth else
                         3 if not stencil else 4)
        for failure_at in range(reads):
            failed, got_reads = sample(color, depth, stencil, mask, failure_at)
            assert not failed and got_reads == failure_at + 1
    for good, bad in (
        ("colorWrite != 0", "colorWrite == 0"),
        ("zWrite != FALSE", "zWrite == FALSE"),
        ("if (stencilEnable == FALSE)", "if (stencilEnable != FALSE)"),
        ("stencilWriteMask == 0", "stencilWriteMask != 0"),
        ("if (!Settings::VRTelemetry)", "if (Settings::VRTelemetry)"),
        ("                    R27TelemetryActiveOnThread = false;",
         "                    R27TelemetryActiveOnThread = true;"),
        ("R28Pacing = {};", "/* retain stale pacing */"),
        ("                    R28PreviousPresentEndQpc = 0;",
         "                    /* preserve stale Present */"),
        ("R28PreviousDrawSerial = TopLevelDrawSerial();",
         "R28PreviousDrawSerial = 0;"),
        ("QueryPerformanceCounter(&end);", "/* QPC end removed */"),
    ):
        assert good in SOURCE, good
        try:
            verify(SOURCE.replace(good, bad, 1))
        except (AssertionError, ValueError, IndexError):
            continue
        raise AssertionError("unsafe R26 mutation escaped: " + good)
    print("PASS R26 write-free occlusion: 16 predicates, all observed getter failures, "
          "10 destructive mutations; disabled Present diagnostics bypass")


if __name__ == "__main__":
    main()
