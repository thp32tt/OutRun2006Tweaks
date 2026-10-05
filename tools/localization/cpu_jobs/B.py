#!/usr/bin/env python3
import os,json,hashlib,struct,urllib.request,math
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("worker B only")

repo=Path.cwd()
run="20261005-B-PRODUCTION83-BA0147DA-PREFLIGHT"
out=repo/"localization/graphics/role_B"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
commit="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
base="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+commit
tmp=Path("/tmp/b83"); tmp.mkdir(exist_ok=True)
dds=tmp/"src.dds"; atlas=tmp/"atlas.json"
urllib.request.urlretrieve(base+"/Release/spr_sprani_sumo_fe_cvt_Exst/BA0147DA_512x512.dds",dds)
urllib.request.urlretrieve(base+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_sumo_fe_cvt_Exst/4x_BA0147DA_512x512_atlas.json",atlas)
sb=dds.read_bytes(); ab=atlas.read_bytes()
def sha(b): return hashlib.sha256(b).hexdigest()
def blob(b): return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
if sb[:4]!=b"DDS ": raise RuntimeError("not DDS")
H,W,pitch,depth,mips=struct.unpack_from("<5I",sb,12)
pf=struct.unpack_from("<8I",sb,76); masks=(pf[4],pf[5],pf[6],pf[7]); fourcc=struct.pack("<I",pf[2])
mode="RGBA" if masks[:3]==(0xff,0xff00,0xff0000) else ("BGRA" if masks[:3]==(0xff0000,0xff00,0xff) else None)
if mode and len(sb)==128+W*H*4:
    raw=Image.frombytes("RGBA",(W,H),sb[128:],"raw",mode)
else:
    raw=Image.open(dds).convert("RGBA")
src=raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
at=json.loads(ab.decode()); regs=at["regions"]
def comp(im):
    z=Image.new("RGBA",im.size,(72,72,72,255)); z.alpha_composite(im); return z.convert("RGB")
def bbox_alpha(im):
    b=im.getchannel("A").getbbox(); return list(b) if b else None
# full readable/raw
full=comp(src); full.thumbnail((1400,1400),Image.Resampling.NEAREST); full.save(out/"B83_BA_READABLE.jpg",quality=96)
rr=Image.new("RGB",(1024,1050),"white"); z=comp(raw); z.thumbnail((1024,1024),Image.Resampling.NEAREST); rr.paste(z,(0,26)); ImageDraw.Draw(rr).text((5,5),"RAW_MIRROR_Y",fill="black"); rr.save(out/"B83_BA_RAW.jpg",quality=96)
# numbered contacts
cards=[]; meta=[]
for r in regs:
    idx=r["idx"]; x,y,cw,ch=r["rect"]; cell=src.crop((x,y,x+cw,y+ch))
    bb=bbox_alpha(cell); alpha_pixels=sum(cell.getchannel("A").histogram()[1:])
    c=comp(cell); scale=min(1.0,360/max(1,c.width),180/max(1,c.height))
    if scale<1: c=c.resize((max(1,int(c.width*scale)),max(1,int(c.height*scale))),Image.Resampling.NEAREST)
    card=Image.new("RGB",(380,220),"white"); card.paste(c,(10,28))
    ImageDraw.Draw(card).text((10,7),f"idx {idx} rect {x},{y},{cw},{ch} alpha={alpha_pixels}",fill="black")
    cards.append(card)
    meta.append({"idx":idx,"rect":[x,y,cw,ch],"alpha_bbox":bb,"alpha_pixels":alpha_pixels})
cols=4; rows=math.ceil(len(cards)/cols)
sheet=Image.new("RGB",(cols*380,rows*220),"white")
for i,c in enumerate(cards): sheet.paste(c,((i%cols)*380,(i//cols)*220))
sheet.save(out/"B83_BA_ATLAS_CONTACT.jpg",quality=96)
report={"schema_version":1,"role":"B","run":run,"index":212,"asset":"BA0147DA","source_sha256":sha(sb),"source_git_blob_sha1":blob(sb),"atlas_git_blob_sha1":blob(ab),"dimensions":[W,H],"pitch":pitch,"mips":mips,"raw_mode":mode,"fourcc":fourcc.decode("latin1"),"raw_orientation":"mirror_y","regions_count":len(regs),"regions":meta,"status":"PREFLIGHT_VISUAL_BINDING_READY_SAME_INVOCATION_CONTINUE_TO_RENDER","RUNTIME_VALIDATION":"UNTESTED"}
(out/"B83_BA_PREFLIGHT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
(wr/"B83_BA0147DA.json").write_text(json.dumps({"run":run,"index":212,"asset":"BA0147DA","source_sha256":sha(sb),"status":report["status"],"report":f"localization/graphics/role_B/{run}/B83_BA_PREFLIGHT.json"},ensure_ascii=False,indent=2)+"\n")
print(json.dumps(report,ensure_ascii=False))
