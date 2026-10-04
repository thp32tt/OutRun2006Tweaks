#!/usr/bin/env python3
import hashlib, json, os, struct, urllib.request
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

if os.environ.get('OUTRUN_CPU_WORKER') != 'github-actions' or os.environ.get('OUTRUN_CPU_ROLE') != 'B':
    raise SystemExit('GitHub-hosted localization CPU worker / role B only')
repo=Path.cwd(); run='20261004-B-RECOVERY08'
out=repo/'localization/graphics/role_B'/run; out.mkdir(parents=True,exist_ok=True)
work=Path('/tmp/outrun_B_recovery08'); work.mkdir(parents=True,exist_ok=True)
source=work/'CBF8ECBF_HD.dds'
url='https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/a95efe01d1f136514cef94b0d9e9fd61df021754/Release/spr_sprani_etc_cvt_Exst/CBF8ECBF_1024x512.dds'
expected='3a2a40256a6c3c945dfd4fab275edba5ec05802e4cff54f2ad93d5196cd992fe'
urllib.request.urlretrieve(url,source)
b=source.read_bytes(); got=hashlib.sha256(b).hexdigest()
if got!=expected: raise RuntimeError((got,expected))
if b[:4]!=b'DDS ': raise RuntimeError('not DDS')
h=struct.unpack_from('<I',b,12)[0]; w=struct.unpack_from('<I',b,16)[0]; pitch=struct.unpack_from('<I',b,20)[0]; mips=struct.unpack_from('<I',b,28)[0]
fourcc=b[84:88]; bpp=struct.unpack_from('<I',b,88)[0]; masks=struct.unpack_from('<IIII',b,92)
if not (w==4096 and h==2048 and pitch==w*4 and mips==1 and fourcc==b'\0\0\0\0' and bpp==32 and masks==(0xff,0xff00,0xff0000,0xff000000) and len(b)==128+w*h*4):
    raise RuntimeError((w,h,pitch,mips,fourcc,bpp,masks,len(b)))
raw=Image.frombytes('RGBA',(w,h),b[128:],'raw','RGBA')
readable=raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)

def comp(im,bg=(72,72,72,255)):
    z=Image.new('RGBA',im.size,bg); z.alpha_composite(im); return z.convert('RGB')
def label(im,title):
    x=comp(im); x.thumbnail((1600,800)); c=Image.new('RGB',(x.width,x.height+36),'white'); c.paste(x,(0,36)); ImageDraw.Draw(c).text((8,8),title,fill='black'); return c
r1=label(readable,'READABLE / mirror_y corrected'); r2=label(raw,'RAW DDS');
sheet=Image.new('RGB',(max(r1.width,r2.width),r1.height+r2.height+8),'white'); sheet.paste(r1,(0,0)); sheet.paste(r2,(0,r1.height+8)); sheet.save(out/'B_RECOVERY08_CBF8ECBF_SOURCE_ORIENTATION.jpg',quality=94)
# readable 128px grid at 50% scale to resolve text cell coordinates while keeping labels legible
view=comp(readable).resize((2048,1024),Image.Resampling.LANCZOS); d=ImageDraw.Draw(view)
for x in range(0,4097,128):
    xx=x//2; d.line((xx,0,xx,1024),fill=(255,0,255),width=1); d.text((xx+2,2),str(x),fill=(255,0,255))
for y in range(0,2049,128):
    yy=y//2; d.line((0,yy,2048,yy),fill=(255,0,255),width=1); d.text((2,yy+2),str(y),fill=(255,0,255))
view.save(out/'B_RECOVERY08_CBF8ECBF_READABLE_GRID.jpg',quality=96)
# quarter strips to preserve high zoom.
base=comp(readable)
for i,(y0,y1) in enumerate(((0,512),(512,1024),(1024,1536),(1536,2048)),1):
    crop=base.crop((0,y0,4096,y1)); crop.save(out/f'B_RECOVERY08_CBF8ECBF_STRIP{i}.jpg',quality=96)
meta={'status':'PREFLIGHT_DIAGNOSTIC_READY_FOR_SAME_INVOCATION_RENDER','asset':'CBF8ECBF','queue_index':50,'source_url':url,'source_sha256':got,'dimensions':[w,h],'format':'RGBA32','mips':mips,'raw_orientation_hypothesis':'mirror_y','candidate_written':False,'required_segments':['Time Over','Game Over','GOAL','PLEASE WAIT','PLAYERS','YOUR FRIENDS','FRIEND REQUEST']}
(out/'B_RECOVERY08_DIAGNOSTIC.json').write_text(json.dumps(meta,indent=2)+'\n')
print('B_RECOVERY08_DIAGNOSTIC',got,w,h)
