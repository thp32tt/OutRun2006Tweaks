#!/usr/bin/env python3
import hashlib,json,os,struct,zipfile
from pathlib import Path
from PIL import Image,ImageDraw,ImageChops

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("B hosted worker only")
repo=Path.cwd(); run="20261005-B-PRODUCTION51-PREFLIGHT"
out=repo/"localization/graphics/role_B"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
asset="textures/load/spr_sprani_sumo_fe_cvt_Exst/1F5FE6E9_1024x512.dds"
srczip=repo/"localization/validation/binary_compare/original/OutRun2_ORIGINAL_matching_FULL_DRAFT.zip"
histzip=repo/"localization/validation/binary_compare/modified/OutRun2_Korean_GFX_FULL_DRAFT_Test.zip"
with zipfile.ZipFile(srczip) as z: sb=z.read(asset)
with zipfile.ZipFile(histzip) as z: hb=z.read(asset)
def sha(b): return hashlib.sha256(b).hexdigest()
if sha(sb)!="3656adbd699b7852cb5fcf4bb01fc4f1f65bbd9d7d39e12e7a1c2ac5a49fef1d": raise RuntimeError("source sha")
if sha(hb)!="a775eff64b49ac61f107a55ab0233f89fc6cdaa0bfd6e97d3fa5aa112180dc45": raise RuntimeError("hist sha")
H=struct.unpack_from("<I",sb,12)[0]; W=struct.unpack_from("<I",sb,16)[0]; mips=struct.unpack_from("<I",sb,28)[0]
if len(sb)!=128+W*H*4: raise RuntimeError(("not rgba32",W,H,mips,len(sb)))
sraw=Image.frombytes("RGBA",(W,H),sb[128:],"raw","RGBA")
hraw=Image.frombytes("RGBA",(W,H),hb[128:],"raw","RGBA")
trans=[
 ("identity",lambda x:x),
 ("mirror_x",lambda x:x.transpose(Image.Transpose.FLIP_LEFT_RIGHT)),
 ("mirror_y",lambda x:x.transpose(Image.Transpose.FLIP_TOP_BOTTOM)),
 ("rotate_180",lambda x:x.transpose(Image.Transpose.ROTATE_180)),
]
def comp(im,bg=(64,64,64,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")
def card(lbl,im):
    v=comp(im); v.thumbnail((720,360),Image.Resampling.LANCZOS)
    c=Image.new("RGB",(v.width,v.height+26),"white"); c.paste(v,(0,26)); ImageDraw.Draw(c).text((5,4),lbl,fill="black"); return c
rows=[]
for name,fn in trans:
    a=card("SOURCE "+name,fn(sraw)); b=card("HIST "+name,fn(hraw))
    row=Image.new("RGB",(a.width+b.width+8,max(a.height,b.height)),"white"); row.paste(a,(0,0)); row.paste(b,(a.width+8,0)); rows.append(row)
sheet=Image.new("RGB",(max(r.width for r in rows),sum(r.height for r in rows)+8*(len(rows)-1)),"white")
y=0
for r in rows: sheet.paste(r,(0,y)); y+=r.height+8
sheet.save(out/"B51_1F5_ORIENTATION_CONTACT.jpg",quality=96)
# readable diff visualization for each transform
for name,fn in trans:
    s=fn(sraw); h=fn(hraw)
    d=ImageChops.difference(s,h).convert("RGB")
    d.save(out/f"B51_1F5_DIFF_{name}.png")
report={"schema_version":1,"role":"B","run":run,"queue_index":132,"asset":asset,
 "source_sha256":sha(sb),"historical_sha256":sha(hb),
 "structure":{"width":W,"height":H,"format":"RGBA32","mipmaps":mips},
 "status":"PREFLIGHT_ORIENTATION_VISUAL_REQUIRED_SAME_INVOCATION","candidate_written":False,
 "RUNTIME_VALIDATION":"UNTESTED"}
(out/"B51_1F5_PREFLIGHT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
(wr/"B51_1F5_PREFLIGHT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
print(json.dumps(report,ensure_ascii=False))
