#!/usr/bin/env python3
import hashlib,json,os,struct,urllib.request
from pathlib import Path
from PIL import Image,ImageDraw

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

repo=Path.cwd()
run="20261005-C151-C598919A"
out=repo/"localization/graphics/role_C"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"
wr.mkdir(parents=True,exist_ok=True)

COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
SOURCE_BLOB_SHA1="3ab34d5fcd66b5b8cb3d59e02d0d199e2e6b5456"
ATLAS_BLOB_SHA1="c2d82b14396fc89ca08affcb8ff9c615d644bc82"
asset="textures/load/spr_sprani_ranking_cvt_Exst/C598919A_1024x1024.dds"

base="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+COMMIT
tmp=Path("/tmp/outrun_C151"); tmp.mkdir(parents=True,exist_ok=True)
dds=tmp/"source.dds"; atlas=tmp/"atlas.json"
urllib.request.urlretrieve(base+"/Release/spr_sprani_ranking_cvt_Exst/C598919A_1024x1024.dds",dds)
urllib.request.urlretrieve(base+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_ranking_cvt_Exst/4x_C598919A_1024x1024_atlas.json",atlas)

def gitblob(b):
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def sha(b): return hashlib.sha256(b).hexdigest()
def bbox_alpha(im):
    return im.getchannel("A").getbbox()
def comp(im,bg=(52,52,52,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")

sb=dds.read_bytes(); ab=atlas.read_bytes()
if gitblob(sb)!=SOURCE_BLOB_SHA1 or gitblob(ab)!=ATLAS_BLOB_SHA1:
    raise RuntimeError(("pinned blob drift",gitblob(sb),gitblob(ab)))

if sb[:4]!=b"DDS ":
    raise RuntimeError("not DDS")
H,W,pitch_or_linear,depth,mips=struct.unpack_from("<5I",sb,12)
pf=struct.unpack_from("<8I",sb,76)
fourcc=struct.pack("<I",pf[2]).decode("ascii","replace")
if (W,H)!=(4096,4096):
    raise RuntimeError(("dimension drift",W,H))
if fourcc not in ("DXT5","DXT3","DXT1"):
    raise RuntimeError(("unexpected fourcc",fourcc,pf))

raw=Image.open(dds).convert("RGBA")
if raw.size!=(W,H):
    raise RuntimeError(("Pillow decode size",raw.size,(W,H)))
readable=raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)

raw.save(out/"C151_C598_SOURCE_RAW_DECODED.png")
readable.save(out/"C151_C598_SOURCE_READABLE.png")

regions=json.loads(ab.decode("utf-8"))["regions"]
meta=[]
for r in regions:
    idx=int(r["idx"]); x,y,w,h=map(int,r["rect"])
    cr=readable.crop((x,y,x+w,y+h))
    bb=bbox_alpha(cr)
    hist=cr.getchannel("A").histogram()
    meta.append({
        "idx":idx,"name":r.get("name"),"cell":[x,y,w,h],
        "alpha_bbox":None if bb is None else [x+bb[0],y+bb[1],x+bb[2],y+bb[3]],
        "alpha_pixels":int(sum(hist[1:])),
        "opaque_alpha_pixels":int(sum(hist[240:]))
    })

def make_contact(lo,hi,name):
    cards=[]
    for r in regions:
        idx=int(r["idx"])
        if idx<lo or idx>hi: continue
        x,y,w,h=map(int,r["rect"])
        cr=readable.crop((x,y,x+w,y+h))
        scale=max(1,min(3,800//max(1,w)))
        show=comp(cr).resize((w*scale,h*scale),Image.Resampling.NEAREST)
        card=Image.new("RGB",(show.width,show.height+30),"white")
        card.paste(show,(0,30))
        ImageDraw.Draw(card).text((4,4),f"idx={idx} cell={x},{y},{w},{h}",fill="black")
        cards.append(card)
    if not cards: return
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
    sheet.thumbnail((1800,14000),Image.Resampling.LANCZOS)
    sheet.save(out/name,quality=94)

maxidx=max(int(r["idx"]) for r in regions)
make_contact(0,39,"C151_C598_CONTACT_000_039.jpg")
make_contact(40,88,"C151_C598_CONTACT_040_088.jpg")
make_contact(89,maxidx,"C151_C598_CONTACT_089_END.jpg")

expected=[
"Giant Statues","Cape Way","Imperial Avenue","Ancient Ruins","Metropolis","Tulip Garden",
"Skyscrapers","Milky Way","Floral Village","Legend","OutRun MODE","Time Attack MODE",
"15 Continuous Course Ranking","Top Runners of Each Goal","Heart Attack MODE","NORMAL","TUNED",
"GOAL A","GOAL B","GOAL C","GOAL D","GOAL E","OutRun2SP 15 Continuous Course","OutRun2 15 Continuous Course"
]
report={
    "schema_version":1,"role":"C","run":run,"queue_index":86,"asset":asset,
    "revalidates":"B_PRODUCTION75 failed preflight assumption",
    "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":COMMIT,
        "git_blob_sha1":SOURCE_BLOB_SHA1,"atlas_git_blob_sha1":ATLAS_BLOB_SHA1,"source_sha256":sha(sb)},
    "structure":{"dimensions":[W,H],"dds_fourcc":fourcc,"mipmaps":mips,
        "pitch_or_linear":pitch_or_linear,"pillow_decoded_rgba":True,"raw_orientation":"mirror_y"},
    "region_count":len(regions),"regions":meta,
    "expected_segments":expected,
    "protected_semantics":["Ferrari model names","MT","AT"],
    "machine_status":"DECODED_EVIDENCE_READY",
    "decision":"PENDING_CONTROLLER_SEMANTIC_BINDING_AND_STRICT_DXT5_ASSESSMENT",
    "RUNTIME_VALIDATION":"UNTESTED"
}
(out/"C151_C598_DECODED_PREFLIGHT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
summary={
    "run":run,"asset":"C598919A","index":86,"source_sha256":sha(sb),
    "dimensions":[W,H],"dds_fourcc":fourcc,"regions":len(regions),
    "status":"C151_DECODED_EVIDENCE_READY_PENDING_CONTROLLER",
    "runtime_validation":"UNTESTED",
    "report":f"localization/graphics/role_C/{run}/C151_C598_DECODED_PREFLIGHT.json"
}
(wr/"C151_C598919A.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False),flush=True)
