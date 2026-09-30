#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, zipfile
from pathlib import Path
from PIL import Image
import numpy as np

BUNDLE_SHA="76f85ed2ca27344a4292ac7e010a786579b4eebb1a370c0aa126fcb2b231d958"
DDS_SHA="a8942f076b9c3d8cddd62ba39c84a3b3abea72b2ba19a61a21e9a2bd6f8e8036"
MEMBER="textures/load/spr_sprani_selector_cvt_Exst/C075FB49_512x512.dds"
CELL=(1710,1410,2008,1515)
TEXT=(245,247,247,255); BLUE=(103,152,220,255); WHITE=(255,255,255,255)

def sha(b): return hashlib.sha256(b).hexdigest()
def bbox(m):
    y,x=np.where(m)
    return None if not len(x) else [int(x.min()),int(y.min()),int(x.max()+1),int(y.max()+1)]
def dilate(m,r=1):
    h,w=m.shape; out=np.zeros_like(m)
    for dy in range(-r,r+1):
      for dx in range(-r,r+1):
        y0=max(0,-dy); y1=min(h,h-dy); x0=max(0,-dx); x1=min(w,w-dx)
        out[y0+dy:y1+dy,x0+dx:x1+dx] |= m[y0:y1,x0:x1]
    return out
def comps(m):
    h,w=m.shape; seen=np.zeros_like(m,bool); out=[]
    for y in range(h):
      for x in range(w):
        if not m[y,x] or seen[y,x]: continue
        q=[(x,y)]; seen[y,x]=1; pts=[]
        while q:
          a,b=q.pop(); pts.append((a,b))
          for nx,ny in ((a+1,b),(a-1,b),(a,b+1),(a,b-1)):
            if 0<=nx<w and 0<=ny<h and m[ny,nx] and not seen[ny,nx]:
              seen[ny,nx]=1; q.append((nx,ny))
        xs=[p[0] for p in pts]; ys=[p[1] for p in pts]
        out.append((len(pts),[min(xs),min(ys),max(xs)+1,max(ys)+1],pts))
    return sorted(out,reverse=True)
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("zip"); args=ap.parse_args()
    zb=Path(args.zip).read_bytes()
    if sha(zb)!=BUNDLE_SHA: raise SystemExit("bundle identity mismatch")
    with zipfile.ZipFile(args.zip) as z: dds=z.read(MEMBER)
    if sha(dds)!=DDS_SHA: raise SystemExit("DDS identity mismatch")
    tmp=Path(args.zip).with_name(".a00289_tmp.dds"); tmp.write_bytes(dds)
    raw=Image.open(tmp).convert("RGBA"); tmp.unlink()
    crop=np.asarray(raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM).crop(CELL))
    text=np.all(crop==TEXT,axis=2); blue=np.all(crop==BLUE,axis=2); white=np.all(crop==WHITE,axis=2)
    qmark=np.zeros_like(white); border=np.zeros_like(white)
    for n,b,pts in comps(white):
      is_q=(b[0]>=100 and b[2]<=190 and b[1]>=55 and (b[2]-b[0])<=80)
      dst=qmark if is_q else border
      for x,y in pts: dst[y,x]=1
    hard=blue|white; env=dilate(hard,1); visible=dilate(text,1)&hard; corridor=text&env
    vals,cnt=np.unique(crop[visible].reshape(-1,4),axis=0,return_counts=True)
    result={
      "schema_version":1,"asset":"C075FB49","queue_index":111,
      "canonical":{"bundle_sha256":sha(zb),"dds_sha256":sha(dds),"decoded_size":list(raw.size),"cell_readable_half_open":list(CELL)},
      "model":{
        "text_fill_pixels":int(text.sum()),"text_fill_bbox":bbox(text),
        "light_blue_pixels":int(blue.sum()),"light_blue_bbox":bbox(blue),
        "question_mark_white_pixels":int(qmark.sum()),"question_mark_white_bbox":bbox(qmark),
        "panel_border_white_pixels":int(border.sum()),
        "hard_protected_visible_pixels":int(hard.sum()),
        "protected_envelope_pixels":int(env.sum()),
        "radius1_visible_conflict_pixels":int(visible.sum()),
        "radius1_visible_conflict_palette":[{"rgba":[int(v) for v in a],"pixels":int(n)} for a,n in zip(vals,cnt)],
        "text_fill_inside_protected_envelope_pixels":int(corridor.sum()),
        "text_fill_inside_protected_envelope_bbox":bbox(corridor)
      },
      "disposition":"PREFLIGHT_ONLY_PROTECTED_ART_MODEL_READY_CLEAN_PLATE_RECONSTRUCTION_REMAINS",
      "candidate_dds_authorized":False,"runtime_validation":"UNTESTED"
    }
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=="__main__": main()
