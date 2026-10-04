#!/usr/bin/env python3
import os,json,hashlib,struct,subprocess,urllib.request
from pathlib import Path
from PIL import Image,ImageDraw

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("GitHub-hosted localization CPU worker / role B only")

repo=Path.cwd(); run="20261005-B-PRODUCTION59-PREFLIGHT"
out=repo/"localization/graphics/role_B"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
asset="textures/load/spr_sprani_sumo_fe_cvt_Exst/4D38BBB0_1024x256.dds"; index=154
COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
SOURCE_BLOB_SHA1="d06a7ea1d9e9c940788be244963fcb0146fe2498"
ATLAS_BLOB_SHA1="11f58c46008eb6ca355cd9b0d64f1fe268695838"
BASE="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+COMMIT
work=Path("/tmp/outrun_B59"); work.mkdir(parents=True,exist_ok=True)
source=work/"4D38BBB0_HD.dds"; atlas=work/"4x_4D38BBB0_1024x256_atlas.json"
urllib.request.urlretrieve(BASE+"/Release/spr_sprani_sumo_fe_cvt_Exst/4D38BBB0_1024x256.dds",source)
urllib.request.urlretrieve(BASE+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_sumo_fe_cvt_Exst/4x_4D38BBB0_1024x256_atlas.json",atlas)
def gitblob(b): return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
sb=source.read_bytes(); ab=atlas.read_bytes()
if gitblob(sb)!=SOURCE_BLOB_SHA1: raise RuntimeError(("source blob",gitblob(sb)))
if gitblob(ab)!=ATLAS_BLOB_SHA1: raise RuntimeError(("atlas blob",gitblob(ab)))
if sb[:4]!=b"DDS ": raise RuntimeError("not DDS")
H,W,pitch,depth,mips=struct.unpack_from("<5I",sb,12); pf=struct.unpack_from("<8I",sb,76)
if (W,H,pitch,mips)!=(4096,1024,16384,1) or len(sb)!=128+W*H*4: raise RuntimeError(("structure",W,H,pitch,depth,mips,len(sb),pf))
masks=(pf[4],pf[5],pf[6])
if masks==(0xff,0xff00,0xff0000): rawmode="RGBA"
elif masks==(0xff0000,0xff00,0xff): rawmode="BGRA"
else: raise RuntimeError(("raw mode",masks))
raw=Image.frombytes("RGBA",(W,H),sb[128:],"raw",rawmode); src=raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
aj=json.loads(ab.decode("utf-8")); regions=sorted(aj["regions"],key=lambda r:r["idx"])
rows=[]; cards=[]
for r in regions:
    x,y,cw,ch=r["rect"]; cell=src.crop((x,y,x+cw,y+ch)); bb=cell.getchannel("A").getbbox()
    ob=[x+bb[0],y+bb[1],x+bb[2],y+bb[3]] if bb else None
    rows.append({"region_idx":r["idx"],"name":r["name"],"cell":r["rect"],"source_alpha_bbox":ob,
                 "alpha_pixels":sum(cell.getchannel("A").histogram()[1:])})
    bg=Image.new("RGBA",cell.size,(64,64,64,255)); bg.alpha_composite(cell); card=bg.convert("RGB")
    scale=min(1.0,1200/max(1,card.width)); card=card.resize((max(1,int(card.width*scale)),max(1,int(card.height*scale))),Image.Resampling.LANCZOS)
    c=Image.new("RGB",(card.width,card.height+30),"white"); c.paste(card,(0,30))
    ImageDraw.Draw(c).text((5,5),f'REGION {r["idx"]} {r["name"]} cell={r["rect"]} alpha_bbox={ob}',fill="black"); cards.append(c)
cw=max(c.width for c in cards); ch=sum(c.height for c in cards)+4*(len(cards)-1)
sheet=Image.new("RGB",(cw,ch),"white"); yy=0
for c in cards: sheet.paste(c,(0,yy)); yy+=c.height+4
sheet.save(out/"B59_4D38_REGION_CONTACT.jpg",quality=96)
full=Image.new("RGBA",src.size,(64,64,64,255)); full.alpha_composite(src)
full.convert("RGB").resize((1024,256),Image.Resampling.LANCZOS).save(out/"B59_4D38_SOURCE_READABLE_QUARTER.jpg",quality=96)
rawbg=Image.new("RGBA",raw.size,(64,64,64,255)); rawbg.alpha_composite(raw)
rawbg.convert("RGB").resize((1024,256),Image.Resampling.LANCZOS).save(out/"B59_4D38_SOURCE_RAW_QUARTER.jpg",quality=96)
report={"schema_version":1,"role":"B","run":run,"index":index,"asset":asset,
 "readiness_tier":"ONE_STAGE_TO_RENDER_SEMANTIC_BINDING",
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":COMMIT,"git_blob_sha1":SOURCE_BLOB_SHA1,
  "sha256":hashlib.sha256(sb).hexdigest(),"path":"Release/spr_sprani_sumo_fe_cvt_Exst/4D38BBB0_1024x256.dds"},
 "structure":{"dimensions":[W,H],"format":"RGBA32","raw_mode":rawmode,"mipmaps":mips,"bytes":len(sb),"header_128_preservable":True,"raw_orientation":"mirror_y"},
 "atlas":{"git_blob_sha1":ATLAS_BLOB_SHA1,"regions":rows},
 "expected_semantics":["MULTIPLAYER","SINGLE PLAYER","DEFAULT LICENSE","CREATE NEW LICENSE","SELECT LICENSE"],
 "semantic_binding":"PENDING_CONTROLLER_VISUAL_BINDING_FROM_REGION_CONTACT","candidate_written":False,
 "next_same_invocation":"bind source labels to exact region indices and continue through candidate render/self-QA",
 "RUNTIME_VALIDATION":"UNTESTED","status":"B59_ONE_STAGE_TO_RENDER_DIAGNOSTIC_COMPLETE"}
(out/"B59_4D38_PREFLIGHT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"B59_4D38BBB0.json").write_text(json.dumps({"run":run,"index":index,"asset":"4D38BBB0","source_sha256":report["source_provenance"]["sha256"],"regions":rows,"status":report["status"],"runtime_validation":"UNTESTED","report":f"localization/graphics/role_B/{run}/B59_4D38_PREFLIGHT.json"},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"run":run,"index":index,"status":report["status"]},ensure_ascii=False))
