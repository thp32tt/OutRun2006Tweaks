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
