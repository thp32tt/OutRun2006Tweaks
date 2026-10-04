#!/usr/bin/env python3
import os, json, hashlib, struct, subprocess, urllib.request
from pathlib import Path
from PIL import Image, ImageDraw

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("GitHub-hosted localization CPU worker / role B only")

repo=Path.cwd()
run="20261005-B-PRODUCTION56-PREFLIGHT"
out=repo/"localization/graphics/role_B"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)

asset="textures/load/spr_sprani_sumo_fe_cvt_Exst/31C58963_512x256.dds"
index=140
COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
SOURCE_BLOB_SHA1="2da84d800f3df0606df148c353f25c2f25a47573"
ATLAS_BLOB_SHA1="7829c90426d563960440dd70b9b7ae74b3b76c0d"
BASE="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+COMMIT
work=Path("/tmp/outrun_B56"); work.mkdir(parents=True,exist_ok=True)
source=work/"31C58963_HD.dds"
atlas=work/"4x_31C58963_512x256_atlas.json"
urllib.request.urlretrieve(BASE+"/Release/spr_sprani_sumo_fe_cvt_Exst/31C58963_512x256.dds",source)
urllib.request.urlretrieve(BASE+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_sumo_fe_cvt_Exst/4x_31C58963_512x256_atlas.json",atlas)

def git_blob_sha1(b): return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def bbox_alpha(im):
    b=im.getchannel("A").getbbox()
    return list(b) if b else None

sb=source.read_bytes(); ab=atlas.read_bytes()
if git_blob_sha1(sb)!=SOURCE_BLOB_SHA1: raise RuntimeError(("source blob",git_blob_sha1(sb)))
if git_blob_sha1(ab)!=ATLAS_BLOB_SHA1: raise RuntimeError(("atlas blob",git_blob_sha1(ab)))
if sb[:4]!=b"DDS ": raise RuntimeError("not DDS")
H,W,pitch,depth,mips=struct.unpack_from("<5I",sb,12)
pf=struct.unpack_from("<8I",sb,76)
if (W,H)!=(2048,1024) or len(sb)!=128+W*H*4:
    raise RuntimeError(("structure",W,H,pitch,depth,mips,len(sb),pf))
masks=(pf[4],pf[5],pf[6])
if masks==(0xff,0xff00,0xff0000): mode="RGBA"
elif masks==(0xff0000,0xff00,0xff): mode="BGRA"
else: raise RuntimeError(("raw mode",masks))
raw=Image.frombytes("RGBA",(W,H),sb[128:],"raw",mode)
src=raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
aj=json.loads(ab.decode("utf-8"))
regions=sorted(aj["regions"],key=lambda r:r["idx"])
if [r["rect"] for r in regions]!=[[0,864,1760,160],[0,704,1760,160],[0,544,1760,160],[0,384,1760,160],[0,308,744,76]]:
    raise RuntimeError(("atlas drift",regions))

rows=[]
cards=[]
for r in regions:
    x,y,cw,ch=r["rect"]
    cell=src.crop((x,y,x+cw,y+ch))
    bb=bbox_alpha(cell)
    if not bb: raise RuntimeError(("empty cell",r["idx"]))
    ob=[x+bb[0],y+bb[1],x+bb[2],y+bb[3]]
    rows.append({"region_idx":r["idx"],"name":r["name"],"cell":r["rect"],"source_alpha_bbox":ob,
                 "source_width":ob[2]-ob[0],"source_height":ob[3]-ob[1],
                 "alpha_pixels":sum(cell.getchannel("A").histogram()[1:])})
    bg=Image.new("RGBA",cell.size,(64,64,64,255)); bg.alpha_composite(cell)
    card=bg.convert("RGB")
    # shrink large cells to 880px wide for controller visual binding
    scale=min(1.0,880/card.width)
    if scale<1:
        card=card.resize((int(card.width*scale),int(card.height*scale)),Image.Resampling.LANCZOS)
    canvas=Image.new("RGB",(card.width,card.height+28),"white")
    canvas.paste(card,(0,28))
    ImageDraw.Draw(canvas).text((5,5),f'REGION {r["idx"]} {r["name"]} cell={r["rect"]} alpha_bbox={ob}',fill="black")
    cards.append(canvas)

Wc=max(c.width for c in cards); Hc=sum(c.height for c in cards)+4*(len(cards)-1)
sheet=Image.new("RGB",(Wc,Hc),"white"); yy=0
for c in cards:
    sheet.paste(c,(0,yy)); yy+=c.height+4
sheet.save(out/"B56_31C_REGION_CONTACT.jpg",quality=96)

fullbg=Image.new("RGBA",src.size,(64,64,64,255)); fullbg.alpha_composite(src)
fullbg.convert("RGB").resize((1024,512),Image.Resampling.LANCZOS).save(out/"B56_31C_SOURCE_READABLE_HALF.jpg",quality=96)
rawbg=Image.new("RGBA",raw.size,(64,64,64,255)); rawbg.alpha_composite(raw)
rawbg.convert("RGB").resize((1024,512),Image.Resampling.LANCZOS).save(out/"B56_31C_SOURCE_RAW_HALF.jpg",quality=96)

report={
 "schema_version":1,"role":"B","run":run,"index":index,"asset":asset,
 "readiness_tier":"ONE_STAGE_TO_RENDER_SEMANTIC_BINDING",
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":COMMIT,
   "git_blob_sha1":SOURCE_BLOB_SHA1,"sha256":hashlib.sha256(sb).hexdigest(),
   "path":"Release/spr_sprani_sumo_fe_cvt_Exst/31C58963_512x256.dds"},
 "structure":{"dimensions":[W,H],"format":"RGBA32","raw_mode":mode,"mipmaps":mips,
   "bytes":len(sb),"header_128_preservable":True,"raw_orientation":"mirror_y"},
 "atlas":{"git_blob_sha1":ATLAS_BLOB_SHA1,"regions":rows},
 "expected_semantics":["PRESS START","SHOWROOM","SELECT MODE","SELECT RACE","SELECT STAGE"],
 "semantic_binding":"PENDING_CONTROLLER_VISUAL_BINDING_FROM_REGION_CONTACT",
 "candidate_written":False,
 "next_same_invocation":"bind the five source strings to region indices from contact sheet, then render/encode/self-QA without opening another unrelated task",
 "RUNTIME_VALIDATION":"UNTESTED",
 "status":"B56_ONE_STAGE_TO_RENDER_DIAGNOSTIC_COMPLETE"
}
(out/"B56_31C_PREFLIGHT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
summary={"run":run,"index":index,"asset":"31C58963","source_sha256":report["source_provenance"]["sha256"],
 "structure":report["structure"],"regions":rows,"status":report["status"],"runtime_validation":"UNTESTED",
 "report":"localization/graphics/role_B/20261005-B-PRODUCTION56-PREFLIGHT/B56_31C_PREFLIGHT.json"}
(wr/"B56_31C58963.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False))
