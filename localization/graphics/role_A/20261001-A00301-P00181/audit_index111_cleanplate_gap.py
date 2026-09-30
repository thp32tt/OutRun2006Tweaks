#!/usr/bin/env python3
"""C075FB49 index111 source-only CLEAN_PLATE gap audit (A00301/P00181)."""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
import numpy as np
from PIL import Image

SRC="a8942f076b9c3d8cddd62ba39c84a3b3abea72b2ba19a61a21e9a2bd6f8e8036"
TBOX=(40,1170,245,1305); NBOX=(375,1170,600,1305); RBOX=(1710,1410,2008,1515)
T=(255,150,0,255); N=(255,243,112,255); RT=(245,247,247,255); BLUE=(103,152,220,255); WHITE=(255,255,255,255)

def mask(a,c): return np.all(a==np.array(c,dtype=np.uint8),axis=2)
def dil(m,r=1):
    h,w=m.shape; out=np.zeros_like(m,bool)
    for dy in range(-r,r+1):
      for dx in range(-r,r+1):
        y0,y1=max(0,-dy),min(h,h-dy); x0,x1=max(0,-dx),min(w,w-dx)
        out[y0+dy:y1+dy,x0+dx:x1+dx] |= m[y0:y1,x0:x1]
    return out
def box(m):
    y,x=np.where(m)
    return None if not len(x) else [int(x.min()),int(y.min()),int(x.max()+1),int(y.max()+1)]
def comps(m):
    h,w=m.shape; seen=np.zeros_like(m,bool); out=[]
    for y in range(h):
      for x in range(w):
        if not m[y,x] or seen[y,x]: continue
        q=[(x,y)]; seen[y,x]=1; pts=[]
        while q:
          a,b=q.pop(); pts.append((a,b))
          for xx,yy in ((a+1,b),(a-1,b),(a,b+1),(a,b-1)):
            if 0<=xx<w and 0<=yy<h and m[yy,xx] and not seen[yy,xx]:
              seen[yy,xx]=1; q.append((xx,yy))
        xs=[p[0] for p in pts]; ys=[p[1] for p in pts]
        out.append((len(pts),[min(xs),min(ys),max(xs)+1,max(ys)+1],pts))
    return sorted(out,reverse=True)
def crop(a,b):
    l,t,r,bt=b; return a[t:bt,l:r].copy()

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("source_dds"); ap.add_argument("--out"); a=ap.parse_args()
    p=Path(a.source_dds); digest=hashlib.sha256(p.read_bytes()).hexdigest()
    if digest!=SRC: raise SystemExit("FAIL source identity")
    im=Image.open(p).convert("RGBA")
    if im.size!=(2048,2048): raise SystemExit("FAIL canvas")
    rd=np.asarray(im.transpose(Image.Transpose.FLIP_TOP_BOTTOM)).copy()
    t,n,r=crop(rd,TBOX),crop(rd,NBOX),crop(rd,RBOX)
    tt,nt=mask(t,T),mask(n,N)
    tc=(t[:,:,3]>=200)&(t[:,:,:3].min(2)>=240); nc=(n[:,:,3]>=200)&(n[:,:,:3].min(2)>=240)
    tc[:60]=False; nc[:60]=False
    tc,nc,tt,nt=tc[:,:200],nc[:,25:225],tt[:,:200],nt[:,25:225]
    inter,union=tc&nc,tc|nc; shared=tt&nt
    r1,r2=shared&dil(union,1),shared&dil(union,2)
    accepted=(int(tc.sum()),int(nc.sum()),int(inter.sum()),int(union.sum()),int(shared.sum()),int(r1.sum()))
    if accepted!=(1517,1392,1378,1531,2971,27): raise SystemExit(f"FAIL sibling fingerprint {accepted}")
    rt,rb,rw=mask(r,RT),mask(r,BLUE),mask(r,WHITE)
    qmark=np.zeros_like(rw); border=np.zeros_like(rw)
    for _,b,pts in comps(rw):
      dst=qmark if b[0]>=100 and b[2]<=190 and b[1]>=55 and (b[2]-b[0])<=80 else border
      for x,y in pts: dst[y,x]=1
    hard=rb|rw; env=dil(hard,1); visible=dil(rt,1)&hard; corridor=rt&env
    rm=(int(rt.sum()),int(rb.sum()),int(qmark.sum()),int(border.sum()),int(hard.sum()),int(env.sum()),int(visible.sum()),int(corridor.sum()))
    if rm!=(3027,1328,453,1591,3372,5169,30,31): raise SystemExit(f"FAIL random fingerprint {rm}")
    vals,cnt=np.unique(r[visible].reshape(-1,4),axis=0,return_counts=True)
    out={"schema_version":15,"task_id":"LOCALIZATION-LOCALIZATION_A-00301","wave_id":"P00181","queue_index":111,"asset":"C075FB49",
      "source":{"sha256":digest,"decoded_size":[2048,2048],"readable_transform":"flip_y"},
      "tuned_normal":{"registration":[25,0],"core":[1517,1392,1378,1531],"jaccard":1378/1531,"shared_english":2971,
        "shared_english_in_protected_r1":27,"r1_bbox":box(r1),"shared_english_in_protected_r2":int(r2.sum()),"r2_bbox":box(r2)},
      "random":{"text":3027,"light_blue":1328,"question_white":453,"border_white":1591,"hard_protected":3372,"envelope_r1":5169,
        "visible_conflict":30,"palette":[{"rgba":[int(v) for v in z],"pixels":int(c)} for z,c in zip(vals,cnt)],"text_in_envelope":31,"corridor_bbox":box(corridor)},
      "clean_plate":"HOLD_EXACT_UNOBSERVABLE_PROTECTED_CORRIDOR","candidate_dds_authorized":False,"runtime_validation":"UNTESTED"}
    s=json.dumps(out,ensure_ascii=False,indent=2)+"\n"
    if a.out: Path(a.out).write_text(s,encoding="utf-8")
    print(s,end="")
if __name__=="__main__": main()
