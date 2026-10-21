#!/usr/bin/env python3
"""Ensure native camera Copy/Stretch provenance uses full GPU pixel coverage."""
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
    return all(token in method for token in [
        "native_game_offscreen_color_key_matches(",
        "record.arraySlice, record.mipSlice",
        "native_game_offscreen_color_region_fully_covered(",
        "matching[matchingCount++] = record.region",
    ]) and "native_game_offscreen_color_regions_intersect(record.region, copied)" not in method and all(
        token in header for token in [
            "native_game_offscreen_color_region_fully_covered(",
            "r.left <= x && r.right >= next",
            "r.top <= y && r.bottom > furthest",
            "if (furthest == y) return false",
        ]
    )

assert connected(SRC, H), "GPU camera copy still certifies partial/foreign color"
assert not connected(SRC.replace(
    "native_game_offscreen_color_region_fully_covered(\n        copied, matching, matchingCount)",
    "native_game_offscreen_color_regions_intersect(record.region, copied)", 1
), H), "overlap-only provenance must fail closed"
assert not connected(SRC.replace(
    "matching[matchingCount++] = record.region",
    "matching[matchingCount++] = copied", 1
), H), "fabricated full-copy coverage must fail closed"
assert not connected(SRC, H.replace(
    "if (furthest == y) return false", "if (furthest != y) return false"
)), "gap detection must remain enforced"
print("DX11 00981 full camera copy-region provenance: PASS")
