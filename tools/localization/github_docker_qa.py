#!/usr/bin/env python3
"""GitHub-hosted, Docker-executed OutRun Korean DDS proof pipeline.

Checks only SHA-pinned repository inputs. Builds a reproducible TEST_ONLY ZIP
from exactly three source-native examples. This is not visual/gameplay approval.
The 954 A/B candidate images must be imported to GitHub separately.
"""
import argparse
import csv
import hashlib
import io
import json
import re
import struct
import zipfile
from collections import Counter
from pathlib import Path, PurePosixPath

from PIL import Image

PACKAGES = (
    ("native-q012", "localization/test_packages/q012_native_format_test_only_20261102/OUTRUN_Q012_IMAGEGEN_NATIVE_FORMAT_1DDS_TEST_ONLY.zip",
     "b943788616522a5a4b5b2210f61cde344c7878a68881bc01213ee6b4fe318c2e", True),
    ("native-q089-q104", "localization/test_packages/OUTRUN_AB_Q089_Q104_NATIVE_2DDS_TEST_ONLY.zip",
     "79fd62e8205632371b31d002643d2565a0eee753412a46aa5e4ff7f5e6aa08fc", True),
    ("earlier-q032-q241", "localization/test_packages/OUTRUN_KOR_Q032_Q241_DDS_TEST_ONLY.zip",
     "63d713551e4018f4f1cc131db230e422ef2ca643d3bffb99a0a8c26c39203633", False),
    ("earlier-ab8", "localization/test_packages/ab_imagegen_alpha_composite_v4_20261102/OUTRUN_AB_IMAGEGEN_ALPHA_COMPOSITE_8DDS_TEST_ONLY.zip",
     "ddc534b526ebc428efbff38839c015fab59782fb6f5813dac5e8a65c3aa9db01", False),
)
EXPECTED_NATIVE = {
    "textures/load/spr_etc_xst/D6DC1380_256x64.dds":
       "7f06b1a8892d760783ee158e51440eae5702d72e48fecf709dd06492701a9bf9",
    "textures/load/spr_sprani_route_cvt_Exst/43B07A77_512x64.dds":
       "2ac06eeaa6e77b9ab5525fed0a712b43707bcec347ed856e7930f2fbc0494395",
    "textures/load/spr_sprani_selector_cvt_Exst/62BEBF33_512x64.dds":
       "7069d1c31feb9b83b59dfb75ee0fb80cd815d216ed0a07a4ffef4dd09f562a95",
}
NATIVE_MASKS = (0x00ff0000, 0x0000ff00, 0x000000ff, 0xff000000)
OUTPUT_NAME = "OUTRUN_KOREAN_NATIVE_3DDS_STATIC_TEST_ONLY.zip"
MAX_TOTAL_UNCOMPRESSED = 650 * 1024 * 1024
MAX_MEMBER = 150 * 1024 * 1024


def sha(data):
    return hashlib.sha256(data).hexdigest()


def safe_name(name):
    if not name or "\\" in name or "\0" in name or name.startswith("/") or ":" in name:
        return False
    path = PurePosixPath(name)
    return ".." not in path.parts and "." not in path.parts and not name.endswith("/")


def zip_members(z):
    seen = set()
    total = 0
    for item in z.infolist():
        name = item.filename
        if not safe_name(name) or name in seen or (item.external_attr >> 16) & 0o170000 == 0o120000:
            raise ValueError("UNSAFE_OR_DUPLICATE_ARCHIVE_MEMBER:" + name)
        if item.file_size > MAX_MEMBER:
            raise ValueError("OVERSIZED_MEMBER:" + name)
        total += item.file_size
        if total > MAX_TOTAL_UNCOMPRESSED:
            raise ValueError("OVERSIZED_ARCHIVE")
        seen.add(name)
    if z.testzip() is not None:
        raise ValueError("ZIP_CRC_FAILURE")
    return seen


def inspect_native(raw):
    if len(raw) < 128 or raw[:4] != b"DDS ":
        raise ValueError("DDS_HEADER_INVALID")
    if struct.unpack_from("<I", raw, 4)[0] != 124:
        raise ValueError("DDS_HEADER_SIZE")
    h, w = struct.unpack_from("<II", raw, 12)
    mips = struct.unpack_from("<I", raw, 28)[0]
    pfsize, flags = struct.unpack_from("<II", raw, 76)
    bpp = struct.unpack_from("<I", raw, 88)[0]
    masks = struct.unpack_from("<IIII", raw, 92)
    if not (0 < w <= 4096 and 0 < h <= 4096):
        raise ValueError("DDS_DIMENSIONS")
    if (pfsize, flags, bpp, masks, mips) != (32, 65, 32, NATIVE_MASKS, 1):
        raise ValueError("DDS_NOT_SOURCE_NATIVE_BGRA_SINGLE_MIP")
    if raw[84:88] != b"\0\0\0\0" or len(raw) != 128 + 4*w*h:
        raise ValueError("DDS_LAYOUT")
    with Image.open(io.BytesIO(raw)) as im:
        im.load()
        if im.size != (w,h):
            raise ValueError("DDS_DECODE_DIMS")
        img = im.convert("RGBA")
    if img.tobytes("raw", "BGRA") != raw[128:]:
        raise ValueError("DDS_DECODE_ROUNDTRIP")
    return img, (w,h)


def stable_json(o):
    return (json.dumps(o, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")


def deterministic_write(z, name, data):
    info = zipfile.ZipInfo(name, date_time=(1980,1,1,0,0,0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    z.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=3)


def audit_candidate_inventory(root):
    """Count GitHub-resident candidate bytes, never confuse CSV paths with bytes."""
    crosswalk = root / "localization/test_packages/ab_preparation_20261102/ab_roi_crosswalk.csv"
    if not crosswalk.is_file():
        return {"status": "INPUT_CROSSWALK_MISSING", "expected_active": 954, "on_github": 0}
    with crosswalk.open(encoding="utf-8-sig",newline="") as f:
        rows = list(csv.DictReader(f))
    keys = [r.get("roi_id","") for r in rows]
    if len(keys) != len(set(keys)) or len(rows) != 954:
        raise ValueError("CROSSWALK_COUNT_OR_UNIQUE_ID_CHANGED")
    present, missing = [], []
    for row in rows:
        paths = row.get("candidate_paths","").split(";")
        available = []
        for p in paths:
            # Absolute paths are N100 coordinates, NEVER a GitHub-hosted input.
            if not p:
                continue
            name = Path(p).name
            role = Path(p).parent.name
            if role not in ("A","B") or not name.endswith(".png"):
                raise ValueError("BAD_CANDIDATE_INDEX:" + row["roi_id"])
            filepath = root / "localization/automation_inputs/candidate_outputs" / role / name
            if filepath.is_file() and not filepath.is_symlink():
                with Image.open(filepath) as im:
                    im.verify()
                available.append(str(filepath.relative_to(root)))
        if len(available) == 1: present.append(row["roi_id"])
        else: missing.append(row["roi_id"])
    return {
        "status": "INPUT_READY" if not missing else "AWAITING_GITHUB_ASSET_IMPORT",
        "expected_active":954, "on_github":len(present), "missing_count":len(missing),
        "missing_samples":missing[:20], "legacy_extras_excluded":1,
    }


def build(root, out):
    root = Path(root).resolve()
    out = Path(out).resolve()
    if out == root or out.is_relative_to(root / "localization/automation_inputs"):
        raise ValueError("UNSAFE_OUTPUT_LOCATION")
    out.mkdir(parents=True,exist_ok=True)
    result = {"schema":"outrun-github-docker-korean-qa-v1",
              "release_approved":False,"runtime_validation":"UNTESTED",
              "visual_qa":"REVIEW_REQUIRED","source_native_static_pass":[],
              "hold_packages":[],"package_checks":[]}
    selected = {}
    for label, relpath, pinned, native in PACKAGES:
        p = root / relpath
        if not p.is_file() or p.is_symlink():
            raise ValueError("REQUIRED_GITHUB_PACKAGE_MISSING:" + label)
        actual = sha(p.read_bytes())
        if actual != pinned:
            raise ValueError("PACKAGE_SHA_CHANGED:" + label)
        with zipfile.ZipFile(p,"r") as z:
            names = zip_members(z)
            dds = sorted(n for n in names if n.lower().endswith(".dds"))
            if not dds:
                raise ValueError("NO_DDS:" + label)
            result["package_checks"].append({"name":label,"sha256":pinned,"dds_count":len(dds),
                                              "state":"NATIVE_STATIC_CHECK" if native else "VISUAL_FORMAT_HOLD"})
            if not native:
                result["hold_packages"].append({
                    "name":label,"dds_count":len(dds),
                    "reason":"OLDER_PACKAGE_NATIVE_FORMAT_AND_VISUAL_QA_UNVERIFIED"})
                continue
            for path in dds:
                if not path.startswith("textures/load/") or path not in EXPECTED_NATIVE:
                    raise ValueError("UNEXPECTED_DDS_TARGET:" + path)
                raw = z.read(path)
                content_sha = sha(raw)
                if content_sha != EXPECTED_NATIVE[path]:
                    raise ValueError("PINNED_DDS_SHA_MISMATCH:" + path)
                image, dims = inspect_native(raw)
                if path in selected:
                    raise ValueError("MULTIPLE_NATIVE_ASSET_OWNERS:" + path)
                selected[path] = raw
                receipt_id = "Q" + ("012" if "D6DC1380" in path else "089" if "43B07A77" in path else "104")
                rec_path = "qa_receipts/" + (receipt_id + "_native_format.json" if receipt_id=="Q012" else receipt_id + ".json")
                if rec_path not in names:
                    raise ValueError("REQUIRED_QA_RECEIPT_MISSING:" + receipt_id)
                rec = json.loads(z.read(rec_path).decode("utf-8"))
                if rec.get("runtime_validation") != "UNTESTED":
                    raise ValueError("FALSE_RUNTIME_APPROVAL:" + receipt_id)
                if rec.get("output_dds_sha256") != content_sha:
                    raise ValueError("QA_RECEIPT_DDS_SHA_MISMATCH:" + receipt_id)
                if rec.get("header_identical") is False or rec.get("outside_box_pixel_changes", rec.get("outside_source_ink_bbox_changes", 0)) != 0:
                    raise ValueError("QA_RECEIPT_PROTECTION_FAIL:" + receipt_id)
                if not rec.get("original_dds_sha256", rec.get("source_sha256")):
                    raise ValueError("SOURCE_PROVENANCE_MISSING:" + receipt_id)
                preview = out / ("PREVIEW_"+receipt_id+".png")
                image.save(preview,format="PNG")
                result["source_native_static_pass"].append({
                    "id":receipt_id,"target_path":path,"sha256":content_sha,
                    "dimensions":list(dims),
                    "gate":"STATIC_ONLY_VISUAL_AND_GAMEPLAY_REVIEW_REQUIRED"})
    if set(selected) != set(EXPECTED_NATIVE):
        raise ValueError("NATIVE_SET_MISSING_OR_EXTRA")
    result["asset_inventory"] = audit_candidate_inventory(root)
    result["native_dds_count"]=len(selected)
    result["test_only_zip"]=OUTPUT_NAME
    manifest = {
        "status":"TEST_ONLY_NOT_RUNTIME_APPROVED",
        "release_approved":False,"runtime_validation":"UNTESTED",
        "visual_qa":"REVIEW_REQUIRED",
        "entries":{p:sha(raw) for p,raw in sorted(selected.items())},
        "source_packages":[k for k,_,_,native in PACKAGES if native],
    }
    with zipfile.ZipFile(out/OUTPUT_NAME,"w") as z:
        for path,raw in sorted(selected.items()):
            deterministic_write(z,path,raw)
        deterministic_write(z,"TEST_ONLY_MANIFEST.json",stable_json(manifest))
    with zipfile.ZipFile(out/OUTPUT_NAME) as z:
        zip_members(z)
        for path,raw in selected.items():
            if z.read(path) != raw:
                raise ValueError("ZIP_DDS_ROUNDTRIP")
    result["test_only_sha256"]=sha((out/OUTPUT_NAME).read_bytes())
    (out/"qa_report.json").write_bytes(stable_json(result))
    with (out/"qa_status.csv").open("w",encoding="utf-8",newline="") as f:
        w=csv.writer(f)
        w.writerow(["asset","status","reason"])
        for r in result["source_native_static_pass"]:
            w.writerow([r["id"],"STATIC_PASS_VISUAL_HOLD","Visual and gameplay review required"])
        for r in result["hold_packages"]:
            w.writerow([r["name"],"HOLD",r["reason"]])
        w.writerow(["A/B active ROI",result["asset_inventory"]["status"],
                    "GitHub-hosted candidate files: "+str(result["asset_inventory"]["on_github"])+"/954"])
    print(json.dumps({
        "native_dds_count":result["native_dds_count"],
        "native_test_sha256":result["test_only_sha256"],
        "input_status":result["asset_inventory"]["status"],
        "github_candidates":result["asset_inventory"]["on_github"],
        "held_package_count":len(result["hold_packages"]),
        "release_approved":False},ensure_ascii=False))
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--repo-root",default=".")
    parser.add_argument("--out",default="/outputs")
    args=parser.parse_args()
    build(args.repo_root,args.out)


if __name__ == "__main__":
    main()
