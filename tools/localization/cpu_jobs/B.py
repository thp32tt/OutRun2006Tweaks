#!/usr/bin/env python3
import os,json,hashlib,struct,urllib.request
from pathlib import Path
from PIL import Image,ImageDraw
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B": raise SystemExit("worker B only")
repo=Path.cwd(); run="20261005-B-PRODUCTION66-PREFLIGHT"; out=repo/"localization/graphics/role_B"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
commit="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"; base="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+commit
work=Path("/tmp/b66"); work.mkdir(exist_ok=True); dds=work/"a.dds"; atlas=work/"a.json"
urllib.request.urlretrieve(base+"/Release/spr_sprani_sumo_fe_cvt_Exst/E3F4BA07_512x128.dds",dds)
urllib.request.urlretrieve(base+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_sumo_fe_cvt_Exst/4x_E3F4BA07_512x128_atlas.json",atlas)
sb=dds.read_bytes(); ab=atlas.read_bytes()
def blob(b): return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
if blob(sb)!="0ac26331b6c2765b9c46b867ff1f2151fd7a15b1" or blob(ab)!="50256e8d4d5af1335249993d44abc5d18a4c5672": raise RuntimeError("blob drift")
H,W,pitch,depth,mips=struct.unpack_from("<5I",sb,12); pf=struct.unpack_from("<8I",sb,76); masks=(pf[4],pf[5],pf[6])
if (W,H,pitch,mips)!=(2048,512,8192,1) or len(sb)!=128+W*H*4: raise RuntimeError(("structure",W,H,pitch,mips,len(sb),pf))
mode="RGBA" if masks==(0xff,0xff00,0xff0000) else ("BGRA" if masks==(0xff0000,0xff00,0xff) else None)
if not mode: raise RuntimeError(("rawmode",masks))
raw=Image.frombytes("RGBA",(W,H),sb[128:],"raw",mode); src=raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
regions=sorted(json.loads(ab.decode())["regions"],key=lambda r:r["idx"]); rows=[]; cards=[]
for r in regions:
 x,y,w,h=r["rect"]; cell=src.crop((x,y,x+w,y+h)); bb=cell.getchannel("A").getbbox(); ob=[x+bb[0],y+bb[1],x+bb[2],y+bb[3]]
 rows.append({"region_idx":r["idx"],"cell":r["rect"],"source_alpha_bbox":ob})
 bg=Image.new("RGBA",cell.size,(64,64,64,255)); bg.alpha_composite(cell); im=bg.convert("RGB")
 scale=min(1.0,980/max(1,im.width)); im=im.resize((max(1,int(im.width*scale)),max(1,int(im.height*scale))),Image.Resampling.LANCZOS)
 c=Image.new("RGB",(im.width,im.height+28),"white"); c.paste(im,(0,28)); ImageDraw.Draw(c).text((5,5),f'REGION {r["idx"]} cell={r["rect"]} bbox={ob}',fill="black"); cards.append(c)
sheet=Image.new("RGB",(max(c.width for c in cards),sum(c.height for c in cards)+4*(len(cards)-1)),"white"); yy=0
for c in cards: sheet.paste(c,(0,yy)); yy+=c.height+4
sheet.save(out/"B66_E3F4_REGION_CONTACT.jpg",quality=96)
full=Image.new("RGBA",src.size,(64,64,64,255)); full.alpha_composite(src); full.convert("RGB").resize((1024,256),Image.Resampling.LANCZOS).save(out/"B66_E3F4_SOURCE_READABLE_HALF.jpg",quality=96)
report={"schema_version":1,"role":"B","run":run,"index":226,"asset":"textures/load/spr_sprani_sumo_fe_cvt_Exst/E3F4BA07_512x128.dds","readiness_tier":"ONE_STAGE_TO_RENDER_SEMANTIC_BINDING","source_sha256":hashlib.sha256(sb).hexdigest(),"structure":{"dimensions":[W,H],"format":"RGBA32","raw_mode":mode,"mipmaps":mips,"raw_orientation":"mirror_y"},"regions":rows,"expected_semantics":["GOAL","GOAL A","GOAL B","GOAL C","GOAL D","GOAL E","15 STAGE CONTINUOUS","STAGE"],"preserve":["OutRun2","OutRun2SP"],"status":"B66_ONE_STAGE_TO_RENDER_DIAGNOSTIC_COMPLETE","RUNTIME_VALIDATION":"UNTESTED"}
(out/"B66_E3F4_PREFLIGHT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
(wr/"B66_E3F4BA07.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"status":report["status"],"source_sha256":report["source_sha256"]}))
