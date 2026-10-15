#!/usr/bin/env python3
"""Bulk ROI proposals from complete registered PNGs, never split-tile inputs."""
import json,hashlib,math,sys
from pathlib import Path
import numpy as np
from PIL import Image,ImageFilter,ImageDraw
root=Path('/home/chatgpt-runner2')
inv=json.loads((root/'work/image-src/text_roi_batches/full_source_inventory.json').read_text())
out=root/'work/c_salvage_text_roi/full_bulk_20261015'
out.mkdir(parents=True,exist_ok=True)
direct=root/'work/c_salvage_text_roi/source_full_20261012'
summary={'source_total':len(inv['sources']),'translation_total':0,'processed_sources':0,'candidate_pngs':0,'hold_sources':[],'status':'TEST_ONLY_REVIEW_REQUIRED','results':[]}
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for c in iter(lambda:f.read(1048576),b''):h.update(c)
 return h.hexdigest()
def regions(im):
 W,H=im.size;sw=max(1,round(W*min(1,640/max(W,H))));sh=max(1,round(H*min(1,640/max(W,H))))
 small=im.getchannel('A').resize((sw,sh),Image.Resampling.NEAREST).point(lambda v:255 if v>=25 else 0)
 if sw>12 and sh>12:small=small.filter(ImageFilter.MaxFilter(5))
 a=np.asarray(small)>0
 # Connected horizontal row runs and union-find, scaled back to full-HD.
 par=[];rect=[];last=[]
 def find(n):
  while par[n]!=n:par[n]=par[par[n]];n=par[n]
  return n
 for y in range(sh):
  r=a[y].astype(np.int8)
  diff=np.diff(np.pad(r,(1,1)))
  runs=list(zip(np.where(diff==1)[0],np.where(diff==-1)[0]))
  new=[];idx=0
  for left,right in runs:
   n=len(par);par.append(n);rect.append((int(left),y,int(right),y+1))
   new.append((int(left),int(right),n))
   while idx<len(last) and last[idx][1]<left-1:idx+=1
   for L,R,p in last[idx:]:
    if L>right+1:break
    p=find(p);q=find(n)
    if p!=q:par[p]=q
  last=new
 boxes={}
 for i,b in enumerate(rect):
  k=find(i)
  if k not in boxes:boxes[k]=list(b)
  else:
   bb=boxes[k]
   bb[0]=min(bb[0],b[0]);bb[1]=min(bb[1],b[1])
   bb[2]=max(bb[2],b[2]);bb[3]=max(bb[3],b[3])
 candidates=[]
 for x0,y0,x1,y1 in boxes.values():
  if x1-x0<max(6,sw//140) or y1-y0<max(3,sh//180):continue
  margin=max(10,round((y1-y0)*H/sh*.06))
  x0=max(0,math.floor(x0*W/sw)-margin);x1=min(W,math.ceil(x1*W/sw)+margin)
  y0=max(0,math.floor(y0*H/sh)-margin);y1=min(H,math.ceil(y1*H/sh)+margin)
  if (x1-x0)*(y1-y0)>2048*2048:continue
  candidates.append([x0,y0,x1,y1])
 # Merge horizontally touching word fragments sharing almost the same line.
 for _ in range(3):
  changed=False
  for i in range(len(candidates)):
   if changed:break
   x0,y0,x1,y1=candidates[i]
   for j in range(i+1,len(candidates)):
    X0,Y0,X1,Y1=candidates[j]
    overlap=max(0,min(y1,Y1)-max(y0,Y0))
    if overlap<.65*min(y1-y0,Y1-Y0):continue
    gap=max(0,X0-x1,x0-X1)
    if gap>min(80,max(16,round(.22*max(y1-y0,Y1-Y0)))):continue
    candidates[i]=[min(x0,X0),min(y0,Y0),max(x1,X1),max(y1,Y1)]
    del candidates[j];changed=True;break
  if not changed:break
 return sorted(candidates,key=lambda z:(z[1],z[0]))[:50]
for n,item in enumerate(inv['sources']):
 trans=item.get('translated_phrases') or []
 summary['translation_total']+=len(trans)
 if not trans:continue
 name=item['source_png'];stem=Path(name).stem
 src=root/item.get('png_path','__absent__')
 provenance='UNVERIFIED_REASSEMBLED_FULL_SOURCE'
 if name=='Q104_62BEBF33_BASE_READABLE_FLIPY.png':
  p=direct/'q104_62BEBF33_READABLE_FLIPY.png'
  if p.exists():src=p;provenance='DIRECT_GITHUB_FULL_HD_SOURCE'
 if name=='Q102_571E78F3_BASE_READABLE_FLIPY.png':
  p=direct/'q102_571E78F3_READABLE_FLIPY.png'
  if p.exists():src=p;provenance='DIRECT_GITHUB_FULL_HD_SOURCE'
 record={'source':name,'provenance':provenance,'phrases':[(t['english'],t['korean']) for t in trans],'candidate_rois':[]}
 try:
  if not src.exists():raise ValueError('MISSING_COMPLETE_SOURCE')
  digest=sha(src)
  if provenance!='DIRECT_GITHUB_FULL_HD_SOURCE' and digest!=item['png_sha256']:raise ValueError('SOURCE_SHA_MISMATCH')
  with Image.open(src) as o:
   if o.format!='PNG' or o.mode!='RGBA' or list(o.size)!=item['source_dimensions']:raise ValueError('BAD_DIMENSIONS_OR_FORMAT')
   im=o.copy()
  boxes=regions(im)
  folder=out/'sources'/stem
  folder.mkdir(exist_ok=True,parents=True)
  pre=im.copy();pre.thumbnail((900,900))
  bg=Image.new('RGBA',pre.size,(55,55,55,255));bg.alpha_composite(pre);draw=ImageDraw.Draw(bg)
  for k,bb in enumerate(boxes,1):
   x0,y0,x1,y1=bb;ww=x1-x0;hh=y1-y0
   scale=next((z for z in (4,3,2,1) if ww*z<=2048 and hh*z<=2048 and ww*hh*z*z<=2048*2048),0)
   if not scale:continue
   dest=folder/('%03d'%k);dest.mkdir(exist_ok=True)
   native=im.crop(tuple(bb));native.save(dest/'english_roi.png')
   zoom=native.resize((ww*scale,hh*scale),Image.Resampling.LANCZOS);zoom.save(dest/'imagegen_input_REVIEW.png')
   am=np.asarray(native.getchannel('A'))>25
   edge=bool(am[:2].any() or am[-2:].any() or am[:,:2].any() or am[:,-2:].any())
   m={'schema':'outrun-phrase-roi-bulk-v1','status':'HOLD_REVIEW_REQUIRED','source_png':name,'source_sha256':digest,
      'source_kind':provenance,'dds_equivalence':item.get('native_dds_equivalence','UNVERIFIED'),
      'native_source_bbox_xyxy':bb,'upscale':scale,'original_english':None,'approved_korean':None,
      'translation_options':record['phrases'],'edge_alpha_present':edge,
      'imagegen_png_sha256':sha(dest/'imagegen_input_REVIEW.png'),'RUNTIME_VALIDATION':'UNTESTED'}
   (dest/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2))
   record['candidate_rois'].append({'index':k,'bbox':bb,'upscale':scale,'path':str(dest.relative_to(out)),'edge_alpha':edge})
   summary['candidate_pngs']+=1
   c=(int(bb[0]*pre.width/im.width),int(bb[1]*pre.height/im.height),int(bb[2]*pre.width/im.width),int(bb[3]*pre.height/im.height))
   draw.rectangle(c,outline=(255,180,0,255),width=2);draw.text((c[0]+1,c[1]+1),str(k),fill=(255,0,50,255))
  bg.convert('RGB').save(folder/'review.jpg',quality=75)
  record['status']='EXTRACTED_UNMAPPED_PROPOSALS'
  summary['processed_sources']+=1
 except Exception as e:
  record['status']='HOLD_SOURCE';record['reason']=str(e)
  summary['hold_sources'].append({'source':name,'reason':str(e)})
 summary['results'].append(record)
 if n%10==0:
  (out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
  print('PROGRESS',n,'sources',summary['processed_sources'],'candidates',summary['candidate_pngs'],flush=True)
(out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
print(json.dumps({k:v for k,v in summary.items() if k!='results'},ensure_ascii=False))