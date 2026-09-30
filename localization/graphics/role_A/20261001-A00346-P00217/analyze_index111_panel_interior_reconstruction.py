#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, io, json
from pathlib import Path
import cv2
import numpy as np
from PIL import Image

TARGET_SHA="a8942f076b9c3d8cddd62ba39c84a3b3abea72b2ba19a61a21e9a2bd6f8e8036"
DONOR_SHA="bad9701ac45e4587d8b04afde335951f4857f747ec20fd71fc838be7d86bf364"
RED=(196,0,0,255)
GREEN=(0,150,0,255)
T_FILL=(255,150,0,255)
N_FILL=(255,243,112,255)
TBOX=(40,1170,245,1305)
NBOX=(375,1170,600,1305)
T_LIGHT=(228,136,136,255)
N_LIGHT=(136,206,136,255)
T_ROI=(20,1190,340,1370)
N_ROI=(380,1190,700,1370)
GUARD=4
MAXGAP=64

def sha(b): return hashlib.sha256(b).hexdigest()
def load(b):
    return np.asarray(Image.open(io.BytesIO(b)).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)).copy()
def exact(a,c): return np.all(a==np.array(c,dtype=np.uint8),axis=2)
def dil(m,r): return cv2.dilate(m.astype(np.uint8),np.ones((2*r+1,2*r+1),np.uint8)).astype(bool)
def textmask(img,fill,roi,r=6):
    x0,y0,x1,y1=roi
    out=np.zeros(img.shape[:2],bool)
    out[y0:y1,x0:x1]=dil(exact(img[y0:y1,x0:x1],fill),r)
    return out
def largest(mask,roi=None):
    if roi:
        x0,y0,x1,y1=roi
        sub=mask[y0:y1,x0:x1].astype(np.uint8)
    else:
        x0=y0=0
        sub=mask.astype(np.uint8)
    n,lab,st,_=cv2.connectedComponentsWithStats(sub,8)
    if n<=1: raise RuntimeError("NO_COMPONENT")
    i=1+int(np.argmax(st[1:,cv2.CC_STAT_AREA]))
    x,y,w,h,area=st[i]
    return (x0+x,y0+y,x0+x+w,y0+y+h,area)
def tr(src,dst):
    sx=(dst[2]-dst[0])/(src[2]-src[0])
    sy=(dst[3]-dst[1])/(src[3]-src[1])
    return sx,sy,dst[0]-src[0]*sx,dst[1]-src[1]*sy
def unresolved(target,donor,color,droi,troi,fill,sroi,sfill,sdx):
    tb=largest(exact(target,color))[:4]
    db=largest(exact(donor,color),droi)[:4]
    sx,sy,tx,ty=tr(db,tb)
    tm=textmask(target,fill,troi)
    dm=textmask(donor,fill,droi)
    sm=textmask(target,sfill,sroi)
    out=np.zeros(tm.shape,bool)
    for y,x in zip(*np.where(tm)):
        xd=int(round((x-tx)/sx)); yd=int(round((y-ty)/sy))
        if 0<=yd<2048 and 0<=xd<2048 and not dm[yd,xd]:
            continue
        xs=x+sdx
        if 0<=xs<2048 and not sm[y,xs]:
            continue
        out[y,x]=1
    return out
def cellmask(img,cell,pred):
    x0,y0,x1,y1=cell
    out=np.zeros(img.shape[:2],bool)
    out[y0:y1,x0:x1]=pred(img[y0:y1,x0:x1])
    return out
def shift(m,dx):
    out=np.zeros_like(m)
    y,x=np.where(m)
    xx=x+dx
    ok=(xx>=0)&(xx<m.shape[1])
    out[y[ok],xx[ok]]=1
    return out
def guards(img):
    def nw(s):
        m=(s[:,:,3]>=200)&(s[:,:,:3].min(2)>=240)
        m[:60,:]=0
        return m
    tw=cellmask(img,TBOX,nw)
    nw_=cellmask(img,NBOX,nw)
    tl=cellmask(img,TBOX,lambda s: exact(s,T_LIGHT))
    nl=cellmask(img,NBOX,lambda s: exact(s,N_LIGHT))
    return tw|shift(nw_,-360)|tl, nw_|shift(tw,360)|nl
def bounded(img,un,color):
    base=exact(img,color)
    out=np.zeros_like(un)
    H,W=un.shape
    for y,x in zip(*np.where(un)):
        l=np.where(base[y,max(0,x-MAXGAP):x])[0]
        r=np.where(base[y,x+1:min(W,x+MAXGAP+1)])[0]
        h=False
        v=False
        if len(l) and len(r):
            L=max(0,x-MAXGAP)+int(l[-1])
            R=x+1+int(r[0])
            q=np.arange(L+1,R)
            h=bool(np.all(base[y,q]|un[y,q]))
        u=np.where(base[max(0,y-MAXGAP):y,x])[0]
        d=np.where(base[y+1:min(H,y+MAXGAP+1),x])[0]
        if len(u) and len(d):
            U=max(0,y-MAXGAP)+int(u[-1])
            D=y+1+int(d[0])
            q=np.arange(U+1,D)
            v=bool(np.all(base[q,x]|un[q,x]))
        out[y,x]=h and v
    return out
def external_panel_interior(img,color,roi):
    x0,y0,x1,y1=roi
    exact_sub=exact(img[y0:y1,x0:x1],color).astype(np.uint8)
    n,lab,st,_=cv2.connectedComponentsWithStats(exact_sub,8)
    if n<=1: raise RuntimeError("NO_PANEL_COMPONENT")
    i=1+int(np.argmax(st[1:,cv2.CC_STAT_AREA]))
    component=(lab==i).astype(np.uint8)
    contours,_=cv2.findContours(component,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    if not contours: raise RuntimeError("NO_EXTERNAL_CONTOUR")
    contour=max(contours,key=cv2.contourArea)
    filled=np.zeros_like(component)
    cv2.drawContours(filled,[contour],-1,1,thickness=cv2.FILLED)
    out=np.zeros(img.shape[:2],bool)
    out[y0:y1,x0:x1]=filled.astype(bool)
    return out
def bbox(m):
    y,x=np.where(m)
    return None if not len(x) else [int(x.min()),int(y.min()),int(x.max()+1),int(y.max()+1)]

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("target")
    ap.add_argument("donor411")
    ap.add_argument("--out",required=True)
    a=ap.parse_args()
    tb=Path(a.target).read_bytes()
    db=Path(a.donor411).read_bytes()
    if sha(tb)!=TARGET_SHA or sha(db)!=DONOR_SHA:
        raise SystemExit("IDENTITY_FAIL")
    t=load(tb)
    d=load(db)

    # Reproduce the exact A00320 accepted masks first.
    ut=unresolved(t,d,RED,(780,820,1180,1110),TBOX,T_FILL,NBOX,N_FILL,360)
    un=unresolved(t,d,GREEN,(1180,820,1570,1110),NBOX,N_FILL,TBOX,T_FILL,-335)
    if (int(ut.sum()),int(un.sum()))!=(3689,3300):
        raise SystemExit("A00309_FINGERPRINT_FAIL")
    bt=bounded(t,ut,RED)
    bn=bounded(t,un,GREEN)
    gt,gn=guards(t)
    k=np.ones((2*GUARD+1,2*GUARD+1),np.uint8)
    gt=cv2.dilate(gt.astype(np.uint8),k).astype(bool)
    gn=cv2.dilate(gn.astype(np.uint8),k).astype(bool)
    a20t=bt&~gt
    a20n=bn&~gn
    if (int(a20t.sum()),int(a20n.sum()))!=(1719,2241):
        raise SystemExit("A00320_FINGERPRINT_FAIL")

    rt=ut&~a20t
    rn=un&~a20n
    if (int(rt.sum()),int(rn.sum()))!=(1970,1059):
        raise SystemExit("A00320_REMAINDER_FAIL")

    # Stage 2: accept only panel interior proven from the external contour of
    # the largest exact base-color component, still excluding protected guard.
    ti=external_panel_interior(t,RED,T_ROI)
    ni=external_panel_interior(t,GREEN,N_ROI)
    s2t=rt&ti&~gt
    s2n=rn&ni&~gn

    p=t.copy()
    p[a20t|s2t]=np.array(RED,np.uint8)
    p[a20n|s2n]=np.array(GREEN,np.uint8)
    ch=np.any(p!=t,2)
    accepted=a20t|a20n|s2t|s2n
    r2t=rt&~s2t
    r2n=rn&~s2n

    out={
      "schema_version":16,
      "schema":"outrun-a00346-index111-panel-interior-source-only-reconstruction-v1",
      "task_id":"LOCALIZATION-LOCALIZATION_A-00346",
      "wave_id":"P00217",
      "asset":"C075FB49",
      "queue_index":111,
      "coordinate_space":"readable/display after raw mirror_y -> flip_y",
      "source_identity":{"target_sha256":TARGET_SHA,"donor411_sha256":DONOR_SHA,"canvas":[2048,2048],"format":"RGBA32","mip_count":1},
      "method":{
        "scope":"TUNED_NORMAL_REMAINDER_ONLY_RANDOM_UNTOUCHED",
        "tuned_analysis_roi":list(T_ROI),
        "normal_analysis_roi":list(N_ROI),
        "panel_interior_rule":"largest exact base-color connected component inside conservative ROI; fill RETR_EXTERNAL contour only; intersect with A00320 remainder and exclude unchanged protected-art guard",
        "protected_guard":"A00320/A00271 sibling-registered near-white car core plus exact panel-light palette, 4px dilated",
        "candidate_pixels_used":False,
        "clean_plate_status":"NOT_APPROVED_PREFLIGHT_ONLY"
      },
      "elements":{
        "tuned_setting":{
          "prior_unresolved_pixels":int(rt.sum()),
          "new_panel_interior_proposal_pixels":int(s2t.sum()),
          "new_actual_changed_pixels":int((ch&s2t).sum()),
          "new_proposal_bbox":bbox(s2t),
          "remaining_unresolved_pixels":int(r2t.sum()),
          "remaining_bbox":bbox(r2t),
          "protected_guard_overlap_pixels":int(np.logical_and(s2t,gt).sum())
        },
        "normal_setting":{
          "prior_unresolved_pixels":int(rn.sum()),
          "new_panel_interior_proposal_pixels":int(s2n.sum()),
          "new_actual_changed_pixels":int((ch&s2n).sum()),
          "new_proposal_bbox":bbox(s2n),
          "remaining_unresolved_pixels":int(r2n.sum()),
          "remaining_bbox":bbox(r2n),
          "protected_guard_overlap_pixels":int(np.logical_and(s2n,gn).sum())
        },
        "random":{
          "prior_unresolved_pixels":5192,
          "new_panel_interior_proposal_pixels":0,
          "new_actual_changed_pixels":0,
          "remaining_unresolved_pixels":5192,
          "disposition":"UNCHANGED_FAIL_CLOSED_PROTECTED_QUESTION_MARK"
        }
      },
      "aggregate":{
        "prior_c_accepted_proposal_resolved_pixels":3960,
        "prior_c_accepted_actual_changed_pixels":1718,
        "new_panel_interior_proposal_pixels":int(s2t.sum()+s2n.sum()),
        "new_panel_interior_actual_changed_pixels":int((ch&(s2t|s2n)).sum()),
        "combined_proposal_resolved_pixels":int(a20t.sum()+a20n.sum()+s2t.sum()+s2n.sum()),
        "combined_actual_changed_pixels":int(ch.sum()),
        "remaining_unresolved_pixels":int(r2t.sum()+r2n.sum()+5192),
        "outside_accepted_mask_changed_pixels":int((ch&~accepted).sum()),
        "alpha_changed_pixels":int(np.sum(t[:,:,3]!=p[:,:,3])),
        "protected_guard_overlap_pixels":int(np.logical_and(s2t,gt).sum()+np.logical_and(s2n,gn).sum())
      },
      "readiness_after":"PREFLIGHT_ONLY__TUNED_NORMAL_PANEL_INTERIOR_RECONSTRUCTION_ADVANCED__5734_UNRESOLVED__RANDOM_AND_PROTECTED_FRINGE_HOLD",
      "candidate_dds_authorized":False,
      "candidate_dds_modified":False,
      "runtime_validation":"UNTESTED"
    }
    fp=(out["elements"]["tuned_setting"]["new_panel_interior_proposal_pixels"],
        out["elements"]["normal_setting"]["new_panel_interior_proposal_pixels"],
        out["aggregate"]["new_panel_interior_actual_changed_pixels"],
        out["aggregate"]["remaining_unresolved_pixels"],
        out["aggregate"]["outside_accepted_mask_changed_pixels"],
        out["aggregate"]["alpha_changed_pixels"],
        out["aggregate"]["protected_guard_overlap_pixels"])
    if fp!=(1507,980,2223,5734,0,0,0):
        raise SystemExit("A00346_FINGERPRINT_FAIL: "+repr(fp))
    Path(a.out).write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(out,ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
