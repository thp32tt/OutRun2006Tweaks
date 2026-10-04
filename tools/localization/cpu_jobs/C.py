#!/usr/bin/env python3
import os,json,hashlib,struct,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

repo=Path.cwd()
run="20261005-C127-D41D0B1"
out=repo/"localization/graphics/role_C"/run
out.mkdir(parents=True,exist_ok=True)
bp=repo/"localization/graphics/role_B/20261005-B-PRODUCTION43"
rep=json.loads((bp/"B_PRODUCTION43_D41_REPORT.json").read_text(encoding="utf-8"))
source=Path("/tmp/C127_D41_source.dds")
urllib.request.urlretrieve(rep["source_url"],source)
candidate=repo/rep["candidate_path"]

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def decode(p):
    b=Path(p).read_bytes()
    if b[:4]!=b"DDS ": raise RuntimeError(("not DDS",str(p)))
    h=struct.unpack_from("<I",b,12)[0]; w=struct.unpack_from("<I",b,16)[0]
    linear=struct.unpack_from("<I",b,20)[0]; depth=struct.unpack_from("<I",b,24)[0]; mips=struct.unpack_from("<I",b,28)[0]
    fourcc=b[84:88]
    if not (w==2048 and h==256 and linear==524288 and depth==1 and mips==1 and fourcc==b"DXT5"):
        raise RuntimeError(("unexpected DDS",w,h,linear,depth,mips,fourcc))
    raw=Image.open(p).convert("RGBA")
    readable=raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    return b,np.asarray(readable),{"width":w,"height":h,"linear_size":linear,"depth":depth,"mips":mips,"format":"DXT5","raw_orientation":"mirror_y"}
def img(p): return np.asarray(Image.open(p).convert("RGBA"))
def mask(p): return np.asarray(Image.open(p).convert("L"))>0
def bb(m):
    y,x=np.nonzero(m)
    return None if not len(x) else [int(x.min()),int(y.min()),int(x.max()+1),int(y.max()+1)]
def rect(shape,b):
    H,W=shape; x0,y0,x1,y1=map(int,b); m=np.zeros((H,W),bool); m[y0:y1,x0:x1]=True; return m
def dil(m,px=2):
    return np.asarray(Image.fromarray((m.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(px*2+1)))>0

if sha(source)!=rep["source_sha256"]: raise RuntimeError(("source sha mismatch",sha(source),rep["source_sha256"]))
if sha(candidate)!=rep["candidate_sha256"]: raise RuntimeError(("candidate sha mismatch",sha(candidate),rep["candidate_sha256"]))
sb,src,si=decode(source); cb,cand,ci=decode(candidate)
header_exact=bool(sb[:128]==cb[:128])
clean=img(bp/"D41D0B1_CLEAN_PLATE.png")
sm=mask(bp/"D41D0B1_SOURCE_TEXT_MASK.png")
allowed=mask(bp/"D41D0B1_ALLOWED_TEXT_REGION_MASK.png")
protected=mask(bp/"D41D0B1_PROTECTED_MASK.png")
ptarget=mask(bp/"D41D0B1_TARGET_TEXT_MASK.png")
if not (src.shape==cand.shape==clean.shape): raise RuntimeError(("shape",src.shape,cand.shape,clean.shape))

clean_changed=np.any(clean!=src,axis=2)
clean_out=int(np.count_nonzero(clean_changed & ~sm))
source_mask_alpha_residue=int(np.count_nonzero(sm & (clean[:,:,3]>16)))
visible=(cand[:,:,3]>16)
alpha_changed=(cand[:,:,3]!=src[:,:,3])
visible_out=int(np.count_nonzero(visible & ~allowed))
alpha_out=int(np.count_nonzero(alpha_changed & ~allowed))
protected_visible=int(np.count_nonzero(visible & protected))
target_guard=dil(ptarget,2)
residual=visible & sm & ~target_guard
residual_gt16=int(np.count_nonzero(residual))
residual_max_alpha=int(cand[:,:,3][residual].max()) if residual_gt16 else 0
target_visible_out=int(np.count_nonzero((visible & target_guard) & ~allowed))

rows=[]
rmasks=[]
for rr in rep["rows"]:
    ob=list(map(int,rr["original_bbox"]))
    region=rect(sm.shape,ob)
    rm=visible & target_guard & region
    lb=bb(rm)
    if lb is None:
        contain=size_ok=False; deltas=[None]*4; lw=lh=0
    else:
        sw,sh=ob[2]-ob[0],ob[3]-ob[1]; lw,lh=lb[2]-lb[0],lb[3]-lb[1]
        contain=lb[0]>=ob[0] and lb[1]>=ob[1] and lb[2]<=ob[2] and lb[3]<=ob[3]
        size_ok=lw<=sw and lh<=sh
        deltas=[lb[0]-ob[0],ob[2]-lb[2],lb[1]-ob[1],ob[3]-lb[3]]
    edge=lb is not None and any(d==0 for d in deltas)
    rows.append({
      "n":rr["n"],"source":rr["source"],"korean":rr["korean"],"original_bbox":ob,"localized_bbox":lb,
      "producer_decoded_localized_bbox":list(map(int,rr["decoded_localized_bbox"])),
      "source_size":[ob[2]-ob[0],ob[3]-ob[1]],"localized_size":[lw,lh],
      "delta_left":deltas[0],"delta_right":deltas[1],"delta_top":deltas[2],"delta_bottom":deltas[3],
      "containment":"PASS" if contain else "FAIL","size_ceiling":"PASS" if size_ok else "FAIL",
      "edge_touch_high_risk":edge
    })
    rmasks.append((str(rr["n"]),rm))

pair_overlap=0; touch=[]
for i in range(len(rmasks)):
    for j in range(i+1,len(rmasks)):
        ov=int(np.count_nonzero(rmasks[i][1]&rmasks[j][1]))
        near=int(np.count_nonzero(dil(rmasks[i][1],1)&rmasks[j][1]))
        pair_overlap+=ov
        if ov or near: touch.append([rmasks[i][0],rmasks[j][0],ov,near])

actual_gap=rows[1]["localized_bbox"][1]-rows[0]["localized_bbox"][3] if all(r["localized_bbox"] for r in rows) else None
all_positive=all(r["containment"]=="PASS" and r["size_ceiling"]=="PASS" and not r["edge_touch_high_risk"] for r in rows)
ok=(header_exact and clean_out==0 and source_mask_alpha_residue==0 and visible_out==0 and alpha_out==0 and
    protected_visible==0 and residual_gt16==0 and target_visible_out==0 and pair_overlap==0 and not touch and
    all_positive and actual_gap is not None and actual_gap>0)

res={
 "schema_version":1,"role":"C","run":run,"asset":"D41D0B1","queue_index":112,"producer_run":"B_PRODUCTION43",
 "source_sha256":rep["source_sha256"],"candidate_sha256":rep["candidate_sha256"],"structure":ci,"header_128_exact":header_exact,
 "clean_changed_pixels_outside_source_mask":clean_out,
 "clean_source_mask_alpha_residue_pixels_gt16":source_mask_alpha_residue,
 "visible_pixels_outside_allowed_alpha_gt16":visible_out,
 "alpha_changed_pixels_outside_allowed":alpha_out,
 "protected_visible_pixels_alpha_gt16":protected_visible,
 "residual_source_effect_pixels_outside_2px_target_guard_alpha_gt16":residual_gt16,
 "residual_max_alpha":residual_max_alpha,
 "target_visible_pixels_outside_allowed":target_visible_out,
 "localized_pair_overlap_pixels":pair_overlap,"localized_touch_pairs":touch,
 "decoded_row_gap":actual_gap,
 "multi_line_style_consistency_from_producer":rep["multi_line"]["style_consistency"],
 "rows":rows,
 "machine_status":"PASS" if ok else "FAIL",
 "controller_visual_qa":"PENDING","runtime_validation":"UNTESTED"
}
(out/"C127_D41D0B1_MACHINE_QA.json").write_text(json.dumps(res,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("C127_D41D0B1",res["machine_status"],rep["candidate_sha256"],"gap",actual_gap,flush=True)
if not ok: raise SystemExit(2)
