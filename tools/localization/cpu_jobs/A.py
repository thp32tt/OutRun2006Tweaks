#!/usr/bin/env python3
import os,json,hashlib,struct,urllib.request
from pathlib import Path
from PIL import Image,ImageDraw,ImageOps

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted role A required")

repo=Path.cwd()
run="20261005-A-PRODUCTION50-PREFLIGHT"
out=repo/"localization/graphics/role_A"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"
wr.mkdir(parents=True,exist_ok=True)
work=Path("/tmp/outrun_A50"); work.mkdir(parents=True,exist_ok=True)

COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
BASE="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+COMMIT
asset_rel="textures/load/spr_sprani_sumo_fe_cvt_Exst/4EDA9DE3_512x256.dds"
source=work/"4EDA9DE3_HD.dds"
atlasp=work/"4x_4EDA9DE3_512x256_atlas.json"
urllib.request.urlretrieve(BASE+"/Release/spr_sprani_sumo_fe_cvt_Exst/4EDA9DE3_512x256.dds",source)
urllib.request.urlretrieve(BASE+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_sumo_fe_cvt_Exst/4x_4EDA9DE3_512x256_atlas.json",atlasp)

sb=source.read_bytes(); ab=atlasp.read_bytes()
if sb[:4]!=b"DDS ": raise RuntimeError("not DDS")
H,W,pitch,depth,mips=struct.unpack_from("<5I",sb,12)
fourcc=sb[84:88]
atlas=json.loads(ab.decode("utf-8"))
regs=sorted(atlas["regions"],key=lambda r:int(r["idx"]))
if len(regs)!=15: raise RuntimeError(("regions",len(regs)))
raw=Image.open(source).convert("RGBA")
if raw.size!=(W,H): raise RuntimeError(("decoded size",raw.size,W,H))
readable=ImageOps.flip(raw)

cards=[]
for r in regs:
    idx=int(r["idx"]); x,y,w,h=map(int,r["rect"])
    # atlas coordinates are readable/game orientation on this raw-mirror-y family
    crop=readable.crop((x,y,x+w,y+h))
    # flatten over dark gray, scale 2x for controller semantic binding
    bg=Image.new("RGBA",crop.size,(70,70,70,255)); bg.alpha_composite(crop)
    rgb=bg.convert("RGB").resize((w*2,h*2),Image.Resampling.NEAREST)
    card=Image.new("RGB",(rgb.width,rgb.height+34),(210,210,210))
    d=ImageDraw.Draw(card); d.text((8,8),f"IDX {idx}",fill=(0,0,0))
    card.paste(rgb,(0,34))
    cards.append(card)

cw=max(c.width for c in cards)
ch=sum(c.height+4 for c in cards)
sheet=Image.new("RGB",(cw,ch),(190,190,190))
yy=0
for c in cards:
    sheet.paste(c,(0,yy)); yy+=c.height+4
sheet.save(out/"A50_4EDA9DE3_ALL_REGIONS.jpg",quality=96)

rawbg=Image.new("RGBA",raw.size,(70,70,70,255)); rawbg.alpha_composite(raw)
rawbg.convert("RGB").resize((1024,512),Image.Resampling.LANCZOS).save(out/"A50_4EDA9DE3_RAW.jpg",quality=94)

report={
 "schema_version":1,"role":"A","run":run,"index":159,"asset":asset_rel,
 "worker":"github-actions",
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":COMMIT,
   "blob_sha1":hashlib.sha1(b"blob "+str(len(sb)).encode()+b"\0"+sb).hexdigest(),
   "sha256":hashlib.sha256(sb).hexdigest()},
 "atlas_provenance":{"blob_sha1":hashlib.sha1(b"blob "+str(len(ab)).encode()+b"\0"+ab).hexdigest(),
   "sha256":hashlib.sha256(ab).hexdigest(),"regions":len(regs)},
 "structure":{"dimensions":[W,H],"fourcc":fourcc.decode("latin1"),"mipmaps":mips,"raw_orientation":"mirror_y"},
 "regions":[{"idx":int(r["idx"]),"rect":list(map(int,r["rect"]))} for r in regs],
 "status":"A50_BINDING_CONTACT_READY_CONTINUE_SAME_INVOCATION",
 "runtime_validation":"UNTESTED"
}
(out/"A50_4EDA9DE3_PREFLIGHT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
summary={"run":run,"index":159,"asset":"4EDA9DE3","status":report["status"],
 "report":"localization/graphics/role_A/20261005-A-PRODUCTION50-PREFLIGHT/A50_4EDA9DE3_PREFLIGHT.json",
 "contact":"localization/graphics/role_A/20261005-A-PRODUCTION50-PREFLIGHT/A50_4EDA9DE3_ALL_REGIONS.jpg"}
(wr/"A50_4EDA9DE3.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
print(json.dumps(summary,ensure_ascii=False,indent=2))
