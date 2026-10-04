#!/usr/bin/env python3
import hashlib, json, os, struct, urllib.request
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

if os.environ.get('OUTRUN_CPU_WORKER')!='github-actions' or os.environ.get('OUTRUN_CPU_ROLE')!='B':
    raise SystemExit('GitHub-hosted localization CPU worker / role B only')
repo=Path.cwd(); outdir=repo/'localization/graphics/role_B/20261004-B-RECOVERY07'; outdir.mkdir(parents=True,exist_ok=True)
url='https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/a95efe01d1f136514cef94b0d9e9fd61df021754/Release/spr_sprani_etc_cvt_Exst/B1696633_512x512.dds'
p=Path('/tmp/B1696633_HD.dds'); urllib.request.urlretrieve(url,p)
b=p.read_bytes(); sha=hashlib.sha256(b).hexdigest(); expected='3c58bf9587d0454e5bb8733bd35c5b2613b11c7fd52c49a428f0fa5fb4cea12d'
if sha!=expected: raise RuntimeError('source SHA mismatch')
h=struct.unpack_from('<I',b,12)[0];w=struct.unpack_from('<I',b,16)[0];masks=struct.unpack_from('<IIII',b,92)
if (w,h)!=(2048,2048) or masks!=(0xff,0xff00,0xff0000,0xff000000): raise RuntimeError((w,h,masks))
raw=Image.frombytes('RGBA',(w,h),b[128:],'raw','RGBA'); src=raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
font_path='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'; f=ImageFont.truetype(font_path,18)
def grid_crop(name,box,step=64):
    bg=Image.new('RGBA',src.size,(72,72,72,255)); bg.alpha_composite(src); im=bg.convert('RGB').crop(box); d=ImageDraw.Draw(im)
    x0,y0,x1,y1=box
    for x in range(((x0+step-1)//step)*step,x1,step):
        xx=x-x0; d.line((xx,0,xx,im.height),fill=(255,0,255),width=1); d.text((xx+2,2),str(x),font=f,fill=(255,0,255))
    for y in range(((y0+step-1)//step)*step,y1,step):
        yy=y-y0; d.line((0,yy,im.width,yy),fill=(255,0,255),width=1); d.text((2,yy+2),str(y),font=f,fill=(255,0,255))
    im.save(outdir/name,quality=96)
grid_crop('B_RECOVERY07_B1696633_HD_HEADER_GRID.jpg',(0,600,2048,960),32)
grid_crop('B_RECOVERY07_B1696633_HD_BOTTOM_GRID.jpg',(0,1400,2048,1980),32)
(outdir/'B_RECOVERY07_HD_GRID_DIAGNOSTIC.json').write_text(json.dumps({'status':'PREFLIGHT_DIAGNOSTIC_EXACT_HD_GRID','source_sha256':sha,'dimensions':[w,h],'raw_orientation':'mirror_y','header_crop':[0,600,2048,960],'bottom_crop':[0,1400,2048,1980],'candidate_written':False},indent=2)+'\n')
print('B_RECOVERY07_HD_GRID_DIAGNOSTIC_DONE',sha)
