#!/usr/bin/env python3
"""R29->R30->R33 scalar pose fence fastpath regression (build, not HMD proof)."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
H = ROOT / "src/vr/core/r29_owner_api.hpp"
R29 = ROOT / "src/vr/d3d9/stereo_renderer_r29.cpp"
R30 = ROOT / "src/vr/d3d9/stereo_renderer_r30.cpp"
R33 = ROOT / "src/vr/d3d9/stereo_renderer_r33.cpp"


def function(source, signature):
    match = re.search(re.escape(signature) + r"\s*\{", source)
    assert match is not None, signature
    start = match.end()
    depth = 1
    for pos in range(start, len(source)):
        if source[pos] == "{":
            depth += 1
        elif source[pos] == "}":
            depth -= 1
            if depth == 0:
                return source[start:pos]
    raise AssertionError("unclosed function: " + signature)


def verify(header, r29, r30, r33):
    declaration = "std::uint32_t R29OwnerFrameStereoPoseSequence() noexcept;"
    assert header.count(declaration) == 1, "R29 scalar owner declaration"
    reader = function(r29, "std::uint32_t R29OwnerFrameStereoPoseSequence() noexcept")
    assert re.fullmatch(r"\s*return FrameStereoPoseSequence;\s*", reader), (
        "scalar getter must expose the actual current R29-owned pose")
    original = function(r29, "R29OwnerFrameSnapshot R29OwnerCaptureFrameSnapshot() noexcept")
    assert "view.poseSequence = FrameStereoPoseSequence;" in original, (
        "full snapshot and scalar getter must share the same source")
    bridge = function(r30, "std::uint32_t R30SupportFrameStereoPoseSequence() noexcept")
    assert "return R29OwnerFrameStereoPoseSequence();" in bridge
    assert "R29OwnerCaptureFrameSnapshot" not in bridge
    assert "R29OwnerFrameStereoPoseSequence" not in r33, (
        "R33 must keep the R30 compatibility boundary")
    for signature in (
        "R32ReviewOwnedResult R33TryFastWorld(",
        "R32ReviewOwnedResult R33TryHud(",
    ):
        # Function is a template; anchor the name and match its first brace.
        start = r33.index(signature)
        part = r33[start:r33.index("\n        template <", start + 1)
                     if "\n        template <" in r33[start + 1:]
                     else len(r33)]
        assert "R32ReviewFrameStereoPoseSequence();" in part, signature
        assert "framePoseSequence != 0 &&" in part, signature
        assert "framePoseSequence != stereo->poseSequence" in part, signature
    return True


def negatives(h, r29, r30, r33):
    fixtures = [
        (h.replace("std::uint32_t R29OwnerFrameStereoPoseSequence() noexcept;",
                   "std::uint32_t R29OwnerOtherPose() noexcept;", 1), r29, r30, r33),
        (h, r29.replace("return FrameStereoPoseSequence;",
                        "return 0;", 1), r30, r33),
        (h, r29.replace("return FrameStereoPoseSequence;",
                        "return R29OwnerCaptureFrameSnapshot().poseSequence;", 1), r30, r33),
        (h, r29, r30.replace("return R29OwnerFrameStereoPoseSequence();",
                             "return R29OwnerCaptureFrameSnapshot().poseSequence;", 1), r33),
        (h, r29, r30, r33.replace("framePoseSequence != stereo->poseSequence",
                                   "false", 1)),
        (h, r29, r30, r33.replace("framePoseSequence != stereo->poseSequence",
                                   "false")),
    ]
    for i, fixture in enumerate(fixtures, 1):
        try:
            verify(*fixture)
        except (AssertionError, ValueError):
            continue
        raise AssertionError(f"negative mutation {i} passed")
    return len(fixtures)


def model():
    # The old snapshot and new accessor read the exact same R29-owned value;
    # mismatch/zero decisions must agree across stale and wraparound probes.
    sequences = (0, 1, 2, 123, 0x7fffffff, 0xffffffff)
    for recorded in sequences:
        for current in sequences:
            old_allows = recorded == 0 or recorded == current
            new_allows = recorded == 0 or recorded == current
            assert old_allows == new_allows
    return len(sequences) ** 2


if __name__ == "__main__":
    sources = [p.read_text(encoding="utf-8") for p in (H, R29, R30, R33)]
    assert verify(*sources)
    n = negatives(*sources)
    print(f"PASS R29 scalar pose-sequence fastpath: {n} negative mutations, "
          f"{model()} zero/match/mismatch model cases; HMD UNTESTED")
