#!/usr/bin/env python3
import hashlib,json,os,struct,urllib.request,zipfile
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFilter,ImageOps
if os.environ.get('OUTRUN_CPU_WORKER')!='github-actions' or os.environ.get('OUTRUN_CPU_ROLE')!='B':raise SystemExit('B hosted worker only')
repo=Path.cwd();run='20261004-B-PRODUCTION17';out=repo/'localization/graphics/role_B'/run;out.mkdir(parents=True,exist_ok=True)
asset='textures/load/spr_sprani_selector_cvt_Exst/788CE557_512x256.dds'
url='https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/a95efe01d1f136514cef94b0d9e9fd61df021754/Release/spr_sprani_selector_cvt_Exst/788CE557_512x256.dds'
source=Path('/tmp/788CE557_HD.dds');urllib.request.urlretrieve(url,source);sb=source.read_bytes();source_sha=hashlib.sha256(sb).hexdigest()

def load_bytes(data,tmp):
 Path(tmp).write_bytes(data);raw=Image.open(tmp).convert('RGBA');return ImageOps.flip(raw)
def load_file(p):return load_bytes(Path(p).read_bytes(),'/tmp/load.dds')
h=struct.unpack_from('<I',sb,12)[0];w=struct.unpack_from('<I',sb,16)[0];pitch=struct.unpack_from('<I',sb,20)[0];mips=struct.unpack_from('<I',sb,28)[0];fourcc=sb[84:88];bpp=struct.unpack_from('<I',sb,88)[0];masks=struct.unpack_from('<IIII',sb,92)
if not(w==2048 and h==1024 and fourcc==b'\0\0\0\0' and bpp==32 and masks==(0xff,0xff00,0xff0000,0xff000000) and mips==1):raise RuntimeError((w,h,pitch,mips,fourcc,bpp,masks))
hd=load_file(source)
zo=repo/'localization/validation/binary_compare/original/OutRun2_ORIGINAL_matching_FULL_DRAFT.zip';zm=repo/'localization/validation/binary_compare/modified/OutRun2_Korean_GFX_FULL_DRAFT_Test.zip'
with zipfile.ZipFile(zo) as z:ob=z.read(asset)
with zipfile.ZipFile(zm) as z:mb=z.read(asset)
orig=load_bytes(ob,'/tmp/orig.dds');hist=load_bytes(mb,'/tmp/hist.dds')
if orig.size!=hist.size:raise RuntimeError('historical size mismatch')
a=np.asarray(orig,dtype=np.int16);b=np.asarray(hist,dtype=np.int16);diff=(np.max(np.abs(a-b),axis=2)>5)&((a[:,:,3]>3)|(b[:,:,3]>3))
# dilate visual diff into label groups.
m=Image.fromarray((diff*255).astype(np.uint8),'L').filter(ImageFilter.MaxFilter(15));arr=np.asarray(m)>0;H,W=arr.shape;seen=np.zeros_like(arr,bool);boxes=[]
for y in range(H):
 for x in range(W):
  if not arr[y,x] or seen[y,x]:continue
  st=[(x,y)];seen[y,x]=1;xs=[];ys=[]
  while st:
   xx,yy=st.pop();xs.append(xx);ys.append(yy)
   for nx,ny in ((xx-1,yy),(xx+1,yy),(xx,yy-1),(xx,yy+1)):
    if 0<=nx<W and 0<=ny<H and arr[ny,nx] and not seen[ny,nx]:seen[ny,nx]=1;st.append((nx,ny))
  if len(xs)>80:boxes.append([max(0,min(xs)-8),max(0,min(ys)-6),min(W,max(xs)+9),min(H,max(ys)+7),len(xs)])
boxes.sort(key=lambda r:(r[1]//20,r[0],r[1]))
def comp(im,bg=(55,55,55,255)):
 z=Image.new('RGBA',im.size,bg);z.alpha_composite(im);return z.convert('RGB')
# source grid.
g=comp(hd);g.thumbnail((2048,1024));d=ImageDraw.Draw(g)
for x in range(0,2049,128):d.line((x,0,x,g.height),fill=(255,0,255),width=1);d.text((x+2,2),str(x),fill=(255,0,255))
for y in range(0,1025,64):d.line((0,y,2048,y),fill=(255,0,255),width=1);d.text((2,y+2),str(y),fill=(255,0,255))
g.save(out/'B_PRODUCTION17_788CE557_HD_GRID.jpg',quality=95)
# source vs historical diff contact at low res, then upscale 2x for inspection.
rows=[]
for i,bb in enumerate(boxes,1):
 x0,y0,x1,y1,_=bb;pad=8;cr=(max(0,x0-pad),max(0,y0-pad),min(orig.width,x1+pad),min(orig.height,y1+pad));s=comp(orig).crop(cr).resize(((cr[2]-cr[0])*2,(cr[3]-cr[1])*2),Image.Resampling.NEAREST);k=comp(hist).crop(cr).resize(s.size,Image.Resampling.NEAREST);c=Image.new('RGB',(s.width+k.width+8,max(s.height,k.height)+28),'white');c.paste(s,(0,28));c.paste(k,(s.width+8,28));ImageDraw.Draw(c).text((4,4),f'{i} lowres bbox={bb[:4]} SRC | HIST',fill='black');rows.append(c)
if rows:
 CW=max(x.width for x in rows);CH=sum(x.height for x in rows)+6*(len(rows)-1);sheet=Image.new('RGB',(CW,CH),'white');yy=0
 for c in rows:sheet.paste(c,(0,yy));yy+=c.height+6
 sheet.save(out/'B_PRODUCTION17_788CE557_DISCOVERY_CONTACT.jpg',quality=96)
# HD mapped crops x4 from each historical group.
hrows=[]
for i,bb in enumerate(boxes,1):
 x0,y0,x1,y1,_=bb;cr=(max(0,x0*4-40),max(0,y0*4-28),min(2048,x1*4+40),min(1024,y1*4+28));v=comp(hd).crop(cr);scale=min(1,1300/max(1,v.width));
 if scale<1:v=v.resize((round(v.width*scale),round(v.height*scale)),Image.Resampling.LANCZOS)
 c=Image.new('RGB',(v.width,v.height+30),'white');c.paste(v,(0,30));ImageDraw.Draw(c).text((4,5),f'{i} HD mapped={cr}',fill='black');hrows.append(c)
if hrows:
 CW=max(x.width for x in hrows);CH=sum(x.height for x in hrows)+6*(len(hrows)-1);sheet=Image.new('RGB',(CW,CH),'white');yy=0
 for c in hrows:sheet.paste(c,(0,yy));yy+=c.height+6
 sheet.save(out/'B_PRODUCTION17_788CE557_HD_CONTACT.jpg',quality=96)
report={'run':run,'queue_index':106,'asset':asset,'source_url':url,'source_sha256':source_sha,'structure':{'width':w,'height':h,'format':'RGBA32','mips':mips,'raw_orientation':'mirror_y','header_masks':[hex(x) for x in masks]},'historical_discovery_boxes':boxes,'mapped_hd_boxes':[[b[0]*4,b[1]*4,b[2]*4,b[3]*4] for b in boxes],'translations':[{'source':'For Experts','korean':'상급자용'},{'source':'OutRun2SP','korean':'아웃런2 SP'},{'source':'Music Change','korean':'음악 변경'},{'source':'Time remaining :','korean':'남은 시간:'}],'historical_pixels_reusable':False,'candidate_written':False,'status':'ONE_STAGE_TO_RENDER_DIAGNOSTIC_READY'}
(out/'B_PRODUCTION17_788CE557_DISCOVERY.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('B_PRODUCTION17_DISCOVERY',source_sha,'groups',len(boxes),boxes)
