#!/usr/bin/env python3
import os,json,struct,urllib.request
from pathlib import Path
from PIL import Image,ImageDraw

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted role A required")
repo=Path.cwd(); out=repo/"localization/graphics/role_A/20261005-A-PRODUCTION28-PREFLIGHT"; out.mkdir(parents=True,exist_ok=True)
COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"; base="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+COMMIT
src=Path("/tmp/754F0599.dds"); at=Path("/tmp/754F0599_atlas.json")
urllib.request.urlretrieve(base+"/Release/spr_sprani_sumo_fe_cvt_Exst/754F0599_512x256.dds",src)
urllib.request.urlretrieve(base+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_sumo_fe_cvt_Exst/4x_754F0599_512x256_atlas.json",at)
b=src.read_bytes(); H,W=struct.unpack_from("<2I",b,12); pf=struct.unpack_from("<8I",b,76); masks=(pf[4],pf[5],pf[6])
mode="RGBA" if masks==(0xff,0xff00,0xff0000) else "BGRA"
raw=Image.frombytes("RGBA",(W,H),b[128:],"raw",mode); flip=raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
def gray(im):
    z=Image.new("RGBA",im.size,(100,100,100,255)); z.alpha_composite(im); return z.convert("RGB")
gray(raw).save(out/"A28_SOURCE_RAW_GRAY.jpg",quality=96)
gray(flip).save(out/"A28_SOURCE_FLIP_GRAY.jpg",quality=96)
regs=json.loads(at.read_text())["regions"]
# raw-atlas aligned crops with idx labels
crops=[]
for r in regs:
    x,y,w,h=r["rect"]; im=gray(raw.crop((x,y,x+w,y+h)))
    canvas=Image.new("RGB",(im.width,im.height+28),(235,235,235)); canvas.paste(im,(0,28))
    ImageDraw.Draw(canvas).text((3,4),f"idx {r['idx']} raw-atlas cell",fill=(0,0,0)); crops.append(canvas)
cw=max(x.width for x in crops); ch=sum(x.height for x in crops)+4*(len(crops)-1)
sheet=Image.new("RGB",(cw,ch),(235,235,235)); yy=0
for im in crops: sheet.paste(im,(0,yy)); yy+=im.height+4
sheet.save(out/"A28_RAW_ATLAS_ROWS.jpg",quality=96)
# same source pixels transformed to flip/readable locations, still labeled by atlas idx
crops=[]
for r in regs:
    x,y,w,h=r["rect"]; fy=H-(y+h); im=gray(flip.crop((x,fy,x+w,fy+h)))
    canvas=Image.new("RGB",(im.width,im.height+28),(235,235,235)); canvas.paste(im,(0,28))
    ImageDraw.Draw(canvas).text((3,4),f"idx {r['idx']} flip-transformed cell",fill=(0,0,0)); crops.append(canvas)
cw=max(x.width for x in crops); ch=sum(x.height for x in crops)+4*(len(crops)-1)
sheet=Image.new("RGB",(cw,ch),(235,235,235)); yy=0
for im in crops: sheet.paste(im,(0,yy)); yy+=im.height+4
sheet.save(out/"A28_FLIP_TRANSFORMED_ROWS.jpg",quality=96)
(out/"A28_PREFLIGHT.json").write_text(json.dumps({"run":"20261005-A-PRODUCTION28-PREFLIGHT","asset":"754F0599","dimensions":[W,H],"raw_mode":mode,"purpose":"semantic/orientation binding before same-invocation candidate construction","runtime_validation":"UNTESTED"},indent=2)+"\n")
