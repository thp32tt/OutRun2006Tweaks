#!/usr/bin/env python3
import os,json,hashlib,struct,subprocess,urllib.request,math
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted role A required")

repo=Path.cwd(); run="20261005-A-PRODUCTION35-PREFLIGHT"
out=repo/"localization/graphics/role_A"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
work=Path("/tmp/outrun_A35_preflight"); work.mkdir(parents=True,exist_ok=True)

COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
BASE="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+COMMIT
SOURCE_BLOB_SHA1="1e95df72109411fb1f9c398445db583ed31de2a1"
ATLAS_BLOB_SHA1="90b0122b7fdc44a553eff3f3e83278725ad0f24b"
source=work/"560FA536_HD.dds"; atlasp=work/"4x_560FA536_1024x1024_atlas.json"
urllib.request.urlretrieve(BASE+"/Release/spr_sprani_selector_cvt_Exst/560FA536_1024x1024.dds",source)
urllib.request.urlretrieve(BASE+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_selector_cvt_Exst/4x_560FA536_1024x1024_atlas.json",atlasp)

def blobsha(data): return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()
def sha256(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
sb=source.read_bytes(); ab=atlasp.read_bytes()
if blobsha(sb)!=SOURCE_BLOB_SHA1: raise RuntimeError(("source blob drift",blobsha(sb)))
if blobsha(ab)!=ATLAS_BLOB_SHA1: raise RuntimeError(("atlas blob drift",blobsha(ab)))
if sb[:4]!=b"DDS ": raise RuntimeError("not DDS")
H,W,pitch,depth,mips=struct.unpack_from("<5I",sb,12)
pf=struct.unpack_from("<8I",sb,76)
if (W,H,pitch,mips)!=(4096,4096,16384,1) or len(sb)!=128+W*H*4:
    raise RuntimeError(("structure",W,H,pitch,depth,mips,len(sb)))
rgbm=(pf[4],pf[5],pf[6])
if pf[3]!=32: raise RuntimeError(("bpp",pf))
if rgbm==(0xff,0xff00,0xff0000): RAWMODE="RGBA"
elif rgbm==(0xff0000,0xff00,0xff): RAWMODE="BGRA"
else: raise RuntimeError(("masks",rgbm))
raw=Image.frombytes("RGBA",(W,H),sb[128:],"raw",RAWMODE)
src=raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
atlas=json.loads(ab.decode("utf-8"))
regions={int(r["idx"]):r for r in atlas["regions"]}
if len(regions)!=48: raise RuntimeError(("atlas",len(regions)))

TARGETS={
 11:"TUNED",12:"NORMAL",14:"RANDOM",21:"初級者向けの車です。",22:"中級者向けの車です。",
 24:'To switch to "Single Player Mode", press the "View Change Button" and the "Brake Pedal" at the same time.',
 31:"Every player must participate at the same time to play this mode.",
 32:"Versus Special Course has been selected.",33:"Time Attack Mode",34:"Time Attack Mode",
 36:"The distance to the final goal will be very long.",37:"You will run 15 courses continuously.",44:"Steering Wheel :"
}
PROTECTED_TEXT={25:"song title",26:"song title",27:"song title",28:"song title",29:"song title",30:"song title",38:"OutRun2",45:"speed value",46:"speed value"}

def flatten(im):
    z=Image.new("RGBA",im.size,(88,88,88,255)); z.alpha_composite(im); return z.convert("RGB")

rows=[]
cards=[]
for idx,label in TARGETS.items():
    r=regions[idx]; x,y,w,h=map(int,r["rect"]); crop=src.crop((x,y,x+w,y+h))
    a=np.asarray(crop)
    alpha=a[:,:,3]
    vis=np.argwhere(alpha>0)
    abox=None
    if len(vis):
        y0,x0=vis.min(axis=0); y1,x1=vis.max(axis=0)+1
        abox=[int(x0),int(y0),int(x1),int(y1)]
    opaque=int((alpha==255).sum()); visible=int((alpha>0).sum())
    # dominant visible RGBs for style classification.
    px=a[alpha>0,:3]
    top=[]
    if len(px):
        q=(px//16)*16
        vals,cnt=np.unique(q,axis=0,return_counts=True)
        order=np.argsort(cnt)[::-1][:12]
        top=[{"rgb":vals[i].tolist(),"count":int(cnt[i])} for i in order]
    rows.append({"idx":idx,"label":label,"rect":[x,y,w,h],"alpha_bbox_local":abox,
                 "visible_pixels":visible,"opaque_pixels":opaque,"alpha_extrema":[int(alpha.min()),int(alpha.max())],
                 "dominant_rgb_q16":top})
    flat=flatten(crop)
    maxw,maxh=900,270
    sc=min(maxw/max(1,w),maxh/max(1,h),1.0)
    if sc<1: flat=flat.resize((max(1,int(w*sc)),max(1,int(h*sc))),Image.Resampling.LANCZOS)
    card=Image.new("RGB",(960,320),(232,232,232)); d=ImageDraw.Draw(card)
    d.text((8,8),f"idx {idx} {label} rect={x},{y},{w},{h} visible={visible}",fill=(0,0,0))
    card.paste(flat,(8,40)); cards.append(card)

sheet=Image.new("RGB",(1920,math.ceil(len(cards)/2)*320),(215,215,215))
for i,c in enumerate(cards): sheet.paste(c,((i%2)*960,(i//2)*320))
sheet.save(out/"A35_TARGET_SOURCE_CONTACTS.jpg",quality=95)

q=flatten(src).resize((1024,1024),Image.Resampling.LANCZOS)
q.save(out/"A35_SOURCE_READABLE_QUARTER.jpg",quality=94)
qr=flatten(raw).resize((1024,1024),Image.Resampling.LANCZOS)
qr.save(out/"A35_SOURCE_RAW_MIRROR_Y_QUARTER.jpg",quality=94)

report={
 "schema_version":1,"role":"A","run":run,"queue_index":101,
 "asset":"textures/load/spr_sprani_selector_cvt_Exst/560FA536_1024x1024.dds",
 "readiness":"ONE_STAGE_TO_RENDER","source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":COMMIT,
 "path":"Release/spr_sprani_selector_cvt_Exst/560FA536_1024x1024.dds","git_blob_sha1":SOURCE_BLOB_SHA1,"sha256":sha256(source)},
 "atlas_provenance":{"git_blob_sha1":ATLAS_BLOB_SHA1,"regions":len(regions),"sha256":sha256(atlasp)},
 "structure":{"dimensions":[W,H],"format":"RGBA32","raw_mode":RAWMODE,"pitch":pitch,"mipmaps":mips,"raw_orientation":"mirror_y"},
 "physical_targets":rows,"semantic_strings":12,"physical_target_count":len(rows),
 "protected_text_indices":PROTECTED_TEXT,
 "next_stage":"bind per-target source masks/style from canonical HD contacts and render in this invocation",
 "runtime_validation":"UNTESTED","status":"A35_PREFLIGHT_COMPLETE_CONTINUE_TO_RENDER"
}
(out/"A35_560FA536_PREFLIGHT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
(wr/"A35_560FA536_PREFLIGHT.json").write_text(json.dumps({
 "run":run,"index":101,"asset":"560FA536","source_sha256":report["source_provenance"]["sha256"],
 "physical_targets":len(rows),"semantic_strings":12,"status":report["status"],
 "report":"localization/graphics/role_A/20261005-A-PRODUCTION35-PREFLIGHT/A35_560FA536_PREFLIGHT.json"
},ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"index":101,"targets":len(rows),"status":report["status"]},ensure_ascii=False))
