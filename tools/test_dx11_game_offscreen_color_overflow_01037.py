#!/usr/bin/env python3
from pathlib import Path
root=Path(__file__).resolve().parents[1]
cpp=(root/"src/vr/d3d11/native_game_stereo_submission.cpp").read_text()
hdr=(root/"src/vr/d3d11/native_game_stereo_submission.hpp").read_text()
src=(root/"src/vr/d3d11/native_game_offscreen_color_provenance.hpp").read_text()
assert "NativeGameOffscreenColorProvenanceState offscreenColorProvenance_" in hdr
assert cpp.count("offscreenColorProvenance_.note_untracked_gpu_write();")==2
assert cpp.count("offscreenColorProvenance_.allows_postpass(")==2
assert "transferred != extraCount" in cpp
assert "return !untrackedGpuWrite &&" in src
print("01037 actual game camera GPU COPY/STRETCH overflow rejection PASS")
