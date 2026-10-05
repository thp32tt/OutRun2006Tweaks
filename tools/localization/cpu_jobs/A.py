#!/usr/bin/env python3
import os,json,hashlib,struct,urllib.request
from pathlib import Path
from PIL import Image,ImageDraw

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("worker A only")

repo=Path.cwd()
run="20261006-A-PRODUCTION77-C05-PREFLIGHT"
out=repo/"localization/graphics/role_A"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)

asset="textures/load/spr_sprani_sumo_fe_cvt_Exst/C05E67EF_128x64.dds"
commit="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
base="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+commit
work=Path("/tmp/a77_c05"); work.mkdir(exist_ok=True)
dds=work/"src.dds"; atlas=work/"atlas.json"
urllib.request.urlretrieve(base+"/Release/spr_sprani_sumo_fe_cvt_Exst/C05E67EF_128x64.dds",dds)
urllib.request.urlretrieve(base+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_sumo_fe_cvt_Exst/4x_C05E67EF_128x64_atlas.json",atlas)
sb=dds.read_bytes(); ab=atlas.read_bytes()
def blob(b): return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def sha(b): return hashlib.sha256(b).hexdigest()
if blob(sb)!="6109bf8757aff5aeb11654e94356e303ed2179d4": raise RuntimeError(("source drift",blob(sb)))
if blob(ab)!="d59e6fed81902cbadb2aa962d30e2eafa230669f": raise RuntimeError(("atlas drift",blob(ab)))
H,W,pitch,depth,mips=struct.unpack_from("<5I",sb,12)
pf=struct.unpack_from("<8I",sb,76)
fourcc,bpp,rm,gm,bm,am=pf[2],pf[3],pf[4],pf[5],pf[6],pf[7]
mode="RGBA" if fourcc==0 and bpp==32 and (rm,gm,bm)==(0xff,0xff00,0xff0000) else ("BGRA" if fourcc==0 and bpp==32 and (rm,gm,bm)==(0xff0000,0xff00,0xff) else None)
if not mode or len(sb)!=128+W*H*4: raise RuntimeError(("structure",W,H,fourcc,bpp,mode,len(sb)))
raw=Image.frombytes("RGBA",(W,H),sb[128:],"raw",mode)
readable=raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
data=json.loads(ab.decode()); regions=sorted(data["regions"],key=lambda x:x["idx"])
readable.save(out/"A77_C05_SOURCE_READABLE.png")
raw.save(out/"A77_C05_SOURCE_RAW.png")

cards=[]
meta=[]
for r in regions:
    idx=r["idx"]; x,y,w,h=r["rect"]
    crop=readable.crop((x,y,x+w,y+h))
    a=crop.getchannel("A"); bb=a.getbbox()
    bg=Image.new("RGBA",crop.size,(72,72,72,255)); bg.alpha_composite(crop); disp=bg.convert("RGB")
    disp=disp.resize((w*2,h*2),Image.Resampling.NEAREST)
    card=Image.new("RGB",(disp.width,disp.height+28),"white")
    card.paste(disp,(0,28))
    ImageDraw.Draw(card).text((4,5),f"idx {idx} rect={x},{y},{w},{h} alpha_bbox={bb}",fill="black")
    cards.append(card)
    meta.append({"idx":idx,"rect":[x,y,w,h],"alpha_bbox":list(bb) if bb else None})

sheet=Image.new("RGB",(max(c.width for c in cards),sum(c.height for c in cards)+4*(len(cards)-1)),"white")
yy=0
for c in cards:
    sheet.paste(c,(0,yy)); yy+=c.height+4
sheet.save(out/"A77_C05_SOURCE_CONTACTS.jpg",quality=98)

report={
 "schema_version":1,"role":"A","run":run,"index":215,"asset":asset,
 "readiness_tier":"ONE_STAGE_TO_RENDER_PHYSICAL_BINDING",
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":commit,"git_blob_sha1":blob(sb),"atlas_git_blob_sha1":blob(ab),"source_sha256":sha(sb)},
 "structure":{"dimensions":[W,H],"format":"RGBA32","raw_mode":mode,"mipmaps":mips,"header_128_exact":True,"raw_orientation":"mirror_y"},
 "atlas_region_count":len(regions),"atlas_regions":meta,
 "expected_transcription":["GOAL A","GOAL B","GOAL C","GOAL D","GOAL E","15con."],
 "candidate_written":False,"runtime_validation":"UNTESTED",
 "status":"A77_PREFLIGHT_BINDING_PENDING_CONTROLLER_SAME_INVOCATION_RENDER"
}
(out/"A77_C05_PREFLIGHT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"A77_C05_PREFLIGHT.json").write_text(json.dumps({"run":run,"index":215,"asset":"C05E67EF","source_sha256":sha(sb),"regions":len(regions),"candidate_written":False,"worker_status":report["status"],"runtime_validation":"UNTESTED","report":f"localization/graphics/role_A/{run}/A77_C05_PREFLIGHT.json"},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"run":run,"index":215,"asset":"C05E67EF","dimensions":[W,H],"regions":len(regions),"status":report["status"]},ensure_ascii=False))
