#!/usr/bin/env python3
import base64, hashlib, json, os, struct, urllib.request
from pathlib import Path
from PIL import Image, ImageDraw, ImageOps

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("B hosted worker only")

repo=Path.cwd()
run="20261005-B-PREFLIGHT153-HOLL"
out=repo/"localization/graphics/role_B"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
asset="textures/load/spr_sprani_HOLL_RANK_Exst/B7E25BAD_1024x512.dds"
COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
BASE="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+COMMIT
tmp=Path("/tmp/outrun_B153"); tmp.mkdir(parents=True,exist_ok=True)
dds=tmp/"B7E25BAD.dds"; atlas=tmp/"atlas.json"
urllib.request.urlretrieve(BASE+"/Release/spr_sprani_HOLL_RANK_Exst/B7E25BAD_1024x512.dds",dds)
urllib.request.urlretrieve(BASE+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_HOLL_RANK_Exst/4x_B7E25BAD_1024x512_atlas.json",atlas)

b=dds.read_bytes(); a=json.loads(atlas.read_text())
if b[:4]!=b"DDS ": raise RuntimeError("not DDS")
H=struct.unpack_from("<I",b,12)[0]; W=struct.unpack_from("<I",b,16)[0]
mips=struct.unpack_from("<I",b,28)[0]
pf=struct.unpack_from("<8I",b,76)
fourcc=struct.pack("<I",pf[2]).decode("latin1")
masks=(pf[4],pf[5],pf[6],pf[7])
fmt="unknown"
if pf[1]&0x4 and fourcc=="DXT5":
    raw=Image.open(dds).convert("RGBA"); fmt="DXT5"
elif len(b)>=128+W*H*4:
    mode="RGBA" if masks[:3]==(0xff,0xff00,0xff0000) else ("BGRA" if masks[:3]==(0xff0000,0xff00,0xff) else None)
    if mode is None: raise RuntimeError(("unsupported masks",masks))
    raw=Image.frombytes("RGBA",(W,H),b[128:128+W*H*4],"raw",mode); fmt=mode+"32"
else:
    raw=Image.open(dds).convert("RGBA"); fmt="PIL"
readable=raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)

# Full readable source with atlas rectangles and labels.
ov=readable.copy()
d=ImageDraw.Draw(ov)
for r in a["regions"]:
    x,y,w,h=map(int,r["rect"])
    d.rectangle([x,y,x+w-1,y+h-1],outline=(255,255,255,255),width=max(2,W//1024))
    d.text((x+4,y+4),f'idx{r["idx"]}',fill=(255,255,255,255))
scale=min(1.0,1800/max(W,H))
disp=ov.resize((max(1,int(W*scale)),max(1,int(H*scale))),Image.Resampling.LANCZOS)
disp.save(out/"B153_SOURCE_ATLAS.jpg",quality=92,optimize=True)
(out/"B153_SOURCE_ATLAS_B64.txt").write_text(base64.b64encode((out/"B153_SOURCE_ATLAS.jpg").read_bytes()).decode())

# Per-region contact strip preserving readable orientation.
thumbs=[]
for r in a["regions"]:
    x,y,w,h=map(int,r["rect"])
    crop=readable.crop((x,y,x+w,y+h))
    s=min(1.0,700/max(w,h))
    c=crop.resize((max(1,int(w*s)),max(1,int(h*s))),Image.Resampling.LANCZOS)
    canvas=Image.new("RGB",(c.width,max(28,c.height+28)),(48,48,48))
    canvas.paste(c.convert("RGB"),(0,28))
    ImageDraw.Draw(canvas).text((5,5),f'idx{r["idx"]} {r["name"]} rect={r["rect"]}',fill=(255,255,255))
    thumbs.append(canvas)
mw=max(x.width for x in thumbs); mh=sum(x.height for x in thumbs)
sheet=Image.new("RGB",(mw,mh),(48,48,48)); yy=0
for c in thumbs: sheet.paste(c,(0,yy)); yy+=c.height
sheet.save(out/"B153_SOURCE_REGIONS.jpg",quality=92,optimize=True)
(out/"B153_SOURCE_REGIONS_B64.txt").write_text(base64.b64encode((out/"B153_SOURCE_REGIONS.jpg").read_bytes()).decode())

report={
 "run":"B153","role":"B","index":34,"asset":asset,
 "canonical_commit":COMMIT,"source_sha256":hashlib.sha256(b).hexdigest(),
 "width":W,"height":H,"mips":mips,"format":fmt,"raw_orientation":"mirror_y",
 "atlas":a,
 "decision":"PREFLIGHT_VISUAL_CLASSIFICATION_REQUIRED",
 "runtime_validation":"UNTESTED"
}
(out/"B153_PREFLIGHT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
(wr/"B153.done").write_text(json.dumps({"run":"B153","index":34,"asset":asset,"status":"PREFLIGHT_VISUAL_CLASSIFICATION_REQUIRED"})+"\n")
