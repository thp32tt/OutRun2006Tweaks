#!/usr/bin/env python3
import os,json,hashlib,struct,urllib.request
from pathlib import Path
from PIL import Image,ImageDraw

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("worker B only")
repo=Path.cwd(); run="20261005-B-PRODUCTION100-CLAR-SIBLING-COMPARE"
out=repo/"localization/graphics/role_B"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
commit="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
base="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+commit+"/Release/spr_sprani_CLAR_RANK_Exst/"
names=["63C91067_512x512.dds","4AFC1BED_512x512.dds","A05BF610_512x512.dds"]
ims=[]; metas=[]
for name in names:
    p=Path("/tmp")/name; urllib.request.urlretrieve(base+name,p)
    b=p.read_bytes(); H,W=struct.unpack_from("<2I",b,12); im=Image.open(p).convert("RGBA").transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    ims.append((name,im))
    metas.append({"name":name,"sha256":hashlib.sha256(b).hexdigest(),"dimensions":[W,H],"fourcc":b[84:88].decode("latin1")})
def comp(im):
    z=Image.new("RGBA",im.size,(72,72,72,255)); z.alpha_composite(im); return z.convert("RGB")
cards=[]
for name,im in ims:
    z=comp(im).resize((1024,1024),Image.Resampling.NEAREST)
    c=Image.new("RGB",(1024,1050),"white"); c.paste(z,(0,26)); ImageDraw.Draw(c).text((5,5),name,fill="black"); cards.append(c)
sheet=Image.new("RGB",(1024,1050*3),"white")
for i,c in enumerate(cards): sheet.paste(c,(0,1050*i))
sheet.save(out/"B100_CLAR_SIBLING_READABLE.jpg",quality=96)
# side-by-side central title crops from top and bottom halves, using generous windows.
rows=[]
for label,box in [("TOP",(450,80,1350,330)),("BOTTOM",(550,1080,1450,1350))]:
    xs=[]
    for name,im in ims:
        cr=comp(im).crop(box)
        cc=Image.new("RGB",(cr.width,cr.height+26),"white"); cc.paste(cr,(0,26)); ImageDraw.Draw(cc).text((5,5),name,fill="black"); xs.append(cc)
    row=Image.new("RGB",(sum(x.width for x in xs),max(x.height for x in xs)),"white"); xx=0
    for x in xs: row.paste(x,(xx,0)); xx+=x.width
    rows.append((label,row))
contact=Image.new("RGB",(max(r.width for _,r in rows),sum(r.height for _,r in rows)+8),"white"); yy=0
for lab,r in rows: contact.paste(r,(0,yy)); yy+=r.height+8
contact.save(out/"B100_CLAR_TITLE_CROPS.jpg",quality=96)
report={"schema_version":1,"role":"B","run":run,"purpose":"Find same-family clean/title reconstruction evidence for 63C91067 after B93-B99 controller visual rejects source-effect ghost residue.","siblings":metas,"status":"SIBLING_VISUAL_COMPARE_READY","RUNTIME_VALIDATION":"UNTESTED"}
(out/"B100_CLAR_SIBLING_REPORT.json").write_text(json.dumps(report,indent=2)+"\n")
(wr/"B100_CLAR_SIBLINGS.json").write_text(json.dumps({"run":run,"status":report["status"],"report":f"localization/graphics/role_B/{run}/B100_CLAR_SIBLING_REPORT.json"},indent=2)+"\n")
print(json.dumps(report))
