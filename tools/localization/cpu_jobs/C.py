#!/usr/bin/env python3
import os,json,hashlib,struct,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

repo=Path.cwd()
run="20261005-C116-313DB8CB"
out=repo/"localization/graphics/role_C"/run
out.mkdir(parents=True,exist_ok=True)
ap=repo/"localization/graphics/role_A/20261005-A-PRODUCTION19"
rep=json.loads((ap/"A_PRODUCTION19_313DB8CB_REPORT.json").read_text(encoding="utf-8"))
source=Path("/tmp/C116_313DB8CB_source.dds")
url="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+rep["source_provenance"]["commit"]+"/"+rep["source_provenance"]["path"]
urllib.request.urlretrieve(url,source)
candidate=repo/rep["candidate_path"]

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def decode(p):
    b=Path(p).read_bytes()
    if b[:4]!=b"DDS ": raise RuntimeError("not DDS")
    h=struct.unpack_from("<I",b,12)[0]; w=struct.unpack_from("<I",b,16)[0]
    pitch=struct.unpack_from("<I",b,20)[0]; depth=struct.unpack_from("<I",b,24)[0]; mips=struct.unpack_from("<I",b,28)[0]
    fourcc=b[84:88]; bpp=struct.unpack_from("<I",b,88)[0]; masks=struct.unpack_from("<IIII",b,92)
    if not (w==2048 and h==1024 and pitch==w*4 and depth==1 and mips==1 and fourcc==b"\0\0\0\0" and bpp==32 and masks==(0xff,0xff00,0xff0000,0xff000000)):
        raise RuntimeError(("unexpected DDS",w,h,pitch,depth,mips,fourcc,bpp,masks))
    raw=Image.frombytes("RGBA",(w,h),b[128:],"raw","RGBA")
    readable=raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    return b,np.asarray(readable),{"width":w,"height":h,"pitch":pitch,"depth":depth,"mips":mips,"format":"RGBA32","raw_orientation":"mirror_y"}
def mask(p): return np.asarray(Image.open(p).convert("L"))>0
def rect(shape,b):
    H,W=shape; x0,y0,x1,y1=map(int,b); m=np.zeros((H,W),bool); m[y0:y1,x0:x1]=True; return m
def bb(m):
    y,x=np.nonzero(m)
    return None if not len(x) else [int(x.min()),int(y.min()),int(x.max()+1),int(y.max()+1)]
def dil1(m):
    return np.asarray(Image.fromarray((m.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(3)))>0

sb,src,si=decode(source); cb,cand,ci=decode(candidate)
if sha(source)!=rep["source_sha256"]: raise RuntimeError(("source sha",sha(source),rep["source_sha256"]))
if sha(candidate)!=rep["candidate_sha256"]: raise RuntimeError(("candidate sha",sha(candidate),rep["candidate_sha256"]))
clean=np.asarray(Image.open(ap/"313DB8CB_HD_CLEAN_PLATE.png").convert("RGBA"))
persisted=np.asarray(Image.open(ap/"313DB8CB_HD_FINAL_DECODED_READABLE.png").convert("RGBA"))
source_mask=mask(ap/"313DB8CB_HD_SOURCE_TEXT_MASK.png")
allowed=mask(ap/"313DB8CB_HD_ALLOWED_SOURCE_BBOX_MASK.png")
protected=mask(ap/"313DB8CB_HD_PROTECTED_VISIBLE_MASK.png")
if not (src.shape==cand.shape==clean.shape==persisted.shape): raise RuntimeError("shape mismatch")

header_exact=bool(sb[:128]==cb[:128])
persisted_diff=int(np.count_nonzero(np.any(cand!=persisted,axis=2)))
clean_diff=np.any(clean!=src,axis=2)
final_diff=np.any(cand!=src,axis=2)
target=np.any(cand!=clean,axis=2)
clean_out=int(np.count_nonzero(clean_diff & ~source_mask))
final_out=int(np.count_nonzero(final_diff & ~allowed))
prot=int(np.count_nonzero(final_diff & protected))
alpha_out=int(np.count_nonzero((cand[:,:,3]!=src[:,:,3]) & ~allowed))
source_residue=int(np.count_nonzero(source_mask & (clean[:,:,3]>0)))
target_out=int(np.count_nonzero(target & ~allowed))

rows=[]; rmasks=[]
for r in rep["rows"]:
    ob=list(map(int,r["original_bbox"]))
    rm=target & rect(target.shape,ob)
    ab=bb(rm)
    sw,sh=ob[2]-ob[0],ob[3]-ob[1]
    if ab is None:
        rr={"key":r["key"],"original_bbox":ob,"localized_bbox":None,"containment":"FAIL","size_ceiling":"FAIL"}
    else:
        lw,lh=ab[2]-ab[0],ab[3]-ab[1]
        rr={"key":r["key"],"original_bbox":ob,"localized_bbox":ab,
            "delta_left":ab[0]-ob[0],"delta_right":ob[2]-ab[2],"delta_top":ab[1]-ob[1],"delta_bottom":ob[3]-ab[3],
            "source_size":[sw,sh],"localized_size":[lw,lh],
            "containment":"PASS" if ab[0]>=ob[0] and ab[1]>=ob[1] and ab[2]<=ob[2] and ab[3]<=ob[3] else "FAIL",
            "size_ceiling":"PASS" if lw<=sw and lh<=sh else "FAIL"}
    rows.append(rr); rmasks.append((r["key"],rm))

pair=0; touch=[]
for i in range(len(rmasks)):
    for j in range(i+1,len(rmasks)):
        ov=int(np.count_nonzero(rmasks[i][1]&rmasks[j][1]))
        near=int(np.count_nonzero(dil1(rmasks[i][1])&rmasks[j][1]))
        pair+=ov
        if ov or near: touch.append([rmasks[i][0],rmasks[j][0],ov,near])

ok=(header_exact and persisted_diff==0 and clean_out==0 and final_out==0 and prot==0 and alpha_out==0 and
    source_residue==0 and target_out==0 and pair==0 and not touch and
    all(x["containment"]=="PASS" and x["size_ceiling"]=="PASS" for x in rows))
res={
 "schema_version":1,"role":"C","run":run,"asset":"313DB8CB","producer_run":"A_PRODUCTION19",
 "source_sha256":rep["source_sha256"],"candidate_sha256":rep["candidate_sha256"],
 "structure":ci,"header_128_exact":header_exact,
 "persisted_final_vs_independent_decode_diff_pixels":persisted_diff,
 "clean_changed_pixels_outside_source_mask":clean_out,
 "clean_source_text_mask_alpha_residue_pixels":source_residue,
 "final_changed_pixels_outside_allowed_source_bboxes":final_out,
 "final_alpha_changed_pixels_outside_allowed_source_bboxes":alpha_out,
 "final_changed_pixels_in_protected_visible_mask":prot,
 "target_pixels_outside_allowed_source_bboxes":target_out,
 "localized_pair_overlap_pixels":pair,"localized_touch_pairs":touch,
 "rows":rows,
 "machine_status":"PASS" if ok else "FAIL",
 "controller_visual_qa":"PENDING",
 "runtime_validation":"UNTESTED"
}
(out/"C116_313DB8CB_MACHINE_QA.json").write_text(json.dumps(res,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("C116_313DB8CB",res["machine_status"],rep["candidate_sha256"],flush=True)
if not ok: raise SystemExit(2)
