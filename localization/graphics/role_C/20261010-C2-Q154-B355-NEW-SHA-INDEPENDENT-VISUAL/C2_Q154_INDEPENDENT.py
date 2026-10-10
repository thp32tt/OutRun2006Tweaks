#!/usr/bin/env python3
"""Independent C2 QA for distinct unpromoted B355 q154 saved DDS: no approvals or artifact promotion."""
import hashlib,json,datetime,struct
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
repo=Path('/home/chatgpt-runner2/work/outrun-c2-1920'); g=repo/'localization/graphics'
out=g/'role_C/20261010-C2-Q154-B355-NEW-SHA-INDEPENDENT-VISUAL'
off=g/'hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst/4D38BBB0_1024x256.dds'
trial=g/'role_B/20261010-B355-Q154-HISTORIC-NATIVE-COUNTER-INTERPOLATION/B355_Q154_GRAY_FAMILY_HALF_PIXEL_UNAPPROVED.dds'
other=g/'role_B/20261010-B354-Q154-THIN-NATIVE-GRAY-SOURCE-FAMILY/B354_Q154_NATIVE_REGULAR_GRAY_UNAPPROVED.dds'
expect=['c4d6c1515716476123b69dfb645dcc27a3cc7a69f31a1368a831004a0b40d524','4db18d96b359a0bd916a2f6bb8cd3537c5cead769b189da6cded4c5fb899ad87','190462fb95c9b2951c24557d1a6b145a14db4bad8eb4518fcd4c3be6ec159c35']
def dds(path,hs):
 b=path.read_bytes(); h=hashlib.sha256(b).hexdigest();assert h==hs,(path,h,hs)
 assert b[:4]==b'DDS '
 ht,w=struct.unpack_from('<II',b,12);assert (w,ht)==(4096,1024)
 assert len(b)==128+ht*w*4
 x=np.frombuffer(b,dtype=np.uint8,offset=128).reshape(ht,w,4)[:,:,[2,1,0,3]].copy()
 return x,{'path':str(path.relative_to(repo)),'sha256':h,'header':{'w':w,'h':ht,'bytes':len(b),'mips':1,'format':'BGRA32'}}
a,official=dds(off,expect[0]);b,current=dds(trial,expect[1]);c,prior=dds(other,expect[2])
# Both raw and readable pixel deltas; bboxes documented by producer in native readable atlas.
regions=[('single_player',[1610,286,2197,350]),('showroom',[2674,288,3094,350]),('multiplayer',[2566,952,3086,1014])]
def masks(h,w,boxes):
 m=np.zeros((h,w),dtype=bool)
 for _,(x0,y0,x1,y1) in boxes:m[y0:y1,x0:x1]=True
 return m
m=masks(1024,4096,regions)
assess=[]
for label,X in [('B355',b),('B354',c)]:
 for orientation,AA,XX in [('READABLE_FLIPY',a[::-1],X[::-1]),('RAW',a,X)]:
  mm=m if orientation=='READABLE_FLIPY' else m[::-1]
  d=np.any(AA!=XX,axis=2);al=AA[:,:,3]!=XX[:,:,3]
  assess.append({'candidate':label,'orientation':orientation,'rgba_changed':int(d.sum()),'alpha_changed':int(al.sum()),'outside_rgba':int(np.count_nonzero(d & ~mm)),'outside_alpha':int(np.count_nonzero(al & ~mm))})
# Persisted-source-independent comparisons: source ROI coords are reported; source authentication inherited from C344, not re-performed.
obs=[]
for name,(x0,y0,x1,y1) in regions:
 A=a[::-1][y0:y1,x0:x1];B=b[::-1][y0:y1,x0:x1];T=c[::-1][y0:y1,x0:x1]
 # Native source bbox bounds are provisional until individually measured from pinned English bytes.
 d=np.any(A!=B,axis=2)
 obs.append({'id':name,'source_bbox_from_B355': [x0,y0,x1,y1],'new_vs_official_changed_rgba':int(d.sum()),'new_vs_official_changed_alpha':int(np.count_nonzero(A[:,:,3]!=B[:,:,3]))})
 for bg,bgcolor in [('gray',(115,115,115,255)),('white',(255,255,255,255)),('black',(0,0,0,255))]:
  mats=[]
  for ar in [A,T,B]:
   rgba=Image.fromarray(np.ascontiguousarray(ar),'RGBA'); canvas=Image.new('RGBA',rgba.size,bgcolor);canvas.alpha_composite(rgba);mats.append(canvas.convert('RGB'))
  pad=21;comp=Image.new('RGB',(x1-x0,(y1-y0)*3+pad*3),(45,45,45));dr=ImageDraw.Draw(comp)
  for n,(t,im) in enumerate(zip(['OFFICIAL REWORK','B354 REGULAR TRIAL','B355 MIDPOINT TRIAL'],mats)):
   y=n*((y1-y0)+pad);dr.text((3,y+3),t,fill=(250,250,250));comp.paste(im,(0,y+pad))
  comp.save(out/f'C2_Q154_{name.upper()}_{bg.upper()}_NATIVE100.png')
  if bg=='gray':comp.resize((comp.width//2,comp.height//2),Image.Resampling.LANCZOS).save(out/f'C2_Q154_{name.upper()}_GRAY_PRACTICAL50.png')
 # independently decoded readable/raw crops from exact B355 persisted bytes for inspection
 Image.fromarray(np.ascontiguousarray(B),'RGBA').save(out/f'C2_Q154_{name.upper()}_B355_PERSISTED_READABLE_RGBA.png')
 # RAW crop raw y transformed using 1024-y1..1024-y0
 Image.fromarray(np.ascontiguousarray(b[1024-y1:1024-y0,x0:x1]),'RGBA').save(out/f'C2_Q154_{name.upper()}_B355_PERSISTED_RAW_RGBA.png')
machine={'queue_index':154,'role':'C2','review_lane':'EVEN','timestamp_kst':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat(timespec='seconds'),
 'source_claimed_sha256':'15a10e6b44ca5f1267fdf24eebbe902bb18a77b3903896370e183fea8a401bcf','source_independently_authenticated_this_run':False,
 'official':official,'new_B355_unapproved':current,'other_B354_unapproved':prior,'region_scope':regions,'pixel_differences':assess,'per_region':obs,
 'scope_limits':['B355 is unapproved and NOT official DDS; original official C356 REWORK persists','exact English source/CLEAN authorization relies on earlier C344; not independently re-authenticated in this run','blind defect calibration not executed','C3 and real game not executed'],
 'approvals_created':0,'dds_promoted':0,'RUNTIME_VALIDATION':'UNTESTED'}
(out/'C2_Q154_INDEPENDENT_MACHINE.json').write_text(json.dumps(machine,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'sha':current['sha256'],'differences':assess,'per_region':obs,'timestamp_kst':machine['timestamp_kst'],'images':len(list(out.glob('*.png')))},ensure_ascii=False))