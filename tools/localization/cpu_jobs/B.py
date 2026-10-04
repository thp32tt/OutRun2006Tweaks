#!/usr/bin/env python3
import hashlib,json,os,struct,urllib.request,zipfile
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageFilter

if os.environ.get('OUTRUN_CPU_WORKER')!='github-actions' or os.environ.get('OUTRUN_CPU_ROLE')!='B':
    raise SystemExit('B hosted worker only')
repo=Path.cwd(); run='20261004-B-PRODUCTION16'
out=repo/'localization/graphics/role_B'/run; out.mkdir(parents=True,exist_ok=True)
asset='textures/load/spr_sprani_selector_cvt_Exst/53CE39D5_512x512.dds'
url='https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/a95efe01d1f136514cef94b0d9e9fd61df021754/Release/spr_sprani_selector_cvt_Exst/53CE39D5_512x512.dds'
srcp=Path('/tmp/53CE39D5_release.dds');urllib.request.urlretrieve(url,srcp)
srcb=srcp.read_bytes(); source_sha=hashlib.sha256(srcb).hexdigest()
if source_sha!='cfed1de58cefd8c235fc464e27058439ffd26427294a3bce17192e584679426a':raise RuntimeError(source_sha)
def load(p_or_bytes):
    if isinstance(p_or_bytes,(bytes,bytearray)):
        p=Path('/tmp/diag.dds');p.write_bytes(p_or_bytes)
    else:p=Path(p_or_bytes)
    b=p.read_bytes();h=struct.unpack_from('<I',b,12)[0];w=struct.unpack_from('<I',b,16)[0]
    raw=Image.frombytes('RGBA',(w,h),b[128:],'raw','RGBA')
    return raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM),(w,h,b[84:88].hex(),struct.unpack_from('<I',b,88)[0])
source,sm=load(srcp)
zo=repo/'localization/validation/binary_compare/original/OutRun2_ORIGINAL_matching_FULL_DRAFT.zip'
zm=repo/'localization/validation/binary_compare/modified/OutRun2_Korean_GFX_FULL_DRAFT_Test.zip'
with zipfile.ZipFile(zo) as z:ob=z.read(asset)
with zipfile.ZipFile(zm) as z:hb=z.read(asset)
old,om=load(ob);hist,hm=load(hb)
if old.size!=hist.size or source.size[0]%old.size[0] or source.size[1]%old.size[1]:raise RuntimeError((source.size,old.size,hist.size))
scale_x=source.size[0]//old.size[0]; scale_y=source.size[1]//old.size[1]
oa=np.asarray(old,dtype=np.uint8);ha=np.asarray(hist,dtype=np.uint8)
diff=np.any(oa!=ha,axis=2)&((oa[:,:,3]>1)|(ha[:,:,3]>1))
mask=np.asarray(Image.fromarray((diff*255).astype(np.uint8),'L').filter(ImageFilter.MaxFilter(13)))>0
H,W=mask.shape;seen=np.zeros_like(mask,bool);comps=[]
for y in range(H):
  for x in range(W):
    if not mask[y,x] or seen[y,x]:continue
    st=[(x,y)];seen[y,x]=1;xs=[];ys=[]
    while st:
      xx,yy=st.pop();xs.append(xx);ys.append(yy)
      for nx,ny in ((xx-1,yy),(xx+1,yy),(xx,yy-1),(xx,yy+1)):
        if 0<=nx<W and 0<=ny<H and mask[ny,nx] and not seen[ny,nx]:seen[ny,nx]=1;st.append((nx,ny))
    if len(xs)>500:comps.append([max(0,min(xs)-22),max(0,min(ys)-18),min(W,max(xs)+23),min(H,max(ys)+19),len(xs)])
comps.sort(key=lambda b:(b[1]//80,b[0],b[1]))
low_comps=[b[:] for b in comps]
comps=[[b[0]*scale_x,b[1]*scale_y,b[2]*scale_x,b[3]*scale_y,b[4]] for b in low_comps]
font=ImageFont.load_default()
def comp(im):
    b=Image.new('RGBA',im.size,(64,64,64,255));b.alpha_composite(im);return b.convert('RGB')
src_rgb=comp(source);old_rgb=comp(old);hist_rgb=comp(hist)
ov=src_rgb.copy();d=ImageDraw.Draw(ov)
for i,b in enumerate(comps,1):
    d.rectangle(tuple(b[:4]),outline=(255,0,255),width=3);d.text((b[0]+3,b[1]+3),str(i),fill=(255,0,255),font=font)
ov.resize((1024,1024),Image.Resampling.LANCZOS).save(out/'B_PRODUCTION16_53CE_SOURCE_BOX_OVERVIEW.jpg',quality=96)
rows=[]
for i,(lb,b) in enumerate(zip(low_comps,comps),1):
    cr=tuple(b[:4]); lcr=tuple(lb[:4]); release=src_rgb.crop(cr)
    oldc=old_rgb.crop(lcr).resize(release.size,Image.Resampling.NEAREST); histc=hist_rgb.crop(lcr).resize(release.size,Image.Resampling.NEAREST)
    ims=[oldc,histc,release];scale=min(1.0,600/max(1,ims[0].width))
    if scale<1:
        ns=(round(ims[0].width*scale),round(ims[0].height*scale));ims=[q.resize(ns,Image.Resampling.LANCZOS) for q in ims]
    h=max(q.height for q in ims)+30;c=Image.new('RGB',(sum(q.width for q in ims)+12,h),'white');xx=0
    for q in ims:c.paste(q,(xx,30));xx+=q.width+6
    ImageDraw.Draw(c).text((4,4),f'{i} bbox={b[:4]} OLD | HIST | RELEASE',fill='black');rows.append(c)
cw=max(q.width for q in rows);ch=sum(q.height for q in rows)+4*(len(rows)-1);sheet=Image.new('RGB',(cw,ch),'white');yy=0
for q in rows:sheet.paste(q,(0,yy));yy+=q.height+4
sheet.save(out/'B_PRODUCTION16_53CE_DISCOVERY_CONTACT.jpg',quality=96)
# coordinate grid for exact release source
grid=src_rgb.resize((1024,1024),Image.Resampling.LANCZOS);d=ImageDraw.Draw(grid)
for x in range(0,2049,128):d.line((x//2,0,x//2,1024),fill=(255,0,255),width=1);d.text((x//2+1,2),str(x),fill=(255,0,255),font=font)
for y in range(0,2049,128):d.line((0,y//2,1024,y//2),fill=(255,0,255),width=1);d.text((2,y//2+1),str(y),fill=(255,0,255),font=font)
grid.save(out/'B_PRODUCTION16_53CE_RELEASE_GRID.jpg',quality=96)
(out/'B_PRODUCTION16_53CE_DISCOVERY.json').write_text(json.dumps({'asset':asset,'source_url':url,'source_sha256':source_sha,'source_structure':sm,'historical_original_sha256':hashlib.sha256(ob).hexdigest(),'historical_candidate_sha256':hashlib.sha256(hb).hexdigest(),'components':[{'id':i+1,'bbox':b[:4]} for i,b in enumerate(comps)],'candidate_written':False,'status':'DIAGNOSTIC_READY_FOR_SAME_INVOCATION_RENDER'},indent=2)+'\n')
print('B_PRODUCTION16_DISCOVERY',source_sha,'components',len(comps))
