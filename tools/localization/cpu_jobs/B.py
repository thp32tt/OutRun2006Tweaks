#!/usr/bin/env python3
import os,json,hashlib,struct,urllib.request,math
from pathlib import Path
from PIL import Image,ImageDraw

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("worker B only")

repo=Path.cwd()
run="20261005-B-PRODUCTION69-PREFLIGHT"
out=repo/"localization/graphics/role_B"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"
wr.mkdir(parents=True,exist_ok=True)

commit="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
base="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+commit
work=Path("/tmp/b69"); work.mkdir(exist_ok=True)
dds=work/"src.dds"; atlas=work/"atlas.json"
urllib.request.urlretrieve(base+"/Release/spr_sprani_sumo_fe_cvt_Exst/E95DA5_512x256.dds",dds)
urllib.request.urlretrieve(base+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_sumo_fe_cvt_Exst/4x_00E95DA5_512x256_atlas.json",atlas)

sb=dds.read_bytes(); ab=atlas.read_bytes()
def blob(b): return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def sha(b): return hashlib.sha256(b).hexdigest()

if blob(sb)!="ee939d33fd363be135e681b076021c92cddcb489":
    raise RuntimeError(("source blob drift",blob(sb)))
if blob(ab)!="d1cbe695add81e599424c29aa40539bb6875ef5a":
    raise RuntimeError(("atlas blob drift",blob(ab)))

H,W,pitch,depth,mips=struct.unpack_from("<5I",sb,12)
pf=struct.unpack_from("<8I",sb,76)
masks=(pf[4],pf[5],pf[6])
mode="RGBA" if masks==(0xff,0xff00,0xff0000) else ("BGRA" if masks==(0xff0000,0xff00,0xff) else None)
if not mode or (W,H)!=(2048,1024) or len(sb)!=128+W*H*4:
    raise RuntimeError(("structure",W,H,pitch,mips,masks,len(sb)))

raw=Image.frombytes("RGBA",(W,H),sb[128:],"raw",mode)
src=raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
src.save(out/"B69_E95_SOURCE_READABLE.png")
raw.save(out/"B69_E95_SOURCE_RAW.png")
regions=json.loads(ab.decode())["regions"]

def comp(im,bg=(72,72,72,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")

cards=[]
meta=[]
for r in regions:
    idx=r["idx"]; x,y,w,h=r["rect"]
    cr=src.crop((x,y,x+w,y+h))
    a=cr.getchannel("A")
    bb=a.getbbox()
    global_bb=None if bb is None else [x+bb[0],y+bb[1],x+bb[2],y+bb[3]]
    meta.append({"idx":idx,"name":r["name"],"cell":[x,y,w,h],"alpha_bbox":global_bb,"alpha_pixels":sum(a.histogram()[1:])})
    scale=max(1,min(4, int(1000/max(w,1))))
    show=comp(cr).resize((w*scale,h*scale),Image.Resampling.NEAREST)
    card=Image.new("RGB",(show.width,show.height+34),"white")
    card.paste(show,(0,34))
    ImageDraw.Draw(card).text((4,5),f"idx={idx} {r['name']} cell={x},{y},{w},{h}",fill="black")
    cards.append(card)

cols=2
cw=max(c.width for c in cards); rowhs=[]
for i in range(0,len(cards),cols): rowhs.append(max(c.height for c in cards[i:i+cols]))
sheet=Image.new("RGB",(cw*cols+12*(cols-1),sum(rowhs)+12*(len(rowhs)-1)),"white")
yy=0
for ri in range(len(rowhs)):
    xx=0
    for c in cards[ri*cols:(ri+1)*cols]:
        sheet.paste(c,(xx,yy)); xx+=cw+12
    yy+=rowhs[ri]+12
sheet.save(out/"B69_E95_REGION_CONTACT.jpg",quality=96)

rep={
 "schema_version":1,"role":"B","run":run,"index":230,
 "asset":"textures/load/spr_sprani_sumo_fe_cvt_Exst/E95DA5_512x256.dds",
 "source_repository":"Sonic-TV/OR2006Sprites","source_commit":commit,
 "source_blob_sha1":blob(sb),"atlas_blob_sha1":blob(ab),
 "source_sha256":sha(sb),
 "structure":{"dimensions":[W,H],"format":"RGBA32","raw_mode":mode,"mipmaps":mips,"header_128_sha256":sha(sb[:128]),"raw_orientation":"mirror_y"},
 "regions":meta,
 "status":"B69_CANONICAL_HD_REGION_BINDING_REQUIRED_SAME_INVOCATION",
 "RUNTIME_VALIDATION":"UNTESTED"
}
(out/"B69_E95_PREFLIGHT.json").write_text(json.dumps(rep,ensure_ascii=False,indent=2)+"\n")
(wr/"B69_E95_PREFLIGHT.json").write_text(json.dumps({"run":run,"index":230,"source_sha256":sha(sb),"region_count":len(meta),"status":rep["status"]},indent=2)+"\n")
print(json.dumps({"source_sha256":sha(sb),"regions":len(meta),"mode":mode,"dimensions":[W,H]}))
