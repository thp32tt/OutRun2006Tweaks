#!/usr/bin/env python3
"""Immutable GitHub source gate for W00012 lane B zoom-review resolutions.

Downloads only pinned Sonic-TV/OR2006Sprites assets from the immutable commit
below. It validates Git blob identities, source PNG identities, atlas mappings,
DDS dimensions, and records DDS format/mip/header metadata for the two newly
confirmed localizable assets. No N100/local clone/GPT Library input is used.
"""
from __future__ import annotations
import argparse, hashlib, json, struct, urllib.parse, urllib.request
from pathlib import Path

SOURCE_REPO = "Sonic-TV/OR2006Sprites"
SOURCE_COMMIT = "a95efe01d1f136514cef94b0d9e9fd61df021754"

ASSETS = [
    {
        "index": 202,
        "asset": "AB56F682",
        "classification": "PRESERVE_ORIGINAL",
        "png_path": "Original (PC)/Original (Tweaks dumps)/spr_sprani_sumo_fe_cvt_Exst/AB56F682_512x512.png",
        "png_blob_sha": "075e1824941df7010b5fc8f8a28f455d213bb963",
        "release_path": "Release/spr_sprani_sumo_fe_cvt_Exst/AB56F682_512x512.dds",
        "release_blob_sha": "a8baacac9ede77ea003ce4662cf48d7ed436f30a",
        "release_bytes": 16777344,
        "atlas_path": "Original (PC)/Original (Tweaks dumps)/spr_sprani_sumo_fe_cvt_Exst/4x_AB56F682_512x512_atlas.json",
        "atlas_blob_sha": "7c58586ed209f032a52f86aaab158e37ee047a12",
        "expected_dimensions": [2048, 2048],
        "regions": {
            "sprite_359": [0, 1160, 748, 888],
            "sprite_360": [748, 1160, 748, 888],
            "sprite_361": [0, 272, 748, 888],
            "sprite_362": [748, 272, 748, 888],
        },
    },
    {
        "index": 206,
        "asset": "AEA507A4",
        "classification": "LOCALIZABLE_TEXT_CONFIRMED",
        "png_path": "Original (PC)/Original (Tweaks dumps)/spr_sprani_sumo_fe_cvt_Exst/AEA507A4_512x256.png",
        "png_blob_sha": "180edf5fe572ebedc83c02c4fa3569b2cf5e6d81",
        "release_path": "Release/spr_sprani_sumo_fe_cvt_Exst/AEA507A4_512x256.dds",
        "release_blob_sha": "63a29db6e8eaaface8036a03f87e9de2ad750184",
        "release_bytes": 2796368,
        "atlas_path": "Original (PC)/Original (Tweaks dumps)/spr_sprani_sumo_fe_cvt_Exst/4x_AEA507A4_512x256_atlas.json",
        "atlas_blob_sha": "d013da136524d480b87f06e900e8ee9dfd12c50d",
        "expected_dimensions": [2048, 1024],
        "regions": {"sprite_1448": [0, 348, 1160, 676]},
    },
    {
        "index": 210,
        "asset": "B5BB7AB0",
        "classification": "PRESERVE_ORIGINAL",
        "png_path": "Original (PC)/Original (Tweaks dumps)/spr_sprani_sumo_fe_cvt_Exst/B5BB7AB0_512x512.png",
        "png_blob_sha": "374a7870815ce009dc9b09a3f27a7263a4ab3021",
        "release_path": "Release/spr_sprani_sumo_fe_cvt_Exst/B5BB7AB0_512x512.dds",
        "release_blob_sha": "c0b2ba8cc1492e92e7b9754ea90ceb77649e8a95",
        "release_bytes": 16777344,
        "atlas_path": "Original (PC)/Original (Tweaks dumps)/spr_sprani_sumo_fe_cvt_Exst/4x_B5BB7AB0_512x512_atlas.json",
        "atlas_blob_sha": "dd23c4ae03fb0928fbfdf73497c21d6841395cd3",
        "expected_dimensions": [2048, 2048],
        "regions": {
            "sprite_363": [0, 1160, 748, 888],
            "sprite_364": [748, 1160, 748, 888],
            "sprite_365": [0, 272, 748, 888],
            "sprite_366": [748, 272, 748, 888],
        },
    },
    {
        "index": 214,
        "asset": "BF229CF4",
        "classification": "LOCALIZABLE_TEXT_CONFIRMED",
        "png_path": "Original (PC)/Original (Tweaks dumps)/spr_sprani_sumo_fe_cvt_Exst/BF229CF4_512x512.png",
        "png_blob_sha": "dcb40a72fb0ce85b0cb8da8ae293ec825a87e58c",
        "release_path": "Release/spr_sprani_sumo_fe_cvt_Exst/BF229CF4_512x512.dds",
        "release_blob_sha": "e8ddd2e7f5ee6a716d17ca4a9539cba9d74dd94c",
        "release_bytes": 16777344,
        "atlas_path": "Original (PC)/Original (Tweaks dumps)/spr_sprani_sumo_fe_cvt_Exst/4x_BF229CF4_512x512_atlas.json",
        "atlas_blob_sha": "38123348456aab4a837aa99747559ad89faeb8cb",
        "expected_dimensions": [2048, 2048],
        "regions": {"sprite_309": [748, 272, 748, 888]},
    },
]

def git_blob_sha(data: bytes) -> str:
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()

def raw_url(path: str) -> str:
    return f"https://raw.githubusercontent.com/{SOURCE_REPO}/{SOURCE_COMMIT}/" + urllib.parse.quote(path, safe="/")

def fetch(path: str) -> bytes:
    req = urllib.request.Request(raw_url(path), headers={"User-Agent":"OR2006-Korean-W00012-B-source-gate"})
    with urllib.request.urlopen(req, timeout=180) as resp:
        return resp.read()

def dds_header(data: bytes) -> dict:
    if len(data) < 128 or data[:4] != b"DDS ":
        raise ValueError("invalid DDS")
    height=struct.unpack_from("<I",data,12)[0]
    width=struct.unpack_from("<I",data,16)[0]
    pitch=struct.unpack_from("<I",data,20)[0]
    mips=struct.unpack_from("<I",data,28)[0] or 1
    fourcc=data[84:88]
    rgb_bits=struct.unpack_from("<I",data,88)[0]
    fmt="DXT5" if fourcc==b"DXT5" else ("RGBA32" if fourcc==b"\0\0\0\0" and rgb_bits==32 else f"OTHER:{fourcc!r}:{rgb_bits}")
    return {"width":width,"height":height,"pitch_or_linear":pitch,"mipmaps":mips,"format":fmt,"rgb_bits":rgb_bits}

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ns=ap.parse_args()
    results=[]; failures=[]
    for spec in ASSETS:
        png=fetch(spec["png_path"])
        dds=fetch(spec["release_path"])
        atlas_bytes=fetch(spec["atlas_path"])
        atlas=json.loads(atlas_bytes.decode("utf-8"))
        regions={r["name"]:r["rect"] for r in atlas["regions"]}
        header=dds_header(dds)
        checks={
            "png_blob_sha":git_blob_sha(png)==spec["png_blob_sha"],
            "release_blob_sha":git_blob_sha(dds)==spec["release_blob_sha"],
            "release_size":len(dds)==spec["release_bytes"],
            "dimensions":[header["width"],header["height"]]==spec["expected_dimensions"],
            "atlas_blob_sha":git_blob_sha(atlas_bytes)==spec["atlas_blob_sha"],
            "atlas_regions":all(regions.get(n)==r for n,r in spec["regions"].items()),
        }
        if not all(checks.values()):
            failures.append({"index":spec["index"],"checks":checks})
        results.append({
            "index":spec["index"],"asset":spec["asset"],"classification":spec["classification"],
            "png_git_blob_sha":git_blob_sha(png),"release_git_blob_sha":git_blob_sha(dds),
            "release_sha256":hashlib.sha256(dds).hexdigest(),"release_bytes":len(dds),
            "dds":header,"atlas_git_blob_sha":git_blob_sha(atlas_bytes),
            "regions":{n:regions.get(n) for n in spec["regions"]},"checks":checks,
        })
    out={"schema_version":1,"source_repository":SOURCE_REPO,"source_commit":SOURCE_COMMIT,
         "assets":results,"failures":failures,"result":"PASS" if not failures else "FAIL",
         "candidate_dds_written":False,"runtime_validation":"UNTESTED"}
    ns.out.parent.mkdir(parents=True,exist_ok=True)
    ns.out.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return 0 if not failures else 2

if __name__=="__main__":
    raise SystemExit(main())
