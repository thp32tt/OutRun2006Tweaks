#!/usr/bin/env python3
"""Extract exact raw-orientation review PNGs and geometry from an uncompressed HD DDS."""
from __future__ import annotations
import argparse, hashlib, json, struct
from pathlib import Path
from PIL import Image

HEADER=128

def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def bbox_alpha(im: Image.Image, threshold: int):
    a=im.getchannel("A")
    if threshold <= 1:
        m=a.point(lambda v: 255 if v > 0 else 0)
    else:
        m=a.point(lambda v: 255 if v >= threshold else 0)
    b=m.getbbox()
    return list(b) if b else None

def dds_info(p: Path):
    b=p.read_bytes()
    if len(b)<HEADER or b[:4]!=b"DDS ":
        raise SystemExit("invalid DDS")
    h=struct.unpack_from("<I",b,12)[0]
    w=struct.unpack_from("<I",b,16)[0]
    mips=struct.unpack_from("<I",b,28)[0] or 1
    fourcc=b[84:88]
    bits=struct.unpack_from("<I",b,88)[0]
    masks=[struct.unpack_from("<I",b,o)[0] for o in (92,96,100,104)]
    return b,{"width":w,"height":h,"mips":mips,"fourcc":fourcc.hex(),"rgb_bits":bits,
              "masks":{"r":masks[0],"g":masks[1],"b":masks[2],"a":masks[3]}}

def decode_bgra32(p: Path):
    b,info=dds_info(p)
    if info["fourcc"]!="00000000" or info["rgb_bits"]!=32:
        raise SystemExit("only exact uncompressed 32-bit DDS is supported")
    w,h=info["width"],info["height"]
    payload=b[HEADER:HEADER+w*h*4]
    if len(payload)!=w*h*4:
        raise SystemExit("unexpected mip/extra payload; fail closed")
    rgba=bytearray(len(payload))
    for i in range(0,len(payload),4):
        B,G,R,A=payload[i:i+4]
        rgba[i:i+4]=bytes((R,G,B,A))
    return Image.frombytes("RGBA",(w,h),bytes(rgba)),info

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--source-dds",required=True)
    ap.add_argument("--output-dir",required=True)
    ap.add_argument("--asset-id",required=True)
    ap.add_argument("--git-blob-sha",required=True)
    ap.add_argument("--cell",nargs=4,type=int,metavar=("X","Y","W","H"))
    a=ap.parse_args()
    src=Path(a.source_dds)
    out=Path(a.output_dir); out.mkdir(parents=True,exist_ok=True)
    raw,info=decode_bgra32(src)
    variants={
      "raw":raw,
      "flip_x":raw.transpose(Image.Transpose.FLIP_LEFT_RIGHT),
      "flip_y":raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM),
      "rotate_180":raw.transpose(Image.Transpose.ROTATE_180),
    }
    files={}
    for name,im in variants.items():
        p=out/f"preflight_{name}.png"; im.save(p,optimize=True); files[name]=str(p)
    cell=None
    if a.cell:
        x,y,w,h=a.cell
        if x<0 or y<0 or w<=0 or h<=0 or x+w>raw.width or y+h>raw.height:
            raise SystemExit("cell outside canvas")
        c=raw.crop((x,y,x+w,y+h))
        cell={
          "rect":[x,y,w,h],
          "alpha_gt0_bbox_canvas":bbox_alpha(raw,1),
          "alpha_ge128_bbox_canvas":bbox_alpha(raw,128),
          "alpha_gt0_bbox_cell_local":bbox_alpha(c,1),
          "alpha_ge128_bbox_cell_local":bbox_alpha(c,128),
        }
    report={
      "schema_version":1,
      "asset_id":a.asset_id,
      "source_dds":str(src),
      "source_git_blob_sha":a.git_blob_sha,
      "source_sha256":sha256(src),
      "dds":info,
      "cell":cell,
      "variants":files,
      "orientation_status":"VISUAL_SELECTION_REQUIRED",
      "signed_slant_status":"MEASURE_AFTER_DISPLAY_TRANSFORM_SELECTION",
      "runtime_validation":"UNTESTED"
    }
    (out/"preflight_metrics.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False))

if __name__=="__main__":
    main()
