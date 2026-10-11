#!/usr/bin/env python3
"""DX9Ex: guard the host DXGI pointer-only frame skip and resource ownership."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "vrhost/src/main_r23.cpp"
HEADER = ROOT / "vrhost/src/runtime/desktop_capture_reuse.hpp"


def verify(source: str, header: str) -> None:
    assert '#include "runtime/desktop_capture_reuse.hpp"' in source
    begin = source.index("CaptureStatus R23Capture(")
    end = source.index("CaptureStatus R23RefreshTheaterFallbackCapture(", begin)
    capture = source[begin:end]
    assert "const bool outputUnchanged = c.duplication_ != nullptr;" in capture
    assert "if (!c.duplication_ && !c.RecreateDuplication(false))" in capture
    key = "OutRunVrDesktopCaptureReuse::CanSkipUnchangedPointerFrame("
    assert capture.count(key) == 1
    first = capture.index("c.duplication_->AcquireNextFrame(")
    decision = capture.index(key)
    qi = capture.index("resource->QueryInterface(")
    copy = capture.index("c.context_->CopyResource(c.source_, texture);")
    assert first < decision < qi < copy

    gate = capture[decision:qi]
    for token in (
        "outputUnchanged, c.haveFrame_, c.sourceSrv_ != nullptr,",
        "fi.AccumulatedFrames, fi.LastPresentTime.QuadPart",
        "resource->Release();",
        "c.duplication_->ReleaseFrame();",
        "status.available = true;",
        "status.fresh = false;",
        "status.accumulatedFrames = 0;",
        "return status;",
    ):
        assert token in gate, f"pointer event fast path missing: {token}"
    assert gate.index("resource->Release();") < gate.index("c.duplication_->ReleaseFrame();") < gate.index("return status;")
    assert capture.count("c.duplication_->ReleaseFrame();") == 2
    assert "status.fresh = fi.AccumulatedFrames > 0;" in capture
    assert "OutRunVrSbsCaptureOverride::PublishProductionCapture(" in capture
    assert "R23Pixels.ScheduleSource(c);" in capture

    for token in (
        "outputUnchanged && haveFrame && haveSourceView",
        "accumulatedFrames == 0 && lastPresentTime == 0",
        "static_assert(CanSkipUnchangedPointerFrame(true, true, true, 0, 0));",
        "static_assert(!CanSkipUnchangedPointerFrame(false, true, true, 0, 0));",
        "static_assert(!CanSkipUnchangedPointerFrame(true, false, true, 0, 0));",
        "static_assert(!CanSkipUnchangedPointerFrame(true, true, false, 0, 0));",
        "static_assert(!CanSkipUnchangedPointerFrame(true, true, true, 1, 0));",
        "static_assert(!CanSkipUnchangedPointerFrame(true, true, true, 0, 123));",
    ):
        assert token in header, f"capture reuse policy regression: {token}"


source = SOURCE.read_text(encoding="utf-8")
header = HEADER.read_text(encoding="utf-8")
verify(source, header)
mutations = (
    (source.replace("status.fresh = false;", "status.fresh = true;", 1), header),
    (source.replace("c.sourceSrv_ != nullptr,", "true,", 1), header),
    (source.replace("resource->Release();\n            c.duplication_->ReleaseFrame();",
                    "c.duplication_->ReleaseFrame();", 1), header),
    (source.replace("status.accumulatedFrames = 0;", "status.accumulatedFrames = 1;", 1), header),
    (source, header.replace("accumulatedFrames == 0 && lastPresentTime == 0",
                            "accumulatedFrames == 0")),
    (source, header.replace("outputUnchanged && haveFrame && haveSourceView",
                            "haveFrame && haveSourceView")),
)
for i, (bad_source, bad_header) in enumerate(mutations):
    assert bad_source != source or bad_header != header, f"mutation {i} absent"
    try:
        verify(bad_source, bad_header)
    except (AssertionError, ValueError):
        continue
    raise AssertionError(f"pointer-only capture mutation {i} escaped")
print("DX9Ex R23 pointer-only GPU-copy elision PASS (6 negative mutations)")
