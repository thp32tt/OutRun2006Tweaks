#!/usr/bin/env python3
import os,json,hashlib,struct,urllib.request
from pathlib import Path
from PIL import Image,ImageDraw
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B": raise SystemExit("worker B only")
repo=Path.cwd(); run="20261005-B-PRODUCTION61-PREFLIGHT"; out=repo/"localization/graphics/role_B"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
commit="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"; base="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+commit
work=Path("/tmp/b61"); work.mkdir(exist_ok=True); dds=work/"a.dds"; atlas=work/"a.json"
urllib.request.urlretrieve(base+"/Release/spr_sprani_sumo_fe_cvt_Exst/49BB5FE5_128x32.dds",dds)
urllib.request.urlretrieve(base+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_sumo_fe_cvt_Exst/4x_49BB5FE5_128x32_atlas.json",atlas)
sb=dds.read_bytes(); ab=atlas.read_bytes()
def blob(b): return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
if blob(sb)!="0288babbb9c70e8f092bdd15561db4cadc19dcb3" or blob(ab)!="ca611e5b613c7fe73eee1b66d4fe89465b52b709": raise RuntimeError("blob drift")
H,W=struct.unpack_from("<II",sb,12); pf=struct.unpack_from("<8I",sb,76)
if (W,H)!=(512,128) or len(sb)!=128+W*H: raise RuntimeError(("structure",W,H,len(sb),pf))
alpha=Image.frombytes("L",(W,H),sb[128:],"raw","L")
raw=Image.new("RGBA",(W,H),(255,255,255,0)); raw.putalpha(alpha)
src=raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM); mode="A8"
regions=sorted(json.loads(ab)["regions"],key=lambda r:r["idx"]); rows=[]; cards=[]
for r in regions:
 x,y,w,h=r["rect"]; cell=src.crop((x,y,x+w,y+h)); bb=cell.getchannel("A").getbbox(); ob=[x+bb[0],y+bb[1],x+bb[2],y+bb[3]]
 rows.append({"region_idx":r["idx"],"cell":r["rect"],"source_alpha_bbox":ob})
 bg=Image.new("RGBA",cell.size,(64,64,64,255)); bg.alpha_composite(cell); im=bg.convert("RGB").resize((w*4,h*4),Image.Resampling.NEAREST)
 c=Image.new("RGB",(im.width,im.height+28),"white"); c.paste(im,(0,28)); ImageDraw.Draw(c).text((5,5),f'REGION {r["idx"]} bbox={ob}',fill="black"); cards.append(c)
sheet=Image.new("RGB",(max(c.width for c in cards),sum(c.height for c in cards)+20),"white"); yy=0
for c in cards: sheet.paste(c,(0,yy)); yy+=c.height+4
sheet.save(out/"B61_49BB_REGION_CONTACT_4X.jpg",quality=96)
full=Image.new("RGBA",src.size,(64,64,64,255)); full.alpha_composite(src); full.convert("RGB").resize((1024,256),Image.Resampling.NEAREST).save(out/"B61_49BB_SOURCE_READABLE_2X.jpg",quality=96)
report={"schema_version":1,"role":"B","run":run,"index":152,"asset":"textures/load/spr_sprani_sumo_fe_cvt_Exst/49BB5FE5_128x32.dds","readiness_tier":"ONE_STAGE_TO_RENDER_SEMANTIC_BINDING","source_sha256":hashlib.sha256(sb).hexdigest(),"structure":{"dimensions":[W,H],"format":"A8","raw_mode":mode,"pixel_format_words":pf,"raw_orientation":"mirror_y"},"regions":rows,"cross_reference_semantics":["PROTOTYPE","INSTRUMENTAL","GUITAR MIX","EURO REMIX","1989","1986"],"policy":"preserve year badges; localize only proven semantic abbreviations","status":"B61_ONE_STAGE_TO_RENDER_DIAGNOSTIC_COMPLETE","RUNTIME_VALIDATION":"UNTESTED"}
(out/"B61_49BB_PREFLIGHT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
(wr/"B61_49BB5FE5.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"status":report["status"],"source_sha256":report["source_sha256"]}))
