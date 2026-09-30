#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, io, json, zipfile
from pathlib import Path
import cv2, numpy as np
from PIL import Image
TARGET_SHA='a8942f076b9c3d8cddd62ba39c84a3b3abea72b2ba19a61a21e9a2bd6f8e8036'
D411_SHA='bad9701ac45e4587d8b04afde335951f4857f747ec20fd71fc838be7d86bf364'
ZIP_SHA='76f85ed2ca27344a4292ac7e010a786579b4eebb1a370c0aa126fcb2b231d958'
D53_MEMBER='textures/load/spr_sprani_selector_cvt_Exst/53CE39D5_512x512.dds'
TBOX=(40,1170,245,1305); NBOX=(375,1170,600,1305); RBOX=(1710,1410,2008,1515)
RED=(196,0,0,255); GREEN=(0,150,0,255); BLUEP=(0,79,159,255)
T_FILL=(255,150,0,255); N_FILL=(255,243,112,255); R_FILL=(245,247,247,255)

def sha(b):return hashlib.sha256(b).hexdigest()
def load_dds_bytes(b):return np.asarray(Image.open(io.BytesIO(b)).convert('RGBA').transpose(Image.Transpose.FLIP_TOP_BOTTOM)).copy()
def exact(a,c):return np.all(a==np.array(c,dtype=np.uint8),axis=2)
def largest(mask,roi=None):
 if roi:
  x0,y0,x1,y1=roi; sub=mask[y0:y1,x0:x1].astype(np.uint8)
 else:
  x0=y0=0; sub=mask.astype(np.uint8)
 n,lab,stats,_=cv2.connectedComponentsWithStats(sub,8)
 if n<=1:return None,None
 i=1+int(np.argmax(stats[1:,cv2.CC_STAT_AREA])); x,y,w,h,area=stats[i]
 out=np.zeros(mask.shape,bool); yy,xx=np.where(lab==i);out[y0+yy,x0+xx]=1
 return out,(int(x0+x),int(y0+y),int(x0+x+w),int(y0+y+h),int(area))
def transform_from_bbox(src,dst):
 sx=(dst[2]-dst[0])/(src[2]-src[0]); sy=(dst[3]-dst[1])/(src[3]-src[1])
 tx=dst[0]-src[0]*sx; ty=dst[1]-src[1]*sy
 return (sx,sy,tx,ty)
def inv_map(x,y,tr):
 sx,sy,tx,ty=tr
 return (int(round((x-tx)/sx)),int(round((y-ty)/sy)))
def dil(m,r):return cv2.dilate(m.astype(np.uint8),np.ones((2*r+1,2*r+1),np.uint8)).astype(bool)
def bbox(m):
 y,x=np.where(m);return None if not len(x) else [int(x.min()),int(y.min()),int(x.max()+1),int(y.max()+1)]

def panel_info(img,color,roi):
 m,b=largest(exact(img,color),roi)
 return m,b[:4]
def textmask(img,fill,roi,r=6):
 l,t,rr,b=roi; sub=exact(img[t:b,l:rr],fill); dm=dil(sub,r); out=np.zeros(img.shape[:2],bool);out[t:b,l:rr]=dm;return out

def coverage_target(target, donor, target_color, donor_roi, target_roi, target_fill, donor_fill, sibling=None, sibling_roi=None, sibling_fill=None, sibling_dx=0, label=''):
 _,tb=panel_info(target,target_color,(0,0,target.shape[1],target.shape[0]))
 _,db=panel_info(donor,target_color,donor_roi)
 tr=transform_from_bbox(db,tb)
 tmask=textmask(target,target_fill,target_roi,6)
 dmask=textmask(donor,donor_fill,donor_roi,6)
 smask=None
 if sibling is not None: smask=textmask(target,sibling_fill,sibling_roi,6)
 yy,xx=np.where(tmask); covered_d=0; covered_s=0; unresolved=[]; donor_used=[]; sibling_used=[]
 for y,x in zip(yy.tolist(),xx.tolist()):
  xd,yd=inv_map(x,y,tr)
  okd=0<=yd<donor.shape[0] and 0<=xd<donor.shape[1] and not dmask[yd,xd]
  if okd:
   donor_used.append((x,y)); covered_d+=1; continue
  if sibling is not None:
   xs=x+sibling_dx
   oks=0<=xs<target.shape[1] and not smask[y,xs]
   if oks:
    sibling_used.append((x,y)); covered_s+=1; continue
  unresolved.append((x,y))
 um=np.zeros(target.shape[:2],bool)
 if unresolved:
  ux,uy=zip(*unresolved);um[list(uy),list(ux)]=1
 return {'label':label,'target_panel_bbox':tb,'donor_panel_bbox':db,'donor_to_target_affine':{'sx':tr[0],'sy':tr[1],'tx':tr[2],'ty':tr[3]},'proposal_scope_pixels':int(tmask.sum()),'donor_clean_coverage_pixels':covered_d,'sibling_clean_coverage_pixels':covered_s,'covered_total_pixels':covered_d+covered_s,'coverage_ratio':(covered_d+covered_s)/int(tmask.sum()),'unresolved_pixels':len(unresolved),'unresolved_bbox':bbox(um),'scope_bbox':bbox(tmask)}

def main():
 ap=argparse.ArgumentParser();ap.add_argument('target');ap.add_argument('donor411');ap.add_argument('zip');ap.add_argument('--out',required=True);a=ap.parse_args()
 tb=Path(a.target).read_bytes();d411b=Path(a.donor411).read_bytes();zb=Path(a.zip).read_bytes()
 if sha(tb)!=TARGET_SHA or sha(d411b)!=D411_SHA or sha(zb)!=ZIP_SHA:raise SystemExit('identity fail')
 z=zipfile.ZipFile(io.BytesIO(zb));d53b=z.read(D53_MEMBER)
 target=load_dds_bytes(tb);d411=load_dds_bytes(d411b);d53=load_dds_bytes(d53b)
 tuned=coverage_target(target,d411,RED,(780,820,1180,1110),TBOX,T_FILL,T_FILL,sibling=target,sibling_roi=NBOX,sibling_fill=N_FILL,sibling_dx=360,label='tuned_setting')
 normal=coverage_target(target,d411,GREEN,(1180,820,1570,1110),NBOX,N_FILL,N_FILL,sibling=target,sibling_roi=TBOX,sibling_fill=T_FILL,sibling_dx=-335,label='normal_setting')
 _,tbx=panel_info(target,BLUEP,(0,0,2048,2048));_,d1b=panel_info(d411,BLUEP,(1570,820,1930,1110));_,d2b=panel_info(d53,BLUEP,(0,0,2048,2048))
 tr1=transform_from_bbox(d1b,tbx);tr2=transform_from_bbox(d2b,tbx)
 tmask=textmask(target,R_FILL,RBOX,6);d1mask=textmask(d411,R_FILL,(1570,820,1930,1110),6);d2mask=textmask(d53,R_FILL,(0,0,2048,2048),6)
 yy,xx=np.where(tmask);c1=c2=0;un=[]
 for y,x in zip(yy.tolist(),xx.tolist()):
  xd,yd=inv_map(x,y,tr1)
  if 0<=yd<2048 and 0<=xd<2048 and not d1mask[yd,xd]:c1+=1;continue
  x2,y2=inv_map(x,y,tr2)
  if 0<=y2<2048 and 0<=x2<2048 and not d2mask[y2,x2]:c2+=1;continue
  un.append((x,y))
 um=np.zeros((2048,2048),bool)
 if un:
  ux,uy=zip(*un);um[list(uy),list(ux)]=1
 random={'label':'random','target_panel_bbox':tbx,'donor411_panel_bbox':d1b,'donor53_panel_bbox':d2b,'donor411_to_target_affine':{'sx':tr1[0],'sy':tr1[1],'tx':tr1[2],'ty':tr1[3]},'donor53_to_target_affine':{'sx':tr2[0],'sy':tr2[1],'tx':tr2[2],'ty':tr2[3]},'proposal_scope_pixels':int(tmask.sum()),'donor411_clean_coverage_pixels':c1,'donor53_clean_coverage_pixels':c2,'covered_total_pixels':c1+c2,'coverage_ratio':(c1+c2)/int(tmask.sum()),'unresolved_pixels':len(un),'unresolved_bbox':bbox(um),'scope_bbox':bbox(tmask)}
 out={'schema_version':16,'schema':'outrun-a00309-index111-multisource-source-only-reconstruction-coverage-v1','target_sha256':TARGET_SHA,'donor411_sha256':D411_SHA,'donor53_member':D53_MEMBER,'donor53_sha256':sha(d53b),'bundle_sha256':ZIP_SHA,'coordinate_space':'readable/display after raw mirror_y -> flip_y','purpose':'Quantify exact source-only clean-background coverage for the three panel-connected index111 elements before constructing CLEAN_PLATE bytes. No Korean/candidate pixels used.','method':'Map clean English HD sibling/donor pixels into target proposal scopes only when the mapped donor location lies outside that donor text-neighborhood mask; otherwise leave the pixel unresolved. Tuned/Normal may fall back to the aligned sibling target panel only when sibling location is outside sibling text-neighborhood.','elements':{'tuned_setting':tuned,'normal_setting':normal,'random':random},'aggregate':{},'readiness_after':'PREFLIGHT_ONLY_MULTISOURCE_RECONSTRUCTION_COVERAGE_LOCKED__UNRESOLVED_PIXELS_REQUIRE_SOURCE_CONSTRAINED_SYNTHESIS_AND_C_CLEANPLATE_QA','candidate_dds_authorized':False,'runtime_validation':'UNTESTED'}
 tot=sum(v['proposal_scope_pixels'] for v in out['elements'].values());cov=sum(v['covered_total_pixels'] for v in out['elements'].values());un=sum(v['unresolved_pixels'] for v in out['elements'].values());out['aggregate']={'proposal_scope_pixels':tot,'source_covered_pixels':cov,'source_coverage_ratio':cov/tot,'unresolved_pixels':un}
 Path(a.out).write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(out,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
