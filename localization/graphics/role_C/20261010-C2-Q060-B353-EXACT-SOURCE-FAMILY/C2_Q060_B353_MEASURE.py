#!/usr/bin/env python3
"""Independent SHA-pinned persisted q060 B353 visual provenance and pixel QA; no promotion."""
from pathlib import Path
import hashlib,struct,json,datetime
import numpy as np
from PIL import Image,ImageDraw
root=Path('/home/chatgpt-runner2/work/outrun-c2-202010-2020');g=root/'localization/graphics'
out=g/'role_C/20261010-C2-Q060-B353-EXACT-SOURCE-FAMILY'
paths={
 'source':g/'hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_game_cvt_Exst/A064FDFC_1024x512.dds',
 'official':g/'hd_candidates/textures/load/spr_sprani_game_cvt_Exst/A064FDFC_1024x512.dds',
 'trial':g/'role_B/20261010-B353-Q060-ENGLISH-PERROW-MATERIAL-PILOT/B353_Q060_SOURCE_CONTOUR_GOLD_KOREAN_UNAPPROVED.dds',
 'clean':g/'role_B/20261010-B348-Q060-BEST-TIME-SOURCE-COMPONENT-PLATE/B348_BEST_TIME_SOURCE_FIRST_PLATE_READABLE.png'}
expected={'source':'6a33c7307e33337af085f0fffea081de8659ed1806f4ef4d2a8809d4120cadbc','official':'d81d0d144f2c4b8192021f9e0b49c7ad44f753da68d6f5dd66f18fe907d06b01','trial':'a44bf0ade48f6f82dc50e2df739ba9ee7339ac1b5d3557e5ea6e30f8d798e9cc','clean':'a03687d4cd23ede4323dca63f07961061b7ba850c19c3a2f69764020a538bb48'}
for name,p in paths.items():assert hashlib.sha256(p.read_bytes()).hexdigest()==expected[name],name
def decode(p):
 b=p.read_bytes()
 assert b[:4]==b'DDS ' and len(b)==33554560
 h,w=struct.unpack_from('<II',b,12);assert (h,w)==(2048,4096)
 # DDS source is R low byte, G next, B third, A last; no BGRA swap.
 assert struct.unpack_from('<IIII',b,92)==(255,65280,16711680,4278190080),struct.unpack_from('<IIII',b,92)
 assert struct.unpack_from('<I',b,28)[0]==1
 return np.frombuffer(b,offset=128,dtype=np.uint8).reshape((h,w,4)).copy(),b[:128]
raw={k:decode(paths[k]) for k in ['source','official','trial']}
S=raw['source'][0][::-1];O=raw['official'][0][::-1];T=raw['trial'][0][::-1]
assert raw['source'][1]==raw['official'][1]==raw['trial'][1]
C=np.asarray(Image.open(paths['clean']).convert('RGBA')).copy()
assert C.shape==S.shape
# User P0 BEST TIME text. Source 849x134 and conservative effect ROI.
sourcebox=[2179,340,3028,474];worker_roi=[2090,337,3120,485];x0,y0,x1,y1=sourcebox
m=np.zeros(S.shape[:2],bool);m[y0:y1,x0:x1]=1
wr=np.zeros(S.shape[:2],bool);a,b,c,d=worker_roi;wr[b:d,a:c]=1
def diff(A,B):
 changed=np.any(A!=B,axis=2);alpha=A[:,:,3]!=B[:,:,3]
 return {'rgba_full':int(changed.sum()),'alpha_full':int(alpha.sum()),'rgba_outside_sourcebox':int(np.count_nonzero(changed&~m)),'alpha_outside_sourcebox':int(np.count_nonzero(alpha&~m)),'rgba_outside_worker_roi':int(np.count_nonzero(changed&~wr)),'alpha_outside_worker_roi':int(np.count_nonzero(alpha&~wr))}
deltas={n:diff(x,y) for n,x,y in [('SOURCE_TO_CLEAN',S,C),('CLEAN_TO_TRIAL',C,T),('OFFICIAL_TO_TRIAL',O,T),('SOURCE_TO_TRIAL',S,T)]}
# Candidate alpha native bbox, source effect bbox. Need use actual alpha pixels not only producer declared text box.
def bbox(a):
 yy,xx=np.nonzero(a)
 return [int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)] if len(xx) else None
source_alpha=S[y0:y1,x0:x1,3];tri_alpha=T[y0:y1,x0:x1,3];clean_alpha=C[y0:y1,x0:x1,3]
sbox=bbox(source_alpha>32);tbox=bbox(tri_alpha>32)
native={'source_alpha32_bbox_in_sourcebox':sbox,'trial_alpha32_bbox_in_sourcebox':tbox,'source_alpha32_pixels':int(np.count_nonzero(source_alpha>32)),'candidate_alpha32_pixels':int(np.count_nonzero(tri_alpha>32)),'clean_alpha_nonzero_inside_sourcebox':int(np.count_nonzero(clean_alpha)),'source_effect_bbox_producer':sourcebox,'trial_effect_bbox_producer':[2245,348,2983,472]}
def composite(ar,bg):
 fg=Image.fromarray(np.ascontiguousarray(ar),'RGBA')
 back=Image.new('RGBA',fg.size,bg);back.alpha_composite(fg)
 return back.convert('RGB')
# Direct native atlas strips from persisted bytes. Source/CLEAN/Official/Trial, with margins and protected-neighbor context.
# 100%,75%,50% cross-background evidence + raw mirror crop.
window=[1940,265,3190,560];a,b,c,d=window
four=[('ENGLISH',S),('CLEAN',C),('OFFICIAL',O),('B353_TRIAL',T)]
created=[]
for mode,color in [('GRAY',(125,125,125,255)),('BLACK',(0,0,0,255)),('WHITE',(255,255,255,255))]:
 w,h=c-a,d-b
 canv=Image.new('RGB',(4*w,h+26),(35,35,35));draw=ImageDraw.Draw(canv)
 for i,(lab,ar) in enumerate(four):
  pic=composite(ar[b:d,a:c],color);canv.paste(pic,(i*w,26));draw.text((i*w+4,7),lab,fill=(240,240,240))
 for percent in (100,75,50):
  resized=canv if percent==100 else canv.resize((int(canv.width*percent/100),int(canv.height*percent/100)),Image.Resampling.LANCZOS)
  name=f'C2_Q060_B353_FOUR_{mode}_{percent}.png';resized.save(out/name);created.append(name)
# Isolate only BEST TIME source region and decoded persisted pixels for independent zoom scrutiny.
for lab,ar in four:
 v=ar[y0:y1,x0:x1]
 for mode,bg in [('GRAY',(125,125,125,255)),('BLACK',(0,0,0,255))]:
  pic=composite(v,bg)
  f=f'C2_Q060_B353_{lab}_{mode}_SOURCE_ROI_NATIVE.png';pic.save(out/f);created.append(f)
# Exact RAW/FLIPY target cropped native with source rectangle raw-reflected across 2048 height.
for lab in ['source','trial']:
 ar=raw[lab][0];r=ar[2048-d:2048-b,a:c]
 f=f'C2_Q060_B353_{lab.upper()}_RAW_NATIVE.png';Image.fromarray(np.ascontiguousarray(r),'RGBA').save(out/f);created.append(f)
 # native full readable crop direct decode
 f=f'C2_Q060_B353_{lab.upper()}_FLIPY_NATIVE.png';Image.fromarray(np.ascontiguousarray(ar[::-1][b:d,a:c]),'RGBA').save(out/f);created.append(f)
# mechanical visual changed mask official vs new trial and source vs clean with declared source glyph bbox overlaid.
for label,A,B in [('OFFICIAL_TO_B353',O,T),('SOURCE_TO_CLEAN',S,C),('CLEAN_TO_TRIAL',C,T)]:
 delta=np.any(A!=B,axis=2)[b:d,a:c]
 overlay=np.zeros((d-b,c-a,4),dtype=np.uint8)
 overlay[delta]=[255,0,200,255]
 pic=Image.fromarray(overlay,'RGBA')
 canv=Image.new('RGBA',(c-a,d-b),(125,125,125,255));canv.alpha_composite(pic)
 dr=ImageDraw.Draw(canv)
 dr.rectangle((x0-a,y0-b,x1-a-1,y1-b-1),outline=(0,255,60,255),width=2)
 f=f'C2_Q060_B353_{label}_CHANGED_MASK.png';canv.save(out/f);created.append(f)
machine={'role':'C2','shard':'EVEN','queue_index':60,'review_target':'B353_UNAPPROVED_NEW_SHA','timestamp_kst':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat(timespec='seconds'),'exact_sha256':expected,'decoded_source_provenance':'OR2-HD-GUI-v0.25.10a','all_three_DDS_headers_identical':True,'format':'RGBA32','mip_levels':1,'native_size':[4096,2048],'readable_transform':'mirror_y','source_bbox':sourcebox,'producer_roi':worker_roi,'native_rois':native,'pixel_deltas':deltas,'newly_created_lossless_evidence':created,'C3':'NOT_RUN','RUNTIME_VALIDATION':'UNTESTED','current_policy_approval':'NOT_CLAIMED'}
(out/'C2_Q060_B353_INDEPENDENT_MACHINE.json').write_text(json.dumps(machine,indent=2,ensure_ascii=False)+'\n')
print(json.dumps({'kstdatetime':machine['timestamp_kst'],'diffs':deltas,'roi':native,'png_count':len(created)},ensure_ascii=False))
