#!/usr/bin/env python3
"""R23 DirectGPU ring hot-path selection and seqlock contract tests.

Synthetic comparisons count full slot snapshots, not physical FPS. Windows
GitHub Actions additionally compiles the material host change.
"""
from pathlib import Path

SOURCE = (Path(__file__).resolve().parents[1] /
          "vrhost/src/runtime/d3d9ex_direct_passthrough.hpp")


def body(source):
    start = source.index("inline bool ReadFrameById(")
    return source[start:source.index("inline bool IncomingProjectionValid(", start)]


def verify(source):
    code = body(source)
    ordered = (
        "const std::uint32_t ringBefore = FrameRing->publishSequence;",
        "if (ringBefore & 1u)",
        "const std::uint32_t before = slot.sequence;",
        "if (before & 1u)",
        "const std::uint32_t probedFrameId = slot.frameId;",
        "const std::uint32_t probeAfter = slot.sequence;",
        "if (before != probeAfter || (probeAfter & 1u))",
        "if (probedFrameId != frameId)",
        "OutRunVR::SharedRenderFrameState candidate{};",
        "std::memcpy(&candidate, &slot, sizeof(candidate));",
        "const std::uint32_t after = slot.sequence;",
        "if (before == after && !(after & 1u) &&",
        "candidate.magic == OutRunVR::RenderFrameMagic",
        "candidate.protocolVersion == OutRunVR::RenderFrameProtocolVersion",
        "candidate.structSize == sizeof(candidate)",
        "OutRunVR::RenderFrameRunIdentityMatches(*FrameRing, candidate)",
        "candidate.frameId == frameId",
        "candidate.state == OutRunVR::StereoSbsActive",
        "(candidate.flags & OutRunVR::RenderFrameDirectGpuTransport) != 0",
        "(candidate.flags & OutRunVR::RenderFramePresentInFlight) == 0",
        "const std::uint32_t ringAfter = FrameRing->publishSequence;",
        "if (found && ringBefore == ringAfter && !(ringAfter & 1u))",
    )
    positions = [code.index(token) for token in ordered]
    assert positions == sorted(positions), "seqlock ordering changed"
    assert code.count("MemoryBarrier();") == 5
    assert "if (probedFrameId != frameId)\n                        break;" in code
    assert "if (found && ringBefore == ringAfter && !(ringAfter & 1u))" in code


def synthetic_probe(slots, wanted):
    """Each slot = (seq before, id, seq after, valid full snapshot)."""
    copies = 0
    for before, frame, after, valid in slots:
        if before & 1 or before != after or after & 1:
            continue
        if frame != wanted:
            continue
        copies += 1
        if valid:
            return True, copies
    return False, copies


def test_model():
    assert synthetic_probe([(2, 1, 2, True), (4, 2, 4, True),
                            (6, 3, 6, True), (8, 4, 8, True)], 9) == (False, 0)
    assert synthetic_probe([(2, 1, 2, True), (4, 2, 4, True),
                            (6, 9, 6, True), (8, 4, 8, True)], 9) == (True, 1)
    assert synthetic_probe([(2, 9, 4, True), (5, 9, 5, True),
                            (6, 9, 6, False), (8, 9, 8, True)], 9) == (True, 2)
    assert synthetic_probe([(2, 9, 2, False)], 9) == (False, 1)
    copies = 0
    for wanted in range(1, 513):
        slots = [(2*(i+1), wanted + i - (wanted % 4),
                  2*(i+1), True) for i in range(4)]
        ok, n = synthetic_probe(slots, wanted)
        assert ok
        copies += n
    assert copies == 512


if __name__ == "__main__":
    source = SOURCE.read_text(encoding="utf-8")
    verify(source)
    mutations = (
        ("const std::uint32_t probedFrameId = slot.frameId;",
         "const std::uint32_t probedFrameId = frameId;"),
        ("const std::uint32_t probeAfter = slot.sequence;",
         "const std::uint32_t probeAfter = before;"),
        ("if (before != probeAfter || (probeAfter & 1u))", "if (false)"),
        ("if (probedFrameId != frameId)", "if (false)"),
        ("if (probedFrameId != frameId)\n                        break;",
         "if (probedFrameId != frameId)\n                        continue;"),
        ("std::memcpy(&candidate, &slot, sizeof(candidate));", "/* no copy */"),
        ("const std::uint32_t after = slot.sequence;",
         "const std::uint32_t after = before;"),
        ("if (before == after && !(after & 1u) &&", "if (before == after &&"),
        ("candidate.frameId == frameId", "true /* no frame id check */"),
        ("candidate.state == OutRunVR::StereoSbsActive",
         "candidate.state != OutRunVR::StereoSbsActive"),
        ("if (found && ringBefore == ringAfter && !(ringAfter & 1u))",
         "if (found)"),
    )
    for good, bad in mutations:
        assert good in body(source), good
        try:
            verify(source.replace(good, bad, 1))
        except (AssertionError, ValueError):
            continue
        raise AssertionError("mutation survived: " + good)
    test_model()
    print("PASS R23 direct ring prefilter: 512 synthetic hits + "
          f"{len(mutations)} destructive mutations")
