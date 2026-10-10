#!/usr/bin/env python3
"""C2 q212 first-hand persisted DDS and SHA-authenticated canonical SOURCE/C158 CLEAN review evidence."""
from pathlib import Path
import hashlib,struct,json,datetime
import numpy as np
from PIL import Image,ImageDraw
repo=Path('/home/chatgpt-runner2/work/outrun-c2-1920')
g=repo/'localization/graphics'
out=g/'role_C/20261010-C2-Q212-B357-INDEPENDENT-P1-MODE-FAMILY'
source=Path('/home/chatgpt-runner2/tmp/c2_q212_source_en_20261010.dds')
clean=g/'role_C/20261005-C158-BA0147DA/C158_VERIFIED_CLEAN_PLATE.png'
official=g/'hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst/BA0147DA_512x512.dds'
trial=g/'role_B/20261010-B357-Q212-NATIVE-SOURCE-MODE-FAMILY/B357_Q212_TWO_FAMILY_NATIVE_UNAPPROVED.dds'
expected={'source':'f83f58483aab7a99ffe230c86eaa0527d9b7323be36808bdf69f2817e29c9f61','clean':'c13a24922d4d5e208b8c228fb51f9464d82b42442d9a14f08f7242305e314c67','official':'e22ad5c46e81489123467783176dba1a040e0d2a36b6e6820349a9fcd87e9fea','trial':'6d0098dcad41b0c430961f3d754455018cc59e0dea2f6d108a9d5c1180a5d88d'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for name,p in [('source',source),('clean',clean),('official',official),('trial',trial)]:
 actual=sha(p);assert actual==expected[name],(name,actual)
def decode(p):
 b=p.read_bytes();assert b[:4]==b'DDS '
 h,w=struct.unpack_from('<II',b,12)
 assert (h,w)==(2048,2048) and len(b)==2048*2048*4+128,(h,w,len(b))
 a=np.frombuffer(b,dtype=np.uint8,offset=128).reshape((h,w,4))[:,:,[2,1,0,3]].copy()
 return a,b[:128]
src_raw,src_head=decode(source);off_raw,off_head=decode(official);tri_raw,tri_head=decode(trial)
src=src_raw[::-1];off=off_raw[::-1];tri=tri_raw[::-1]
cp=np.asarray(Image.open(clean).convert('RGBA')).copy()
assert cp.shape==src.shape
# Two exact English sprite cells; core boxes are from canonical persisted source alpha>32
regions=[
 {'id':'r43_professional','source_text':'PROFESSIONAL','candidate_text':'프로페셔널 모드','source_full_bbox':[0,341,638,404],'english_opaque_bbox':[240,341,637,386],'window':[0,331,643,407]},
 {'id':'r44_outrun','source_text':'OUTRUN','candidate_text':'아웃런 모드','source_full_bbox':[1626,524,1837,587],'english_opaque_bbox':[1626,524,1837,569],'window':[1608,510,1854,600]}
]
m=np.zeros((2048,2048),bool)
for r in regions:
 x0,y0,x1,y1=r['source_full_bbox'];m[y0:y1,x0:x1]=True
d=np.any(off!=tri,axis=2);a=off[:,:,3]!=tri[:,:,3]
outside_rgba=int(np.count_nonzero(d & ~m));outside_alpha=int(np.count_nonzero(a & ~m))
assert outside_rgba==outside_alpha==0,(outside_rgba,outside_alpha)
assert src_head==off_head==tri_head
def comp(x,color=(125,125,125,255)):
 a=Image.fromarray(np.ascontiguousarray(x),'RGBA');bg=Image.new('RGBA',a.size,color);bg.alpha_composite(a);return bg.convert('RGB')
res=[]
for r in regions:
 x0,y0,x1,y1=r['source_full_bbox'];u0,v0,u1,v1=r['english_opaque_bbox']
 S=src[y0:y1,x0:x1];C=cp[y0:y1,x0:x1];T=tri[y0:y1,x0:x1];O=off[y0:y1,x0:x1]
 def px(A,B):return int(np.count_nonzero(np.any(A!=B,axis=2)))
 core=tri[v0:v1,u0:u1,3]>32
 yy,xx=np.nonzero(core)
 bbox=[int(u0+xx.min()),int(v0+yy.min()),int(u0+xx.max()+1),int(v0+yy.max()+1)] if len(xx) else None
 whole=tri[y0:y1,x0:x1,3]>32
 y2,x2=np.nonzero(whole)
 full_bbox=[int(x0+x2.min()),int(y0+y2.min()),int(x0+x2.max()+1),int(y0+y2.max()+1)] if len(x2) else None
 source=src[y0:y1,x0:x1,3]>32; sy,sx=np.nonzero(source)
 source_bbox=[int(x0+sx.min()),int(y0+sy.min()),int(x0+sx.max()+1),int(y0+sy.max()+1)]
 single={'id':r['id'],'source_label':r['source_text'],'candidate_label':r['candidate_text'],'source_full_bbox':r['source_full_bbox'],'source_native_alpha32_bbox_measured':source_bbox,'candidate_native_alpha32_bbox_full_scope':full_bbox,'candidate_within_english_core_bbox':bool(full_bbox and full_bbox[0]>=u0 and full_bbox[1]>=v0 and full_bbox[2]<=u1 and full_bbox[3]<=v1),'candidate_strict_positive_margins':[full_bbox[0]-u0,full_bbox[1]-v0,u1-full_bbox[2],v1-full_bbox[3]] if full_bbox else None,'source_to_authored_clean_rgba_changes_cell':px(S,C),'clean_alpha_nonzero_in_cell':int(np.count_nonzero(C[:,:,3])),'clean_to_trial_rgba_changes_cell':px(C,T),'official_to_trial_rgba_changes_cell':px(O,T),'native_source_width':source_bbox[2]-source_bbox[0],'native_trial_width':full_bbox[2]-full_bbox[0]}
 res.append(single)
 w0,h0,w1,h1=r['window'];rimgs=[('ENGLISH_SOURCE',src),('AUTHORED_C158_CLEAN',cp),('CURRENT_OFFICIAL',off),('NEW_B357_UNAPPROVED',tri)]
 for bg,bgcolor in [('gray',(127,127,127,255)),('white',(255,255,255,255)),('black',(0,0,0,255))]:
  imgs=[(label,comp(x[h0:h1,w0:w1],bgcolor)) for label,x in rimgs]
  wd=w1-w0;ht=h1-h0
  canvas=Image.new('RGB',(wd*4,ht+20),(28,28,28));dr=ImageDraw.Draw(canvas)
  for j,(label,img) in enumerate(imgs):dr.text((wd*j+4,4),label,fill=(255,255,255));canvas.paste(img,(wd*j,20))
  for pct in [100,75,50]:
   im=canvas if pct==100 else canvas.resize((round(canvas.width*pct/100),round(canvas.height*pct/100)),Image.Resampling.LANCZOS)
   im.save(out/f'C2_Q212_B357_{r["id"].upper()}_{bg.upper()}_{pct}_4VIEW.png')
 # RAW and FLIPY by independently decoding same persisted candidate bytes.
 ra=tri_raw[2048-h1:2048-h0,w0:w1];fl=tri[h0:h1,w0:w1]
 Image.fromarray(np.ascontiguousarray(ra),'RGBA').save(out/f'C2_Q212_B357_{r["id"].upper()}_RAW_NATIVE.png')
 Image.fromarray(np.ascontiguousarray(fl),'RGBA').save(out/f'C2_Q212_B357_{r["id"].upper()}_FLIPY_NATIVE.png')
assert int(d.sum())==12899, int(d.sum())
machine={'role':'C2','index':212,'shard':'EVEN','mode':'B357_NEW_UNAPPROVED_TRIAL_INDEPENDENT','timestamp_kst':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat(timespec='seconds'),
'sha256':expected,'canonical_source_provenance':'Sonic-TV/OR2006Sprites@3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6','canonical_source_directly_downloaded_sha_verified':True,'C158_authored_clean_sha_verified':True,'persisted_dds_header_identical':True,'native_dims':[2048,2048],'codec':'RGBA32','mip_count':1,'raw_transform':'mirror_y',
'official_to_B357_rgba_changed_total':int(d.sum()),'official_to_B357_alpha_changed_total':int(a.sum()),'official_to_B357_changed_rgba_outside_two_source_regions':outside_rgba,'official_to_B357_changed_alpha_outside_two_source_regions':outside_alpha,'other_ten_cells_official_exact':bool(outside_rgba==0),'regions':res,'RUNTIME_VALIDATION':'UNTESTED','C3_approval':'NOT_RUN'}
(out/'C2_Q212_B357_EXACT_BYTES_MACHINE.json').write_text(json.dumps(machine,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'timestamp':machine['timestamp_kst'],'machine_change':int(d.sum()),'alpha_change':int(a.sum()),'outside':outside_rgba,'regions':res,'png':len(list(out.glob('*.png')))},ensure_ascii=False))
