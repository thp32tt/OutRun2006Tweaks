#!/usr/bin/env python3
import os,json,hashlib,struct,urllib.request
from pathlib import Path
from PIL import Image,ImageDraw

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("worker B only")
repo=Path.cwd()
run="20261005-B-PRODUCTION90-63C91067-PREFLIGHT"
out=repo/"localization/graphics/role_B"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
commit="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
base="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+commit
work=Path("/tmp/b90"); work.mkdir(exist_ok=True)
dds=work/"src.dds"; atlas=work/"atlas.json"
urllib.request.urlretrieve(base+"/Release/spr_sprani_CLAR_RANK_Exst/63C91067_512x512.dds",dds)
urllib.request.urlretrieve(base+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_CLAR_RANK_Exst/4x_63C91067_512x512_atlas.json",atlas)
sb=dds.read_bytes(); ab=atlas.read_bytes()
def sha(b): return hashlib.sha256(b).hexdigest()
def blob(b): return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
if sb[:4]!=b"DDS ": raise RuntimeError("not DDS")
H,W,pitch,depth,mips=struct.unpack_from("<5I",sb,12)
fourcc=sb[84:88].decode("latin1")
raw=Image.open(dds).convert("RGBA")
readable=raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
regs=json.loads(ab.decode())["regions"]
def comp(im):
    z=Image.new("RGBA",im.size,(72,72,72,255)); z.alpha_composite(im); return z.convert("RGB")
# evidence
for name,im in [("READABLE",readable),("RAW",raw)]:
    z=comp(im); z.thumbnail((1400,1400),Image.Resampling.NEAREST); z.save(out/f"B90_63C_{name}.jpg",quality=96)
cards=[]; meta=[]
for r in regs:
    idx=r["idx"]; x,y,cw,ch=r["rect"]; cell=readable.crop((x,y,x+cw,y+ch)); a=cell.getchannel("A"); bb=a.getbbox()
    gb=None if bb is None else [x+bb[0],y+bb[1],x+bb[2],y+bb[3]]
    show=comp(cell)
    sc=max(1,min(4,1000//max(1,cw)))
    show=show.resize((cw*sc,ch*sc),Image.Resampling.NEAREST)
    card=Image.new("RGB",(max(900,show.width),show.height+38),"white"); card.paste(show,(0,38))
    ImageDraw.Draw(card).text((5,7),f"idx {idx} {r.get('name','')} cell={x},{y},{cw},{ch} bbox={gb}",fill="black")
    cards.append(card)
    meta.append({"idx":idx,"name":r.get("name",""),"cell":[x,y,cw,ch],"alpha_bbox":gb,"alpha_pixels":sum(a.histogram()[1:])})
sheet=Image.new("RGB",(max(c.width for c in cards),sum(c.height+5 for c in cards)),"white"); yy=0
for c in cards: sheet.paste(c,(0,yy)); yy+=c.height+5
sheet.thumbnail((1600,12000),Image.Resampling.LANCZOS); sheet.save(out/"B90_63C_ATLAS_CONTACT.jpg",quality=96)
report={"schema_version":1,"role":"B","run":run,"index":26,"asset":"textures/load/spr_sprani_CLAR_RANK_Exst/63C91067_512x512.dds",
"source_sha256":sha(sb),"source_git_blob_sha1":blob(sb),"atlas_git_blob_sha1":blob(ab),
"structure":{"dimensions":[W,H],"fourcc":fourcc,"mipmaps":mips,"raw_orientation":"mirror_y"},
"regions_count":len(regs),"regions":meta,
"status":"PREFLIGHT_VISUAL_CLASSIFICATION_REQUIRED","RUNTIME_VALIDATION":"UNTESTED"}
(out/"B90_63C_PREFLIGHT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
(wr/"B90_63C91067.json").write_text(json.dumps({"run":run,"index":26,"asset":"63C91067","source_sha256":sha(sb),"regions_count":len(regs),"status":report["status"],"report":f"localization/graphics/role_B/{run}/B90_63C_PREFLIGHT.json"},ensure_ascii=False,indent=2)+"\n")
print(json.dumps(report,ensure_ascii=False))
