#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, io, json
from pathlib import Path
import cv2
import numpy as np
from PIL import Image

TARGET_SHA='a8942f076b9c3d8cddd62ba39c84a3b3abea72b2ba19a61a21e9a2bd6f8e8036'
D411_SHA='bad9701ac45e4587d8b04afde335951f4857f747ec20fd71fc838be7d86bf364'
D53_SHA='cfed1de58cefd8c235fc464e27058439ffd26427294a3bce17192e584679426a'
RED=(196,0,0,255); GREEN=(0,150,0,255); PANEL=(0,79,159,255)
T_FILL=(255,150,0,255); N_FILL=(255,243,112,255); R_FILL=(245,247,247,255)
LIGHT_BLUE=(103,152,220,255); WHITE=(255,255,255,255)
TBOX=(40,1170,245,1305); NBOX=(375,1170,600,1305); RBOX=(1710,1410,2008,1515)
T_LIGHT=(228,136,136,255); N_LIGHT=(136,206,136,255)
T_ROI=(20,1190,340,1370); N_ROI=(380,1190,700,1370); RANDOM_ROI=(1680,1380,2030,1620)
GUARD=4; MAXGAP=64

def sha(b): return hashlib.sha256(b).hexdigest()
def load(b): return np.asarray(Image.open(io.BytesIO(b)).convert('RGBA').transpose(Image.Transpose.FLIP_TOP_BOTTOM)).copy()
def exact(a,c): return np.all(a==np.array(c,dtype=np.uint8),axis=2)
def dil(m,r): return cv2.dilate(m.astype(np.uint8),np.ones((2*r+1,2*r+1),np.uint8)).astype(bool)
def bbox(m):
    y,x=np.where(m)
    return None if not len(x) else [int(x.min()),int(y.min()),int(x.max()+1),int(y.max()+1)]
def mask_sha(m): return hashlib.sha256(np.packbits(m.reshape(-1)).tobytes()).hexdigest()
def textmask(img,fill,roi,r=6):
    x0,y0,x1,y1=roi; out=np.zeros(img.shape[:2],bool)
    out[y0:y1,x0:x1]=dil(exact(img[y0:y1,x0:x1],fill),r); return out
def largest(mask,roi=None):
    if roi:
        x0,y0,x1,y1=roi; sub=mask[y0:y1,x0:x1].astype(np.uint8)
    else:
        x0=y0=0; sub=mask.astype(np.uint8)
    n,lab,st,_=cv2.connectedComponentsWithStats(sub,8)
    if n<=1: raise RuntimeError('NO_COMPONENT')
    i=1+int(np.argmax(st[1:,cv2.CC_STAT_AREA])); x,y,w,h,area=st[i]
    return (x0+x,y0+y,x0+x+w,y0+y+h,area)
def tr(src,dst):
    sx=(dst[2]-dst[0])/(src[2]-src[0]); sy=(dst[3]-dst[1])/(src[3]-src[1])
    return sx,sy,dst[0]-src[0]*sx,dst[1]-src[1]*sy
def inv_map(x,y,t):
    sx,sy,tx,ty=t; return int(round((x-tx)/sx)),int(round((y-ty)/sy))
def unresolved_tn(target,donor,color,droi,troi,fill,sroi,sfill,sdx):
    tb=largest(exact(target,color))[:4]; db=largest(exact(donor,color),droi)[:4]; tf=tr(db,tb)
    tm=textmask(target,fill,troi); dm=textmask(donor,fill,droi); sm=textmask(target,sfill,sroi)
    out=np.zeros(tm.shape,bool)
    for y,x in zip(*np.where(tm)):
        xd,yd=inv_map(x,y,tf)
        if 0<=yd<2048 and 0<=xd<2048 and not dm[yd,xd]: continue
        xs=x+sdx
        if 0<=xs<2048 and not sm[y,xs]: continue
        out[y,x]=1
    return out
def unresolved_random(target,d411,d53):
    tb=largest(exact(target,PANEL))[:4]
    d1b=largest(exact(d411,PANEL),(1570,820,1930,1110))[:4]
    d2b=largest(exact(d53,PANEL))[:4]
    t1=tr(d1b,tb); t2=tr(d2b,tb)
    tm=textmask(target,R_FILL,RBOX); d1m=textmask(d411,R_FILL,(1570,820,1930,1110)); d2m=textmask(d53,R_FILL,(0,0,2048,2048))
    out=np.zeros(tm.shape,bool)
    for y,x in zip(*np.where(tm)):
        xd,yd=inv_map(x,y,t1)
        if 0<=yd<2048 and 0<=xd<2048 and not d1m[yd,xd]: continue
        x2,y2=inv_map(x,y,t2)
        if 0<=y2<2048 and 0<=x2<2048 and not d2m[y2,x2]: continue
        out[y,x]=1
    return out
def cellmask(img,cell,pred):
    x0,y0,x1,y1=cell; out=np.zeros(img.shape[:2],bool); out[y0:y1,x0:x1]=pred(img[y0:y1,x0:x1]); return out
def shift(m,dx):
    out=np.zeros_like(m); y,x=np.where(m); xx=x+dx; ok=(xx>=0)&(xx<m.shape[1]); out[y[ok],xx[ok]]=1; return out
def guards(img):
    def nw(s):
        m=(s[:,:,3]>=200)&(s[:,:,:3].min(2)>=240); m[:60,:]=0; return m
    tw=cellmask(img,TBOX,nw); nw_=cellmask(img,NBOX,nw)
    tl=cellmask(img,TBOX,lambda s: exact(s,T_LIGHT)); nl=cellmask(img,NBOX,lambda s: exact(s,N_LIGHT))
    return tw|shift(nw_,-360)|tl, nw_|shift(tw,360)|nl
def bounded(img,un,color):
    base=exact(img,color); out=np.zeros_like(un); H,W=un.shape
    for y,x in zip(*np.where(un)):
        l=np.where(base[y,max(0,x-MAXGAP):x])[0]; r=np.where(base[y,x+1:min(W,x+MAXGAP+1)])[0]
        h=v=False
        if len(l) and len(r):
            L=max(0,x-MAXGAP)+int(l[-1]); R=x+1+int(r[0]); q=np.arange(L+1,R); h=bool(np.all(base[y,q]|un[y,q]))
        u=np.where(base[max(0,y-MAXGAP):y,x])[0]; dd=np.where(base[y+1:min(H,y+MAXGAP+1),x])[0]
        if len(u) and len(dd):
            U=max(0,y-MAXGAP)+int(u[-1]); D=y+1+int(dd[0]); q=np.arange(U+1,D); v=bool(np.all(base[q,x]|un[q,x]))
        out[y,x]=h and v
    return out
def external_panel_interior(img,color,roi):
    x0,y0,x1,y1=roi; sub=exact(img[y0:y1,x0:x1],color).astype(np.uint8)
    n,lab,st,_=cv2.connectedComponentsWithStats(sub,8)
    if n<=1: raise RuntimeError('NO_PANEL_COMPONENT')
    i=1+int(np.argmax(st[1:,cv2.CC_STAT_AREA])); component=(lab==i).astype(np.uint8)
    contours,_=cv2.findContours(component,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    contour=max(contours,key=cv2.contourArea); filled=np.zeros_like(component); cv2.drawContours(filled,[contour],-1,1,cv2.FILLED)
    out=np.zeros(img.shape[:2],bool); out[y0:y1,x0:x1]=filled.astype(bool); return out
def convex_hull_mask(img,color,roi):
    x0,y0,x1,y1=roi; sub=exact(img[y0:y1,x0:x1],color)
    yy,xx=np.where(sub)
    if len(xx)<3: raise RuntimeError('INSUFFICIENT_HULL_POINTS')
    pts=np.column_stack([xx,yy]).astype(np.int32); hull=cv2.convexHull(pts)
    hm=np.zeros(sub.shape,np.uint8); cv2.fillConvexPoly(hm,hull,1)
    out=np.zeros(img.shape[:2],bool); out[y0:y1,x0:x1]=hm.astype(bool); return out,len(xx)

def reproduce_a00346(target,d411):
    ut=unresolved_tn(target,d411,RED,(780,820,1180,1110),TBOX,T_FILL,NBOX,N_FILL,360)
    un=unresolved_tn(target,d411,GREEN,(1180,820,1570,1110),NBOX,N_FILL,TBOX,T_FILL,-335)
    if (int(ut.sum()),int(un.sum()))!=(3689,3300): raise SystemExit('A00309_TN_FINGERPRINT_FAIL')
    bt=bounded(target,ut,RED); bn=bounded(target,un,GREEN); gt,gn=guards(target)
    k=np.ones((2*GUARD+1,2*GUARD+1),np.uint8); gt=cv2.dilate(gt.astype(np.uint8),k).astype(bool); gn=cv2.dilate(gn.astype(np.uint8),k).astype(bool)
    a20t=bt&~gt; a20n=bn&~gn
    if (int(a20t.sum()),int(a20n.sum()))!=(1719,2241): raise SystemExit('A00320_FINGERPRINT_FAIL')
    rt=ut&~a20t; rn=un&~a20n
    ti=external_panel_interior(target,RED,T_ROI); ni=external_panel_interior(target,GREEN,N_ROI)
    s2t=rt&ti&~gt; s2n=rn&ni&~gn
    r2t=rt&~s2t; r2n=rn&~s2n
    if (int(s2t.sum()),int(s2n.sum()),int(r2t.sum()),int(r2n.sum()))!=(1507,980,463,79): raise SystemExit('A00346_FINGERPRINT_FAIL')
    return r2t,r2n

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('target'); ap.add_argument('donor411'); ap.add_argument('donor53'); ap.add_argument('--out',required=True); a=ap.parse_args()
    tb=Path(a.target).read_bytes(); d1b=Path(a.donor411).read_bytes(); d2b=Path(a.donor53).read_bytes()
    if (sha(tb),sha(d1b),sha(d2b))!=(TARGET_SHA,D411_SHA,D53_SHA): raise SystemExit('IDENTITY_FAIL')
    target=load(tb); d411=load(d1b); d53=load(d2b)
    r2t,r2n=reproduce_a00346(target,d411)
    rr=unresolved_random(target,d411,d53)
    if int(rr.sum())!=5192: raise SystemExit('A00309_RANDOM_FINGERPRINT_FAIL')
    panel_interior=external_panel_interior(target,PANEL,RANDOM_ROI)
    circle_hull,visible_light_blue=convex_hull_mask(target,LIGHT_BLUE,RANDOM_ROI)
    circle_guard=dil(circle_hull,GUARD)
    white=np.zeros(rr.shape,bool); x0,y0,x1,y1=RANDOM_ROI; white[y0:y1,x0:x1]=exact(target[y0:y1,x0:x1],WHITE)
    white_guard=dil(white,GUARD)
    proposal=rr & panel_interior & ~circle_guard & ~white_guard
    remain=rr & ~proposal
    preview=target.copy(); preview[proposal]=np.array(PANEL,np.uint8)
    changed=np.any(preview!=target,axis=2)
    accepted=proposal
    out={
      'schema_version':30,
      'schema':'outrun-a00366-index111-random-dark-panel-source-only-reconstruction-v1',
      'task_id':'LOCALIZATION-LOCALIZATION_A-00366','wave_id':'P00235','lane':'LOCALIZATION_A','queue_index':111,'asset':'C075FB49',
      'coordinate_space':'readable/display after raw mirror_y -> flip_y',
      'source_identity':{'pinned_release_archive_sha256':'76f85ed2ca27344a4292ac7e010a786579b4eebb1a370c0aa126fcb2b231d958','target_sha256':TARGET_SHA,'donor411_sha256':D411_SHA,'donor53_sha256':D53_SHA,'canvas':[2048,2048],'format':'RGBA32','mip_count':1},
      'accepted_prior':{'c176_a00346_status':'PASS_PREFLIGHT_ONLY_PARTIAL_RECONSTRUCTION_5734_UNRESOLVED','tuned_remaining_pixels':int(r2t.sum()),'normal_remaining_pixels':int(r2n.sum()),'random_remaining_pixels':int(rr.sum()),'aggregate_remaining_pixels':int(r2t.sum()+r2n.sum()+rr.sum())},
      'method':{
        'scope':'RANDOM_REMAINDER_DARK_PANEL_ONLY__TUNED_NORMAL_UNCHANGED',
        'random_analysis_roi':list(RANDOM_ROI),'panel_base_rgba':list(PANEL),'protected_circle_visible_rgba':list(LIGHT_BLUE),'protected_white_rgba':list(WHITE),
        'panel_interior_rule':'fill RETR_EXTERNAL contour of the largest exact dark-panel connected component, then intersect only with the C176-accepted RANDOM unresolved mask',
        'protected_circle_rule':'convex hull of every exact light-blue source pixel in RANDOM_ROI, filled conservatively across text-occluded gaps and dilated 4px before any dark-panel proposal',
        'protected_white_rule':'all exact white source pixels in RANDOM_ROI (question-mark/border family) dilated 4px',
        'fill_rule':'proposed pixels are set only to the exact dark-panel base RGBA; no inferred circle/question-mark reconstruction is attempted',
        'candidate_pixels_used':False,'clean_plate_status':'NOT_APPROVED_PREFLIGHT_ONLY'
      },
      'random':{
        'prior_unresolved_pixels':int(rr.sum()),'visible_light_blue_source_pixels':int(visible_light_blue),'circle_hull_pixels':int(circle_hull.sum()),'circle_guard_pixels':int(circle_guard.sum()),
        'exact_white_source_pixels_in_roi':int(white.sum()),'white_guard_pixels':int(white_guard.sum()),'panel_interior_pixels':int(panel_interior.sum()),
        'new_dark_panel_proposal_pixels':int(proposal.sum()),'new_actual_changed_pixels':int((changed&proposal).sum()),'proposal_bbox':bbox(proposal),'actual_changed_bbox':bbox(changed&proposal),
        'remaining_unresolved_pixels':int(remain.sum()),'remaining_bbox':bbox(remain),'proposal_circle_guard_overlap_pixels':int((proposal&circle_guard).sum()),'proposal_white_guard_overlap_pixels':int((proposal&white_guard).sum()),
        'proposal_mask_sha256_packbits':mask_sha(proposal),'remaining_mask_sha256_packbits':mask_sha(remain)
      },
      'aggregate':{
        'prior_c176_unresolved_pixels':int(r2t.sum()+r2n.sum()+rr.sum()),'new_proposal_resolved_pixels':int(proposal.sum()),'new_actual_changed_pixels':int((changed&proposal).sum()),
        'remaining_unresolved_pixels':int(r2t.sum()+r2n.sum()+remain.sum()),'unresolved_reduction_ratio':float(proposal.sum()/(r2t.sum()+r2n.sum()+rr.sum())),
        'outside_accepted_mask_changed_pixels':int((changed&~accepted).sum()),'alpha_changed_pixels':int(np.sum(target[:,:,3]!=preview[:,:,3])),
        'protected_circle_guard_overlap_pixels':int((proposal&circle_guard).sum()),'protected_white_guard_overlap_pixels':int((proposal&white_guard).sum())
      },
      'readiness_after':'PREFLIGHT_ONLY__RANDOM_DARK_PANEL_RECONSTRUCTION_ADVANCED__2590_UNRESOLVED__CIRCLE_QUESTION_MARK_CORRIDOR_AND_TUNED_NORMAL_FRINGE_HOLD',
      'candidate_dds_authorized':False,'candidate_dds_modified':False,'runtime_validation':'UNTESTED'
    }
    fp=(out['random']['new_dark_panel_proposal_pixels'],out['random']['new_actual_changed_pixels'],out['random']['remaining_unresolved_pixels'],out['aggregate']['remaining_unresolved_pixels'],out['aggregate']['outside_accepted_mask_changed_pixels'],out['aggregate']['alpha_changed_pixels'],out['aggregate']['protected_circle_guard_overlap_pixels'],out['aggregate']['protected_white_guard_overlap_pixels'])
    if fp!=(3144,1874,2048,2590,0,0,0,0): raise SystemExit('A00366_FINGERPRINT_FAIL:'+repr(fp))
    Path(a.out).write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(out,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
