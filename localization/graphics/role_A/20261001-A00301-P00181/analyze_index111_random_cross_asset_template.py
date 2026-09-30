#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
from PIL import Image
import numpy as np

TARGET_SHA="a8942f076b9c3d8cddd62ba39c84a3b3abea72b2ba19a61a21e9a2bd6f8e8036"
DONOR_SHA="bad9701ac45e4587d8b04afde335951f4857f747ec20fd71fc838be7d86bf364"
BLUE=(103,152,220,255); WHITE=(255,255,255,255)
TARGET_BLUE_ROI=(1690,1420,2010,1610)
DONOR_BLUE_ROI=(1570,850,1920,1100)
TARGET_WHITE_ROI=(1800,1470,1910,1580)
DONOR_WHITE_ROI=(1650,900,1830,1070)
VALIDATION_Y_MIN=1500
BLUE_XFORM=(0.755,0.675,533.4325,858.425)
WHITE_XFORM=(0.66,0.635,698.3,896.6675)

def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def rgba_readable(p: Path) -> np.ndarray:
    im=Image.open(p).convert("RGBA")
    if im.size != (2048,2048):
        raise SystemExit(f"unexpected size {im.size} for {p}")
    return np.asarray(im.transpose(Image.Transpose.FLIP_TOP_BOTTOM)).copy()

def exact(img: np.ndarray, rgba) -> np.ndarray:
    return np.all(img == np.asarray(rgba,dtype=np.uint8), axis=2)

def largest_component(mask: np.ndarray, roi) -> np.ndarray:
    x0,y0,x1,y1=roi
    sub=mask[y0:y1,x0:x1]
    h,w=sub.shape
    seen=np.zeros_like(sub,dtype=bool)
    best=[]
    for y in range(h):
        for x in range(w):
            if not sub[y,x] or seen[y,x]:
                continue
            stack=[(x,y)]; seen[y,x]=True; pts=[]
            while stack:
                a,b=stack.pop(); pts.append((a,b))
                for nx,ny in ((a+1,b),(a-1,b),(a,b+1),(a,b-1)):
                    if 0<=nx<w and 0<=ny<h and sub[ny,nx] and not seen[ny,nx]:
                        seen[ny,nx]=True; stack.append((nx,ny))
            if len(pts)>len(best): best=pts
    out=np.zeros_like(mask,dtype=bool)
    for x,y in best: out[y0+y,x0+x]=True
    return out

def transform_mask(mask: np.ndarray, xform) -> np.ndarray:
    sx,sy,tx,ty=xform
    y,x=np.where(mask)
    xx=np.rint(x*sx+tx).astype(np.int32)
    yy=np.rint(y*sy+ty).astype(np.int32)
    ok=(xx>=0)&(xx<mask.shape[1])&(yy>=0)&(yy<mask.shape[0])
    out=np.zeros_like(mask,dtype=bool)
    out[yy[ok],xx[ok]]=True
    return out

def dilate(m: np.ndarray, r: int) -> np.ndarray:
    if r == 0: return m.copy()
    h,w=m.shape; out=np.zeros_like(m,dtype=bool)
    for dy in range(-r,r+1):
        for dx in range(-r,r+1):
            y0=max(0,-dy); y1=min(h,h-dy)
            x0=max(0,-dx); x1=min(w,w-dx)
            out[y0+dy:y1+dy,x0+dx:x1+dx] |= m[y0:y1,x0:x1]
    return out

def metrics(pred: np.ndarray, target: np.ndarray, tol: int) -> dict:
    yy=np.indices(target.shape)[0]
    band=yy>=VALIDATION_Y_MIN
    p=pred&band; t=target&band
    pn=int(p.sum()); tn=int(t.sum())
    ph=int((p & dilate(target,tol)).sum())
    th=int((t & dilate(pred,tol)).sum())
    precision=ph/pn if pn else 0.0
    recall=th/tn if tn else 0.0
    f1=(2*precision*recall/(precision+recall)) if precision+recall else 0.0
    return {
        "tolerance_chebyshev_px":tol,
        "predicted_pixels":pn,
        "target_visible_pixels":tn,
        "predicted_supported_pixels":ph,
        "target_supported_pixels":th,
        "precision":precision,
        "recall":recall,
        "f1":f1,
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("target_c075")
    ap.add_argument("donor_411")
    args=ap.parse_args()
    tp=Path(args.target_c075); dp=Path(args.donor_411)
    if sha256(tp)!=TARGET_SHA: raise SystemExit("C075 target SHA mismatch")
    if sha256(dp)!=DONOR_SHA: raise SystemExit("411 donor SHA mismatch")
    t=rgba_readable(tp); d=rgba_readable(dp)
    tblue=largest_component(exact(t,BLUE),TARGET_BLUE_ROI)
    dblue=largest_component(exact(d,BLUE),DONOR_BLUE_ROI)
    twhite=largest_component(exact(t,WHITE),TARGET_WHITE_ROI)
    dwhite=largest_component(exact(d,WHITE),DONOR_WHITE_ROI)
    pblue=transform_mask(dblue,BLUE_XFORM)
    pwhite=transform_mask(dwhite,WHITE_XFORM)
    out={
      "schema":"outrun-index111-random-cross-asset-template-replay-v1",
      "target_sha256":TARGET_SHA,
      "donor_sha256":DONOR_SHA,
      "coordinate_space":"readable/display after raw mirror_y -> flip_y",
      "validation_y_min":VALIDATION_Y_MIN,
      "light_blue_component":{
        "target_visible_pixels":int(tblue.sum()),
        "donor_pixels":int(dblue.sum()),
        "transform":{"sx":BLUE_XFORM[0],"sy":BLUE_XFORM[1],"tx":BLUE_XFORM[2],"ty":BLUE_XFORM[3]},
        "metrics_exact":metrics(pblue,tblue,0),
        "metrics_1px":metrics(pblue,tblue,1),
      },
      "question_mark_white_component":{
        "target_visible_pixels":int(twhite.sum()),
        "donor_pixels":int(dwhite.sum()),
        "transform":{"sx":WHITE_XFORM[0],"sy":WHITE_XFORM[1],"tx":WHITE_XFORM[2],"ty":WHITE_XFORM[3]},
        "metrics_exact":metrics(pwhite,twhite,0),
        "metrics_2px":metrics(pwhite,twhite,2),
      },
      "interpretation":"Cross-asset English HD source provides a strong protected-art geometry template, but the white question-mark mapping is not exact enough to authorize a clean plate automatically. Use these transforms only as a reconstruction constraint, preserve target-visible protected pixels exactly, and require independent CLEAN_PLATE QA before Korean render.",
      "clean_plate_authorized":False,
      "candidate_dds_authorized":False,
      "runtime_validation":"UNTESTED"
    }
    print(json.dumps(out,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
