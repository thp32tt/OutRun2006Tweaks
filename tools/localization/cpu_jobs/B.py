#!/usr/bin/env python3
import os,json,hashlib,struct,urllib.request,math
from pathlib import Path
from PIL import Image,ImageDraw

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("worker B only")

repo=Path.cwd()
run="20261005-B-PRODUCTION86-DDF0392A-PREFLIGHT"
out=repo/"localization/graphics/role_B"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
commit="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
base="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+commit
tmp=Path("/tmp/b86"); tmp.mkdir(exist_ok=True)
dds=tmp/"src.dds"; atlas=tmp/"atlas.json"
urllib.request.urlretrieve(base+"/Release/spr_sprani_sumo_fe_cvt_Exst/DDF0392A_256x512.dds",dds)
urllib.request.urlretrieve(base+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_sumo_fe_cvt_Exst/4x_DDF0392A_256x512_atlas.json",atlas)
sb=dds.read_bytes(); ab=atlas.read_bytes()
def sha(b): return hashlib.sha256(b).hexdigest()
def blob(b): return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
if sb[:4]!=b"DDS ": raise RuntimeError("not DDS")
H,W,pitch,depth,mips=struct.unpack_from("<5I",sb,12)
pf=struct.unpack_from("<8I",sb,76); masks=(pf[4],pf[5],pf[6],pf[7]); fourcc=struct.pack("<I",pf[2]).decode("latin1")
mode="RGBA" if masks[:3]==(0xff,0xff00,0xff0000) else ("BGRA" if masks[:3]==(0xff0000,0xff00,0xff) else None)
if mode and len(sb)==128+W*H*4:
    raw=Image.frombytes("RGBA",(W,H),sb[128:],"raw",mode)
else:
    raw=Image.open(dds).convert("RGBA")
src=raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
at=json.loads(ab.decode()); regs=at["regions"]
def comp(im):
    z=Image.new("RGBA",im.size,(72,72,72,255)); z.alpha_composite(im); return z.convert("RGB")
# readable + raw proof
z=comp(src); z.thumbnail((1024,2048),Image.Resampling.NEAREST); z.save(out/"B86_DDF_READABLE.jpg",quality=96)
z=comp(raw); z.thumbnail((1024,2048),Image.Resampling.NEAREST); z.save(out/"B86_DDF_RAW.jpg",quality=96)
cards=[]; meta=[]
for r in regs:
    idx=r["idx"]; x,y,cw,ch=r["rect"]; cell=src.crop((x,y,x+cw,y+ch))
    a=cell.getchannel("A"); bb=a.getbbox(); ap=sum(a.histogram()[1:])
    c=comp(cell)
    sc=min(1.0,880/max(1,c.width),150/max(1,c.height))
    if sc<1: c=c.resize((max(1,int(c.width*sc)),max(1,int(c.height*sc))),Image.Resampling.NEAREST)
    card=Image.new("RGB",(900,190),"white"); card.paste(c,(10,30))
    ImageDraw.Draw(card).text((10,7),f"idx {idx} rect {x},{y},{cw},{ch} alpha={ap}",fill="black")
    cards.append(card)
    meta.append({"idx":idx,"rect":[x,y,cw,ch],"alpha_bbox":list(bb) if bb else None,"alpha_pixels":ap})
sheet=Image.new("RGB",(900,len(cards)*190),"white")
for i,c in enumerate(cards): sheet.paste(c,(0,i*190))
sheet.thumbnail((1200,10000),Image.Resampling.LANCZOS); sheet.save(out/"B86_DDF_ATLAS_CONTACT.jpg",quality=96)
report={"schema_version":1,"role":"B","run":run,"index":222,"asset":"DDF0392A",
"source_sha256":sha(sb),"source_git_blob_sha1":blob(sb),"atlas_git_blob_sha1":blob(ab),
"dimensions":[W,H],"pitch":pitch,"mips":mips,"raw_mode":mode,"fourcc":fourcc,"raw_orientation":"mirror_y",
"regions_count":len(regs),"regions":meta,
"policy_note":"Rush A Difficulty / Shake The Street / Who Are You? are known song titles and must remain original English; target semantics are Journey Mode / Random, OutRun 1986, OutRun Mode / 15 C. only.",
"status":"PREFLIGHT_VISUAL_BINDING_READY_SAME_INVOCATION_CONTINUE_TO_RENDER","RUNTIME_VALIDATION":"UNTESTED"}
(out/"B86_DDF_PREFLIGHT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
(wr/"B86_DDF0392A.json").write_text(json.dumps({"run":run,"index":222,"asset":"DDF0392A","source_sha256":sha(sb),"status":report["status"],"report":f"localization/graphics/role_B/{run}/B86_DDF_PREFLIGHT.json"},ensure_ascii=False,indent=2)+"\n")
print(json.dumps(report,ensure_ascii=False))
