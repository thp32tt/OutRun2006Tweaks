#!/usr/bin/env python3
"""C2 even q060 distinct B359: native persisted SHA and source-clean-final pixel checks."""
from pathlib import Path
import hashlib,json,datetime,struct
import numpy as np
from PIL import Image,ImageDraw
root=Path('/home/chatgpt-runner2/work/outrun-c2-20261010-2150')
g=root/'localization/graphics'
out=g/'role_C/20261010-C2-Q060-B359-INDEPENDENT-NATIVE-FAMILY'
p={
'source':g/'hd_source/OR2-HD-GUI-v0.25.10a/textures/load/spr_sprani_game_cvt_Exst/A064FDFC_1024x512.dds',
'clean':g/'role_B/20261010-B348-Q060-BEST-TIME-SOURCE-COMPONENT-PLATE/B348_BEST_TIME_SOURCE_FIRST_PLATE_READABLE.png',
'official':g/'hd_candidates/textures/load/spr_sprani_game_cvt_Exst/A064FDFC_1024x512.dds',
'B353':g/'role_B/20261010-B353-Q060-ENGLISH-PERROW-MATERIAL-PILOT/B353_Q060_SOURCE_CONTOUR_GOLD_KOREAN_UNAPPROVED.dds',
'B359':g/'role_B/20261010-B359-Q060-CONTOUR-NORMAL-BEVEL-FAMILY/B359_Q060_SOURCE_CONTOUR_GOLD_KOREAN_UNAPPROVED.dds'}
sha={'source':'6a33c7307e33337af085f0fffea081de8659ed1806f4ef4d2a8809d4120cadbc','clean':'a03687d4cd23ede4323dca63f07961061b7ba850c19c3a2f69764020a538bb48','official':'d81d0d144f2c4b8192021f9e0b49c7ad44f753da68d6f5dd66f18fe907d06b01','B353':'a44bf0ade48f6f82dc50e2df739ba9ee7339ac1b5d3557e5ea6e30f8d798e9cc','B359':'6551bdf12b3bed1ce11829d1934934900f92a6aa3ad8d3743b0f97107fa86366'}
for k,v in p.items(): assert hashlib.sha256(v.read_bytes()).hexdigest()==sha[k],k
def read_dds(path):
 b=path.read_bytes();assert b[:4]==b'DDS ' and len(b)==33554560
 h,w=struct.unpack_from('<II',b,12);assert (h,w)==(2048,4096)
 masks=struct.unpack_from('<IIII',b,92)
 assert masks==(255,65280,16711680,4278190080)
 assert struct.unpack_from('<I',b,28)[0]==1
 return np.frombuffer(b,dtype=np.uint8,offset=128).reshape(h,w,4).copy(),b[:128]
raw={};headers={};R={}
for k in ['source','official','B353','B359']:
 ar,head=read_dds(p[k]);raw[k]=ar;headers[k]=head;R[k]=ar[::-1].copy()
assert all(headers['source']==x for x in headers.values())
R['clean']=np.asarray(Image.open(p['clean']).convert('RGBA')).copy()
assert R['clean'].shape==(2048,4096,4)
source_box=(2179,340,3028,474);work_box=(2090,337,3120,485)
smask=np.zeros((2048,4096),bool);x0,y0,x1,y1=source_box;smask[y0:y1,x0:x1]=True
wmask=np.zeros((2048,4096),bool);x0,y0,x1,y1=work_box;wmask[y0:y1,x0:x1]=True
def stat(a,b,mask):
 changed=np.any(R[a]!=R[b],axis=2)
 alpha=R[a][:,:,3]!=R[b][:,:,3]
 return {'rgba_changed':int(changed.sum()),'alpha_changed':int(alpha.sum()),'outside_rgba':int(np.count_nonzero(changed & ~mask)),'outside_alpha':int(np.count_nonzero(alpha & ~mask))}
v={
'SOURCE_TO_CLEAN_source_box':stat('source','clean',smask),
'OFFICIAL_TO_B359_worker_ROI':stat('official','B359',wmask),
'B353_TO_B359_worker_ROI':stat('B353','B359',wmask),
'CLEAN_TO_B359_worker_ROI':stat('clean','B359',wmask),
'SOURCE_TO_B359_worker_ROI':stat('source','B359',wmask)
}
# Saved B359 candidate effect bounding box vs source exact high-alpha bbox via restricted same source region.
def alpha_bbox(a,box,threshold):
 x0,y0,x1,y1=box
 q=R[a][y0:y1,x0:x1,3]>threshold
 yy,xx=np.nonzero(q)
 return [int(x0+xx.min()),int(y0+yy.min()),int(x0+xx.max()+1),int(y0+yy.max()+1)] if len(xx) else None
sb=alpha_bbox('source',source_box,32)
tb=alpha_bbox('B359',source_box,32)
clean_source_alpha=int(np.count_nonzero(R['clean'][source_box[1]:source_box[3],source_box[0]:source_box[2],3]))
def comp(arr,bg):
 f=Image.fromarray(np.ascontiguousarray(arr),'RGBA');b=Image.new('RGBA',f.size,bg);b.alpha_composite(f);return b.convert('RGB')
# New independent 5-way 100/75/50 visuals from persisted bytes; show English + source Clean + old official + B353 rejected + B359 new.
preview=(2030,270,3140,555)
a,b,c,d=preview;w=c-a;h=d-b
newimgs=[]
for bg,color in [('GRAY',(128,128,128,255)),('BLACK',(0,0,0,255)),('WHITE',(255,255,255,255))]:
 pic=Image.new('RGB',(w*5,h+23),(30,30,30));dr=ImageDraw.Draw(pic)
 for idx,key in enumerate(['source','clean','official','B353','B359']):
  dr.text((idx*w+4,5),key,fill=(255,255,255))
  pic.paste(comp(R[key][b:d,a:c],color),(idx*w,23))
 for scale in [100,75,50]:
  image=pic if scale==100 else pic.resize((round(pic.width*scale/100),round(pic.height*scale/100)),Image.Resampling.LANCZOS)
  fname=f'C2_Q060_B359_FIVEWAY_{bg}_{scale}.png';image.save(out/fname);newimgs.append(fname)
for key in ['source','clean','official','B353','B359']:
 for bg,color in [('GRAY',(125,125,125,255)),('BLACK',(0,0,0,255))]:
  x0,y0,x1,y1=source_box
  f=f'C2_Q060_B359_{key.upper()}_{bg}_BESTTIME_NATIVE.png'
  comp(R[key][y0:y1,x0:x1],color).save(out/f);newimgs.append(f)
for key in ['source','B359']:
 ar=raw[key]; f=f'C2_Q060_B359_{key.upper()}_RAW_ROI.png'
 Image.fromarray(np.ascontiguousarray(ar[2048-d:2048-b,a:c]),'RGBA').save(out/f);newimgs.append(f)
 f=f'C2_Q060_B359_{key.upper()}_FLIPY_ROI.png'
 Image.fromarray(np.ascontiguousarray(ar[::-1][b:d,a:c]),'RGBA').save(out/f);newimgs.append(f)
# Direct saved old/new mask inside protected source ROI and entire worker ROI
ch=np.any(R['official']!=R['B359'],axis=2)[b:d,a:c]
rgb=np.zeros((h,w,3),dtype=np.uint8);rgb[:]=128;rgb[ch]=[255,0,165]
im=Image.fromarray(rgb,'RGB');dd=ImageDraw.Draw(im);dd.rectangle((source_box[0]-a,source_box[1]-b,source_box[2]-a-1,source_box[3]-b-1),outline=(0,255,65),width=2)
f='C2_Q060_B359_OFFICIAL_TRIAL_RGBA_CHANGED_MASK.png';im.save(out/f);newimgs.append(f)
machine={'role':'C2','index':60,'shard':'EVEN','timestamp_kst':datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat(timespec='seconds'),'sha256':sha,
'format':'RGBA32','width':4096,'height':2048,'mip_count':1,'dds_headers_exact_equal':True,'orientation':'RAW_Y_MIRROR_TO_READABLE_FLIP_Y','source_bbox':list(source_box),'worker_roi':list(work_box),
'computed_pixel_differences':v,'source_alpha32_bbox':sb,'B359_alpha32_bbox':tb,'source_clean_alpha_nonzero_inside_sourcebox':clean_source_alpha,'images':newimgs,
'RUNTIME_VALIDATION':'UNTESTED','C3':'NOT_RUN','note':'Full authored source CLEAN retains English in non-BEST TIME cells unlike localized B359, therefore CLEAN_TO_B359 outside single ROI is expected other-asset delta, not source damage.'}
(out/'C2_Q060_B359_INDEPENDENT_MACHINE.json').write_text(json.dumps(machine,ensure_ascii=False,indent=2)+'\n')
assert v['OFFICIAL_TO_B359_worker_ROI']['outside_rgba']==0
assert v['OFFICIAL_TO_B359_worker_ROI']['outside_alpha']==0
assert v['SOURCE_TO_CLEAN_source_box']['outside_rgba']==0
print(json.dumps({'date':machine['timestamp_kst'],'changes':v,'bbox':{'source':sb,'B359':tb},'clean_source_alpha':clean_source_alpha,'png':len(newimgs)},ensure_ascii=False))
