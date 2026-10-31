#!/usr/bin/env python3
"""Exact RGBA matching across verified console variants for unresolved text.

No OCR API or approximate fuzzy matching. Generates human-review-required
SHA-bound source manifests, then the normal bridge applies its own recheck.
No DDS, existing source PNG, generated Korean image or OCR-state modifications.
"""
from __future__ import annotations
import argparse
import collections
import functools
import hashlib
import importlib.util
import json
import os
import tempfile
from pathlib import Path
from PIL import Image

ROOT = Path("/home/chatgpt-runner2/work")
DIR = Path(__file__).resolve().parent
IMAGEGEN = ROOT / "image-src/text_roi_batches"


def atomic_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
        temp = Path(f.name)
    os.chmod(temp, 0o644)
    os.replace(temp, path)


def module(name):
    path = DIR / name
    s = importlib.util.spec_from_file_location(path.stem, path)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


def matches(g, bridge):
    g.PRODUCTION_MANIFEST = IMAGEGEN / "production_manifest.json"
    prod = json.loads(g.PRODUCTION_MANIFEST.read_text(encoding="utf-8"))
    rows = g._manifest_rows()
    by_sha = {x["png_sha256"]: x for x in rows.values()}
    source_index = collections.defaultdict(list)
    for item in prod["items"]:
        donor = by_sha.get(item.get("source_png_sha256"))
        if (donor and item.get("english") and item.get("korean")
                and item.get("status") in ("ROI_APPROVED_FOR_IMAGEGEN", "ROI_REBALANCED_TO_B")):
            source_index[(bridge.qid(donor["png_filename"]),
                          bridge.normalized(item["english"]))].append((item, donor))
    tr = bridge.translations(ROOT / "c_salvage_text_roi/source_full_20261012/transcriptions.jsonl")

    @functools.lru_cache(maxsize=4)
    def rgba(path):
        row = rows[path]
        p = g.SRC / path
        if (not p.is_file() or p.is_symlink()
                or p.stat().st_size != int(row["png_size_bytes"])
                or g._digest(p) != row["png_sha256"]):
            raise ValueError("SOURCE_SHA_MISMATCH:" + path)
        with Image.open(p) as im:
            if im.format != "PNG" or im.mode != "RGBA" or im.size != (
                    int(row["width"]), int(row["height"])):
                raise ValueError("SOURCE_FORMAT_INVALID:" + path)
            return im.copy()
    chosen = {}
    examined = 0
    for dest_row, phrases in g._exhausted_candidates():
        dest_name = dest_row["png_filename"]
        q = bridge.qid(dest_name)
        for english in phrases:
            kos = tr.get((q,bridge.normalized(english)),set())
            if len(kos) != 1:
                continue
            for donor, donor_row in source_index.get((q,bridge.normalized(english)),[]):
                donor_name = donor_row["png_filename"]
                if donor_name == dest_name or donor_row["png_sha256"] == dest_row["png_sha256"]:
                    continue
                bbox = donor.get("bbox_xyxy")
                if (not isinstance(bbox,list) or len(bbox)!=4
                        or not all(type(v) is int for v in bbox)
                        or donor.get("korean") not in kos):
                    continue
                a=rgba(dest_name)
                b=rgba(donor_name)
                if (a.size!=b.size or bbox[0]<0 or bbox[1]<0
                        or not 0<=bbox[0]<bbox[2]<=a.width
                        or not 0<=bbox[1]<bbox[3]<=a.height):
                    continue
                examined += 1
                pa=a.crop(tuple(bbox)).tobytes()
                pb=b.crop(tuple(bbox)).tobytes()
                if pa != pb:
                    continue
                key=(dest_row["png_sha256"],bridge.normalized(english))
                data={
                    "status":"DIRECT_IMAGEGEN_READY",
                    "source_type":"SHA_MANIFEST_VERIFIED_UNSPLIT_HD_PNG",
                    "source_png":dest_name,
                    "source_png_path":str(g.SRC / dest_name),
                    "source_sha256":dest_row["png_sha256"],
                    "reference_dds_path":dest_row["source_dds_path"],
                    "reference_dds_sha256":dest_row["dds_sha256"],
                    "english": english,
                    "approved_korean":next(iter(kos)),
                    "bbox_xyxy":bbox,
                    "source_dimensions":list(a.size),
                    "target_dimensions":[bbox[2]-bbox[0],bbox[3]-bbox[1]],
                    "direct_full_hd_reference":True,
                    "crop_created":False,
                    "old_split_tiles_used":False,
                    "cross_variant_exact_rgba_verified":True,
                    "cross_variant_donor_png":donor_name,
                    "cross_variant_donor_sha256":donor_row["png_sha256"],
                    "cross_variant_donor_id":donor["id"],
                    "cross_variant_exact_pixel_sha256":hashlib.sha256(pa).hexdigest(),
                    "cross_variant_evidence":"IDENTICAL_RAW_RGBA_BYTES_SAME_BBOX_SOURCE_SHA_VERIFIED",
                    "human_review_required":True,
                    "external_api_used":False,
                    "image_generation_used":False,
                    "runtime_validation":"UNTESTED",
                    "independent_DDS_pixel_equality":"NOT_TESTED",
                }
                previous=chosen.get(key)
                area=(bbox[2]-bbox[0])*(bbox[3]-bbox[1])
                if previous is None or area < previous[0]:
                    chosen[key]=(area,data)
    return [z[1] for z in sorted(chosen.values(),key=lambda z:(z[1]["source_png"],z[1]["english"]))],examined


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--execute",action="store_true")
    args=p.parse_args()
    g=module("gpt_vision_chat_ocr.py")
    bridge=module("crop_to_imagegen_queue.py")
    found,compared=matches(g,bridge)
    saved=[]
    if args.execute:
        for item in found:
            key=hashlib.sha256((item["source_sha256"]+"|"+item["english"]+"|"+json.dumps(item["bbox_xyxy"])).encode()).hexdigest()[:16]
            path=IMAGEGEN/"cross_variant_verified"/Path(item["source_png"]).stem/key/"manifest.json"
            if path.exists():
                current=json.loads(path.read_text(encoding="utf-8"))
                if current != item:
                    raise RuntimeError("EXISTING_EVIDENCE_CHANGED:"+str(path))
            else:
                atomic_json(path,item)
            saved.append(str(path))
    print(json.dumps({"status":"CROSS_VARIANT_PIXEL_IDENTICAL_REVIEW_ONLY",
       "compared_pairs":compared,"unique_source_sha_and_phrase":len(found),
       "examples":[{"source":v["source_png"],"english":v["english"],
                    "korean":v["approved_korean"],"bbox":v["bbox_xyxy"],
                    "donor":v["cross_variant_donor_png"]} for v in found],
       "evidence_files":saved,
       "auto_generated_png":0,
       "dds_changed":False,
       "ocr_state_changed":False,
       "production_queue_changed":False},ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
