#!/usr/bin/env python3
import os,json,hashlib,struct,urllib.request
from pathlib import Path
from PIL import Image,ImageDraw

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("worker B only")

repo=Path.cwd()
run="20261005-B-PRODUCTION75-PREFLIGHT"
out=repo/"localization/graphics/role_B"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)

commit="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
base="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+commit
work=Path("/tmp/b75"); work.mkdir(exist_ok=True)
dds=work/"src.dds"; atlas=work/"atlas.json"
urllib.request.urlretrieve(base+"/Release/spr_sprani_ranking_cvt_Exst/C598919A_1024x1024.dds",dds)
urllib.request.urlretrieve(base+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_ranking_cvt_Exst/4x_C598919A_1024x1024_atlas.json",atlas)
sb=dds.read_bytes(); ab=atlas.read_bytes()
def blob(b): return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def sha(b): return hashlib.sha256(b).hexdigest()
if blob(sb)!="3ab34d5fcd66b5b8cb3d59e02d0d199e2e6b5456": raise RuntimeError(("source blob drift",blob(sb)))
if blob(ab)!="c2d82b14396fc89ca08affcb8ff9c615d644bc82": raise RuntimeError(("atlas blob drift",blob(ab)))
H,W,pitch,depth,mips=struct.unpack_from("<5I",sb,12)
pf=struct.unpack_from("<8I",sb,76); masks=(pf[4],pf[5],pf[6])
mode="RGBA" if masks==(0xff,0xff00,0xff0000) else ("BGRA" if masks==(0xff0000,0xff00,0xff) else None)
if not mode or len(sb)!=128+W*H*4: raise RuntimeError(("structure",W,H,mips,masks,len(sb)))
raw=Image.frombytes("RGBA",(W,H),sb[128:],"raw",mode)
src=raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
src.save(out/"B75_C598_SOURCE_READABLE.png")
raw.save(out/"B75_C598_SOURCE_RAW.png")
regions=json.loads(ab.decode())["regions"]

def comp(im,bg=(55,55,55,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")

meta=[]; cards=[]
for r in regions:
    idx=r["idx"]; x,y,w,h=r["rect"]
    cr=src.crop((x,y,x+w,y+h)); a=cr.getchannel("A"); bb=a.getbbox()
    meta.append({"idx":idx,"name":r["name"],"cell":[x,y,w,h],"alpha_bbox":None if bb is None else [x+bb[0],y+bb[1],x+bb[2],y+bb[3]],"alpha_pixels":sum(a.histogram()[1:])})
    if idx<40 or idx>88: continue
    scale=max(1,min(2,900//max(1,w)))
    show=comp(cr).resize((w*scale,h*scale),Image.Resampling.NEAREST)
    card=Image.new("RGB",(show.width,show.height+36),"white"); card.paste(show,(0,36))
    ImageDraw.Draw(card).text((4,5),f"idx={idx} cell={x},{y},{w},{h}",fill="black")
    cards.append(card)
cols=2
cw=max(c.width for c in cards); rhs=[max(c.height for c in cards[i:i+cols]) for i in range(0,len(cards),cols)]
sheet=Image.new("RGB",(cw*cols+12,sum(rhs)+12*(len(rhs)-1)),"white")
yy=0
for ri,rh in enumerate(rhs):
    xx=0
    for c in cards[ri*cols:(ri+1)*cols]:
        sheet.paste(c,(xx,yy)); xx+=cw+12
    yy+=rh+12
sheet.thumbnail((1800,12000),Image.Resampling.LANCZOS)
sheet.save(out/"B75_C598_TEXT_REGION_CONTACT.jpg",quality=92)

rep={"schema_version":1,"role":"B","run":run,"index":86,
 "asset":"textures/load/spr_sprani_ranking_cvt_Exst/C598919A_1024x1024.dds",
 "source_repository":"Sonic-TV/OR2006Sprites","source_commit":commit,
 "source_blob_sha1":blob(sb),"atlas_blob_sha1":blob(ab),"source_sha256":sha(sb),
 "structure":{"dimensions":[W,H],"format":"RGBA32","raw_mode":mode,"mipmaps":mips,"header_128_sha256":sha(sb[:128]),"raw_orientation":"mirror_y"},
 "regions":meta,
 "expected_segments":["Giant Statues","Cape Way","Imperial Avenue","Ancient Ruins","Metropolis","Tulip Garden","Skyscrapers","Milky Way","Floral Village","Legend","OutRun MODE","Time Attack MODE","15 Continuous Course Ranking","Top Runners of Each Goal","Heart Attack MODE","NORMAL","TUNED","GOAL A","GOAL B","GOAL C","GOAL D","GOAL E","OutRun2SP 15 Continuous Course","OutRun2 15 Continuous Course"],
 "protected_semantics":["Ferrari model names","MT","AT"],
 "status":"B75_CANONICAL_HD_TEXT_BINDING_REQUIRED_SAME_INVOCATION","RUNTIME_VALIDATION":"UNTESTED"}
(out/"B75_C598_PREFLIGHT.json").write_text(json.dumps(rep,ensure_ascii=False,indent=2)+"\n")
(wr/"B75_C598_PREFLIGHT.json").write_text(json.dumps({"run":run,"index":86,"source_sha256":sha(sb),"region_count":len(meta),"status":rep["status"]},indent=2)+"\n")
print(json.dumps({"source_sha256":sha(sb),"regions":len(meta),"mode":mode,"dimensions":[W,H]}))
