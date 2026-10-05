#!/usr/bin/env python3
import os,json,hashlib,struct,urllib.request
from pathlib import Path
from PIL import Image

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted role A required")

COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
base="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+COMMIT
src=Path("/tmp/754F0599.dds"); at=Path("/tmp/754F0599_atlas.json")
urllib.request.urlretrieve(base+"/Release/spr_sprani_sumo_fe_cvt_Exst/754F0599_512x256.dds",src)
urllib.request.urlretrieve(base+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_sumo_fe_cvt_Exst/4x_754F0599_512x256_atlas.json",at)
b=src.read_bytes()
H,W,pitch,depth,mips=struct.unpack_from("<5I",b,12)
pf=struct.unpack_from("<8I",b,76)
m=(pf[4],pf[5],pf[6])
mode="RGBA" if m==(0xff,0xff00,0xff0000) else "BGRA" if m==(0xff0000,0xff00,0xff) else "?"
raw=Image.frombytes("RGBA",(W,H),b[128:],"raw",mode)
flip=raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
regs=json.loads(at.read_text())["regions"]
def cellinfo(im,rect):
    x,y,w,h=rect; c=im.crop((x,y,x+w,y+h)); a=c.getchannel("A"); bb=a.getbbox()
    ac=sum(a.histogram()[1:])
    rgb=c.convert("RGB")
    nonblack=sum(1 for p in rgb.getdata() if p!=(0,0,0))
    return {"alpha_count":ac,"alpha_bbox":bb,"rgb_nonblack":nonblack}
print(json.dumps({
 "structure":{"W":W,"H":H,"pitch":pitch,"depth":depth,"mips":mips,"pf":pf,"rawmode":mode,"global_raw_alpha_bbox":raw.getchannel("A").getbbox(),"global_flip_alpha_bbox":flip.getchannel("A").getbbox()},
 "regions":[{"idx":r["idx"],"rect":r["rect"],"raw_direct":cellinfo(raw,r["rect"]),"flip_direct":cellinfo(flip,r["rect"]),
             "flip_transformed":cellinfo(flip,[r["rect"][0],H-(r["rect"][1]+r["rect"][3]),r["rect"][2],r["rect"][3]])} for r in regs]
},indent=2))
