#!/usr/bin/env python3
import argparse,hashlib,json
from pathlib import Path
import cv2,numpy as np
from PIL import Image
TS='a8942f076b9c3d8cddd62ba39c84a3b3abea72b2ba19a61a21e9a2bd6f8e8036';S411='bad9701ac45e4587d8b04afde335951f4857f747ec20fd71fc838be7d86bf364';S53='cfed1de58cefd8c235fc464e27058439ffd26427294a3bce17192e584679426a'
BLUE=(0,79,159,255);RF=(245,247,247,255);ELL=(103,152,220,255);WHITE=(255,255,255,255)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return np.asarray(Image.open(p).convert('RGBA').transpose(Image.Transpose.FLIP_TOP_BOTTOM)).copy()
def ex(a,c):return np.all(a==np.array(c,np.uint8),2)
def dil(m,r):return cv2.dilate(m.astype('uint8'),np.ones((2*r+1,2*r+1),np.uint8)).astype(bool)
def largest(m,roi):
 x0,y0,x1,y1=roi;n,lab,st,_=cv2.connectedComponentsWithStats(m[y0:y1,x0:x1].astype('uint8'),8);i=1+int(np.argmax(st[1:,cv2.CC_STAT_AREA]));x,y,w,h,a=st[i];return (x0+x,y0+y,x0+x+w,y0+y+h,int(a))
def textm(a,roi):
 x0,y0,x1,y1=roi;o=np.zeros(a.shape[:2],bool);o[y0:y1,x0:x1]=dil(ex(a[y0:y1,x0:x1],RF),6);return o
def tr(s,d):
 sx=(d[2]-d[0])/(s[2]-s[0]);sy=(d[3]-d[1])/(s[3]-s[1]);return sx,sy,d[0]-s[0]*sx,d[1]-s[1]*sy
def inv(x,y,t):sx,sy,tx,ty=t;return int(round((x-tx)/sx)),int(round((y-ty)/sy))
def extfill(a,c,roi):
 x0,y0,x1,y1=roi;sub=ex(a[y0:y1,x0:x1],c).astype('uint8');n,lab,st,_=cv2.connectedComponentsWithStats(sub,8);i=1+int(np.argmax(st[1:,cv2.CC_STAT_AREA]));cs,_=cv2.findContours((lab==i).astype('uint8'),cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE);f=np.zeros_like(sub);cv2.drawContours(f,[max(cs,key=cv2.contourArea)],-1,1,-1);o=np.zeros(a.shape[:2],bool);o[y0:y1,x0:x1]=f.astype(bool);return o
def bbox(m):
 y,x=np.where(m);return [int(x.min()),int(y.min()),int(x.max()+1),int(y.max()+1)]
def main():
 p=argparse.ArgumentParser();p.add_argument('target');p.add_argument('d411');p.add_argument('d53');p.add_argument('--out',required=True);a=p.parse_args()
 if (sha(a.target),sha(a.d411),sha(a.d53))!=(TS,S411,S53):raise SystemExit('IDENTITY_FAIL')
 t,d1,d2=map(load,[a.target,a.d411,a.d53]);tb=largest(ex(t,BLUE),(0,0,2048,2048));b1=largest(ex(d1,BLUE),(1570,820,1930,1110));b2=largest(ex(d2,BLUE),(0,0,2048,2048));t1,t2=tr(b1,tb),tr(b2,tb)
 tm,m1,m2=textm(t,(1710,1410,2008,1515)),textm(d1,(1570,820,1930,1110)),textm(d2,(0,0,2048,2048));u=np.zeros(tm.shape,bool)
 for y,x in zip(*np.where(tm)):
  qx,qy=inv(x,y,t1)
  if 0<=qx<2048 and 0<=qy<2048 and not m1[qy,qx]:continue
  qx,qy=inv(x,y,t2)
  if 0<=qx<2048 and 0<=qy<2048 and not m2[qy,qx]:continue
  u[y,x]=1
 if int(u.sum())!=5192 or bbox(u)!=[1761,1448,1943,1481]:raise SystemExit('RANDOM_BASELINE_FAIL')
 Y,X=np.indices(u.shape);em=ex(t,ELL)&(X>=1770)&(X<1930)&(Y>=1440)&(Y<1590);yy,xx=np.where(em);h=cv2.convexHull(np.column_stack([xx,yy]).astype('int32').reshape(-1,1,2));hm=np.zeros(u.shape,'uint8');cv2.fillConvexPoly(hm,h,1);eg=dil(hm.astype(bool),2)
 x0,y0,x1,y1=(1780,1460,1940,1590);sub=ex(t[y0:y1,x0:x1],WHITE).astype('uint8');n,lab,st,_=cv2.connectedComponentsWithStats(sub,8);cand=[(int(st[i,4]),i) for i in range(1,n) if st[i,4]>=500 and st[i,2]<120 and st[i,3]<120];qa,qi=max(cand);qm=np.zeros(u.shape,bool);yy,xx=np.where(lab==qi);qm[y0+yy,x0+xx]=1;qg=dil(qm,12)
 pi=extfill(t,BLUE,(1690,1435,2010,1605));prop=u&pi&~eg&~qg;known=(~tm)&pi&~eg&~qg;kc=int(known.sum());kb=int((known&ex(t,BLUE)).sum())
 out={'schema_version':30,'task_id':'LOCALIZATION-LOCALIZATION_A-00366','wave_id':'P00235','asset':'C075FB49','source_sha256':[TS,S411,S53],'prior_c176_unresolved':5734,'random_prior_unresolved':int(u.sum()),'proposal_resolved':int(prop.sum()),'proposal_actual_changed':int((prop&~ex(t,BLUE)).sum()),'random_remaining':int((u&~prop).sum()),'aggregate_remaining':2335,'proposal_bbox':bbox(prop),'remaining_bbox':bbox(u&~prop),'known_domain_pixels':kc,'known_domain_exact_blue':kb,'ellipse_guard_overlap':int((prop&eg).sum()),'question_guard_overlap':int((prop&qg).sum()),'alpha_changes':0,'outside_proposal_changes':0,'candidate_dds_modified':False,'runtime_validation':'UNTESTED','readiness':'PREFLIGHT_ONLY'}
 fp=(out['proposal_resolved'],out['proposal_actual_changed'],out['random_remaining'],kc,kb,out['ellipse_guard_overlap'],out['question_guard_overlap']);exp=(3399,2082,1793,17674,17674,0,0)
 if fp!=exp:raise SystemExit('FINGERPRINT_FAIL '+repr(fp))
 Path(a.out).write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out,indent=2))
if __name__=='__main__':main()
