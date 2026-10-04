#!/usr/bin/env python3
import os,json,hashlib,struct,urllib.request
from pathlib import Path
from PIL import Image,ImageDraw
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B": raise SystemExit("worker B only")
repo=Path.cwd(); run="20261005-B-PRODUCTION64-PREFLIGHT"; out=repo/"localization/graphics/role_B"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
commit="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"; base="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+commit
work=Path("/tmp/b64"); work.mkdir(exist_ok=True); dds=work/"src.dds"; atlas=work/"atlas.json"
urllib.request.urlretrieve(base+"/Release/spr_sprani_sumo_fe_cvt_Exst/D657C2EB_512x128.dds",dds)
urllib.request.urlretrieve(base+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_sumo_fe_cvt_Exst/4x_D657C2EB_512x128_atlas.json",atlas)
sb=dds.read_bytes(); ab=atlas.read_bytes()
def blob(b): return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
if blob(sb)!="0b3bdc37870e75da3290f2d5587cebd9cd73655c" or blob(ab)!="4c6af70c683fb6c298e32c289d762a1f7e6a56b5": raise RuntimeError("input drift")
H,W,mips=struct.unpack_from("<I",sb,12)[0],struct.unpack_from("<I",sb,16)[0],struct.unpack_from("<I",sb,28)[0]; pf=struct.unpack_from("<8I",sb,76); masks=(pf[4],pf[5],pf[6])
mode="RGBA" if masks==(0xff,0xff00,0xff0000) else "BGRA"
if (W,H)!=(2048,512) or len(sb)!=128+W*H*4: raise RuntimeError(("structure",W,H,len(sb),pf))
raw=Image.frombytes("RGBA",(W,H),sb[128:],"raw",mode); src=raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
regions=sorted(json.loads(ab)["regions"],key=lambda r:r["idx"]); rows=[]; cards=[]
for r in regions:
 x,y,w,h=r["rect"]; cell=src.crop((x,y,x+w,y+h)); bb=cell.getchannel("A").getbbox(); ob=[x+bb[0],y+bb[1],x+bb[2],y+bb[3]] if bb else None
 rows.append({"region_idx":r["idx"],"cell":r["rect"],"source_alpha_bbox":ob})
 bg=Image.new("RGBA",cell.size,(64,64,64,255)); bg.alpha_composite(cell); im=bg.convert("RGB")
 sc=min(1.0,1000/max(1,w)); im=im.resize((max(1,int(w*sc)),max(1,int(h*sc))),Image.Resampling.LANCZOS)
 c=Image.new("RGB",(im.width,im.height+28),"white"); c.paste(im,(0,28)); ImageDraw.Draw(c).text((5,5),f'REGION {r["idx"]} bbox={ob}',fill="black"); cards.append(c)
sheet=Image.new("RGB",(max(c.width for c in cards),sum(c.height for c in cards)+24),"white"); yy=0
for c in cards:sheet.paste(c,(0,yy));yy+=c.height+4
sheet.save(out/"B64_D657_REGION_CONTACT.jpg",quality=96)
full=Image.new("RGBA",src.size,(64,64,64,255)); full.alpha_composite(src); full.convert("RGB").resize((1024,256),Image.Resampling.LANCZOS).save(out/"B64_D657_SOURCE_READABLE_HALF.jpg",quality=96)
rep={"schema_version":1,"role":"B","run":run,"index":220,"asset":"textures/load/spr_sprani_sumo_fe_cvt_Exst/D657C2EB_512x128.dds","readiness_tier":"ONE_STAGE_TO_RENDER_SEMANTIC_BINDING","source_sha256":hashlib.sha256(sb).hexdigest(),"structure":{"dimensions":[W,H],"format":"RGBA32","raw_mode":mode,"mipmaps":mips,"raw_orientation":"mirror_y"},"regions":rows,"expected_semantics":["REMOVE FRIEND","SEND GAME INVITE","TIME ATTACK","COAST 2 COAST","OUTRUN","HEART ATTACK"],"status":"B64_ONE_STAGE_TO_RENDER_DIAGNOSTIC_COMPLETE","RUNTIME_VALIDATION":"UNTESTED"}
(out/"B64_D657_PREFLIGHT.json").write_text(json.dumps(rep,ensure_ascii=False,indent=2)+"\n"); (wr/"B64_D657C2EB.json").write_text(json.dumps(rep,ensure_ascii=False,indent=2)+"\n"); print(json.dumps({"status":rep["status"],"source_sha256":rep["source_sha256"]}))
