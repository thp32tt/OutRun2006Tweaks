#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, io, json
from pathlib import Path
import cv2
import numpy as np
from PIL import Image

TARGET_SHA="a8942f076b9c3d8cddd62ba39c84a3b3abea72b2ba19a61a21e9a2bd6f8e8036"
DONOR_SHA="bad9701ac45e4587d8b04afde335951f4857f747ec20fd71fc838be7d86bf364"
RED=(196,0,0,255); GREEN=(0,150,0,255)
T_FILL=(255,150,0,255); N_FILL=(255,243,112,255)
TBOX=(40,1170,245,1305); NBOX=(375,1170,600,1305)
T_CELL=TBOX; N_CELL=NBOX
T_LIGHT=(228,136,136,255); N_LIGHT=(136,206,136,255)
GUARD=4; MAXGAP=64

def sha(b): return hashlib.sha256(b).hexdigest()
def load(b): return np.asarray(Image.open(io.BytesIO(b)).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)).copy()
def exact(a,c): return np.all(a==np.array(c,dtype=np.uint8),axis=2)
def dil(m,r): return cv2.dilate(m.astype(np.uint8),np.ones((2*r+1,2*r+1),np.uint8)).astype(bool)
def textmask(img,fill,roi,r=6):
    x0,y0,x1,y1=roi; out=np.zeros(img.shape[:2],bool)
    out[y0:y1,x0:x1]=dil(exact(img[y0:y1,x0:x1],fill),r); return out
def largest(mask,roi=None):
    if roi: x0,y0,x1,y1=roi; sub=mask[y0:y1,x0:x1].astype(np.uint8)
    else: x0=y0=0; sub=mask.astype(np.uint8)
    n,lab,st,_=cv2.connectedComponentsWithStats(sub,8)
    i=1+int(np.argmax(st[1:,cv2.CC_STAT_AREA])); x,y,w,h,area=st[i]
    return (x0+x,y0+y,x0+x+w,y0+y+h,area)
def tr(src,dst):
    sx=(dst[2]-dst[0])/(src[2]-src[0]); sy=(dst[3]-dst[1])/(src[3]-src[1])
    return sx,sy,dst[0]-src[0]*sx,dst[1]-src[1]*sy
def unresolved(target,donor,color,droi,troi,fill,sroi,sfill,sdx):
    tb=largest(exact(target,color))[:4]; db=largest(exact(donor,color),droi)[:4]; sx,sy,tx,ty=tr(db,tb)
    tm=textmask(target,fill,troi); dm=textmask(donor,fill,droi); sm=textmask(target,sfill,sroi)
    out=np.zeros(tm.shape,bool)
    for y,x in zip(*np.where(tm)):
        xd=int(round((x-tx)/sx)); yd=int(round((y-ty)/sy))
        if 0<=yd<2048 and 0<=xd<2048 and not dm[yd,xd]: continue
        xs=x+sdx
        if 0<=xs<2048 and not sm[y,xs]: continue
        out[y,x]=1
    return out
def cellmask(img,cell,pred):
    x0,y0,x1,y1=cell; out=np.zeros(img.shape[:2],bool); out[y0:y1,x0:x1]=pred(img[y0:y1,x0:x1]); return out
def shift(m,dx):
    out=np.zeros_like(m); y,x=np.where(m); xx=x+dx; ok=(xx>=0)&(xx<m.shape[1]); out[y[ok],xx[ok]]=1; return out
def guards(img):
    def nw(s):
        m=(s[:,:,3]>=200)&(s[:,:,:3].min(2)>=240); m[:60,:]=0; return m
    tw=cellmask(img,T_CELL,nw); nw_=cellmask(img,N_CELL,nw)
    tl=cellmask(img,T_CELL,lambda s: exact(s,T_LIGHT)); nl=cellmask(img,N_CELL,lambda s: exact(s,N_LIGHT))
    return tw|shift(nw_,-360)|tl, nw_|shift(tw,360)|nl
def bounded(img,un,color):
    base=exact(img,color); out=np.zeros_like(un)
    H,W=un.shape
    for y,x in zip(*np.where(un)):
        l=np.where(base[y,max(0,x-MAXGAP):x])[0]; r=np.where(base[y,x+1:min(W,x+MAXGAP+1)])[0]
        h=False; v=False
        if len(l) and len(r):
            L=max(0,x-MAXGAP)+int(l[-1]); R=x+1+int(r[0]); q=np.arange(L+1,R)
            h=bool(np.all(base[y,q]|un[y,q]))
        u=np.where(base[max(0,y-MAXGAP):y,x])[0]; d=np.where(base[y+1:min(H,y+MAXGAP+1),x])[0]
        if len(u) and len(d):
            U=max(0,y-MAXGAP)+int(u[-1]); D=y+1+int(d[0]); q=np.arange(U+1,D)
            v=bool(np.all(base[q,x]|un[q,x]))
        out[y,x]=h and v
    return out
def bbox(m):
    y,x=np.where(m)
    return None if not len(x) else [int(x.min()),int(y.min()),int(x.max()+1),int(y.max()+1)]

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("target"); ap.add_argument("donor411"); ap.add_argument("--out",required=True); a=ap.parse_args()
    tb=Path(a.target).read_bytes(); db=Path(a.donor411).read_bytes()
    if sha(tb)!=TARGET_SHA or sha(db)!=DONOR_SHA: raise SystemExit("IDENTITY_FAIL")
    t=load(tb); d=load(db)
    ut=unresolved(t,d,RED,(780,820,1180,1110),TBOX,T_FILL,NBOX,N_FILL,360)
    un=unresolved(t,d,GREEN,(1180,820,1570,1110),NBOX,N_FILL,TBOX,T_FILL,-335)
    if (int(ut.sum()),int(un.sum()))!=(3689,3300): raise SystemExit("A00309_FINGERPRINT_FAIL")
    bt=bounded(t,ut,RED); bn=bounded(t,un,GREEN); gt,gn=guards(t)
    k=np.ones((2*GUARD+1,2*GUARD+1),np.uint8); gt=cv2.dilate(gt.astype(np.uint8),k).astype(bool); gn=cv2.dilate(gn.astype(np.uint8),k).astype(bool)
    at=bt&~gt; an=bn&~gn
    p=t.copy(); p[at]=np.array(RED,np.uint8); p[an]=np.array(GREEN,np.uint8)
    ch=np.any(p!=t,2); ac=at|an
    out={
      "schema_version":16,
      "schema":"outrun-a00320-index111-tuned-normal-solid-core-reconstruction-proposal-v1",
      "task_id":"LOCALIZATION-LOCALIZATION_A-00320","wave_id":"P00196","asset":"C075FB49","queue_index":111,
      "coordinate_space":"readable/display after raw mirror_y -> flip_y",
      "source_identity":{"target_sha256":TARGET_SHA,"donor411_sha256":DONOR_SHA,"canvas":[2048,2048],"format":"RGBA32","mip_count":1},
      "method":{"scope":"TUNED_NORMAL_ONLY_RANDOM_UNTOUCHED","max_axis_gap_px":MAXGAP,"protected_guard_dilation_px":GUARD,
        "bounded_background_rule":"inside C-accepted A00309 unresolved mask; exact panel base color encloses pixel on both axes; every intervening non-base pixel also belongs to that unresolved mask",
        "protected_guard":"A00271 sibling-registered near-white protected-car core plus exact per-panel light-panel palette","candidate_pixels_used":False,
        "clean_plate_status":"PROPOSAL_ONLY_REQUIRES_INDEPENDENT_C_QA"},
      "elements":{
        "tuned_setting":{"prior_unresolved_pixels":int(ut.sum()),"bounded_biaxial_pixels_before_guard":int(bt.sum()),"excluded_by_protected_guard":int(np.logical_and(bt,gt).sum()),"proposal_resolved_pixels":int(at.sum()),"proposal_actual_changed_pixels":int((ch&at).sum()),"remaining_unresolved_pixels":int(ut.sum()-at.sum()),"proposal_bbox":bbox(at),"actual_changed_bbox":bbox(ch&at),"proposal_overlap_protected_guard_pixels":int(np.logical_and(at,gt).sum())},
        "normal_setting":{"prior_unresolved_pixels":int(un.sum()),"bounded_biaxial_pixels_before_guard":int(bn.sum()),"excluded_by_protected_guard":int((bn&gn).sum()),"proposal_resolved_pixels":int(an.sum()),"proposal_actual_changed_pixels":int((ch&an).sum()),"remaining_unresolved_pixels":int(un.sum()-an.sum()),"proposal_bbox":bbox(an),"actual_changed_bbox":bbox(ch&an),"proposal_overlap_protected_guard_pixels":int((an&gn).sum())},
        "random":{"prior_unresolved_pixels":5192,"proposal_resolved_pixels":0,"remaining_unresolved_pixels":5192,"disposition":"UNCHANGED_FAIL_CLOSED_PROTECTED_QUESTION_MARK"}},
      "aggregate":{"prior_unresolved_pixels":12181,"proposal_resolved_pixels":int(at.sum()+an.sum()),"proposal_actual_changed_pixels":int(ch.sum()),"remaining_unresolved_pixels":int(12181-at.sum()-an.sum()),"outside_accepted_mask_changed_pixels":int((ch&~ac).sum()),"alpha_changed_pixels":int(np.sum(t[:,:,3]!=p[:,:,3])),"protected_guard_overlap_pixels":int(np.logical_and(at,gt).sum()+(an&gn).sum())},
      "readiness_after":"PREFLIGHT_ONLY_TUNED_NORMAL_SOLID_CORE_RECONSTRUCTION_PROPOSAL_READY_FOR_INDEPENDENT_C_CLEANPLATE_QA__RANDOM_AND_TUNED_NORMAL_FRINGE_REMAINDERS_STILL_HOLD",
      "candidate_dds_authorized":False,"candidate_dds_modified":False,"runtime_validation":"UNTESTED"}
    if (out["elements"]["tuned_setting"]["proposal_resolved_pixels"],out["elements"]["normal_setting"]["proposal_resolved_pixels"],out["aggregate"]["proposal_actual_changed_pixels"],out["aggregate"]["remaining_unresolved_pixels"],out["aggregate"]["outside_accepted_mask_changed_pixels"],out["aggregate"]["protected_guard_overlap_pixels"])!=(1719,2241,1718,8221,0,0): raise SystemExit("PROPOSAL_FINGERPRINT_FAIL")
    Path(a.out).write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(out,ensure_ascii=False,indent=2))
if __name__=="__main__": main()
