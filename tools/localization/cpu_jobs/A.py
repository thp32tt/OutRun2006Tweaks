#!/usr/bin/env python3
import os,json,hashlib,struct,urllib.request,statistics
from pathlib import Path
from PIL import Image,ImageDraw
if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A": raise SystemExit("worker A only")
repo=Path.cwd(); run="20261005-A-PRODUCTION61-PREFLIGHT"
out=repo/"localization/graphics/role_A"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
commit="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"; base="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+commit
work=Path("/tmp/a61"); work.mkdir(exist_ok=True)
dds=work/"src.dds"; atlas=work/"atlas.json"
urllib.request.urlretrieve(base+"/Release/spr_sprani_sumo_fe_cvt_Exst/6DC89C6E_512x512.dds",dds)
urllib.request.urlretrieve(base+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_sumo_fe_cvt_Exst/4x_6DC89C6E_512x512_atlas.json",atlas)
sb=dds.read_bytes(); ab=atlas.read_bytes()
def blob(b): return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def sha(b): return hashlib.sha256(b).hexdigest()
H,W,pitch,depth,mips=struct.unpack_from("<5I",sb,12)
pf=struct.unpack_from("<8I",sb,76); fourcc,bpp,rm,gm,bm,am=pf[2],pf[3],pf[4],pf[5],pf[6],pf[7]
mode="RGBA" if fourcc==0 and bpp==32 and (rm,gm,bm)==(0xff,0xff00,0xff0000) else ("BGRA" if fourcc==0 and bpp==32 and (rm,gm,bm)==(0xff0000,0xff00,0xff) else None)
if not mode: raise RuntimeError(("unsupported",W,H,fourcc,bpp,hex(rm),hex(gm),hex(bm)))
raw=Image.frombytes("RGBA",(W,H),sb[128:],"raw",mode); src=raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
regions={r["idx"]:r for r in json.loads(ab.decode())["regions"]}
rows=[]; cards=[]
for idx in range(21):
 x,y,cw,ch=regions[idx]["rect"]; cell=src.crop((x,y,x+cw,y+ch)); bb=cell.getchannel("A").getbbox()
 if not bb: raise RuntimeError(("empty",idx))
 ob=[x+bb[0],y+bb[1],x+bb[2],y+bb[3]]
 vals=[]; p=cell.load()
 for yy in range(ch):
  for xx in range(cw):
   r,g,b,a=p[xx,yy]
   if a>=96: vals.append((r,g,b,a))
 med=[int(round(statistics.median(v[k] for v in vals))) for k in range(4)]
 rows.append({"region_idx":idx,"cell":[x,y,cw,ch],"source_bbox":ob,"width":ob[2]-ob[0],"height":ob[3]-ob[1],"median_rgba":med})
 bg=Image.new("RGBA",cell.size,(72,72,72,255)); bg.alpha_composite(cell); im=bg.convert("RGB").resize((cell.width,cell.height),Image.Resampling.NEAREST)
 card=Image.new("RGB",(im.width,im.height+32),"white"); card.paste(im,(0,32)); ImageDraw.Draw(card).text((6,7),f"idx {idx} bbox {ob[2]-ob[0]}x{ob[3]-ob[1]}",fill="black"); cards.append(card)
sheet=Image.new("RGB",(max(c.width for c in cards),sum(c.height for c in cards)+4*(len(cards)-1)),"white"); yy=0
for c in cards: sheet.paste(c,(0,yy)); yy+=c.height+4
sheet.thumbnail((2000,12000),Image.Resampling.LANCZOS); sheet.save(out/"A61_6DC89C6E_SOURCE_ROWS.jpg",quality=97)
rep={"schema_version":1,"role":"A","run":run,"index":173,"asset":"textures/load/spr_sprani_sumo_fe_cvt_Exst/6DC89C6E_512x512.dds",
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":commit,"git_blob_sha1":blob(sb),"atlas_git_blob_sha1":blob(ab),"source_sha256":sha(sb)},
 "structure":{"dimensions":[W,H],"format":"RGBA32","raw_mode":mode,"mipmaps":mips,"raw_orientation":"mirror_y"},"rows":rows,
 "readiness_tier":"ONE_STAGE_TO_RENDER_SEMANTIC_PHYSICAL_BINDING",
 "evidence":"localization/graphics/role_A/20261005-A-PRODUCTION61-PREFLIGHT/A61_6DC89C6E_SOURCE_ROWS.jpg",
 "status":"A61_PREFLIGHT_SOURCE_CONTACT_READY_FOR_CONTROLLER_BINDING_AND_SAME_INVOCATION_RENDER","runtime_validation":"UNTESTED"}
(out/"A61_6DC89C6E_PREFLIGHT.json").write_text(json.dumps(rep,ensure_ascii=False,indent=2)+"\n")
(wr/"A61_6DC89C6E.json").write_text(json.dumps({"run":run,"index":173,"asset":"6DC89C6E","source_sha256":sha(sb),"status":rep["status"],"report":f"localization/graphics/role_A/{run}/A61_6DC89C6E_PREFLIGHT.json","runtime_validation":"UNTESTED"},ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"run":run,"index":173,"rows":21,"status":rep["status"]},ensure_ascii=False))
