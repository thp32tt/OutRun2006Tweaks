#!/usr/bin/env python3
"""Pixel-exact English phrase crops ONLY from SHA-pinned original HD full PNGs.

No ImageGen, upscaling, alpha extraction, masking, clean plates, translation,
DDS composition, legacy tiles, A/B queue/state or auto scheduling.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from PIL import Image

SCHEMA = "outrun-c-n100-hd-original-crop-v1"
BANNED = ("tile", "reassembled", "generated", "korean", "_kor", "translated", "input_upscaled")

def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def leaf(name: str) -> str:
    if not isinstance(name, str) or not name or Path(name).name != name or name in (".", ".."):
        raise ValueError("UNSAFE_FILENAME")
    return name

def run(spec_path: Path, source_root: Path, output_root: Path) -> dict:
    cfg = json.loads(spec_path.read_text(encoding="utf-8"))
    if cfg.get("schema") != SCHEMA or not isinstance(cfg.get("regions"), list):
        raise ValueError("INVALID_SCHEMA")
    if cfg.get("source_kind") not in ("N100_PINNED_FULL_ORIGINAL_HD_PNG", "N100_DDS_VERIFIED_READABLE_FULL_HD_PNG"):
        raise ValueError("FULL_HD_ORIGINAL_REQUIRED")
    name = leaf(cfg["source_png"])
    if any(x in name.lower() for x in BANNED):
        raise ValueError("NOT_A_FULL_ORIGINAL_HD_SOURCE")
    srcroot, outroot = source_root.resolve(), output_root.resolve()
    if srcroot == outroot or srcroot in outroot.parents or outroot in srcroot.parents:
        raise ValueError("SOURCE_OUTPUT_ROOTS_MUST_BE_SEPARATE")
    source = source_root / name
    data = source.read_bytes()
    if digest(data) != cfg.get("source_sha256"):
        raise ValueError("ORIGINAL_PNG_SHA_MISMATCH")
    with Image.open(source) as im:
        if im.format != "PNG" or im.mode not in ("RGB", "RGBA"):
            raise ValueError("EXPECTED_NATIVE_HD_PNG")
        if im.size != tuple(cfg.get("source_dimensions", ())):
            raise ValueError("SOURCE_DIMENSIONS_MISMATCH")
        if not (128 <= im.width <= 8192 and 32 <= im.height <= 8192):
            raise ValueError("UNEXPECTED_SOURCE_SIZE")
        full = im.copy()
    result = {"schema": SCHEMA, "mode": "C_CROP_ONLY", "ready": [], "hold": [], "A_B_STATE": "UNCHANGED"}
    seen = set()
    for region in cfg["regions"]:
        identity = cfg["queue_id"] + "-" + leaf(region["id"])
        try:
            if identity in seen:
                raise ValueError("DUPLICATE_ID")
            seen.add(identity)
            xyxy = region["bbox_xyxy"]
            if not isinstance(xyxy, list) or len(xyxy) != 4 or any(type(i) is not int for i in xyxy):
                raise ValueError("INVALID_XYXY")
            x0,y0,x1,y1 = xyxy
            if not (0 <= x0 < x1 <= full.width and 0 <= y0 < y1 <= full.height):
                raise ValueError("XYXY_OUTSIDE_FULL_HD")
            text = region.get("english", "").strip()
            if not text:
                raise ValueError("MISSING_EXACT_ENGLISH")
            output = output_root / identity
            if output.exists():
                raise ValueError("OUTPUT_EXISTS_SKIP_DUPLICATE")
            output.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(dir=output.parent, prefix=".crop-only-") as t:
                tmp = Path(t)
                roi = full.crop((x0,y0,x1,y1))
                png = tmp / "english_original_native_crop.png"
                roi.save(png, format="PNG")
                with Image.open(png) as verify:
                    if verify.mode != full.mode or verify.size != roi.size or verify.tobytes() != roi.tobytes():
                        raise ValueError("CROP_PIXEL_VERIFICATION_FAIL")
                receipt = {
                    "schema": SCHEMA, "queue_id": cfg["queue_id"], "region_id": region["id"],
                    "english": text, "source_kind": cfg["source_kind"],
                    "source_full_png": name, "source_full_png_sha256": cfg["source_sha256"],
                    "source_dds_path": cfg.get("source_dds_path", ""),
                    "source_dds_sha256": cfg.get("source_dds_sha256", ""),
                    "original_dimensions": list(full.size),
                    "native_xyxy": xyxy, "crop_dimensions": list(roi.size),
                    "crop_png_sha256": digest(png.read_bytes()),
                    "pixel_exact": True,
                    "isolation": "UNMODIFIED_SOURCE_PIXELS_NOT_GLYPH_ISOLATION",
                    "edge_clearance": "PENDING_VISUAL_REVIEW",
                    "status": "CROP_TEST_ONLY_REVIEW_REQUIRED",
                    "imagegen": "NOT_RUN", "upscale": "NOT_RUN",
                    "clean_plate": "NOT_RUN", "Korean_composite": "NOT_RUN",
                    "A_B_QUEUE": "NOT_TOUCHED", "C1": "NOT_RUN",
                    "C3": "NOT_RUN", "RUNTIME_VALIDATION": "UNTESTED"
                }
                (tmp / "crop_manifest.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
                os.rename(tmp, output)
            result["ready"].append({"id":identity,"path":str(output),"sha256":receipt["crop_png_sha256"]})
        except (OSError, ValueError, TypeError, KeyError) as e:
            result["hold"].append({"id":identity,"reason":str(e)})
    return result

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", required=True, type=Path)
    ap.add_argument("--source-root", required=True, type=Path)
    ap.add_argument("--output-root", required=True, type=Path)
    a = ap.parse_args()
    print(json.dumps(run(a.spec, a.source_root, a.output_root), ensure_ascii=False))

if __name__ == "__main__":
    main()
