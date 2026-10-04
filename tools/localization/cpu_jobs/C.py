#!/usr/bin/env python3
import os,json,hashlib,struct,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

repo=Path.cwd()
run="20261005-C126-42E618FD"
out=repo/"localization/graphics/role_C"/run
out.mkdir(parents=True,exist_ok=True)
bp=repo/"localization/graphics/role_B/20261005-B-PRODUCTION40"
rep=json.loads((bp/"B_PRODUCTION40_42E_REPORT.json").read_text(encoding="utf-8"))
source=Path("/tmp/C126_42E_source.dds")
urllib.request.urlretrieve(rep["source_url"],source)
candidate=repo/rep["candidate_path"]

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def decode(p):
    b=Path(p).read_bytes()
    if b[:4]!=b"DDS ": raise RuntimeError(("not DDS",str(p)))
    h=struct.unpack_from("<I",b,12)[0]; w=struct.unpack_from("<I",b,16)[0]
    linear=struct.unpack_from("<I",b,20)[0]; depth=struct.unpack_from("<I",b,24)[0]; mips=struct.unpack_from("<I",b,28)[0]
    fourcc=b[84:88]
    if not (w==2048 and h==128 and linear==262144 and depth==1 and mips==1 and fourcc==b"DXT5"):
        raise RuntimeError(("unexpected DDS",w,h,linear,depth,mips,fourcc))
    raw=Image.open(p).convert("RGBA")
    readable=raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    return b,np.asarray(readable),{"width":w,"height":h,"linear_size":linear,"depth":depth,"mips":mips,"format":"DXT5","raw_orientation":"mirror_y"}

def img(p): return np.asarray(Image.open(p).convert("RGBA"))
def mask(p): return np.asarray(Image.open(p).convert("L"))>0
def bb(m):
    y,x=np.nonzero(m)
    return None if not len(x) else [int(x.min()),int(y.min()),int(x.max()+1),int(y.max()+1)]
def dilate(m,px=2):
    im=Image.fromarray((m.astype(np.uint8)*255),"L")
    return np.asarray(im.filter(ImageFilter.MaxFilter(px*2+1)))>0

if sha(source)!=rep["source_sha256"]: raise RuntimeError(("source sha mismatch",sha(source),rep["source_sha256"]))
if sha(candidate)!=rep["candidate_sha256"]: raise RuntimeError(("candidate sha mismatch",sha(candidate),rep["candidate_sha256"]))
sb,src,si=decode(source); cb,cand,ci=decode(candidate)
header_exact=bool(sb[:128]==cb[:128])

clean=img(bp/"42E618FD_CLEAN_PLATE.png")
sm=mask(bp/"42E618FD_SOURCE_TEXT_MASK.png")
allowed=mask(bp/"42E618FD_ALLOWED_TEXT_REGION_MASK.png")
protected=mask(bp/"42E618FD_PROTECTED_MASK.png")
ptarget=mask(bp/"42E618FD_TARGET_TEXT_MASK.png")
if not (src.shape==cand.shape==clean.shape): raise RuntimeError(("shape mismatch",src.shape,cand.shape,clean.shape))

clean_changed=np.any(clean!=src,axis=2)
clean_out=int(np.count_nonzero(clean_changed & ~sm))
source_mask_unchanged=int(np.count_nonzero(sm & np.all(clean==src,axis=2)))

# For BC3, alpha/visible decoded evidence is authoritative; transparent RGB can drift.
alpha_changed=(cand[:,:,3]!=src[:,:,3])
visible=(cand[:,:,3]>16)
visible_out=int(np.count_nonzero(visible & ~allowed))
alpha_out=int(np.count_nonzero(alpha_changed & ~allowed))
protected_visible=int(np.count_nonzero(visible & protected))
target_guard=dilate(ptarget,2)
residual=visible & sm & ~target_guard
residual_pixels=int(np.count_nonzero(residual))
residual_max_alpha=int(cand[:,:,3][residual].max()) if residual_pixels else 0
residual_ge17=int(np.count_nonzero(residual & (cand[:,:,3]>16)))
residual_ge32=int(np.count_nonzero(residual & (cand[:,:,3]>=32)))

# Derive localized visible bbox using candidate alpha above policy threshold within the exact original bbox.
rr=rep["rows"][0]
ob=list(map(int,rr["original_bbox"]))
x0,y0,x1,y1=ob
region=np.zeros(sm.shape,bool);region[y0:y1,x0:x1]=True
localized=visible & region & target_guard
lb=bb(localized)
if lb is None: raise RuntimeError("no localized visible pixels")
sw,sh=x1-x0,y1-y0; lw,lh=lb[2]-lb[0],lb[3]-lb[1]
contain=lb[0]>=x0 and lb[1]>=y0 and lb[2]<=x1 and lb[3]<=y1
size_ok=lw<=sw and lh<=sh
deltas=[lb[0]-x0,x1-lb[2],lb[1]-y0,y1-lb[3]]
edge_touch=any(d==0 for d in deltas)

# Producer target mask can be precompression geometry; only ensure all intended target visible pixels are captured.
target_visible=visible & target_guard
target_outside_allowed=int(np.count_nonzero(target_visible & ~allowed))

ok=(header_exact and clean_out==0 and source_mask_unchanged==0 and visible_out==0 and alpha_out==0 and
    protected_visible==0 and residual_ge17==0 and target_outside_allowed==0 and contain and size_ok and not edge_touch)

res={
 "schema_version":1,"role":"C","run":run,"asset":"42E618FD","queue_index":98,"producer_run":"B_PRODUCTION40",
 "source_sha256":rep["source_sha256"],"candidate_sha256":rep["candidate_sha256"],
 "structure":ci,"header_128_exact":header_exact,
 "clean_changed_pixels_outside_source_mask":clean_out,
 "source_mask_pixels_unchanged_in_clean":source_mask_unchanged,
 "visible_pixels_outside_allowed_mask_alpha_gt16":visible_out,
 "alpha_changed_pixels_outside_allowed_mask":alpha_out,
 "protected_visible_pixels_alpha_gt16":protected_visible,
 "residual_visible_pixels_outside_2px_target_guard_alpha_gt16":residual_ge17,
 "residual_pixels_all_alpha":residual_pixels,
 "residual_max_alpha":residual_max_alpha,
 "residual_pixels_alpha_ge32":residual_ge32,
 "target_visible_pixels_outside_allowed":target_outside_allowed,
 "rows":[{
   "source":rr["source"],"korean":rr["korean"],"original_bbox":ob,"localized_bbox":lb,
   "producer_decoded_localized_bbox":list(map(int,rr["decoded_localized_bbox"])),
   "source_size":[sw,sh],"localized_size":[lw,lh],
   "delta_left":deltas[0],"delta_right":deltas[1],"delta_top":deltas[2],"delta_bottom":deltas[3],
   "containment":"PASS" if contain else "FAIL","size_ceiling":"PASS" if size_ok else "FAIL",
   "edge_touch_high_risk":edge_touch
 }],
 "machine_status":"PASS" if ok else "FAIL",
 "controller_visual_qa":"PENDING",
 "runtime_validation":"UNTESTED"
}
(out/"C126_42E618FD_MACHINE_QA.json").write_text(json.dumps(res,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("C126_42E618FD",res["machine_status"],rep["candidate_sha256"],res["rows"][0],flush=True)
if not ok: raise SystemExit(2)
