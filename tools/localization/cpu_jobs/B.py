#!/usr/bin/env python3
import hashlib,json,os,struct,urllib.request,zipfile
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFilter,ImageOps
if os.environ.get('OUTRUN_CPU_WORKER')!='github-actions' or os.environ.get('OUTRUN_CPU_ROLE')!='B':raise SystemExit('B hosted worker only')
repo=Path.cwd();run='20261004-B-PRODUCTION19';out=repo/'localization/graphics/role_B'/run;out.mkdir(parents=True,exist_ok=True)
asset='textures/load/spr_sprani_sumo_fe_cvt_Exst/5B65E08C_512x256.dds';url='https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/a95efe01d1f136514cef94b0d9e9fd61df021754/Release/spr_sprani_sumo_fe_cvt_Exst/5B65E08C_512x256.dds'
source=Path('/tmp/5B65E08C_HD.dds');urllib.request.urlretrieve(url,source);sb=source.read_bytes();source_sha=hashlib.sha256(sb).hexdigest()
def load_bytes(data,tmp):Path(tmp).write_bytes(data);return ImageOps.flip(Image.open(tmp).convert('RGBA'))
def comp(im,bg=(55,55,55,255)):z=Image.new('RGBA',im.size,bg);z.alpha_composite(im);return z.convert('RGB')
h=struct.unpack_from('<I',sb,12)[0];w=struct.unpack_from('<I',sb,16)[0];pitch=struct.unpack_from('<I',sb,20)[0];mips=struct.unpack_from('<I',sb,28)[0];fourcc=sb[84:88];bpp=struct.unpack_from('<I',sb,88)[0];masks=struct.unpack_from('<IIII',sb,92)
if not(w==2048 and h==1024 and fourcc==b'\0\0\0\0' and bpp==32 and masks==(0xff,0xff00,0xff0000,0xff000000) and mips==1):raise RuntimeError((w,h,pitch,mips,fourcc,bpp,masks))
hd=load_bytes(sb,'/tmp/hd.dds')
zo=repo/'localization/validation/binary_compare/original/OutRun2_ORIGINAL_matching_FULL_DRAFT.zip';zm=repo/'localization/validation/binary_compare/modified/OutRun2_Korean_GFX_FULL_DRAFT_Test.zip'
with zipfile.ZipFile(zo) as z:ob=z.read(asset)
with zipfile.ZipFile(zm) as z:mb=z.read(asset)
orig=load_bytes(ob,'/tmp/orig.dds');hist=load_bytes(mb,'/tmp/hist.dds');a=np.asarray(orig,dtype=np.int16);b=np.asarray(hist,dtype=np.int16);diff=(np.max(np.abs(a-b),axis=2)>5)&((a[:,:,3]>3)|(b[:,:,3]>3));ys,xs=np.nonzero(diff)
if not len(xs):raise RuntimeError('historical diff empty')
lb=[int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)];hd_base=[x*4 for x in lb];pad=36;cell=[max(0,hd_base[0]-pad),max(0,hd_base[1]-pad),min(w,hd_base[2]+pad),min(h,hd_base[3]+pad)]
# visual proof low-res and HD mapped exact source.
s=comp(orig).crop((max(0,lb[0]-12),max(0,lb[1]-12),min(orig.width,lb[2]+12),min(orig.height,lb[3]+12))).resize(((lb[2]-lb[0]+24)*3,(lb[3]-lb[1]+24)*3),Image.Resampling.NEAREST);k=comp(hist).crop((max(0,lb[0]-12),max(0,lb[1]-12),min(orig.width,lb[2]+12),min(orig.height,lb[3]+12))).resize(s.size,Image.Resampling.NEAREST);c=Image.new('RGB',(s.width+k.width+8,max(s.height,k.height)+30),'white');c.paste(s,(0,30));c.paste(k,(s.width+8,30));ImageDraw.Draw(c).text((5,5),f'LOWRES SRC | HIST diff={lb}',fill='black');c.save(out/'B_PRODUCTION19_5B65E08C_DISCOVERY_CONTACT.jpg',quality=96)
v=comp(hd).crop(tuple(cell));scale=min(1,1600/max(1,v.width));
if scale<1:v=v.resize((round(v.width*scale),round(v.height*scale)),Image.Resampling.LANCZOS)
c=Image.new('RGB',(v.width,v.height+30),'white');c.paste(v,(0,30));ImageDraw.Draw(c).text((5,5),f'HD mapped base={hd_base} cell={cell}',fill='black');c.save(out/'B_PRODUCTION19_5B65E08C_HD_CONTACT.jpg',quality=96)
# full grid.
g=comp(hd);d=ImageDraw.Draw(g)
for x in range(0,w+1,128):d.line((x,0,x,h),fill=(255,0,255),width=1);d.text((x+2,2),str(x),fill=(255,0,255))
for y in range(0,h+1,64):d.line((0,y,w,y),fill=(255,0,255),width=1);d.text((2,y+2),str(y),fill=(255,0,255))
g.save(out/'B_PRODUCTION19_5B65E08C_HD_GRID.jpg',quality=95)
# alpha stats in mapped cell.
ca=np.asarray(hd.crop(tuple(cell)),dtype=np.uint8);border=np.concatenate([ca[:8].reshape(-1,4),ca[-8:].reshape(-1,4),ca[:,:8].reshape(-1,4),ca[:,-8:].reshape(-1,4)]);tf=float(np.mean(border[:,3]<=1));alpha_pixels=int(np.count_nonzero(ca[:,:,3]>1));ab=Image.fromarray(ca[:,:,3],'L').getbbox()
rep={'run':run,'queue_index':164,'asset':asset,'source_url':url,'source_sha256':source_sha,'structure':{'width':w,'height':h,'format':'RGBA32','mips':mips,'raw_orientation':'mirror_y','masks':[hex(x) for x in masks]},'historical_diff_bbox':lb,'mapped_hd_base_bbox':hd_base,'mapped_hd_cell':cell,'cell_border_transparent_fraction':tf,'cell_alpha_pixels':alpha_pixels,'cell_alpha_bbox_local':ab,'source':'SELECT LICENSE','korean':'라이선스 선택','historical_pixels_reusable':False,'candidate_written':False,'status':'ONE_STAGE_TO_RENDER_DIAGNOSTIC_READY'}
(out/'B_PRODUCTION19_5B65E08C_DISCOVERY.json').write_text(json.dumps(rep,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print('B_PRODUCTION19_DISCOVERY',source_sha,lb,hd_base,cell,tf,ab)
