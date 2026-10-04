#!/usr/bin/env python3
import hashlib,json,os,struct,zipfile
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageFilter
if os.environ.get('OUTRUN_CPU_WORKER')!='github-actions' or os.environ.get('OUTRUN_CPU_ROLE')!='B': raise SystemExit('B hosted worker only')
repo=Path.cwd(); run='20261004-B-RECOVERY09'; out=repo/'localization/graphics/role_B'/run; out.mkdir(parents=True,exist_ok=True)
asset='textures/load/spr_sprani_ranking_cvt_Exst/C598919A_1024x1024.dds'
zo=repo/'localization/validation/binary_compare/original/OutRun2_ORIGINAL_matching_FULL_DRAFT.zip'; zm=repo/'localization/validation/binary_compare/modified/OutRun2_Korean_GFX_FULL_DRAFT_Test.zip'
def load(data):
 h=struct.unpack_from('<I',data,12)[0];w=struct.unpack_from('<I',data,16)[0]; fourcc=data[84:88];
 p=Path('/tmp/x.dds');p.write_bytes(data); raw=Image.open(p).convert('RGBA'); return raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM),(w,h,fourcc.decode('latin1'))
with zipfile.ZipFile(zo) as z: sb=z.read(asset)
with zipfile.ZipFile(zm) as z: hb=z.read(asset)
source,sm=load(sb); hist,hm=load(hb)
if sm!=hm or sm[:2]!=(4096,4096) or sm[2]!='DXT5': raise RuntimeError((sm,hm))
source_sha=hashlib.sha256(sb).hexdigest(); hist_sha=hashlib.sha256(hb).hexdigest()
sa=np.asarray(source,dtype=np.uint8); ha=np.asarray(hist,dtype=np.uint8)
diff=np.any(sa!=ha,axis=2); visible=(sa[:,:,3]>3)|(ha[:,:,3]>3); m=(diff&visible)
# Merge glyphs into label-sized components with anisotropic dilation, then extract sizable components.
mask=Image.fromarray((m*255).astype(np.uint8),'L').filter(ImageFilter.MaxFilter(31))
arr=np.asarray(mask)>0; H,W=arr.shape;seen=np.zeros_like(arr,bool); comps=[]
for y in range(H):
 for x in range(W):
  if not arr[y,x] or seen[y,x]:continue
  st=[(x,y)];seen[y,x]=1;xs=[];ys=[]
  while st:
   xx,yy=st.pop();xs.append(xx);ys.append(yy)
   for nx,ny in ((xx-1,yy),(xx+1,yy),(xx,yy-1),(xx,yy+1)):
    if 0<=nx<W and 0<=ny<H and arr[ny,nx] and not seen[ny,nx]:seen[ny,nx]=1;st.append((nx,ny))
  if len(xs)>400:
   x0=max(0,min(xs)-24);y0=max(0,min(ys)-18);x1=min(W,max(xs)+25);y1=min(H,max(ys)+19)
   comps.append([x0,y0,x1,y1,len(xs)])
# sort reading order. Some close labels can merge; evidence is diagnostic only.
comps.sort(key=lambda b:(b[1]//90,b[0],b[1]))
font=ImageFont.load_default()
def composite(im):
 bg=Image.new('RGBA',im.size,(64,64,64,255));bg.alpha_composite(im);return bg.convert('RGB')
src_rgb=composite(source); hist_rgb=composite(hist)
# full overview with grid and component ids
ov=src_rgb.resize((2048,2048),Image.Resampling.LANCZOS); d=ImageDraw.Draw(ov)
for i,b in enumerate(comps,1):
 x0,y0,x1,y1,_=b; d.rectangle((x0//2,y0//2,x1//2,y1//2),outline=(255,0,255),width=2); d.text((x0//2+2,y0//2+2),str(i),fill=(255,0,255),font=font)
ov.save(out/'B_RECOVERY09_C598_SOURCE_BOX_OVERVIEW.jpg',quality=95)
# contact rows: source | historical candidate, 1:1 capped to 1600 width each
rows=[]
for i,b in enumerate(comps,1):
 x0,y0,x1,y1,_=b; s=src_rgb.crop((x0,y0,x1,y1));h=hist_rgb.crop((x0,y0,x1,y1));
 scale=min(1.0,1100/max(1,s.width));
 if scale<1: ns=(round(s.width*scale),round(s.height*scale));s=s.resize(ns,Image.Resampling.LANCZOS);h=h.resize(ns,Image.Resampling.LANCZOS)
 ch=max(s.height,h.height)+34; c=Image.new('RGB',(s.width+h.width+10,ch),'white');c.paste(s,(0,34));c.paste(h,(s.width+10,34));ImageDraw.Draw(c).text((5,5),f'{i} bbox={b[:4]} SRC | HIST',fill='black',font=font);rows.append(c)
CW=max(x.width for x in rows); CH=sum(x.height for x in rows)+4*(len(rows)-1); sheet=Image.new('RGB',(CW,CH),'white');yy=0
for c in rows:sheet.paste(c,(0,yy));yy+=c.height+4
sheet.save(out/'B_RECOVERY09_C598_DISCOVERY_CONTACT.jpg',quality=96)
# Four source strips with 128px coordinate grid for manual cell recovery.
for j,y0 in enumerate(range(0,4096,1024),1):
 strip=src_rgb.crop((0,y0,4096,y0+1024)).resize((2048,512),Image.Resampling.LANCZOS);d=ImageDraw.Draw(strip)
 for x in range(0,4097,256):d.line((x//2,0,x//2,512),fill=(255,0,255),width=1);d.text((x//2+1,2),str(x),fill=(255,0,255),font=font)
 for y in range(y0,y0+1025,128):yy=(y-y0)//2;d.line((0,yy,2048,yy),fill=(255,0,255),width=1);d.text((2,yy+1),str(y),fill=(255,0,255),font=font)
 strip.save(out/f'B_RECOVERY09_C598_SOURCE_STRIP{j}.jpg',quality=96)
report={'run':run,'asset':asset,'source_sha256':source_sha,'historical_full_draft_sha256':hist_sha,'dimensions':[4096,4096],'format':'DXT5','raw_orientation':'mirror_y','visible_diff_components_after_dilation':len(comps),'components':[{'id':i+1,'bbox':b[:4],'dilated_pixels':b[4]} for i,b in enumerate(comps)],'usage':'historical candidate is discovery evidence only; no historical localized pixels may be reused in final candidate','candidate_written':False,'status':'PREFLIGHT_DIAGNOSTIC_READY_FOR_SAME_INVOCATION_RENDER'}
(out/'B_RECOVERY09_C598_DISCOVERY.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('B_RECOVERY09_DISCOVERY',source_sha,hist_sha,'components',len(comps))
