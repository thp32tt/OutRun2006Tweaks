#!/usr/bin/env python3
import os,json,hashlib,struct,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

repo=Path.cwd()
run="20261005-C112-53CE"
out=repo/"localization/graphics/role_C"/run
out.mkdir(parents=True,exist_ok=True)
bp=repo/"localization/graphics/role_B/20261005-B-PRODUCTION28"
rep=json.loads((bp/"B_PRODUCTION28_53CE_REPORT.json").read_text(encoding="utf-8"))
source_url=rep["source_url"]
source_sha=rep["source_sha256"]
candidate=repo/rep["candidate_path"]
source_dds=Path("/tmp/C112_53CE_source.dds")
urllib.request.urlretrieve(source_url,source_dds)

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def decode(p):
    b=Path(p).read_bytes()
    if b[:4]!=b"DDS ": raise RuntimeError("not DDS")
    h=struct.unpack_from("<I",b,12)[0]; w=struct.unpack_from("<I",b,16)[0]
    pitch=struct.unpack_from("<I",b,20)[0]; mips=struct.unpack_from("<I",b,28)[0]
    fourcc=b[84:88]; bpp=struct.unpack_from("<I",b,88)[0]; masks=struct.unpack_from("<IIII",b,92)
    if not (w==2048 and h==2048 and pitch==w*4 and mips==1 and fourcc==b"\0\0\0\0" and bpp==32 and masks==(0xff,0xff00,0xff0000,0xff000000)):
        raise RuntimeError(("unexpected DDS",w,h,pitch,mips,fourcc,bpp,masks))
    raw=Image.frombytes("RGBA",(w,h),b[128:],"raw","RGBA")
    im=raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    return b,np.asarray(im),{"width":w,"height":h,"pitch":pitch,"mips":mips,"format":"RGBA32","raw_orientation":"mirror_y"}
def loadmask(p): return np.asarray(Image.open(p).convert("L"))>0
def bbox(m):
    yy,xx=np.nonzero(m)
    return None if not len(xx) else [int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)]
def rect(shape,b):
    h,w=shape; x0,y0,x1,y1=map(int,b); m=np.zeros((h,w),bool); m[y0:y1,x0:x1]=True; return m
def dil1(m):
    return np.asarray(Image.fromarray((m.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(3)))>0

sb,src,si=decode(source_dds); cb,cand,ci=decode(candidate)
if sha(source_dds)!=source_sha: raise RuntimeError("source sha mismatch")
if sha(candidate)!=rep["candidate_sha256"]: raise RuntimeError("candidate sha mismatch")
clean=np.asarray(Image.open(bp/"53CE39D5_HD_CLEAN_PLATE.png").convert("RGBA"))
source_mask=loadmask(bp/"53CE39D5_HD_SOURCE_TEXT_MASK.png")
allowed=loadmask(bp/"53CE39D5_HD_ALLOWED_TEXT_REGION_MASK.png")
protected=loadmask(bp/"53CE39D5_HD_PROTECTED_MASK.png")
persisted_target=loadmask(bp/"53CE39D5_HD_TARGET_TEXT_MASK.png")
if clean.shape!=src.shape or cand.shape!=src.shape: raise RuntimeError("shape mismatch")

clean_diff=np.any(clean!=src,axis=2)
final_diff=np.any(cand!=src,axis=2)
target=np.any(cand!=clean,axis=2)

# Independent structural/mask gates.
header_exact=bool(sb[:128]==cb[:128])
clean_outside=int(np.count_nonzero(clean_diff & ~source_mask))
source_mask_unchanged=int(np.count_nonzero(source_mask & np.all(clean==src,axis=2)))
final_outside=int(np.count_nonzero(final_diff & ~allowed))
final_protected=int(np.count_nonzero(final_diff & protected))
target_xor=int(np.count_nonzero(target ^ persisted_target))
target_outside=int(np.count_nonzero(target & ~allowed))

rows=[]; row_masks=[]
for i,r in enumerate(rep["rows"],1):
    ob=list(map(int,r["original_bbox"]))
    rm=target & rect(target.shape,ob)
    lb=bbox(rm)
    sw,sh=ob[2]-ob[0],ob[3]-ob[1]
    if lb is None:
        rows.append({"n":i,"target":r["target"],"line_index":r["line_index"],"original_bbox":ob,"localized_bbox":None,"containment":"FAIL","size_ceiling":"FAIL"})
        row_masks.append((f'{r["target"]}/{r["line_index"]}',rm))
        continue
    lw,lh=lb[2]-lb[0],lb[3]-lb[1]
    contain=lb[0]>=ob[0] and lb[1]>=ob[1] and lb[2]<=ob[2] and lb[3]<=ob[3]
    size=lw<=sw and lh<=sh
    rows.append({"n":i,"target":r["target"],"line_index":r["line_index"],"original_bbox":ob,"localized_bbox":lb,
      "delta_left":lb[0]-ob[0],"delta_right":ob[2]-lb[2],"delta_top":lb[1]-ob[1],"delta_bottom":ob[3]-lb[3],
      "source_size":[sw,sh],"localized_size":[lw,lh],"containment":"PASS" if contain else "FAIL","size_ceiling":"PASS" if size else "FAIL"})
    row_masks.append((f'{r["target"]}/{r["line_index"]}',rm))

pair_overlap=0; touch=[]
for i in range(len(row_masks)):
    for j in range(i+1,len(row_masks)):
        ov=int(np.count_nonzero(row_masks[i][1] & row_masks[j][1]))
        near=int(np.count_nonzero(dil1(row_masks[i][1]) & row_masks[j][1]))
        pair_overlap+=ov
        if ov or near: touch.append([row_masks[i][0],row_masks[j][0],ov,near])

# Independent clean-plate residue scan for the 18 orange text lines.
# Each orange source line sits on a smooth light-blue plate. Estimate the plate colour
# from the semantic cell after excluding all producer-declared text bboxes, then inspect
# a modestly expanded neighborhood around each source bbox. Any source-effect-looking
# pixel left byte-identical in CLEAN is a residue candidate, even if the producer mask missed it.
by_target={}
for r in rep["rows"]: by_target.setdefault(r["target"],[]).append(r)
independent_residue={}
residue_union=np.zeros(target.shape,bool)
for r in rep["rows"]:
    if r["style_kind"]!="orange": continue
    cell=list(map(int,r["cell"])); x0,y0,x1,y1=cell
    group=by_target[r["target"]]
    exclude=np.zeros(target.shape,bool)
    for g in group:
        gx0,gy0,gx1,gy1=map(int,g["original_bbox"])
        gx0=max(x0,gx0-18); gy0=max(y0,gy0-10); gx1=min(x1,gx1+18); gy1=min(y1,gy1+10)
        exclude[gy0:gy1,gx0:gx1]=True
    cellmask=np.zeros(target.shape,bool); cellmask[y0:y1,x0:x1]=True
    sample=src[cellmask & ~exclude & (src[:,:,3]>0)]
    if len(sample)<100: raise RuntimeError(("insufficient independent plate samples",r["target"],r["line_index"],len(sample)))
    q=(sample[:,:3]//8).astype(np.uint8)
    uq,cnt=np.unique(q,axis=0,return_counts=True)
    mode=uq[int(np.argmax(cnt))]
    near_mode=np.all(np.abs(q.astype(np.int16)-mode.astype(np.int16))<=1,axis=1)
    plate=np.median(sample[near_mode],axis=0) if np.any(near_mode) else np.median(sample,axis=0)
    ob=list(map(int,r["original_bbox"]))
    ex0=max(x0+4,ob[0]-10); ey0=max(y0+2,ob[1]-8); ex1=min(x1-4,ob[2]+10); ey1=min(y1-2,ob[3]+8)
    region=np.zeros(target.shape,bool); region[ey0:ey1,ex0:ex1]=True
    dist=np.max(np.abs(src.astype(np.int16)-plate.astype(np.int16)),axis=2)
    rr=src[:,:,0].astype(np.int16); gg=src[:,:,1].astype(np.int16); bb=src[:,:,2].astype(np.int16); aa=src[:,:,3]
    lum=.2126*rr+.7152*gg+.0722*bb
    orange=(rr>145)&(gg>45)&(gg<225)&(bb<145)&(rr>gg+15)&(gg>bb+10)&(aa>0)
    shadow=(lum<175)&(aa>0)
    effect_like=region & ((dist>7) | orange | shadow)
    unchanged=effect_like & np.all(clean==src,axis=2)
    n=int(np.count_nonzero(unchanged))
    independent_residue[f'{r["target"]}/{r["line_index"]}']={
      "plate_rgba":[int(x) for x in np.round(plate)],
      "expanded_scan_bbox":[ex0,ey0,ex1,ey1],
      "source_effect_like_pixels":int(np.count_nonzero(effect_like)),
      "unchanged_source_effect_like_pixels_in_clean":n,
      "unchanged_bbox":bbox(unchanged)
    }
    residue_union |= unchanged

# Evidence overlay makes C controller review reproducible.
base=Image.fromarray(clean.copy(),"RGBA").convert("RGB")
draw=ImageDraw.Draw(base)
yy,xx=np.nonzero(residue_union)
for x,y in zip(xx,yy):
    draw.rectangle((int(x)-2,int(y)-2,int(x)+2,int(y)+2),outline=(255,0,0),width=1)
base.resize((1024,1024),Image.Resampling.NEAREST).save(out/"C112_53CE_INDEPENDENT_RESIDUE_OVERLAY.png")

independent_residue_pixels=int(np.count_nonzero(residue_union))
machine_ok=(header_exact and clean_outside==0 and source_mask_unchanged==0 and final_outside==0 and final_protected==0 and
            target_xor==0 and target_outside==0 and pair_overlap==0 and not touch and
            all(x["containment"]=="PASS" and x["size_ceiling"]=="PASS" for x in rows) and independent_residue_pixels==0)
res={
 "schema_version":1,"role":"C","run":run,"asset":"53CE39D5","producer_run":"B_PRODUCTION28",
 "source_sha256":source_sha,"candidate_sha256":rep["candidate_sha256"],
 "structure":ci,"header_128_exact":header_exact,
 "clean_changed_pixels_outside_producer_source_mask":clean_outside,
 "producer_source_mask_pixels_unchanged_in_clean":source_mask_unchanged,
 "final_changed_pixels_outside_allowed":final_outside,
 "final_changed_pixels_in_protected":final_protected,
 "target_mask_xor_vs_persisted_target_mask":target_xor,
 "target_pixels_outside_allowed":target_outside,
 "localized_pair_overlap_pixels":pair_overlap,"localized_touch_pairs":touch,
 "rows":rows,
 "independent_orange_clean_plate_residue_scan":independent_residue,
 "independent_residue_pixels":independent_residue_pixels,
 "independent_residue_bbox":bbox(residue_union),
 "machine_status":"PASS" if machine_ok else "FAIL",
 "controller_visual_qa":"PENDING",
 "runtime_validation":"UNTESTED"
}
(out/"C112_53CE_MACHINE_QA.json").write_text(json.dumps(res,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("C112_53CE",res["machine_status"],"independent_residue_pixels",independent_residue_pixels,rep["candidate_sha256"],flush=True)
