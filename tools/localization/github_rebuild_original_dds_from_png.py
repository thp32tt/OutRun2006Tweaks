#!/usr/bin/env python3
"""Reconstruct *only* SHA-identical original HD DDS bytes from verified PNG.

Source PNG bytes were independently matched to the user's 108-file Google
Drive source manifest. Candidate DDS files are used for headers only.
Never treats a reconstructed DDS as an original unless its full SHA256 matches
the previously recorded original DDS SHA256; no unverified fallback.
"""
import argparse
import hashlib
import io
import json
import struct
from pathlib import Path

from PIL import Image

ROOT = "localization/automation_inputs/drive_verified_original_hd_png"
CANDIDATES = "localization/graphics/hd_candidates"
DEST = "localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a"
ENTRIES = (
    {
        "id": "Q046", "filename": "Q046_AA04D779_BASE_READABLE_FLIPY.png",
        "target": "textures/load/spr_sprani_etc_cvt_Exst/AA04D779_512x512.dds",
        "png_sha256": "3ca447ddebe3035a2a16a70fd36f7805858bba02c6cf9ccd749c80d7a9c59d6c",
        "source_dds_sha256": "1a01e19b2749acdd275d10ff6e82bcb525d6621fd9118fb0c1fa5997c4c1dfa5",
    },
    {
        "id": "Q047", "filename": "Q047_AD720950_BASE_READABLE_FLIPY.png",
        "target": "textures/load/spr_sprani_etc_cvt_Exst/AD720950_1024x256.dds",
        "png_sha256": "ebeb96e71cabb5b410e466c541aee04336c4a415c8ff386702243af379d4a92f",
        "source_dds_sha256": "141e1f0773b82a8eca6ff49cd93d637221b96211566541f97de9ef4fc454d26f",
    },
)
BGRA = (0x00ff0000, 0x0000ff00, 0x000000ff, 0xff000000)
RGBA = (0x000000ff, 0x0000ff00, 0x00ff0000, 0xff000000)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def reconstruct(hd_png, existing_dds):
    """Rebuild original byte layout, never guess masks or pixel orientation."""
    if existing_dds[:4] != b"DDS " or len(existing_dds) < 128:
        raise ValueError("INVALID_CANDIDATE_DDS_HEADER")
    header = existing_dds[:128]
    if struct.unpack_from("<I", header, 4)[0] != 124:
        raise ValueError("INVALID_DDS_HEADER_SIZE")
    h, w = struct.unpack_from("<II", header, 12)
    if not (0 < w <= 4096 and 0 < h <= 4096):
        raise ValueError("UNSAFE_DDS_DIMENSIONS")
    if (len(existing_dds) != 128 + 4 * w * h or
            struct.unpack_from("<I", header, 28)[0] != 1 or
            struct.unpack_from("<I", header, 76)[0] != 32 or
            struct.unpack_from("<I", header, 80)[0] != 65 or
            struct.unpack_from("<I", header, 88)[0] != 32):
        raise ValueError("UNSUPPORTED_DDS_FORMAT")
    masks = tuple(struct.unpack_from("<IIII", header, 92))
    if masks not in (BGRA, RGBA):
        raise ValueError("DDS_MASKS_UNVERIFIED")
    with Image.open(io.BytesIO(hd_png)) as im:
        if im.format != "PNG" or im.size != (w, h):
            raise ValueError("SOURCE_PNG_DIMENSION_MISMATCH")
        im.load()
        image = im.convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    pixel_mode = "BGRA" if masks == BGRA else "RGBA"
    raw = image.tobytes("raw", pixel_mode)
    result = header + raw
    if len(result) != len(existing_dds):
        raise ValueError("DDS_LENGTH_MISMATCH")
    with Image.open(io.BytesIO(result)) as back:
        if back.convert("RGBA").tobytes("raw", pixel_mode) != raw:
            raise ValueError("DDS_DECODE_MISMATCH")
    return result, {"width": w, "height": h, "mask": list(masks),
                    "mode": pixel_mode, "orientation": "FLIPY"}


def run(repo_root, out):
    root, out = Path(repo_root).resolve(), Path(out).resolve()
    if out.is_relative_to(root):
        raise ValueError("OUTPUT_MUST_BE_OUTSIDE_GITHUB_CHECKOUT")
    out.mkdir(parents=True, exist_ok=True)
    report = {"schema":"outrun.original-dds-from-hd-png.sha-gated.v1",
              "release_approved":False,"runtime_validation":"UNTESTED","records":[]}
    for item in ENTRIES:
        result = {k:item[k] for k in ("id","target","png_sha256","source_dds_sha256")}
        try:
            png_path = root / ROOT / item["filename"]
            dds_path = root / CANDIDATES / item["target"]
            if not png_path.is_file() or not dds_path.is_file() or png_path.is_symlink() or dds_path.is_symlink():
                raise ValueError("INPUT_NOT_IN_GITHUB")
            png_bytes = png_path.read_bytes()
            if sha(png_bytes) != item["png_sha256"]:
                raise ValueError("SOURCE_PNG_SHA_CHANGED")
            candidate_bytes = dds_path.read_bytes()
            rebuilt, metadata = reconstruct(png_bytes, candidate_bytes)
            result["candidate_header_source_sha256"] = sha(candidate_bytes)
            result.update(metadata)
            result["reconstructed_sha256"] = sha(rebuilt)
            if result["reconstructed_sha256"] != item["source_dds_sha256"]:
                result["status"]="HOLD_RECONSTRUCTED_SHA_NOT_ORIGINAL"
                # Unverified DDS is not written even to the package.
            else:
                result["status"]="EXACT_ORIGINAL_DDS_RECOVERED"
                dest=out/item["target"]
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(rebuilt)
                if sha(dest.read_bytes()) != item["source_dds_sha256"]:
                    raise ValueError("RECOVERED_WRITE_READBACK_MISMATCH")
                result["recoverable_path"]=str(dest.relative_to(out))
        except (ValueError,OSError) as e:
            result["status"]="HOLD_"+str(e)[:110]
        report["records"].append(result)
    report["exact_recovered_count"]=sum(x["status"]=="EXACT_ORIGINAL_DDS_RECOVERED" for x in report["records"])
    (out/"recovery_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,sort_keys=True))
    return report


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--repo-root",default=".")
    p.add_argument("--out",default="/tmp/recover-exact-dds")
    args=p.parse_args()
    run(args.repo_root,args.out)
