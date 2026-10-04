#!/usr/bin/env python3
import os,json,hashlib,struct,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

repo=Path.cwd()
run="20261005-C113-FD90"
out=repo/"localization/graphics/role_C"/run
out.mkdir(parents=True,exist_ok=True)
ar=repo/"localization/graphics/role_A/20261005-A-RECOVERY13"
rep=json.loads((ar/"A_RECOVERY13_FD90AA9_REPORT.json").read_text(encoding="utf-8"))
asset=rep["asset"]
source=repo/"localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a"/asset
candidate=repo/rep["candidate_path"]
old_url="https://raw.githubusercontent.com/thp32tt/OutRun2006Tweaks/dd479022a3554baff84e5ca8ac53f2ab7dff109b/localization/graphics/hd_candidates/textures/load/spr_sprani_selector_cvt_Exst/FD90AA9_1024x1024.dds"
old_path=Path("/tmp/C113_FD90_old.dds")
urllib.request.urlretrieve(old_url,old_path)
OLD_SHA=rep["input_candidate_sha256"]

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def decode(p):
    b=Path(p).read_bytes()
    if b[:4]!=b"DDS ": raise RuntimeError("not DDS")
    h=struct.unpack_from("<I",b,12)[0]; w=struct.unpack_from("<I",b,16)[0]
    pitch=struct.unpack_from("<I",b,20)[0]; depth=struct.unpack_from("<I",b,24)[0]; mips=struct.unpack_from("<I",b,28)[0]
    fourcc=b[84:88]; bpp=struct.unpack_from("<I",b,88)[0]; masks=struct.unpack_from("<IIII",b,92)
    if not (w==4096 and h==4096 and pitch==w*4 and depth==1 and mips==1 and fourcc==b"\0\0\0\0" and bpp==32 and masks==(0xff,0xff00,0xff0000,0xff000000)):
        raise RuntimeError(("unexpected DDS",w,h,pitch,depth,mips,fourcc,bpp,masks))
    raw=Image.frombytes("RGBA",(w,h),b[128:],"raw","RGBA")
    im=raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    return b,np.asarray(im),{"width":w,"height":h,"pitch":pitch,"depth":depth,"mips":mips,"format":"RGBA32","raw_orientation":"mirror_y"}
def mask(p): return np.asarray(Image.open(p).convert("L"))>0
def rect(shape,b):
    H,W=shape; x0,y0,x1,y1=map(int,b); m=np.zeros((H,W),bool); m[y0:y1,x0:x1]=True; return m
def bb(m):
    y,x=np.nonzero(m)
    return None if not len(x) else [int(x.min()),int(y.min()),int(x.max()+1),int(y.max()+1)]
def dil1(m):
    return np.asarray(Image.fromarray((m.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(3)))>0

sb,src,si=decode(source); cb,cand,ci=decode(candidate); ob,old,oi=decode(old_path)
if sha(source)!=rep["source_sha256"]: raise RuntimeError("source sha mismatch")
if sha(candidate)!=rep["candidate_sha256"]: raise RuntimeError("candidate sha mismatch")
if sha(old_path)!=OLD_SHA: raise RuntimeError(("old candidate sha mismatch",sha(old_path),OLD_SHA))
if sb[:128]!=cb[:128] or sb[:128]!=ob[:128]: raise RuntimeError("header mismatch")

clean=np.asarray(Image.open(ar/"FD90AA9_CLEAN_PLATE.png").convert("RGBA"))
source_mask=mask(ar/"FD90AA9_SOURCE_TEXT_MASK.png")
protected=mask(ar/"FD90AA9_CLEAN_PLATE_PROTECTED_MASK.png")
final_persist=np.asarray(Image.open(ar/"FD90AA9_FINAL_READABLE.png").convert("RGBA"))
if not (clean.shape==src.shape==cand.shape==old.shape==final_persist.shape): raise RuntimeError("shape mismatch")

decoded_final_diff=int(np.count_nonzero(np.any(cand!=final_persist,axis=2)))
clean_diff=np.any(clean!=src,axis=2)
clean_outside=int(np.count_nonzero(clean_diff & ~source_mask))
clean_protected=int(np.count_nonzero(clean_diff & protected))
source_mask_unchanged=int(np.count_nonzero(source_mask & np.all(clean==src,axis=2)))

target=np.any(cand!=clean,axis=2)
allowed=np.zeros(target.shape,bool)
rows=[]; rmasks=[]
for r in rep["rows"]:
    obox=list(map(int,r["original_bbox"])); lbox=list(map(int,r["localized_bbox"]))
    allowed |= rect(target.shape,obox)
    rm=target & rect(target.shape,lbox)
    ab=bb(rm)
    sw,sh=obox[2]-obox[0],obox[3]-obox[1]
    if ab is None:
        rr={"key":r["key"],"original_bbox":obox,"localized_bbox":None,"containment":"FAIL","size_ceiling":"FAIL"}
    else:
        lw,lh=ab[2]-ab[0],ab[3]-ab[1]
        rr={"key":r["key"],"original_bbox":obox,"localized_bbox":ab,
            "delta_left":ab[0]-obox[0],"delta_right":obox[2]-ab[2],"delta_top":ab[1]-obox[1],"delta_bottom":obox[3]-ab[3],
            "source_size":[sw,sh],"localized_size":[lw,lh],
            "containment":"PASS" if ab[0]>=obox[0] and ab[1]>=obox[1] and ab[2]<=obox[2] and ab[3]<=obox[3] else "FAIL",
            "size_ceiling":"PASS" if lw<=sw and lh<=sh else "FAIL"}
    rows.append(rr); rmasks.append((r["key"],rm))

target_outside=int(np.count_nonzero(target & ~allowed))
final_diff=np.any(cand!=src,axis=2)
final_outside=int(np.count_nonzero(final_diff & ~allowed))

pair=0; touch=[]
for i in range(len(rmasks)):
    for j in range(i+1,len(rmasks)):
        ov=int(np.count_nonzero(rmasks[i][1]&rmasks[j][1]))
        near=int(np.count_nonzero(dil1(rmasks[i][1])&rmasks[j][1]))
        pair+=ov
        if ov or near: touch.append([rmasks[i][0],rmasks[j][0],ov,near])

rework=set(rep["reworked_keys"])
returned_union=np.zeros(target.shape,bool)
for r in rep["rows"]:
    if r["key"] in rework: returned_union |= rect(target.shape,r["original_bbox"])
new_vs_old=np.any(cand!=old,axis=2)
changes_vs_old_outside=int(np.count_nonzero(new_vs_old & ~returned_union))

preserved={}
for r in rep["rows"]:
    if r["key"] in rework: continue
    box=list(map(int,r["original_bbox"]))
    m=rect(target.shape,box)
    preserved[r["key"]]=int(np.count_nonzero(new_vs_old & m))
preserved_ok=all(v==0 for v in preserved.values()) and len(preserved)==25

machine_ok=(decoded_final_diff==0 and clean_outside==0 and clean_protected==0 and source_mask_unchanged==0 and
            target_outside==0 and final_outside==0 and pair==0 and not touch and
            changes_vs_old_outside==0 and preserved_ok and
            all(r["containment"]=="PASS" and r["size_ceiling"]=="PASS" for r in rows))
res={
 "schema_version":1,"role":"C","run":run,"asset":"FD90AA9","producer_run":"A_RECOVERY13",
 "source_sha256":rep["source_sha256"],"prior_candidate_sha256":OLD_SHA,"candidate_sha256":rep["candidate_sha256"],
 "structure":ci,"header_128_exact":True,
 "persisted_final_vs_independent_decode_diff_pixels":decoded_final_diff,
 "clean_changed_pixels_outside_source_mask":clean_outside,
 "clean_changed_pixels_in_protected_mask":clean_protected,
 "source_mask_pixels_unchanged_in_clean":source_mask_unchanged,
 "target_pixels_outside_union_source_bboxes":target_outside,
 "final_changed_pixels_outside_union_source_bboxes":final_outside,
 "localized_pair_overlap_pixels":pair,"localized_touch_pairs":touch,
 "changes_vs_prior_candidate_outside_4_returned_source_bboxes":changes_vs_old_outside,
 "preserved_25_prior_candidate_pixel_diffs":preserved,"preserved_25_all_zero":preserved_ok,
 "rows":rows,
 "machine_status":"PASS" if machine_ok else "FAIL",
 "controller_visual_qa":"PENDING","runtime_validation":"UNTESTED"
}
(out/"C113_FD90AA9_MACHINE_QA.json").write_text(json.dumps(res,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("C113_FD90",res["machine_status"],rep["candidate_sha256"],"preserved",preserved_ok,"outside",changes_vs_old_outside,flush=True)
