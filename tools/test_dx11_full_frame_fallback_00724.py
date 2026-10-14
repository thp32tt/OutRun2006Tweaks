#!/usr/bin/env python3
"""Exact live full-frame fallback wiring; no game/HMD result is inferred."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CPP = ROOT / "src/vr/d3d11/live_game_frame_bridge.cpp"
HDR = ROOT / "src/vr/d3d11/native_game_readback_provenance.hpp"


def proves_current_frame_quarantine(source: str, header: str) -> bool:
    start = source.find("void before_game_present(")
    end = source.find("void before_game_reset()", start)
    if start < 0 or end <= start:
        return False
    p = source[start:end]
    call = p.find("GameReadbackProvenance::quarantine_full_frame(")
    invalidate = p.find("if (++s.outputGeneration == 0u) ++s.outputGeneration;", call)
    getdata = p.find("ctx->GetData(")
    mapping = p.find("ctx->Map(")
    return (
        "s.frameBatch.publishable_full(s.pending, s.sourceDrawsThisFrame)" in p
        and ("s.frameBatch.publishable_full(s.pending, s.sourceDrawsThisFrame) &&\n"
             "            s.sourceGameDevice == presentDevice;") in p
        and "fullMode, currentFullFrameComplete, outputWritable" in p
        and 0 <= call < invalidate < getdata < mapping
        and "oldest.provenance.same_output(s.outputGeneration)" in p
        and "? currentFullFrameComplete" in p
        and "fullMode && (!currentFullFrameComplete || !outputWritable)" in header
    )


def main() -> None:
    src = CPP.read_text(encoding="utf-8")
    hdr = HDR.read_text(encoding="utf-8")
    assert proves_current_frame_quarantine(src, hdr)
    for old, new in (
        ("s.sourceGameDevice == presentDevice", "s.sourceGameDevice != presentDevice"),
        ("fullMode, currentFullFrameComplete, outputWritable",
         "false, currentFullFrameComplete, outputWritable"),
        ("if (++s.outputGeneration == 0u) ++s.outputGeneration;",
         "/* incomplete full frames keep old output generation */"),
    ):
        p = src.index("void before_game_present(")
        e = src.index("void before_game_reset()", p)
        before, body, after = src[:p], src[p:e], src[e:]
        call = body.index("GameReadbackProvenance::quarantine_full_frame(")
        if old.startswith("if (++s.outputGeneration"):
            assert old in body[call:]
            body = body[:call] + body[call:].replace(old, new, 1)
        else:
            assert old in body
            body = body.replace(old, new, 1)
        assert not proves_current_frame_quarantine(before + body + after, hdr)
    assert not proves_current_frame_quarantine(
        src, hdr.replace("fullMode && (!currentFullFrameComplete || !outputWritable)",
                         "fullMode && currentFullFrameComplete && outputWritable"))
    print("DX11 00724 full-frame missed-draw/readback quarantine source regressions PASS")


if __name__ == "__main__":
    main()
