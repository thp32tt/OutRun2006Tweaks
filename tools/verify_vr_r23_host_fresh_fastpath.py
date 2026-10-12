#!/usr/bin/env python3
"""Guard R23 Present host-freshness CPU fast path and seqlock correctness."""
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "src/vr/d3d9/stereo_renderer_r23.cpp"


def function(source: str) -> str:
    start = source.index("const char* R23DiagnoseHostFreshness(")
    end = source.index("void R23MaybeLogSummary()", start)
    return source[start:end]


def verify(source: str) -> None:
    body = function(source)
    required = (
        "if (!SharedState)",
        "offsetof(OutRunVR::SharedPoseState, orientation)",
        "static_assert(R23HostFreshSnapshotBytes == 40u",
        "std::memcpy(&snap, SharedState, R23HostFreshSnapshotBytes);",
        "if (before & 1u) continue;",
        "if (before == after && !(after & 1u))",
        'if (!stable) return "seqlock-busy";',
        "if (snap.magic != OutRunVR::SharedMagic ||",
        "snap.protocolVersion != OutRunVR::SharedProtocolVersion ||",
        "snap.structSize != sizeof(OutRunVR::SharedPoseState)",
        "if (!snap.hostPid)",
        "snap.flags & OutRunVR::HostAlive",
        "snap.flags & OutRunVR::SessionVisible",
        "snap.flags & OutRunVR::HostShouldRender",
        "if (snap.sampleQpc <= 0)",
        "static const LONGLONG frequency = []() noexcept {",
        "QueryPerformanceFrequency(&value)",
        "QueryPerformanceCounter(&now)",
        "frequency <= 0 || now.QuadPart < snap.sampleQpc",
    )
    for token in required:
        assert token in body, token
    assert body.count("MemoryBarrier();") == 2
    assert body.count("QueryPerformanceFrequency(") == 1
    assert "sizeof(snap)" not in body
    assert "SharedState->magic" not in body
    assert "SharedState->protocolVersion" not in body
    assert body.index('if (!stable) return "seqlock-busy";') < body.index(
        "if (snap.magic != OutRunVR::SharedMagic ||")
    assert body.index("std::memcpy(&snap, SharedState") < body.index(
        "const std::uint32_t after = SharedState->sequence;")
    assert body.index("if (snap.sampleQpc <= 0)") < body.index(
        "QueryPerformanceCounter(&now)")




RASTER_SOURCE = Path(__file__).resolve().parents[1] / "src/vr/d3d9/stereo_renderer_r22.cpp"


def verify_raster_snapshot_footprint(r23: str, r22: str) -> None:
    accessor_start = r22.index("inline bool TrackedRasterShadowValid()")
    accessor_end = r22.index("inline bool TryGetTrackedViewport", accessor_start)
    accessor = r22[accessor_start:accessor_end]
    assert "return R22ShadowState.Valid();" in accessor
    assert "R22ShadowState = snapshot;" in r22
    assert "R22ShadowState = {};" in r22
    assert r23.count("TrackedRasterShadowValid()") == 2
    assert "GetTrackedRasterShadow().Valid()" not in r23

    clear = r23[r23.index("HRESULT __stdcall ClearDestR23("):
                r23.index("void R23BeforeTopLevelDraw(")]
    draw = r23[r23.index("void R23BeforeTopLevelDraw("):
               r23.index("HRESULT __stdcall DrawPrimitiveDestR23")]
    for route in (clear, draw):
        assert "IsTrackedStateBlockReliable()" in route
        assert "TrackedRasterShadowValid()" in route
    assert "R23CaptureActualGameState(" in clear
    assert "R23ClearR22Hook.stdcall<HRESULT>" in clear
    assert 'R23CaptureActualGameState(device, ignored, "Draw", false);' in draw

    capture = r23[r23.index("bool R23CaptureActualGameState("):
                  r23.index("void R23Reject(")]
    assert "const auto shadow = GetTrackedRasterShadow();" in capture
    assert "CaptureTrackedRasterState(device, actual)" in capture
    assert "SetTrackedRasterShadow(actual)" in capture

    present = function(r23)
    header = present[present.index("struct R23HostFreshHeader"):
                     present.index("R23HostFreshHeader snap{};")]
    for field in ("magic", "protocolVersion", "structSize", "sequence",
                  "hostPid", "clientPid", "flags", "heartbeat", "sampleQpc"):
        assert field in header, field
    assert "sizeof(R23HostFreshHeader) == R23HostFreshSnapshotBytes" in header
    assert "offsetof(R23HostFreshHeader, sampleQpc) ==" in header
    assert "offsetof(OutRunVR::SharedPoseState, sampleQpc)" in header
    assert "R23HostFreshHeader snap{};" in present
    assert "OutRunVR::SharedPoseState snap{};" not in present
    assert "std::memcpy(&snap, SharedState, R23HostFreshSnapshotBytes);" in present
    assert present.count("MemoryBarrier();") == 2
    assert "if (before == after && !(after & 1u))" in present
    assert "now.QuadPart < snap.sampleQpc" in present

if __name__ == "__main__":
    source = SOURCE.read_text(encoding="utf-8")
    verify(source)
    mutations = (
        ("R23HostFreshSnapshotBytes);", "sizeof(snap));"),
        ("offsetof(OutRunVR::SharedPoseState, orientation)",
         "sizeof(OutRunVR::SharedPoseState)"),
        ("MemoryBarrier();", "/* missing barrier */"),
        ("before == after && !(after & 1u)", "before == after"),
        ("static const LONGLONG frequency", "const LONGLONG frequency"),
        ("QueryPerformanceFrequency(&value)", "QueryPerformanceFrequency(&now)"),
        ('if (!stable) return "seqlock-busy";', 'if (false) return "seqlock-busy";'),
        ("snap.flags & OutRunVR::SessionVisible", "snap.flags & OutRunVR::HostAlive"),
        ("if (snap.magic != OutRunVR::SharedMagic ||",
         "if (snap.magic == OutRunVR::SharedMagic &&"),
    )
    for good, bad in mutations:
        assert good in function(source), good
        try:
            verify(source.replace(good, bad, 1))
        except (AssertionError, ValueError):
            continue
        raise AssertionError("R23 destructive mutation survived: " + good)
    print(f"PASS R23 host freshness prefix/frequency and {len(mutations)} destructive mutations")
    r22_source = RASTER_SOURCE.read_text(encoding="utf-8")
    verify_raster_snapshot_footprint(source, r22_source)
    footprint_mutations = (
        ("r22", "return R22ShadowState.Valid();", "return true;"),
        ("r23", "TrackedRasterShadowValid()", "GetTrackedRasterShadow().Valid()"),
        ("r23", "R23HostFreshHeader snap{};", "OutRunVR::SharedPoseState snap{};"),
        ("r23", "sizeof(R23HostFreshHeader) == R23HostFreshSnapshotBytes",
         "sizeof(R23HostFreshHeader) != R23HostFreshSnapshotBytes"),
        ("r23", "offsetof(OutRunVR::SharedPoseState, sampleQpc)",
         "offsetof(OutRunVR::SharedPoseState, orientation)"),
        ("r23", "CaptureTrackedRasterState(device, actual)",
         "/* no live fallback */"),
    )
    for location, good, bad in footprint_mutations:
        original = r22_source if location == "r22" else source
        assert good in original
        changed = original.replace(good, bad, 1)
        try:
            verify_raster_snapshot_footprint(
                changed if location == "r23" else source,
                changed if location == "r22" else r22_source)
        except (AssertionError, ValueError):
            continue
        raise AssertionError("R23 snapshot-footprint mutation survived: " + good)
    print(f"PASS R23 snapshot footprint and {len(footprint_mutations)} negative mutations")
