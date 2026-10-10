#!/usr/bin/env python3
"""New SHA C2 even q212: persisted-DDS + exact canonical source/C158 CLEAN image evidence."""
from pathlib import Path
import numpy as np,hashlib,struct,json,datetime
from PIL import Image,ImageDraw
root=Path('/home/chatgpt-runner2/work/outrun-c2-20261010-b358')
g=root/'localization/graphics'
out=g/'role_C/20261010-C2-Q212-B358-PERSISTED-PLATE-FAMILY'
sources={
'source':Path('/home/chatgpt-runner2/tmp/c2_q212_b358_canonical_source_20261010.dds'),
'clean':g/'role_C/20261005-C158-BA0147DA/C158_VERIFIED_CLEAN_PLATE.png',
'official':g/'hd_candidates/textures/load/spr_sprani_sumo_fe_cvt_Exst/BA0147DA_512x512.dds',
'B357':g/'role_B/20261010-B357-Q212-NATIVE-SOURCE-MODE-FAMILY/B357_Q212_TWO_FAMILY_NATIVE_UNAPPROVED.dds',
'B358':g/'role_B/20261010-B358-Q212-OLD-GLYPH-CLEAN-REBUILD/B358_Q212_TWO_FAMILY_NATIVE_UNAPPROVED.dds'}
expected={
'source':'f83f58483aab7a99ffe230c86eaa0527d9b7323be36808bdf69f2817e29c9f61',
'clean':'c13a24922d4d5e208b8c228fb51f9464d82b42442d9a14f08f7242305e314c67',
'official':'e22ad5c46e81489123467783176dba1a040e0d2a36b6e6820349a9fcd87e9fea',
'B357':'6d0098dcad41b0c430961f3d754455018cc59e0dea2f6d108a9d5c1180a5d88d',
'B358':'38aac182b8691062259b0c758173f19c790b04afbb8e84d241f0b9023c2478a8'}
for k,f in sources.items():
 digest=hashlib.sha256(f.read_bytes()).hexdigest()
 assert digest==expected[k],(k,digest)
def decoded(file):
 data=file.read_bytes()
 assert data[:4]==b'DDS ' and len(data)==16777344
 height,width=struct.unpack_from('<II',data,12)
 assert (height,width)==(2048,2048)
 assert struct.unpack_from('<I',data,28)[0]==1
 # Only the original atlas DDS' channel masks and its FLIP-Y are authoritative.
 masks=struct.unpack_from('<IIII',data,92)
 assert masks in ((0xff0000,0xff00,0xff,0xff000000),(0xff,0xff00,0xff0000,0xff000000)),masks
 original=np.frombuffer(data,dtype=np.uint8,offset=128).reshape(height,width,4).copy()
 rgba=original[:,:,[2,1,0,3]] if masks[0]==0xff0000 else original
 return rgba,np.array(masks).tolist(),hashlib.sha256(data).hexdigest()
R={};heads={}
for k in ('source','official','B357','B358'):
 raw,masks,digest=decoded(sources[k]);R[k]=raw[::-1].copy();heads[k]={'sha':digest,'masks':masks}
R['clean']=np.asarray(Image.open(sources['clean']).convert('RGBA')).copy()
assert all(x.shape==(2048,2048,4) for x in R.values())
regions=[
 {'id':'r43_professional','source_label':'PROFESSIONAL','new_label':'프로페셔널 모드','source_glyph_bbox':[240,341,637,386],'full_cell_bbox':[0,341,638,404],'render_bbox':[0,328,648,415]},
 {'id':'r44_outrun','source_label':'OUTRUN','new_label':'아웃런 모드','source_glyph_bbox':[1626,524,1837,569],'full_cell_bbox':[1626,524,1837,587],'render_bbox':[1605,509,1861,600]}
]
union=np.zeros((2048,2048),dtype=bool)
for r in regions:
 x0,y0,x1,y1=r['full_cell_bbox'];union[y0:y1,x0:x1]=True
def delta(k1,k2,scope):
 a=R[k1];b=R[k2]
 rgba=np.any(a!=b,axis=2)
 alpha=a[:,:,3]!=b[:,:,3]
 return {'changed_rgba_full':int(rgba.sum()),'changed_alpha_full':int(alpha.sum()),'changed_rgba_outside_two_cells':int(np.count_nonzero(rgba&~scope)),'changed_alpha_outside_two_cells':int(np.count_nonzero(alpha&~scope))}
stats={}
for a,b in [('source','clean'),('official','B358'),('B357','B358'),('clean','B358'),('source','B358')]:
 stats[a+'_TO_'+b]=delta(a,b,union)
def box(mask,offset):
 yy,xx=np.nonzero(mask)
 return [int(xx.min()+offset[0]),int(yy.min()+offset[1]),int(xx.max()+1+offset[0]),int(yy.max()+1+offset[1])] if len(xx) else None
def composite(arr,bg):
 fg=Image.fromarray(np.ascontiguousarray(arr),'RGBA')
 back=Image.new('RGBA',fg.size,bg);back.alpha_composite(fg)
 return back.convert('RGB')
evidence=[];parts=[]
for r in regions:
 id=r['id'];x0,y0,x1,y1=r['full_cell_bbox'];sx,sy,ex,ey=r['source_glyph_bbox']
 core=np.zeros((y1-y0,x1-x0),bool)
 core[sy-y0:ey-y0,sx-x0:ex-x0]=True
 sub={k:v[y0:y1,x0:x1] for k,v in R.items()}
 cur=sub['B358'][:,:,3]>32;old=sub['B357'][:,:,3]>32;official=sub['official'][:,:,3]>32
 outside=~core
 p={
 'id':id,'english':r['source_label'],'candidate':r['new_label'],
 'source_glyph_bbox':r['source_glyph_bbox'],'full_cell_bbox':r['full_cell_bbox'],
 'source_alpha32_bbox':box(sub['source'][:,:,3]>32,(x0,y0)),
 'B357_alpha32_bbox':box(old,(x0,y0)),
 'B358_alpha32_bbox':box(cur,(x0,y0)),
 'B357_visible_alpha32_outside_source_glyph_bbox':int(np.count_nonzero(old & outside)),
 'B358_visible_alpha32_outside_source_glyph_bbox':int(np.count_nonzero(cur & outside)),
 'official_visible_alpha32_outside_source_glyph_bbox':int(np.count_nonzero(official & outside)),
 'canonical_clean_nonzero_alpha':int(np.count_nonzero(sub['clean'][:,:,3])),
 'B358_alpha32_pixels_inside_source_glyph_bbox':int(np.count_nonzero(cur&core)),
 'B358_alpha32_pixels_full_cell':int(np.count_nonzero(cur)),
 'B358_inherited_B357_visible_alpha32_outside_source':int(np.count_nonzero(cur&old&outside)),
 'clean_to_B358_nonzero_alpha_outside_source':int(np.count_nonzero((sub['clean'][:,:,3]!=sub['B358'][:,:,3])&outside)),
 }
 parts.append(p)
 u,v,w,h=r['render_bbox']
 slices=[(k,R[k][v:h,u:w]) for k in ['source','clean','official','B357','B358']]
 for bg,rgb in [('GRAY',(125,125,125,255)),('BLACK',(0,0,0,255)),('WHITE',(255,255,255,255))]:
  canvas=Image.new('RGB',((w-u)*5,(h-v)+21),(28,28,28))
  d=ImageDraw.Draw(canvas)
  for i,(title,img) in enumerate(slices):
   canvas.paste(composite(img,rgb),(i*(w-u),21));d.text((4+i*(w-u),4),title,fill=(255,255,255))
  for factor in (100,75,50):
   pic=canvas if factor==100 else canvas.resize((round(canvas.width*factor/100),round(canvas.height*factor/100)),Image.Resampling.LANCZOS)
   filename=f'C2_Q212_B358_{id.upper()}_{bg}_{factor}_5WAY.png'
   pic.save(out/filename);evidence.append(filename)
 # Outline the actual English source core and highlight B357-visible vs B358-visible outside English bbox
 for target in ['B357','B358']:
  pic=composite(sub[target],(118,118,118,255)).copy()
  px=np.array(pic);outside_alpha=(sub[target][:,:,3]>32)&outside
  px[outside_alpha]=[255,0,195]
  img=Image.fromarray(px)
  dd=ImageDraw.Draw(img);dd.rectangle((sx-x0,sy-y0,ex-x0-1,ey-y0-1),outline=(0,255,80),width=1)
  filename=f'C2_Q212_B358_{id.upper()}_{target}_SOURCE_CORE_MASK_3X.png'
  img.resize((img.width*3,img.height*3),Image.Resampling.NEAREST).save(out/filename);evidence.append(filename)
 for k in ('source','B358'):
  # RAW source atlas same exact bytes but row order reverse. RGBA actual means reversing only Y.
  filename=f'C2_Q212_B358_{id.upper()}_{k.upper()}_RAW_RGBA.png'
  Image.fromarray(np.ascontiguousarray(R[k][::-1][2048-h:2048-v,u:w]),'RGBA').save(out/filename);evidence.append(filename)
  filename=f'C2_Q212_B358_{id.upper()}_{k.upper()}_FLIPY_RGBA.png'
  Image.fromarray(np.ascontiguousarray(R[k][v:h,u:w]),'RGBA').save(out/filename);evidence.append(filename)
assert stats['official_TO_B358']['changed_rgba_outside_two_cells']==0
assert stats['official_TO_B358']['changed_alpha_outside_two_cells']==0
# r43/r44 must be source core contained in saved trial, regardless prior producer assertion
for p in parts:assert p['B358_visible_alpha32_outside_source_glyph_bbox']==0,p
obj={'reviewer':'C2','queue_index':212,'review_scope':'new B358 saved bytes, not duplicate B357','timestamp_kst':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat(timespec='seconds'),'canonical_source_revision':'Sonic-TV/OR2006Sprites@3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6','sha256':expected,'dds_provenance':heads,'native_size':[2048,2048],'format':'RGBA32','mips':1,'readable_transform':'flip_y','comparisons':stats,'regions':parts,'new_images':evidence,'visual_review':'MUST_BE_DONE_HUMAN_SEPARATELY','C3':'NOT_RUN','RUNTIME_VALIDATION':'UNTESTED'}
(out/'C2_Q212_B358_INDEPENDENT_MACHINE.json').write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'sha':expected['B358'],'comparisons':stats,'regions':parts,'images':len(evidence)},ensure_ascii=False))
