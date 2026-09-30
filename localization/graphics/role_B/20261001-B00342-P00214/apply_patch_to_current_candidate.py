#!/usr/bin/env python3
from pathlib import Path
from PIL import Image
import numpy as np, struct, hashlib, json, sys
BASE_SHA="28f4c6bde58bcabd2e7bf8b0c1ce200858201928dfa77abd44152522e52ba593"
PATCHES={"cut_line":((2597,1008,3027,1096),(2598,1018,3025,1085),"cut_line_patch.png"),"stage_bonus":((3872,1800,4028,1893),(3855,1801,4034,1892),"stage_bonus_patch.png")}
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main(inp,out):
 b=Path(inp).read_bytes(); assert sha(inp)==BASE_SHA, sha(inp); assert b[:4]==b"DDS " and len(b)==67108992
 h,w=struct.unpack_from("<II",b,12); assert (w,h)==(4096,4096)
 masks=[struct.unpack_from("<I",b,o)[0] for o in (92,96,100,104)]; assert masks==[0xff,0xff00,0xff0000,0xff000000]
 a=np.frombuffer(b,dtype=np.uint8,offset=128).reshape(h,w,4).copy(); r=a[::-1].copy(); before=r.copy()
 for k,(clr,gb,pn) in PATCHES.items():
  x0,y0,x1,y1=clr; r[y0:y1,x0:x1]=0
  p=np.array(Image.open(Path(__file__).with_name(pn)).convert("RGBA")); x0,y0,x1,y1=gb; assert p.shape[:2]==(y1-y0,x1-x0)
  dst=Image.fromarray(r[y0:y1,x0:x1],"RGBA"); dst.alpha_composite(Image.fromarray(p,"RGBA")); r[y0:y1,x0:x1]=np.array(dst)
 changed=(before!=r).any(axis=2); allowed=np.zeros((h,w),bool)
 for clr,gb,_ in PATCHES.values():
  for x0,y0,x1,y1 in (clr,gb): allowed[y0:y1,x0:x1]=1
 assert not (changed & ~allowed).any()
 outb=b[:128]+r[::-1].tobytes(); Path(out).write_bytes(outb); assert outb[:128]==b[:128] and len(outb)==len(b)
 print(json.dumps({"input_sha256":BASE_SHA,"output_sha256":sha(out),"changed_pixels":int(changed.sum()),"outside_allowed_changed_pixels":0,"runtime_validation":"UNTESTED"},ensure_ascii=False))
if __name__=="__main__": main(sys.argv[1],sys.argv[2])
