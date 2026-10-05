#!/usr/bin/env python3
import os,json,hashlib,struct,urllib.request
from pathlib import Path
from PIL import Image,ImageDraw

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("worker B only")
repo=Path.cwd()
run="20261005-B-PRODUCTION110-PREFLIGHT"
out=repo/"localization/graphics/role_B"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
BASE="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+COMMIT+"/Release/spr_sprani_CLAR_RANK_Exst/"
names=["4AFC1BED_512x512.dds","63C91067_512x512.dds","A05BF610_512x512.dds"]
ims=[]; meta=[]
for name in names:
    p=Path("/tmp")/name
    urllib.request.urlretrieve(BASE+name,p)
    b=p.read_bytes()
    H,W,pitch,depth,mips=struct.unpack_from("<5I",b,12)
    pf=struct.unpack_from("<8I",b,76)
    masks=(pf[4],pf[5],pf[6],pf[7])
    mode="RGBA" if masks[:3]==(0xff,0xff00,0xff0000) else ("BGRA" if masks[:3]==(0xff0000,0xff00,0xff) else None)
    if mode is None or len(b)!=128+W*H*4: raise RuntimeError((name,W,H,len(b),masks))
    raw=Image.frombytes("RGBA",(W,H),b[128:],"raw",mode)
    readable=raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    ims.append((name,readable))
    meta.append({"name":name,"sha256":hashlib.sha256(b).hexdigest(),"dimensions":[W,H],"raw_mode":mode,"mips":mips,"alpha_bbox":list(readable.getchannel("A").getbbox() or ())})
thumbs=[]
for name,im in ims:
    bg=Image.new("RGBA",im.size,(72,72,72,255)); bg.alpha_composite(im)
    z=bg.convert("RGB").resize((768,768),Image.Resampling.LANCZOS)
    panel=Image.new("RGB",(768,800),"white"); panel.paste(z,(0,32))
    ImageDraw.Draw(panel).text((8,8),name,fill="black")
    thumbs.append(panel)
sheet=Image.new("RGB",(768*len(thumbs),800),"white")
for i,p in enumerate(thumbs): sheet.paste(p,(768*i,0))
sheet.save(out/"B110_CLAR_RANK_SIBLINGS.jpg",quality=96)
report={"schema_version":1,"role":"B","run":run,"purpose":"inspect sibling canonical CLAR_RANK HD DDS for reusable clean plate geometry","source_commit":COMMIT,"assets":meta,"status":"B110_PREFLIGHT_COMPLETE_CONTINUE_SAME_INVOCATION","runtime_validation":"UNTESTED"}
(out/"B110_SIBLING_PREFLIGHT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
(wr/"B110_CLAR_RANK_PREFLIGHT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
print(json.dumps(report,ensure_ascii=False))
