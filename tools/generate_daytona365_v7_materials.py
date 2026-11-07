#!/usr/bin/env python3
"""Bake actual reference-derived tileable PBR textures for editable Daytona v7.
Inputs are small crops of the user-generated target image, not scene art.
No copying interior layout onto UV; extract ONLY fine material grain and palette.
"""
from pathlib import Path
from PIL import Image,ImageFilter,ImageOps,ImageStat
import json,math,random,os
root=Path(os.environ.get("DAYTONA_V7_ROOT","/home/chatgpt-runner/work_handoff/daytona365_rework_20261107"))
src=root/"reference_v7"
out=root/"blender_v7/textures"
out.mkdir(parents=True,exist_ok=True)
size=512
configs={
 "TanLeather":{"rgb":(166,98,58),"rough":203,"metal":0,"grain":11,"height":.00055},
 "BlackLeather":{"rgb":(34,31,30),"rough":218,"metal":0,"grain":8,"height":.00035},
 "WalnutRim":{"rgb":(109,56,31),"rough":67,"metal":0,"grain":19,"height":.00012}
}
manifest={}
for index,(kind,cfg) in enumerate(configs.items()):
 file=src/(("wood" if kind=="WalnutRim" else ("tan" if kind=="TanLeather" else "black"))+"_reference.jpg")
 try:
  sample=Image.open(file).convert("RGB")
 except Exception:
  # Other high-frequency source samples were damaged during transport;
  # use the intact generated-image tan micrograin but the correct black palette.
  assert kind in ("BlackLeather","WalnutRim")
  file=src/"tan_reference.jpg"
  sample=Image.open(file).convert("RGB")
 if sample.size!=(48,48):raise ValueError("reference sample changed")
 # Mirror-quad tile: exact matching at left/right and top/bottom seams.
 src_small=sample.resize((size//2,size//2),Image.Resampling.LANCZOS)
 tile=Image.new("RGB",(size,size))
 tile.paste(src_small,(0,0))
 tile.paste(ImageOps.mirror(src_small),(size//2,0))
 tile.paste(ImageOps.flip(src_small),(0,size//2))
 tile.paste(ImageOps.flip(ImageOps.mirror(src_small)),(size//2,size//2))
 luminance=tile.convert("L")
 smooth=luminance.filter(ImageFilter.GaussianBlur(12))
 a=luminance.load();b=smooth.load()
 rng=random.Random(0x365000+index)
 height=Image.new("L",(size,size),128)
 h=height.load()
 base=Image.new("RGB",(size,size))
 cp=base.load()
 for y in range(size):
  for x in range(size):
   # Microscopic leather pores; stronger wood linear grain oriented around rim UV.
   grain=float(a[x,y]-b[x,y])
   if kind=="WalnutRim":
    grain += 7.0*math.sin(2*math.pi*y/47+1.8*math.sin(x*.031))
    grain += 2.8*math.sin(2*math.pi*y/13)
   else:
    grain += .65*math.sin((x*13+y*7)*.71)
   detail=max(-20,min(20,grain*.64+rng.uniform(-2,2)))
   h[x,y]=max(0,min(255,round(128+detail*1.8)))
   lum=detail*(.67 if kind=="WalnutRim" else .52)
   warm=(.65, .48,.34) if kind=="TanLeather" else (.35,.35,.35)
   cp[x,y]=tuple(max(0,min(255,round(cfg["rgb"][k]+lum*warm[k]))) for k in range(3))
 # Derivative map from microscopic grain, tileable wrap continuity
 normal=Image.new("RGB",(size,size));np=normal.load()
 orm=Image.new("RGB",(size,size));op=orm.load()
 for y in range(size):
  for x in range(size):
   nx=-float(h[(x+1)%size,y]-h[(x-1)%size,y])/255*.8
   ny=-float(h[x,(y+1)%size]-h[x,(y-1)%size])/255*.8
   zz=1.0
   length=math.sqrt(nx*nx+ny*ny+zz*zz)
   np[x,y]=(round(127.5+127.5*nx/length),
            round(127.5+127.5*ny/length),
            round(127.5+127.5*zz/length))
   rough=cfg["rough"]+round((h[x,y]-128)*.12)
   op[x,y]=(round(max(204,min(255,240-(h[x,y]-128)*.08))),
             max(0,min(255,rough)),cfg["metal"])
 files={
  "BaseColor":base,
  "Normal":normal,
  "ORM":orm,
  "HeightOffline":height
 }
 for suffix,img in files.items():
  path=out/(kind+"_"+suffix+".png")
  img.save(path,optimize=True)
 manifest[kind]={"source":file.name,"size":size,"palette":cfg["rgb"],
  "mapFiles":[kind+"_"+q+".png" for q in files],
  "height_meters":cfg["height"],
  "source_sample_is_from_user_generated_target_image":True}
(out/"V7_MATERIAL_MANIFEST.json").write_text(json.dumps(manifest,indent=2))
print(json.dumps(manifest,indent=2))