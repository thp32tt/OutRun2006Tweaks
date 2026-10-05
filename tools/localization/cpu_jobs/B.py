#!/usr/bin/env python3
import os,json,hashlib,struct,urllib.request
from pathlib import Path
from PIL import Image,ImageDraw

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("worker B only")

repo=Path.cwd()
run="20261005-B-PRODUCTION74-PREFLIGHT"
out=repo/"localization/graphics/role_B"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)

commit="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
base="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+commit
work=Path("/tmp/b74"); work.mkdir(exist_ok=True)
dds=work/"src.dds"; atlas=work/"atlas.json"
urllib.request.urlretrieve(base+"/Release/spr_sprani_sumo_fe_cvt_Exst/75C3586A_512x512.dds",dds)
urllib.request.urlretrieve(base+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_sumo_fe_cvt_Exst/4x_75C3586A_512x512_atlas.json",atlas)

sb=dds.read_bytes(); ab=atlas.read_bytes()
def blob(b): return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def sha(b): return hashlib.sha256(b).hexdigest()
if blob(sb)!="9d21e4fb47d3b17dab89a05b9552cfeaa913eac9": raise RuntimeError(("source blob drift",blob(sb)))
if blob(ab)!="07620598cd03cc6d62455b57d3537158cabfc21a": raise RuntimeError(("atlas blob drift",blob(ab)))

H,W,pitch,depth,mips=struct.unpack_from("<5I",sb,12)
pf=struct.unpack_from("<8I",sb,76); masks=(pf[4],pf[5],pf[6])
mode="RGBA" if masks==(0xff,0xff00,0xff0000) else ("BGRA" if masks==(0xff0000,0xff00,0xff) else None)
if not mode or len(sb)!=128+W*H*4: raise RuntimeError(("structure",W,H,mips,masks,len(sb)))
raw=Image.frombytes("RGBA",(W,H),sb[128:],"raw",mode)
src=raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
src.save(out/"B74_75C_SOURCE_READABLE.png")
raw.save(out/"B74_75C_SOURCE_RAW.png")
regions=json.loads(ab.decode())["regions"]

def comp(im,bg=(72,72,72,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")

cards=[]; meta=[]
for r in regions:
    idx=r["idx"]; x,y,w,h=r["rect"]
    cr=src.crop((x,y,x+w,y+h))
    a=cr.getchannel("A")
    bb=a.getbbox()
    global_bb=None if bb is None else [x+bb[0],y+bb[1],x+bb[2],y+bb[3]]
    hist=a.histogram()
    alpha_pixels=sum(hist[1:])
    opaque=sum(hist[240:])
    # preserve actual scale for tiny cells, shrink only very large cells
    scale=min(3,max(1,900//max(1,w)))
    show=comp(cr).resize((w*scale,h*scale),Image.Resampling.NEAREST)
    card=Image.new("RGB",(show.width,show.height+36),"white")
    card.paste(show,(0,36))
    ImageDraw.Draw(card).text((4,5),f"idx={idx} {r['name']} cell={x},{y},{w},{h} alpha={alpha_pixels}",fill="black")
    cards.append(card)
    meta.append({"idx":idx,"name":r["name"],"cell":[x,y,w,h],"alpha_bbox":global_bb,"alpha_pixels":alpha_pixels,"opaque_alpha_pixels":opaque})

cols=2
cw=max(c.width for c in cards)
rowhs=[max(c.height for c in cards[i:i+cols]) for i in range(0,len(cards),cols)]
sheet=Image.new("RGB",(cw*cols+12,sum(rowhs)+12*(len(rowhs)-1)),"white")
yy=0
for ri,rh in enumerate(rowhs):
    xx=0
    for c in cards[ri*cols:(ri+1)*cols]:
        sheet.paste(c,(xx,yy)); xx+=cw+12
    yy+=rh+12
sheet.save(out/"B74_75C_REGION_CONTACT.jpg",quality=96)

rep={
 "schema_version":1,"role":"B","run":run,"index":176,
 "asset":"textures/load/spr_sprani_sumo_fe_cvt_Exst/75C3586A_512x512.dds",
 "source_repository":"Sonic-TV/OR2006Sprites","source_commit":commit,
 "source_blob_sha1":blob(sb),"atlas_blob_sha1":blob(ab),"source_sha256":sha(sb),
 "structure":{"dimensions":[W,H],"format":"RGBA32","raw_mode":mode,"mipmaps":mips,"header_128_sha256":sha(sb[:128]),"raw_orientation":"mirror_y"},
 "regions":meta,
 "expected_transcription":["FLAGMAN 4","HOLLY","JENNIFER","CLARISSA"],
 "status":"B74_CANONICAL_HD_REGION_BINDING_REQUIRED_SAME_INVOCATION",
 "RUNTIME_VALIDATION":"UNTESTED"
}
(out/"B74_75C_PREFLIGHT.json").write_text(json.dumps(rep,ensure_ascii=False,indent=2)+"\n")
(wr/"B74_75C_PREFLIGHT.json").write_text(json.dumps({"run":run,"index":176,"source_sha256":sha(sb),"region_count":len(meta),"status":rep["status"]},indent=2)+"\n")
print(json.dumps({"source_sha256":sha(sb),"regions":len(meta),"mode":mode,"dimensions":[W,H]}))
