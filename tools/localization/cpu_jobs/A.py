#!/usr/bin/env python3
import os, json, hashlib, struct, urllib.request, math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted role A required")

repo=Path.cwd()
run="20261005-A-PRODUCTION30-PREFLIGHT"
out=repo/"localization/graphics/role_A"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"
wr.mkdir(parents=True,exist_ok=True)
work=Path("/tmp/outrun_A_prod30_preflight")
work.mkdir(parents=True,exist_ok=True)

COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
BASE="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+COMMIT
SOURCE_BLOB_SHA1="eeecec9ecd494270932ce97a6c38dfd05205eb24"
ATLAS_BLOB_SHA1="581d42b49da9b882f2a54cdfef7675d147afacaa"
source=work/"37759842_HD.dds"
atlasp=work/"4x_37759842_1024x1024_atlas.json"
urllib.request.urlretrieve(BASE+"/Release/spr_sprani_selector_cvt_Exst/37759842_1024x1024.dds",source)
urllib.request.urlretrieve(BASE+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_selector_cvt_Exst/4x_37759842_1024x1024_atlas.json",atlasp)

def blobsha(data):
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
def sha256(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def count_alpha(im):
    h=im.getchannel("A").histogram()
    return sum(h[1:])

sb=source.read_bytes()
ab=atlasp.read_bytes()
if blobsha(sb)!=SOURCE_BLOB_SHA1:
    raise RuntimeError(("source blob drift",blobsha(sb)))
if blobsha(ab)!=ATLAS_BLOB_SHA1:
    raise RuntimeError(("atlas blob drift",blobsha(ab)))
if sb[:4]!=b"DDS ":
    raise RuntimeError("not DDS")

H,W,pitch,depth,mips=struct.unpack_from("<5I",sb,12)
pf=struct.unpack_from("<8I",sb,76)
if (W,H)!=(4096,4096) or len(sb)!=128+W*H*4:
    raise RuntimeError(("unexpected source structure",W,H,len(sb)))
rgbm=(pf[4],pf[5],pf[6])
if pf[3]!=32:
    raise RuntimeError(("unexpected bpp",pf))
if rgbm==(0xff,0xff00,0xff0000):
    rawmode="RGBA"
elif rgbm==(0xff0000,0xff00,0xff):
    rawmode="BGRA"
else:
    raise RuntimeError(("unexpected channel masks",rgbm))

raw=Image.frombytes("RGBA",(W,H),sb[128:],"raw",rawmode)
readable=raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
atlas=json.loads(ab.decode("utf-8"))
regions=sorted(atlas["regions"],key=lambda r:int(r["idx"]))
if len(regions)!=87 or atlas.get("width")!=4096 or atlas.get("height")!=4096:
    raise RuntimeError(("atlas drift",len(regions),atlas.get("width"),atlas.get("height")))

bg=(88,88,88)
def flatten(im):
    z=Image.new("RGBA",im.size,bg+(255,))
    z.alpha_composite(im)
    return z.convert("RGB")

# Full readable source and numbered atlas map.
flatten(readable).save(out/"A30_37759842_SOURCE_READABLE.jpg",quality=92)
annot=flatten(readable).copy()
d=ImageDraw.Draw(annot)
for r in regions:
    x,y,w,h=map(int,r["rect"])
    d.rectangle((x,y,x+w-1,y+h-1),outline=(255,255,255),width=3)
    label=str(r["idx"])
    d.rectangle((x,y,x+max(42,14*len(label)),y+28),fill=(0,0,0))
    d.text((x+4,y+3),label,fill=(255,255,255))
annot.save(out/"A30_37759842_ATLAS_NUMBERED.jpg",quality=92)

# Contact sheets preserve each atlas cell at a readable scale with idx + geometry.
meta=[]
cells=[]
for r in regions:
    idx=int(r["idx"]); x,y,w,h=map(int,r["rect"])
    crop=readable.crop((x,y,x+w,y+h))
    abox=crop.getchannel("A").getbbox()
    if abox:
        gb=[x+abox[0],y+abox[1],x+abox[2],y+abox[3]]
    else:
        gb=None
    meta.append({
        "idx":idx,"name":r.get("name"),"rect":[x,y,w,h],"alpha_bbox_local":list(abox) if abox else None,
        "alpha_bbox_global":gb,"visible_pixels":count_alpha(crop),"alpha_extrema":list(crop.getchannel("A").getextrema())
    })
    flat=flatten(crop)
    maxw,maxh=460,190
    scale=min(maxw/max(1,w),maxh/max(1,h),1.0)
    if scale<1.0:
        flat=flat.resize((max(1,int(round(w*scale))),max(1,int(round(h*scale)))),Image.Resampling.LANCZOS)
    card=Image.new("RGB",(500,240),(232,232,232))
    cd=ImageDraw.Draw(card)
    cd.text((8,7),f"idx {idx}  rect={x},{y},{w},{h}  visible={meta[-1]['visible_pixels']}",fill=(0,0,0))
    card.paste(flat,(8,40))
    cells.append(card)

cols=4
per_sheet=24
for start in range(0,len(cells),per_sheet):
    chunk=cells[start:start+per_sheet]
    rows=math.ceil(len(chunk)/cols)
    sheet=Image.new("RGB",(cols*500,rows*240),(210,210,210))
    for j,card in enumerate(chunk):
        sheet.paste(card,((j%cols)*500,(j//cols)*240))
    end=start+len(chunk)-1
    sheet.save(out/f"A30_37759842_CONTACT_{start:02d}_{end:02d}.jpg",quality=94)

report={
    "schema_version":1,
    "role":"A",
    "run":run,
    "queue_index":95,
    "asset":"textures/load/spr_sprani_selector_cvt_Exst/37759842_1024x1024.dds",
    "readiness":"ONE_STAGE_TO_RENDER",
    "purpose":"canonical HD atlas geometry/style binding preflight; continue to render in same controller invocation",
    "source_provenance":{
        "repository":"Sonic-TV/OR2006Sprites","commit":COMMIT,
        "path":"Release/spr_sprani_selector_cvt_Exst/37759842_1024x1024.dds",
        "git_blob_sha1":SOURCE_BLOB_SHA1,"sha256":sha256(source)
    },
    "atlas_provenance":{
        "path":"Original (PC)/Original (Tweaks dumps)/spr_sprani_selector_cvt_Exst/4x_37759842_1024x1024_atlas.json",
        "git_blob_sha1":ATLAS_BLOB_SHA1,"sha256":sha256(atlasp),"regions":len(regions)
    },
    "structure":{"dimensions":[W,H],"format":"RGBA32","pixel_raw_mode":rawmode,"pitch":pitch,"depth":depth,"mipmaps":mips,"bytes":len(sb),"raw_orientation":"mirror_y"},
    "regions":meta,
    "translation_segments_expected":20,
    "protected_policy":"song titles, Ferrari model names, MT/AT badges and brand logos remain original",
    "runtime_validation":"UNTESTED",
    "status":"A30_PREFLIGHT_COMPLETE_CONTINUE_TO_RENDER"
}
(out/"A30_37759842_PREFLIGHT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
(wr/"A30_37759842_PREFLIGHT.json").write_text(json.dumps({
    "run":run,"index":95,"asset":"37759842","source_sha256":report["source_provenance"]["sha256"],
    "source_dimensions":[W,H],"format":"RGBA32","regions":len(regions),
    "status":report["status"],"runtime_validation":"UNTESTED",
    "report":"localization/graphics/role_A/20261005-A-PRODUCTION30-PREFLIGHT/A30_37759842_PREFLIGHT.json"
},ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"run":run,"index":95,"regions":len(regions),"status":report["status"]},ensure_ascii=False))
