#!/usr/bin/env python3
import hashlib,json,os,struct,urllib.request
from pathlib import Path
from PIL import Image

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted localization CPU worker / role A only")

repo=Path.cwd(); run="20261006-A-PROBE110-ZOOM169171177"
out=repo/"localization/graphics/role_A"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
BASE="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst"
prior=[
 (155,"4D49CA85_512x256.dds"),
 (157,"4DF4D7CD_512x512.dds"),
 (165,"5C98F2_512x512.dds"),
]
items=[
 (169,"638F38C0_512x256.dds"),
 (171,"67CE2848_512x256.dds"),
 (177,"7978907D_512x128.dds"),
]
def parse(p):
    raw=p.read_bytes()
    if raw[:4]!=b"DDS ": raise RuntimeError(("not dds",p.name))
    h=struct.unpack_from("<I",raw,12)[0]; w=struct.unpack_from("<I",raw,16)[0]; mips=struct.unpack_from("<I",raw,28)[0]
    bpp=struct.unpack_from("<I",raw,88)[0]; masks=struct.unpack_from("<IIII",raw,92)
    im=Image.open(p).convert("RGBA")
    if im.size!=(w,h): raise RuntimeError(("size mismatch",p.name,im.size,(w,h)))
    return raw,w,h,mips,bpp,masks,im
def proof(im,path,maxwh=(1100,900),quality=88):
    bg=Image.new("RGBA",im.size,(235,235,235,255)); bg.alpha_composite(im)
    z=bg.convert("RGB"); z.thumbnail(maxwh,Image.Resampling.LANCZOS); z.save(path,quality=quality,optimize=True)
results=[]
tmp=Path("/tmp/a110"); tmp.mkdir(exist_ok=True)
for idx,name in prior:
    p=tmp/name; urllib.request.urlretrieve(BASE+"/"+name,p)
    raw,w,h,mips,bpp,masks,rawim=parse(p)
    proof(rawim,out/f"A110_PRIOR_{name.split('_')[0]}_RAW_PROOF.jpg")
for idx,name in items:
    p=tmp/name; url=BASE+"/"+name; urllib.request.urlretrieve(url,p)
    raw,w,h,mips,bpp,masks,rawim=parse(p)
    readable=rawim.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    stem=name.split("_")[0]
    proof(readable,out/f"A110_{stem}_READABLE_PROOF.jpg",(1200,1000),92)
    proof(rawim,out/f"A110_{stem}_RAW_PROOF.jpg",(1200,1000),92)
    results.append({
      "queue_index":idx,"asset":name,"source_url":url,"sha256":hashlib.sha256(raw).hexdigest(),
      "bytes":len(raw),"width":w,"height":h,"mipmaps":mips,"bpp":bpp,"masks":[hex(x) for x in masks]
    })
report={"schema_version":1,"role":"A","run":run,"prior_raw_proofs":[155,157,165],"items":results,
        "status":"A110_PRIOR_RAW_PROOFS_PLUS_NEW_ZOOM_PROBE_COMPLETE_CONTROLLER_CLASSIFICATION_REQUIRED"}
(out/"A110_ZOOM169171177_PROBE.json").write_text(json.dumps(report,indent=2)+"\n")
(wr/"A110_ZOOM169171177_PROBE.json").write_text(json.dumps({
 "run":run,"indices":[169,171,177],"items":results,"report":str((out/"A110_ZOOM169171177_PROBE.json").relative_to(repo)),
 "status":report["status"]},indent=2)+"\n")
print(json.dumps(report),flush=True)
