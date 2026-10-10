#!/usr/bin/env python3
"""Reproduce exact q212 English DDS bytes from its 2048x2048 external layered PSD's merged raster.

This is a SOURCE production-pipeline validation, not a Korean localization candidate.
"""
import argparse,hashlib,json,struct
from pathlib import Path
import numpy as np
from PIL import Image,ImageOps

PSD_SHA="be5095d2598a831461e2e345c8fd2cead0cdd8de00ea7481256f0494c671d736"
DDS_SHA="f83f58483aab7a99ffe230c86eaa0527d9b7323be36808bdf69f2817e29c9f61"
def sha(data):return hashlib.sha256(data).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument("--psd",required=True);p.add_argument("--dds",required=True);p.add_argument("--out-dir",required=True);a=p.parse_args()
 out=Path(a.out_dir);out.mkdir(parents=True,exist_ok=True)
 psd_bytes=Path(a.psd).read_bytes();source=Path(a.dds).read_bytes()
 assert sha(psd_bytes)==PSD_SHA,"PSD identity mismatch"
 assert sha(source)==DDS_SHA,"canonical source identity mismatch"
 assert source[:4]==b"DDS " and len(source)==16777344,"unexpected DDS header/length"
 height,width=struct.unpack_from("<II",source,12)
 assert (width,height)==(2048,2048),"unexpected source dimensions"
 masks=struct.unpack_from("<4I",source,92)
 assert masks==(255,65280,16711680,4278190080),"unexpected channel masks"
 psd=Image.open(a.psd).convert("RGBA");native=ImageOps.flip(psd)
 actual=Image.open(a.dds).convert("RGBA")
 assert native.size==actual.size,"canvas mismatch"
 matches=int(np.count_nonzero(np.all(np.asarray(native)==np.asarray(actual),axis=2)))
 assert matches==width*height,"flipped source pixel mismatch"
 arr=np.asarray(native)
 pixel=np.zeros((height,width),dtype=np.uint32)
 for i,mask in enumerate(masks):
  shift=(mask & -mask).bit_length()-1
  pixel |= arr[:,:,i].astype(np.uint32)<<shift
 rebuilt=source[:128]+pixel.astype("<u4").tobytes()
 assert rebuilt==source,"DDS output not exact English reference"
 (out/"REBUILT_CANONICAL_ENGLISH.dds").write_bytes(rebuilt)
 report={"result":"SOURCE_REPRODUCTION_ONLY_PASS","psd_sha256":sha(psd_bytes),"source_sha256":sha(source),"rebuilt_sha256":sha(rebuilt),"identical_pixels":matches,"total_pixels":width*height,"different_bytes":0,"new_korean_dds":0,"runtime_validation":"UNTESTED"}
 (out/"report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
 print(json.dumps(report))
if __name__=="__main__":main()
