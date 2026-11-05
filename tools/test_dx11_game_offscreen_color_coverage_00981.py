#!/usr/bin/env python3
"""Ensure native camera COPY/STRETCH uses keyed, complete GPU pixel coverage."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
SRC = (ROOT / "src/vr/d3d11/native_game_stereo_submission.cpp").read_text()
H = (ROOT / "src/vr/d3d11/native_game_offscreen_color_provenance.hpp").read_text()

def connected(source: str, header: str) -> bool:
    if "bool NativeGameEyeDrawEncoder::offscreen_color_source_proven(" not in source:
        return False
    method = source.split(
        "bool NativeGameEyeDrawEncoder::offscreen_color_source_proven(", 1
    )[1].split("bool NativeGameEyeDrawEncoder::color_writable_for_samples(", 1)[0]
    if "native_game_gpu_eye_composite_source_proven(" not in header:
        return False
    helper = header.split("native_game_gpu_eye_composite_source_proven(", 1)[1].split(
        "// When many authentic game camera Draw/Clear tiles", 1
    )[0]
    return all(token in method for token in [
        "record.arraySlice, record.mipSlice",
        "regions[count++] = record.region",
        "native_game_gpu_eye_composite_source_proven(",
        "key, copied, keys, regions, count",
    ]) and all(token in helper for token in [
        "native_game_offscreen_color_key_matches(sampledKey, keys[i])",
        "matching[matchingCount++] = regions[i]",
        "native_game_offscreen_color_region_fully_covered(",
        "sampled, matching, matchingCount",
    ]) and all(token in header for token in [
        "r.left <= x && r.right >= next",
        "r.top <= y && r.bottom > furthest",
        "if (furthest == y) return false",
    ]) and "native_game_offscreen_color_regions_intersect(record.region, copied)" not in method

assert connected(SRC, H), "GPU camera copy still certifies partial/foreign color"
# Preserve negative mutation coverage after the proof moved to the keyed
# helper: fabricated input, foreign key bypass, overlap-only, and absent
# raster-gap rejection must all disconnect the real renderer source chain.
assert not connected(SRC.replace(
    "regions[count++] = record.region", "regions[count++] = copied", 1
), H), "fabricated full-copy coverage must fail closed"
assert not connected(SRC, H.replace(
    "matching[matchingCount++] = regions[i]", "matching[matchingCount++] = sampled", 1
)), "fabricated helper coverage must fail closed"
assert not connected(SRC, H.replace(
    "native_game_offscreen_color_key_matches(sampledKey, keys[i])",
    "sampledKey.resource != 0u", 1
)), "foreign mip/array eye key must fail closed"
assert not connected(SRC, H.replace(
    "native_game_offscreen_color_region_fully_covered(\n        sampled, matching, matchingCount)",
    "native_game_offscreen_color_regions_intersect(sampled, matching[0])", 1
)), "overlap-only provenance must fail closed"
assert not connected(SRC, H.replace(
    "if (furthest == y) return false", "if (furthest != y) return false"
)), "gap detection must remain enforced"
print("DX11 00981 keyed full camera copy-region provenance: PASS")
