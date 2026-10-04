#!/usr/bin/env python3
import os,json,hashlib,struct,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

repo=Path.cwd(); run="20261005-C122-1A43-RESIDUAL"
out=repo/"localization/graphics/role_C"/run; out.mkdir(parents=True,exist_ok=True)
bp=repo/"localization/graphics/role_B/20261005-B-PRODUCTION38"
rep=json.loads((bp/"B_PRODUCTION38_1A43_REPORT.json").read_text(encoding="utf-8"))
source=Path("/tmp/C122_1A43_source.dds"); urllib.request.urlretrieve(rep["source_url"],source)
candidate=repo/rep["candidate_path"]

def decode(p):
 b=Path(p).read_bytes(); h=struct.unpack_from("<I",b,12)[0];w=struct.unpack_from("<I",b,16)[0]
 raw=Image.open(p).convert("RGBA"); return np.asarray(raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM))
def mask(p): return np.asarray(Image.open(p).convert("L"))>0
def bbox(m):
 y,x=np.nonzero(m); return None if not len(x) else [int(x.min()),int(y.min()),int(x.max()+1),int(y.max()+1)]
src=decode(source); cand=decode(candidate)
clean=np.asarray(Image.open(bp/"1A43E9D9_CLEAN_PLATE.png").convert("RGBA"))
sm=mask(bp/"1A43E9D9_SOURCE_TEXT_MASK.png")
pt=mask(bp/"1A43E9D9_TARGET_TEXT_MASK.png")
allowed=mask(bp/"1A43E9D9_ALLOWED_TEXT_REGION_MASK.png")

visible=(cand[:,:,3]>0)&(clean[:,:,3]==0)
resid=visible & ~pt & sm
outside_source=resid & (src[:,:,3]==0)
source_overlap=resid & (src[:,:,3]>0)
alpha=cand[:,:,3]
thresholds={str(t):int(np.count_nonzero(resid & (alpha>=t))) for t in [1,2,4,8,16,32,64,96,128,160,192,224]}
source_alpha=src[:,:,3]
source_thresholds={str(t):int(np.count_nonzero(resid & (source_alpha>=t))) for t in [1,8,32,64,128,192]}
exact_rgba=int(np.count_nonzero(resid & np.all(cand==src,axis=2)))
same_alpha=int(np.count_nonzero(resid & (cand[:,:,3]==src[:,:,3])))
rows=[]
for rr in rep["rows"]:
 x0,y0,x1,y1=map(int,rr["original_bbox"]); r=np.zeros(resid.shape,bool);r[y0:y1,x0:x1]=resid[y0:y1,x0:x1]
 rows.append({"n":rr["n"],"source":rr["source"],"residual_pixels":int(r.sum()),"residual_bbox":bbox(r),
              "alpha_ge_8":int(np.count_nonzero(r&(alpha>=8))),"alpha_ge_32":int(np.count_nonzero(r&(alpha>=32))),
              "alpha_ge_128":int(np.count_nonzero(r&(alpha>=128))),"source_alpha_overlap":int(np.count_nonzero(r&(source_alpha>0)))})
# visual diagnostic: candidate readable plus red overlay on residual at native size, then 2x crop
base=Image.fromarray(cand,"RGBA").convert("RGB")
overlay=base.copy(); d=ImageDraw.Draw(overlay)
ys,xs=np.nonzero(resid)
for x,y in zip(xs.tolist(),ys.tolist()):
    d.point((x,y),fill=(255,0,0))
cr=(300,0,1700,256)
overlay.crop(cr).resize(((cr[2]-cr[0])*2,(cr[3]-cr[1])*2),Image.Resampling.NEAREST).save(out/"C122_RESIDUAL_OVERLAY_2X.png")
Image.fromarray((resid.astype(np.uint8)*255),"L").save(out/"C122_RESIDUAL_MASK.png")
res={"schema_version":1,"role":"C","run":run,"asset":"1A43E9D9","producer_run":"B_PRODUCTION38",
 "candidate_sha256":hashlib.sha256(candidate.read_bytes()).hexdigest(),
 "residual_definition":"decoded candidate visible alpha over transparent CLEAN, outside producer target mask, inside producer source-text mask",
 "residual_pixels":int(resid.sum()),"residual_bbox":bbox(resid),"residual_source_alpha_overlap_pixels":int(source_overlap.sum()),
 "residual_outside_source_visible_alpha_pixels":int(outside_source.sum()),"candidate_alpha_threshold_counts":thresholds,
 "source_alpha_threshold_counts_at_residual":source_thresholds,"candidate_exactly_equals_source_rgba_pixels":exact_rgba,
 "candidate_alpha_equals_source_alpha_pixels":same_alpha,"rows":rows,
 "policy_interpretation":"Any confirmed source-script/effect alpha residue outside localized target is a zero-residue/zero-overlap failure; controller must inspect overlay before final decision.",
 "runtime_validation":"UNTESTED"}
(out/"C122_RESIDUAL_DIAGNOSTIC.json").write_text(json.dumps(res,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(res,ensure_ascii=False),flush=True)
