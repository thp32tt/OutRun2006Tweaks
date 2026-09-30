#!/usr/bin/env python3
"""Fail-closed source audit for C075FB49 RANDOM protected-art separation.

This does not generate a Korean DDS. It proves whether the exact English HD
source permits a simple dilation-based source-text removal mask without touching
the unique RANDOM panel artwork. The audit is intentionally source-only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageFilter

SOURCE_SHA256 = "a8942f076b9c3d8cddd62ba39c84a3b3abea72b2ba19a61a21e9a2bd6f8e8036"
RANDOM_CELL = (1710, 1410, 2008, 1515)  # half-open readable coordinates
TEXT_FILL_RGBA = (245, 247, 247, 255)
PROTECTED_LIGHT_BLUE_RGBA = (103, 152, 220, 255)
DILATION_RADII = (1, 2, 3, 4, 5, 8, 12)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def exact_mask(image: Image.Image, rgba: tuple[int, int, int, int]) -> Image.Image:
    out = Image.new("L", image.size, 0)
    src = image.load()
    dst = out.load()
    for y in range(image.height):
        for x in range(image.width):
            if src[x, y] == rgba:
                dst[x, y] = 255
    return out


def count(mask: Image.Image) -> int:
    return sum(mask.histogram()[1:])


def bbox_half_open(mask: Image.Image):
    bbox = mask.getbbox()
    return None if bbox is None else list(map(int, bbox))


def overlap_count(a: Image.Image, b: Image.Image) -> int:
    aa = a.load()
    bb = b.load()
    total = 0
    for y in range(a.height):
        for x in range(a.width):
            if aa[x, y] and bb[x, y]:
                total += 1
    return total


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_dds")
    parser.add_argument("--out")
    args = parser.parse_args()

    source = Path(args.source_dds)
    digest = sha256(source)
    if digest != SOURCE_SHA256:
        raise SystemExit(f"FAIL source sha256 {digest} != {SOURCE_SHA256}")

    raw = Image.open(source).convert("RGBA")
    if raw.size != (2048, 2048):
        raise SystemExit(f"FAIL source size {raw.size}")
    readable = raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    random_cell = readable.crop(RANDOM_CELL)

    text_fill = exact_mask(random_cell, TEXT_FILL_RGBA)
    protected = exact_mask(random_cell, PROTECTED_LIGHT_BLUE_RGBA)
    if count(text_fill) != 3027 or count(protected) != 1328:
        raise SystemExit("FAIL exact source palette fingerprint changed")

    proximity = {}
    for radius in DILATION_RADII:
        dilated = text_fill.filter(ImageFilter.MaxFilter(radius * 2 + 1))
        proximity[str(radius)] = overlap_count(dilated, protected)

    report = {
        "schema": "outrun-a00276-c075-random-protected-art-audit-v1",
        "source_sha256": digest,
        "canvas": [2048, 2048],
        "readable_transform": "flip_y",
        "random": {
            "cell_half_open": list(RANDOM_CELL),
            "source_text_fill_rgba": list(TEXT_FILL_RGBA),
            "source_text_fill_pixels": count(text_fill),
            "source_text_fill_bbox_local_half_open": bbox_half_open(text_fill),
            "protected_light_blue_rgba": list(PROTECTED_LIGHT_BLUE_RGBA),
            "protected_light_blue_pixels": count(protected),
            "protected_light_blue_bbox_local_half_open": bbox_half_open(protected),
            "dilation_metric": "square/Chebyshev neighborhood",
            "text_fill_dilation_intersection_with_protected_pixels": proximity,
            "one_pixel_separation_safe": proximity["1"] == 0,
            "disposition": (
                "SOURCE_ONLY_SIMPLE_MASK_RECONSTRUCTION_REJECTED"
                if proximity["1"] else "SOURCE_ONLY_SIMPLE_MASK_RECONSTRUCTION_POSSIBLE"
            ),
        },
        "interpretation": (
            "The exact RANDOM source text and unique panel artwork are not separated by a one-pixel guard. "
            "Any simple dilation-based English removal mask would consume protected artwork; use an explicit "
            "protected-art reconstruction/model or a verified current-candidate-preserving merge and fail closed otherwise."
        ),
    }

    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        Path(args.out).write_text(payload, encoding="utf-8")
    print(payload, end="")


if __name__ == "__main__":
    main()
