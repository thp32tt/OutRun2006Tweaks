#!/usr/bin/env python3
"""Deterministically rebuild B00332 index232 EBFC709F Korean DDS candidate.
Requires Pillow and a local Noto Sans CJK KR Bold TTC; font bytes are not distributed.
"""
import argparse, hashlib, struct
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

SOURCE_SHA="ad7a1c21be17d1fa93463201a26a85a21899dbe1162d5c2748ddeb6136a4f9a0"
CANDIDATE_SHA="41334c7d5ae5692e232fd9dfe25b75119419187f096566a8beae22eb74dc8026"
ELEMENTS=[
 ("big_join","게임 참가",(11,876,977,1017),(186,0,0,255),136),
 ("big_create","게임 만들기",(26,697,1243,838),(186,0,0,255),136),
 ("desc_join","친구들과 함께 아웃런 게임에 참가하세요!",(6,529,1136,595),(63,71,74,255),48),
 ("desc_create","게임을 만들고 친구를 초대하세요!",(9,369,1118,435),(63,71,74,255),48),
 ("small_join","게임 참가",(16,289,416,348),(63,71,74,255),44),
 ("small_create","게임 만들기",(900,293,1418,352),(63,71,74,255),44),
]
def sha(b): return hashlib.sha256(b).hexdigest()
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("source_dds", type=Path)
    ap.add_argument("output_dds", type=Path)
    ap.add_argument("--font", required=True, type=Path)
    ap.add_argument("--font-index", type=int, default=1)
    a=ap.parse_args()
    src=a.source_dds.read_bytes()
    if sha(src)!=SOURCE_SHA: raise SystemExit("canonical source SHA mismatch")
    if src[:4]!=b"DDS ": raise SystemExit("not DDS")
    h=struct.unpack_from("<I",src,12)[0]; w=struct.unpack_from("<I",src,16)[0]; mip=struct.unpack_from("<I",src,28)[0]
    if (w,h,mip)!=(2048,1024,1): raise SystemExit("DDS geometry mismatch")
    # Q00070 accepted all-zero CLEAN_PLATE for this transparent text-only atlas.
    readable=Image.new("RGBA",(w,h),(0,0,0,0))
    d=ImageDraw.Draw(readable)
    for _,text,(x0,y0,x1,y1),fill,start_size in ELEMENTS:
        sw=x1-x0+1; sh=y1-y0+1; size=start_size
        while size>=8:
            f=ImageFont.truetype(str(a.font),size,index=a.font_index)
            b=f.getbbox(text); iw=b[2]-b[0]; ih=b[3]-b[1]
            if iw<=sw-4 and ih<=sh-4: break
            size-=1
        ix=x0+2; iy=y0+(sh-ih)//2
        if ix+iw>x1-1: ix=x0+(sw-iw)//2
        d.text((ix-b[0],iy-b[1]),text,font=f,fill=fill)
    raw=readable.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    c=np.array(raw,dtype=np.uint8)
    bgra=c[:,:,[2,1,0,3]].tobytes()
    out=src[:128]+bgra
    if out[:128]!=src[:128]: raise SystemExit("header drift")
    if sha(out)!=CANDIDATE_SHA: raise SystemExit(f"candidate hash mismatch: {sha(out)}")
    a.output_dds.parent.mkdir(parents=True,exist_ok=True)
    a.output_dds.write_bytes(out)
if __name__=="__main__": main()
