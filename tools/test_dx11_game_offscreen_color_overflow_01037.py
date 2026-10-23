#!/usr/bin/env python3
from pathlib import Path
root=Path(__file__).resolve().parents[1]
cpp=(root/"src/vr/d3d11/native_game_stereo_submission.cpp").read_text()
hdr=(root/"src/vr/d3d11/native_game_stereo_submission.hpp").read_text()
src=(root/"src/vr/d3d11/native_game_offscreen_color_provenance.hpp").read_text()
assert "NativeGameOffscreenColorProvenanceState offscreenColorProvenance_" in hdr
assert cpp.count("offscreenColorProvenance_.note_untracked_gpu_write();")==3
assert cpp.count("offscreenColorProvenance_.allows_postpass(")==2
assert "transferred != extraCount" in cpp
assert "return !untrackedGpuWrite &&" in src
print("01037 actual game camera GPU COPY/STRETCH overflow rejection PASS")

# A successful queued game Draw with unprovable viewport/scissor/RTV pixels
# must quarantine COPY/STRETCH attribution, not masquerade as untouched.
capture=cpp.split("void NativeGameEyeDrawEncoder::remember_offscreen_color_source(",1)[1].split("// Keep the exact per-camera GPU-written color union",1)[0]
assert "offscreenColorProvenance_.note_untracked_gpu_write();" in capture
assert capture.count("reject_unknown_footprint();")==5
for condition in ("!allocation || FAILED(allocation.As(&texture)) || !texture",
                  "!view.valid", "viewportCount != 1u",
                  "scissorCount != 1u",
                  "!native_game_offscreen_color_region_valid(region)"):
    assert condition in capture, condition
# Mutation-check each individual early return. A silent return after a
# previously queued eligible Draw would otherwise appear to be untouched.
for condition in ("!allocation || FAILED(allocation.As(&texture)) || !texture",
                  "!view.valid", "viewportCount != 1u",
                  "scissorCount != 1u",
                  "!native_game_offscreen_color_region_valid(region)"):
    prefix="if (" + condition + ")"
    assert prefix in capture, condition
    body=capture.split(prefix,1)[1].split("}",1)[0]
    assert "reject_unknown_footprint();" in body, condition
    bad=capture.replace(prefix + body, prefix + body.replace(
        "reject_unknown_footprint();", "/* unsafe omission */",1), 1)
    assert "reject_unknown_footprint();" not in bad.split(prefix,1)[1].split("}",1)[0]
print("01037 queued GPU camera Draw uncertain-raster fail-closed guards PASS")
