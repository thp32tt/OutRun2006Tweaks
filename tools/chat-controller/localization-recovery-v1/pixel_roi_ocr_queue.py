#!/usr/bin/env python3
"""Fail-closed RGBA pixel ROI discovery for ChatGPT image-attachment OCR.

No external OCR API, no fabricated English text, no DDS write, no automatic
localization promotion. Outputs compact evidence crops and a review-only queue.
Run from the verified OutRun host checkout: --execute --max-sources 8.
"""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import math
import os
import re
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

WORK = Path("/home/chatgpt-runner2/work")
SCRIPT_DIR = Path(__file__).resolve().parent
OCR_FILE = SCRIPT_DIR / "gpt_vision_chat_ocr.py"
OUTPUT = WORK / "image-src/text_roi_batches/pixel_ocr_review"
SCHEMA = "outrun.pixel_ocr_review.v1"


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False,
                                     dir=path.parent, suffix=".tmp") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        tmp = Path(stream.name)
    os.chmod(tmp, 0o644)
    os.replace(tmp, path)


def _components(binary):
    """Union of neighboring horizontal runs; much cheaper than pixel BFS."""
    height, width = binary.shape
    parent = []
    bounds = []
    prior = []
    for y in range(height):
        padded = np.empty(width+2, dtype=np.uint8)
        padded[0] = padded[-1] = 0
        padded[1:-1] = binary[y]
        dif = np.diff(padded.astype(np.int8))
        starts = np.flatnonzero(dif == 1)
        ends = np.flatnonzero(dif == -1)
        cur = []
        for lo, hi in zip(starts, ends):
            idx = len(parent)
            parent.append(idx)
            bounds.append([int(lo), y, int(hi), y+1])
            cur.append((int(lo), int(hi), idx))
        def root(a):
            while parent[a] != a:
                parent[a] = parent[parent[a]]
                a = parent[a]
            return a
        k = 0
        for lo, hi, idx in cur:
            while k < len(prior) and prior[k][1] < lo - 1:
                k += 1
            t = k
            while t < len(prior) and prior[t][0] <= hi + 1:
                other = root(prior[t][2])
                now = root(idx)
                if other != now:
                    parent[other] = now
                    b = bounds[other]
                    a = bounds[now]
                    a[0] = min(a[0], b[0])
                    a[1] = min(a[1], b[1])
                    a[2] = max(a[2], b[2])
                    a[3] = max(a[3], b[3])
                t += 1
        prior = cur
    out = []
    for i, b in enumerate(bounds):
        j = i
        while parent[j] != j:
            parent[j] = parent[parent[j]]
            j = parent[j]
        if i == j:
            out.append(b)
    return out


def segment(image, known, factor=4, max_proposals=40):
    width, height = image.size
    alpha = np.asarray(image.getchannel("A"), dtype=np.uint8)
    pad_h = (-height) % factor
    pad_w = (-width) % factor
    if pad_h or pad_w:
        alpha = np.pad(alpha, ((0, pad_h), (0, pad_w)), constant_values=0)
    low = alpha.reshape(alpha.shape[0]//factor, factor,
                        alpha.shape[1]//factor, factor).max(axis=(1, 3))
    mask = low >= 24
    # Known ROI must be from an identical original PNG SHA. Mask only the
    # interior, retaining a narrow edge for unknown adjacent glyphs.
    for _, rect in known:
        x0, y0, x1, y1 = map(int, rect)
        x0, y0 = max(0, x0//factor+1), max(0, y0//factor+1)
        x1, y1 = min(mask.shape[1], (x1+factor-1)//factor-1), min(mask.shape[0], (y1+factor-1)//factor-1)
        if x1 > x0 and y1 > y0:
            mask[y0:y1, x0:x1] = False
    # Join adjacent glyph components while leaving disjoint strings apart.
    # This is proposal generation only, never a proof of any English phrase.
    blurred = Image.fromarray((mask.astype("uint8")*255), "L").filter(
        ImageFilter.MaxFilter(7))
    comps = _components(np.asarray(blurred, dtype=np.uint8) > 0)
    proposals = []
    for cx0, cy0, cx1, cy1 in comps:
        box = [max(0, cx0*factor-6), max(0, cy0*factor-6),
               min(width, cx1*factor+6), min(height, cy1*factor+6)]
        w, h = box[2]-box[0], box[3]-box[1]
        if w < 24 or h < 12 or w > width*.80 or h > height*.45:
            continue
        # Remove residual edges created by the conservative ROI mask.
        inside = 0
        for _, v in known:
            xx0 = max(box[0], v[0]); yy0 = max(box[1], v[1])
            xx1 = min(box[2], v[2]); yy1 = min(box[3], v[3])
            inside += max(0, xx1-xx0)*max(0, yy1-yy0)
        covered = min(1.0, inside / max(1, w*h))
        if covered >= .55:
            continue
        visible = int((alpha[box[1]:box[3], box[0]:box[2]] >= 24).sum())
        if visible < 40:
            continue
        art_risk = w >= width*.25 or h >= height*.20 or w/h < .35
        proposals.append({"bbox_xyxy": box,
                          "alpha_pixels": visible,
                          "registered_box_overlap_fraction": round(covered, 3),
                          "art_or_merged_risk": bool(art_risk),
                          "status": "PENDING_VISUAL_OCR_NOT_APPROVED"})
    proposals.sort(key=lambda v: (v["art_or_merged_risk"], v["bbox_xyxy"][1], v["bbox_xyxy"][0]))
    return proposals[:max_proposals], len(comps)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--execute", action="store_true",
                    help="Store verified contact sheet and individual review PNGs.")
    ap.add_argument("--max-sources", type=int, default=8)
    ap.add_argument("--max-proposals", type=int, default=24)
    ap.add_argument("--only", action="append", help="Exact source PNG filename.")
    args = ap.parse_args(argv)
    if not (1 <= args.max_sources <= 108 and 1 <= args.max_proposals <= 40):
        raise SystemExit("BOUNDED_INPUT_REQUIRED")
    spec = importlib.util.spec_from_file_location("gpt_vision_chat_ocr", OCR_FILE)
    g = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(g)
    g.PRODUCTION_MANIFEST = WORK / "image-src/text_roi_batches/production_manifest.json"
    rows = g._manifest_rows()
    outstanding = g._exhausted_candidates()
    if args.only:
        selected = [(row, phrases) for row, phrases in outstanding
                    if row["png_filename"] in args.only]
        if set(args.only) != {row["png_filename"] for row, _ in selected}:
            raise SystemExit("SOURCE_NOT_IN_UNRESOLVED_MANIFEST")
    else:
        selected = sorted(outstanding, key=lambda z: (len(z[1]), z[0]["png_filename"]),
                          reverse=True)
    selected = selected[:args.max_sources]
    batch = []
    for row, phrases in selected:
        name = row["png_filename"]
        source = g.SRC / name
        if (not source.is_file() or source.is_symlink()
                or source.stat().st_size != int(row["png_size_bytes"])
                or sha(source) != row["png_sha256"]):
            raise RuntimeError("SOURCE_SHA_FAILED:" + name)
        with Image.open(source) as img:
            if img.format != "PNG" or img.mode != "RGBA" or img.size != (
                    int(row["width"]), int(row["height"])):
                raise RuntimeError("SOURCE_IMAGE_TYPE_OR_SIZE_INVALID:" + name)
            im = img.copy()
        known = g._known_ocr_regions(name, row["png_sha256"])
        boxes, component_count = segment(im, known, max_proposals=args.max_proposals)
        for idx, p in enumerate(boxes):
            rect = p["bbox_xyxy"]
            p["id"] = hashlib.sha256((row["png_sha256"] + "|" + json.dumps(rect)).encode()).hexdigest()[:16]
            p["display_name"] = f'{Path(name).stem}_{idx:02d}_{p["id"]}.png'
            if args.execute:
                dst = OUTPUT / "crops" / p["display_name"]
                dst.parent.mkdir(parents=True, exist_ok=True)
                if not dst.exists():
                    im.crop(tuple(rect)).save(dst)
                p["crop_sha256"] = sha(dst)
                p["crop_path"] = str(dst)
        batch.append({"source_png": name, "source_png_sha256": row["png_sha256"],
                      "source_dimensions": list(im.size),
                      "target_unresolved_phrases": phrases,
                      "known_registered_box_count": len(known),
                      "raw_component_count": component_count,
                      "proposal_count": len(boxes), "proposals": boxes})
    output = {
        "schema": SCHEMA, "created_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "execution": "WRITE_CROPS" if args.execute else "DRY_RUN",
        "external_api_used": False, "originals_modified": False,
        "production_manifest_modified": False, "ocr_state_modified": False,
        "automatically_approved_roi": 0,
        "verification": "source SHA and original manifest verified; proposals require human/chat vision",
        "sources": batch}
    if args.execute:
        # Stable per-batch manifest, preserve prior runs and source images.
        atomic_json(OUTPUT/"latest.json", output)
        # Create a readable contact page for independent ChatGPT visual review
        # from the source-cropped snippets, not generated image pixels.
        tiles = []
        for entry in batch:
            for p in entry["proposals"][:8]:
                box = p["bbox_xyxy"]
                path = Path(p["crop_path"])
                with Image.open(path) as im:
                    crop = im.convert("RGBA")
                    crop.thumbnail((480, 170), Image.Resampling.LANCZOS)
                    bg = Image.new("RGB", (500, 218), "#20242a")
                    backing = Image.new("RGBA", crop.size, "#353a40")
                    backing.alpha_composite(crop)
                    bg.paste(backing.convert("RGB"), ((500-crop.width)//2, 35))
                draw = ImageDraw.Draw(bg)
                draw.text((8, 5), entry["source_png"][:42], fill="white")
                draw.text((8, 194), str(box) + (" ART?" if p["art_or_merged_risk"] else " REVIEW"),
                          fill="#e0e0e0")
                tiles.append(bg)
        if tiles:
            sheet = Image.new("RGB", (1000, math.ceil(len(tiles)/2)*218), "#181a1c")
            for i, tile in enumerate(tiles):
                sheet.paste(tile, ((i % 2)*500, (i // 2)*218))
            sheet.save(OUTPUT/"contact_sheet.png")
    print(json.dumps({"status": "EXTRACTED_REVIEW_ONLY",
                      "saved": bool(args.execute),
                      "manifest": str(OUTPUT/"latest.json") if args.execute else None,
                      "contact_sheet": str(OUTPUT/"contact_sheet.png") if args.execute else None,
                      "source_count": len(batch),
                      "candidate_regions": sum(len(z["proposals"]) for z in batch),
                      "candidate_risky": sum(v["art_or_merged_risk"] for z in batch for v in z["proposals"]),
                      "per_source": [{"source": z["source_png"], "phrases": len(z["target_unresolved_phrases"]),
                                      "proposals": z["proposal_count"],
                                      "risky": sum(v["art_or_merged_risk"] for v in z["proposals"])}
                                     for z in batch],
                      "auto_approved": 0}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
