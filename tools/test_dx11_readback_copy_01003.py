#!/usr/bin/env python3
"""Destructive source regression for real native GPU staging copy ownership."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]
src=(root/"src/vr/d3d11/live_game_frame_bridge.cpp").read_text(encoding="utf-8")
hdr=(root/"src/vr/d3d11/native_game_frame_publication.hpp").read_text(encoding="utf-8")
def integrated(s,h):
    return ("struct GameNativeReadbackCopyStamp" in h
        and "GameNativeReadbackCopyStamp copyStamp{};" in s
        and s.count("next.copyStamp = GameNativeReadbackCopyStamp::capture(")==2
        and s.count("item.copyStamp = {};")==2
        and "prior.copyStamp.width, staleMap.RowPitch" in s
        and "!prior.copyStamp.map_pitch_valid(staleMap.RowPitch)" in s
        and "!oldest.copyStamp.matches(" in s
        and s.count("oldest.copyStamp.width, mapped.RowPitch")==2
        and "oldest.copyStamp.map_pitch_valid(mapped.RowPitch)" in s)
assert integrated(src,hdr)
for x in (
    src.replace("prior.copyStamp.width, staleMap.RowPitch","s.nativeWidth, staleMap.RowPitch",1),
    src.replace("next.copyStamp = GameNativeReadbackCopyStamp::capture(","REMOVED copy(",1),
    src.replace("oldest.copyStamp.map_pitch_valid(mapped.RowPitch)","true",1),
    src.replace("oldest.copyStamp.width, mapped.RowPitch","surfaceWidth, mapped.RowPitch",1),
):
    assert not integrated(x,hdr), "mutation escaped"
print("PASS source-owned D3D11 GPU readback Map and live Present generation")
