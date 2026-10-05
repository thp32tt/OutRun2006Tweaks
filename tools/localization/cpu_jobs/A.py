#!/usr/bin/env python3
import os,json,hashlib,struct,urllib.request
from pathlib import Path
from PIL import Image,ImageDraw,ImageOps

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted role A required")
repo=Path.cwd(); run="20261005-A-PRODUCTION52-PREFLIGHT"
out=repo/"localization/graphics/role_A"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
work=Path("/tmp/outrun_A52"); work.mkdir(parents=True,exist_ok=True)
COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"; BASE="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+COMMIT
source=work/"55B57CDE_HD.dds"; atlasp=work/"4x_55B57CDE_512x512_atlas.json"
urllib.request.urlretrieve(BASE+"/Release/spr_sprani_sumo_fe_cvt_Exst/55B57CDE_512x512.dds",source)
urllib.request.urlretrieve(BASE+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_sumo_fe_cvt_Exst/4x_55B57CDE_512x512_atlas.json",atlasp)
sb=source.read_bytes(); ab=atlasp.read_bytes()
if sb[:4]!=b"DDS ": raise RuntimeError("not DDS")
H,W,pitch,depth,mips=struct.unpack_from("<5I",sb,12)
raw=Image.open(source).convert("RGBA"); readable=ImageOps.flip(raw)
atlas=json.loads(ab.decode("utf-8")); regs=sorted(atlas["regions"],key=lambda r:int(r["idx"]))
if len(regs)!=38: raise RuntimeError(("regions",len(regs)))
cards=[]
for r in regs:
    idx=int(r["idx"]); x,y,w,h=map(int,r["rect"]); crop=readable.crop((x,y,x+w,y+h))
    bg=Image.new("RGBA",crop.size,(70,70,70,255)); bg.alpha_composite(crop)
    rgb=bg.convert("RGB").resize((w*2,h*2),Image.Resampling.NEAREST)
    card=Image.new("RGB",(rgb.width,rgb.height+28),(210,210,210)); d=ImageDraw.Draw(card)
    d.text((6,6),f"IDX {idx}",fill=(0,0,0)); card.paste(rgb,(0,28)); cards.append(card)
cw=max(c.width for c in cards); ch=sum(c.height+3 for c in cards)
sheet=Image.new("RGB",(cw,ch),(190,190,190)); yy=0
for c in cards: sheet.paste(c,(0,yy)); yy+=c.height+3
sheet.save(out/"A52_55B57CDE_ALL_REGIONS.jpg",quality=96)
report={"schema_version":1,"role":"A","run":run,"index":161,
 "asset":"textures/load/spr_sprani_sumo_fe_cvt_Exst/55B57CDE_512x512.dds",
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":COMMIT,
 "blob_sha1":hashlib.sha1(b"blob "+str(len(sb)).encode()+b"\0"+sb).hexdigest(),"sha256":hashlib.sha256(sb).hexdigest()},
 "atlas_provenance":{"blob_sha1":hashlib.sha1(b"blob "+str(len(ab)).encode()+b"\0"+ab).hexdigest(),"sha256":hashlib.sha256(ab).hexdigest(),"regions":38},
 "structure":{"dimensions":[W,H],"mipmaps":mips,"raw_orientation":"mirror_y"},
 "regions":[{"idx":int(r["idx"]),"rect":list(map(int,r["rect"]))} for r in regs],
 "status":"A52_BINDING_CONTACT_READY_CONTINUE_SAME_INVOCATION","runtime_validation":"UNTESTED"}
(out/"A52_55B57CDE_PREFLIGHT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
summary={"run":run,"index":161,"asset":"55B57CDE","status":report["status"],
 "report":"localization/graphics/role_A/20261005-A-PRODUCTION52-PREFLIGHT/A52_55B57CDE_PREFLIGHT.json",
 "contact":"localization/graphics/role_A/20261005-A-PRODUCTION52-PREFLIGHT/A52_55B57CDE_ALL_REGIONS.jpg"}
(wr/"A52_55B57CDE.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
print(json.dumps(summary,ensure_ascii=False,indent=2))
