#!/usr/bin/env python3
"""Protect R21 Present-bound host liveness, coherent IPC and cached QPC frequency."""
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "src/vr/d3d9/stereo_renderer_r21.cpp"

def slices(source):
    clock = source[source.index("bool R21ComputeAgeMs("):source.index("R21HostStatus R21ReadHostFreshness(")]
    read = source[source.index("R21HostStatus R21ReadHostFreshness("):source.index("void R21ApplyHostFailClosedAtPresent()")]
    caller = source[source.index("void R21ApplyHostFailClosedAtPresent()"):source.index("HRESULT __stdcall PresentDestR21(")]
    return clock, read, caller

def verify(source):
    clock, read, caller = slices(source)
    for token in (
        "if (sampleQpc <= 0)",
        "static const LONGLONG frequency = []() noexcept {",
        "QueryPerformanceFrequency(&value)",
        "frequency <= 0 || !QueryPerformanceCounter(&now)",
        "now.QuadPart < sampleQpc",
        "if (delta > INT64_MAX / 1000)",
        "ageMs = (delta * 1000) / frequency;",
    ):
        assert token in clock, token
    assert clock.count("QueryPerformanceFrequency(") == 1
    assert clock.index("if (delta > INT64_MAX / 1000)") < clock.index("ageMs = (delta * 1000)")
    for token in (
        "if (!SharedState)",
        "const std::uint32_t before = SharedState->sequence;",
        "if (before & 1u)",
        "const std::uint32_t headerMagic = SharedState->magic;",
        "const std::uint32_t headerVersion = SharedState->protocolVersion;",
        "const std::uint32_t headerSize = SharedState->structSize;",
        "const std::uint32_t after = SharedState->sequence;",
        "if (before != after || (after & 1u))",
        "if (headerMagic != OutRunVR::SharedMagic ||",
        "headerVersion != OutRunVR::SharedProtocolVersion ||",
        "headerSize != sizeof(OutRunVR::SharedPoseState))",
        "if (!hostPid ||",
        "R21ComputeAgeMs(sampleQpc, ageMs)",
        "if ((flags & OutRunVR::HostShouldRender) == 0)",
        "return R21HostStatus::SoftSuspend;",
        "return R21HostStatus::Fresh;",
    ):
        assert token in read, token
    assert read.count("MemoryBarrier();") == 2
    assert read.index("const std::uint32_t before") < read.index("const std::uint32_t headerMagic")
    assert read.index("const std::uint32_t headerMagic") < read.index("const std::uint32_t after")
    assert read.index("if (before != after ||") < read.index("if (headerMagic !=")
    assert read.index("if (headerMagic !=") < read.index("hostPid = pid;")
    assert "SharedState->magic != OutRunVR::SharedMagic" not in read
    for token in ("ObserveFreshHost();", "ObserveSoftHostSuspend();", "RuntimeEligibility::FailClosed();", "nowMs - R21LastHealthyTickMs <="):
        assert token in caller, token

def status(valid, coherent, pid, flags, sample, now, hz):
    if not valid or not coherent or not pid or (flags & 3) != 3:
        return "STALE"
    if sample <= 0 or hz <= 0 or now < sample:
        return "STALE"
    delta = now - sample
    if delta > (2**63 - 1) // 1000 or (delta * 1000) // hz > 250:
        return "STALE"
    return "FRESH" if flags & 4 else "SOFT"

def main():
    source = SOURCE.read_text(encoding="utf-8")
    verify(source)
    fixtures = (
        ("FRESH", (1, 1, 9, 7, 100000, 130000, 1000000)),
        ("SOFT", (1, 1, 9, 3, 100000, 130000, 1000000)),
        ("STALE", (0, 1, 9, 7, 100000, 130000, 1000000)),
        ("STALE", (1, 0, 9, 7, 100000, 130000, 1000000)),
        ("STALE", (1, 1, 0, 7, 100000, 130000, 1000000)),
        ("STALE", (1, 1, 9, 7, 100000, 430000, 1000000)),
        ("STALE", (1, 1, 9, 7, 1, 2**63-1, 1000000)),
        ("STALE", (1, 1, 9, 7, 200, 100, 1000000)),
    )
    for expected, args in fixtures:
        assert status(*args) == expected, (expected, args)
    mutations = (
        ("static const LONGLONG frequency", "const LONGLONG frequency"),
        ("QueryPerformanceFrequency(&value)", "QueryPerformanceFrequency(&now)"),
        ("if (delta > INT64_MAX / 1000)", "if (false)"),
        ("if (before & 1u)", "if (false)"),
        ("MemoryBarrier();", "/* lost barrier */"),
        ("if (before != after || (after & 1u))", "if (false)"),
        ("if (headerMagic != OutRunVR::SharedMagic ||", "if (false ||"),
        ("headerVersion != OutRunVR::SharedProtocolVersion ||", "false ||"),
        ("headerSize != sizeof(OutRunVR::SharedPoseState))", "false)"),
        ("if ((flags & OutRunVR::HostShouldRender) == 0)", "if (false)"),
        ("if (!hostPid ||", "if (false ||"),
    )
    for original, damaged in mutations:
        assert original in source, original
        try:
            verify(source.replace(original, damaged, 1))
        except (AssertionError, ValueError):
            continue
        raise AssertionError("R21 destructive mutation survived: " + original)
    print(f"PASS R21 host clock/coherent-seqlock/soft/fail-closed: 8 scenarios, {len(mutations)} negative mutations")

if __name__ == "__main__":
    main()
