#!/usr/bin/env python3
import os,json,hashlib,struct,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

repo=Path.cwd()
run="20261005-C119-NEW-A"
out=repo/"localization/graphics/role_C"/run
out.mkdir(parents=True,exist_ok=True)

ASSETS=[
 {
  "asset":"9CE4E175","producer_run":"A_PRODUCTION20","producer_dir":"localization/graphics/role_A/20261005-A-PRODUCTION20",
  "report":"A_PRODUCTION20_9CE4E175_REPORT.json",
  "source_png":"9CE4E175_HD_SOURCE_READABLE.png","clean_png":"9CE4E175_HD_CLEAN_PLATE.png",
  "final_png":"9CE4E175_HD_FINAL_DECODED_READABLE.png","source_mask":"9CE4E175_HD_SOURCE_TEXT_MASK.png",
  "allowed_mask":"9CE4E175_HD_ALLOWED_SOURCE_BBOX_MASK.png","protected_mask":"9CE4E175_HD_PROTECTED_VISIBLE_MASK.png"
 },
 {
  "asset":"EBEF6D20","producer_run":"A_PRODUCTION21","producer_dir":"localization/graphics/role_A/20261005-A-PRODUCTION21",
  "report":"A_PRODUCTION21_EBEF6D20_REPORT.json",
  "source_png":"EBEF6D20_HD_SOURCE_READABLE.png","clean_png":"EBEF6D20_HD_CLEAN_PLATE.png",
  "final_png":"EBEF6D20_HD_FINAL_DECODED_READABLE.png","source_mask":"EBEF6D20_HD_SOURCE_TEXT_MASK.png",
  "allowed_mask":"EBEF6D20_HD_ALLOWED_SOURCE_BBOX_MASK.png","protected_mask":"EBEF6D20_HD_PROTECTED_VISIBLE_MASK.png"
 }
]

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def decode_dds(p):
    b=Path(p).read_bytes()
    if b[:4]!=b"DDS ": raise RuntimeError(("not DDS",str(p)))
    h=struct.unpack_from("<I",b,12)[0]; w=struct.unpack_from("<I",b,16)[0]
    pitch=struct.unpack_from("<I",b,20)[0]; depth=struct.unpack_from("<I",b,24)[0]; mips=struct.unpack_from("<I",b,28)[0]
    fourcc=b[84:88]; bpp=struct.unpack_from("<I",b,88)[0]; masks=struct.unpack_from("<IIII",b,92)
    if fourcc!=b"\0\0\0\0" or bpp!=32 or pitch!=w*4 or mips!=1:
        raise RuntimeError(("unexpected DDS",w,h,pitch,depth,mips,fourcc,bpp,masks))
    if masks==(0xff,0xff00,0xff0000,0xff000000): rawmode="RGBA"
    elif masks==(0xff0000,0xff00,0xff,0xff000000): rawmode="BGRA"
    else: raise RuntimeError(("unsupported masks",masks))
    raw=Image.frombytes("RGBA",(w,h),b[128:],"raw",rawmode)
    readable=raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    return b,np.asarray(readable),{"width":w,"height":h,"pitch":pitch,"depth":depth,"mips":mips,"format":"RGBA32","raw_mode":rawmode,"masks":[hex(x) for x in masks],"raw_orientation":"mirror_y"}

def img(p): return np.asarray(Image.open(p).convert("RGBA"))
def mask(p): return np.asarray(Image.open(p).convert("L"))>0
def bb(m):
    y,x=np.nonzero(m)
    return None if not len(x) else [int(x.min()),int(y.min()),int(x.max()+1),int(y.max()+1)]
def rect(shape,b):
    H,W=shape; x0,y0,x1,y1=map(int,b); m=np.zeros((H,W),bool); m[y0:y1,x0:x1]=True; return m
def dil1(m):
    return np.asarray(Image.fromarray((m.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(3)))>0

results=[]
for cfg in ASSETS:
    ap=repo/cfg["producer_dir"]
    rep=json.loads((ap/cfg["report"]).read_text(encoding="utf-8"))
    sp=rep["source_provenance"]
    url="https://raw.githubusercontent.com/"+sp["repository"]+"/"+sp["commit"]+"/"+sp["path"]
    source=Path("/tmp/C119_"+cfg["asset"]+"_source.dds")
    urllib.request.urlretrieve(url,source)
    candidate=repo/rep["candidate_path"]
    if sha(source)!=rep["source_sha256"]: raise RuntimeError((cfg["asset"],"source sha",sha(source),rep["source_sha256"]))
    if sha(candidate)!=rep["candidate_sha256"]: raise RuntimeError((cfg["asset"],"candidate sha",sha(candidate),rep["candidate_sha256"]))

    sb,src,si=decode_dds(source); cb,cand,ci=decode_dds(candidate)
    if sb[:128]!=cb[:128]: raise RuntimeError((cfg["asset"],"header mismatch"))
    src_p=img(ap/cfg["source_png"]); clean=img(ap/cfg["clean_png"]); persisted=img(ap/cfg["final_png"])
    sm=mask(ap/cfg["source_mask"]); allowed=mask(ap/cfg["allowed_mask"]); protected=mask(ap/cfg["protected_mask"])
    if not (src.shape==cand.shape==src_p.shape==clean.shape==persisted.shape): raise RuntimeError((cfg["asset"],"shape mismatch"))
    source_png_diff=int(np.count_nonzero(np.any(src!=src_p,axis=2)))
    persisted_diff=int(np.count_nonzero(np.any(cand!=persisted,axis=2)))
    if source_png_diff or persisted_diff: raise RuntimeError((cfg["asset"],"persist mismatch",source_png_diff,persisted_diff))

    clean_changed=np.any(clean!=src,axis=2); final_changed=np.any(cand!=src,axis=2); target=np.any(cand!=clean,axis=2)
    clean_out=int(np.count_nonzero(clean_changed & ~sm))
    source_mask_unchanged=int(np.count_nonzero(sm & np.all(clean==src,axis=2)))
    final_out=int(np.count_nonzero(final_changed & ~allowed))
    alpha_out=int(np.count_nonzero((cand[:,:,3]!=src[:,:,3]) & ~allowed))
    protected_changed=int(np.count_nonzero(final_changed & protected))
    target_out=int(np.count_nonzero(target & ~allowed))

    prows=rep.get("rows")
    if prows is None:
        prows=[{"key":"not_available","original_bbox":rep["original_bbox"],"localized_bbox":rep["localized_bbox"]}]
    rows=[]; rmasks=[]
    for rr in prows:
        ob=list(map(int,rr["original_bbox"]))
        rm=target & rect(target.shape,ob)
        ab=bb(rm)
        if ab is None:
            contain=size=False
        else:
            contain=ab[0]>=ob[0] and ab[1]>=ob[1] and ab[2]<=ob[2] and ab[3]<=ob[3]
            size=(ab[2]-ab[0])<=(ob[2]-ob[0]) and (ab[3]-ab[1])<=(ob[3]-ob[1])
        producer_lb=list(map(int,rr["localized_bbox"]))
        rows.append({
          "key":rr.get("key","not_available"),"original_bbox":ob,"localized_bbox":ab,
          "producer_localized_bbox":producer_lb,"localized_bbox_matches_producer":bool(ab==producer_lb),
          "delta_left":None if ab is None else ab[0]-ob[0],"delta_right":None if ab is None else ob[2]-ab[2],
          "delta_top":None if ab is None else ab[1]-ob[1],"delta_bottom":None if ab is None else ob[3]-ab[3],
          "source_size":[ob[2]-ob[0],ob[3]-ob[1]],
          "localized_size":None if ab is None else [ab[2]-ab[0],ab[3]-ab[1]],
          "containment":"PASS" if contain else "FAIL","size_ceiling":"PASS" if size else "FAIL"
        })
        rmasks.append((rr.get("key","not_available"),rm))
    overlap=0; touch=[]
    for i in range(len(rmasks)):
        for j in range(i+1,len(rmasks)):
            ov=int(np.count_nonzero(rmasks[i][1]&rmasks[j][1]))
            near=int(np.count_nonzero(dil1(rmasks[i][1])&rmasks[j][1]))
            overlap+=ov
            if ov or near: touch.append([rmasks[i][0],rmasks[j][0],ov,near])

    ok=(source_png_diff==0 and persisted_diff==0 and clean_out==0 and source_mask_unchanged==0 and
        final_out==0 and alpha_out==0 and protected_changed==0 and target_out==0 and overlap==0 and not touch and
        all(x["containment"]=="PASS" and x["size_ceiling"]=="PASS" and x["localized_bbox_matches_producer"] for x in rows))
    res={
      "asset":cfg["asset"],"producer_run":cfg["producer_run"],"source_sha256":rep["source_sha256"],
      "candidate_sha256":rep["candidate_sha256"],"structure":ci,"header_128_exact":True,
      "source_png_vs_independent_decode_diff_pixels":source_png_diff,
      "persisted_final_vs_independent_decode_diff_pixels":persisted_diff,
      "clean_changed_pixels_outside_source_mask":clean_out,
      "source_mask_pixels_unchanged_in_clean":source_mask_unchanged,
      "final_changed_pixels_outside_allowed_mask":final_out,
      "alpha_changed_pixels_outside_allowed_mask":alpha_out,
      "final_changed_pixels_in_protected_mask":protected_changed,
      "target_pixels_outside_allowed_mask":target_out,
      "localized_pair_overlap_pixels":overlap,"localized_touch_pairs":touch,
      "rows":rows,"machine_status":"PASS" if ok else "FAIL",
      "controller_visual_qa":"PENDING","runtime_validation":"UNTESTED"
    }
    results.append(res)
    if not ok: raise RuntimeError((cfg["asset"],res))

report={"schema_version":1,"role":"C","run":run,"assets":results,
        "machine_status":"PASS" if all(x["machine_status"]=="PASS" for x in results) else "FAIL",
        "controller_visual_qa":"PENDING","runtime_validation":"UNTESTED"}
(out/"C119_NEW_A_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("C119_NEW_A_MACHINE_QA",report["machine_status"],[(x["asset"],x["candidate_sha256"]) for x in results],flush=True)
