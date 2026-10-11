#!/usr/bin/env python3
"""DX9Ex R23 production capture: reject recurring DXGI metadata/heap hot-path work.

Desktop dirty/move rectangles are output-global and advisory. R35.3 already
correlates an actual completed game Present via LastPresentTime + Frame.v2.
This guard prevents a reintroduction of the per-XR-frame metadata round trips
without disabling capture, source ownership or stereo correlation.
"""
from pathlib import Path

source = (Path(__file__).resolve().parents[1] / "vrhost/src/main_r23.cpp").read_text(encoding="utf-8")


def require_order(block: str, tokens: tuple[str, ...]) -> None:
    offsets = [block.find(token) for token in tokens]
    if any(offset < 0 for offset in offsets) or offsets != sorted(offsets):
        raise ValueError(f"missing/reordered producer path: {tokens}")


def verify(text: str) -> None:
    start = text.find("CaptureStatus R23Capture(")
    end = text.find("CaptureStatus R23RefreshTheaterFallbackCapture(", start)
    if start < 0 or end < 0:
        raise ValueError("R23 production capture entrypoint missing")
    capture = text[start:end]
    for banned in ("GetFrameDirtyRects(", "GetFrameMoveRects(",
                   "std::vector<RECT>", "std::vector<DXGI_OUTDUPL_MOVE_RECT>"):
        if banned in capture:
            raise ValueError(f"DXGI metadata/heap work on capture hot path: {banned}")
    # An unchanged pointer-only DXGI event now exits after releasing the
    # acquired frame, before QueryInterface/CopyResource. Validate the real
    # pixel-copy branch independently, without mistaking that earlier release
    # for the mandatory release after CopyResource.
    acquire_at = capture.find(
        "c.duplication_->AcquireNextFrame(waitMs, &fi, &resource)")
    query_at = capture.find("resource->QueryInterface(")
    if acquire_at < 0 or query_at <= acquire_at:
        raise ValueError("DXGI acquire must precede pixel resource query")
    require_order(capture[query_at:], (
        "resource->QueryInterface(",
        "c.context_->CopyResource(c.source_, texture)",
        "c.duplication_->ReleaseFrame()",
        "status.fresh = fi.AccumulatedFrames > 0",
        "OutRunVrSbsCaptureOverride::PublishProductionCapture(",
        "R23Pixels.ScheduleSource(c)",
    ))
    select_at = text.find("bool R23SelectClassicFrameForCapture(")
    select_end = text.find("bool R23ValidateDirectResourceSize(", select_at)
    if select_at < 0 or select_end < 0:
        raise ValueError("classic frame ownership selection missing")
    select = text[select_at:select_end]
    for required in ("!capture.available", "!capture.fresh",
                     "!capture.fullGameClientVisible",
                     "capture.lastPresentQpc <= 0",
                     "frame.presentQpc > capture.lastPresentQpc",
                     "maxSkewTicks > 0 && skew > maxSkewTicks",
                     "R23FrameUnchanged(reader, selected)"):
        if required not in select:
            raise ValueError(f"classic correlation guard missing: {required}")
    if "capture.gameRegionChanged" in text or "desktop-update-outside-game" in text:
        raise ValueError("stale DXGI dirty metadata incorrectly gates/rejects stereo")


verify(source)
# Three material regressions must be rejected by the verifier, not merely
# leave no changes: another dirty query, a removed copy, and missing QPC skew.
mutants = (
    source.replace("        ID3D11Texture2D* texture = nullptr;",
                   "        c.duplication_->GetFrameDirtyRects(0, nullptr, nullptr);\n"
                   "        ID3D11Texture2D* texture = nullptr;", 1),
    source.replace("c.context_->CopyResource(c.source_, texture);", "", 1),
    source.replace("maxSkewTicks > 0 && skew > maxSkewTicks", "false", 1),
)
for n, mutated in enumerate(mutants):
    if mutated == source:
        raise ValueError(f"negative mutation {n} not constructed")
    try:
        verify(mutated)
    except ValueError:
        continue
    raise ValueError(f"negative mutation {n} escaped R23 metadata regression")
print("DX9Ex R23 capture metadata-free hot path PASS (3 negative mutations)")
