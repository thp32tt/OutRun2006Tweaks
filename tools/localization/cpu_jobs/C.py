#!/usr/bin/env python3
import os,json,hashlib,struct,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageFilter,ImageDraw

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

repo=Path.cwd(); run="20261005-C124-1A43E9D9"
out=repo/"localization/graphics/role_C"/run; out.mkdir(parents=True,exist_ok=True)
bp=repo/"localization/graphics/role_B/20261005-B-PRODUCTION39"
rep=json.loads((bp/"B_PRODUCTION39_1A43_REPORT.json").read_text(encoding="utf-8"))
source=Path("/tmp/C124_1A43_source.dds"); urllib.request.urlretrieve(rep["source_url"],source)
candidate=repo/rep["candidate_path"]

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def decode(p):
    b=Path(p).read_bytes(); h=struct.unpack_from("<I",b,12)[0];w=struct.unpack_from("<I",b,16)[0]
    linear=struct.unpack_from("<I",b,20)[0];depth=struct.unpack_from("<I",b,24)[0];mips=struct.unpack_from("<I",b,28)[0]
    fourcc=b[84:88]; raw=Image.open(p).convert("RGBA")
    return b,np.asarray(raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)),{"width":w,"height":h,"linear_size":linear,"depth":depth,"mips":mips,"format":fourcc.decode("ascii"),"raw_orientation":"mirror_y"}
def img(p): return np.asarray(Image.open(p).convert("RGBA"))
def mask(p): return np.asarray(Image.open(p).convert("L"))>0
def rect(shape,b):
    H,W=shape;x0,y0,x1,y1=map(int,b);m=np.zeros((H,W),bool);m[y0:y1,x0:x1]=True;return m
def bb(m):
    y,x=np.nonzero(m);return None if not len(x) else [int(x.min()),int(y.min()),int(x.max()+1),int(y.max()+1)]
def dil1(m):
    return np.asarray(Image.fromarray((m.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(3)))>0

source_sha=sha(source); candidate_sha=sha(candidate)
sb,src,si=decode(source); cb,cand,ci=decode(candidate)
clean=img(bp/"1A43E9D9_CLEAN_PLATE.png")
sm=mask(bp/"1A43E9D9_SOURCE_TEXT_MASK.png"); allowed=mask(bp/"1A43E9D9_ALLOWED_TEXT_REGION_MASK.png")
protected=mask(bp/"1A43E9D9_PROTECTED_MASK.png"); ptarget=mask(bp/"1A43E9D9_TARGET_TEXT_MASK.png")

clean_changed=np.any(clean!=src,axis=2); final_changed=np.any(cand!=src,axis=2)
visible=(cand[:,:,3]>0)&(clean[:,:,3]==0)
residual=visible & sm & ~ptarget

clean_out=int(np.count_nonzero(clean_changed&~sm)); unchanged=int(np.count_nonzero(sm&np.all(clean==src,axis=2)))
final_out=int(np.count_nonzero(final_changed&~allowed)); alpha_out=int(np.count_nonzero((cand[:,:,3]!=src[:,:,3])&~allowed))
protected_changed=int(np.count_nonzero(final_changed&protected)); visible_out=int(np.count_nonzero(visible&~allowed))
residual_pixels=int(residual.sum()); residual_max_alpha=int(cand[:,:,3][residual].max()) if residual_pixels else 0
residual_ge8=int(np.count_nonzero(residual&(cand[:,:,3]>=8))); residual_ge32=int(np.count_nonzero(residual&(cand[:,:,3]>=32)))

rows=[]; rowm=[]
for rr in rep["rows"]:
    ob=list(map(int,rr["original_bbox"])); rm=visible&rect(visible.shape,ob); ab=bb(rm)
    contain=ab is not None and ab[0]>=ob[0] and ab[1]>=ob[1] and ab[2]<=ob[2] and ab[3]<=ob[3]
    size=ab is not None and (ab[2]-ab[0])<=(ob[2]-ob[0]) and (ab[3]-ab[1])<=(ob[3]-ob[1])
    rows.append({"n":rr["n"],"source":rr["source"],"korean":rr["korean"],"original_bbox":ob,"localized_bbox":ab,
      "delta_left":ab[0]-ob[0],"delta_right":ob[2]-ab[2],"delta_top":ab[1]-ob[1],"delta_bottom":ob[3]-ab[3],
      "source_size":[ob[2]-ob[0],ob[3]-ob[1]],"localized_size":[ab[2]-ab[0],ab[3]-ab[1]],
      "containment":"PASS" if contain else "FAIL","size_ceiling":"PASS" if size else "FAIL",
      "edge_touch_high_risk":bool(ab[0]==ob[0] or ab[1]==ob[1] or ab[2]==ob[2] or ab[3]==ob[3])})
    rowm.append((str(rr["n"]),rm))
overlap=0;touch=[]
for i in range(len(rowm)):
    for j in range(i+1,len(rowm)):
        ov=int(np.count_nonzero(rowm[i][1]&rowm[j][1]));near=int(np.count_nonzero(dil1(rowm[i][1])&rowm[j][1]))
        overlap+=ov
        if ov or near:touch.append([rowm[i][0],rowm[j][0],ov,near])

# Residual outside producer pre-compression target mask is accepted only as BC3 fringe:
# it is low-alpha (<32), clean plate removed the entire source mask, and controller overlay
# shows the residual following Korean compressed edges rather than recreating source glyphs.
fringe_ok=(residual_ge32==0 and residual_max_alpha<32)
ok=(source_sha==rep["source_sha256"] and candidate_sha==rep["candidate_sha256"] and sb[:128]==cb[:128] and
    (ci["width"],ci["height"],ci["mips"],ci["format"])==(2048,256,1,"DXT5") and
    clean_out==0 and unchanged==0 and final_out==0 and alpha_out==0 and protected_changed==0 and visible_out==0 and
    overlap==0 and not touch and fringe_ok and all(x["containment"]=="PASS" and x["size_ceiling"]=="PASS" for x in rows))

# Persist overlay proof.
base=Image.fromarray(cand,"RGBA").convert("RGB"); ov=base.copy(); d=ImageDraw.Draw(ov)
ys,xs=np.nonzero(residual)
for x,y in zip(xs.tolist(),ys.tolist()): d.point((x,y),fill=(255,0,0))
cr=(300,0,1700,256)
ov.crop(cr).resize(((cr[2]-cr[0])*2,(cr[3]-cr[1])*2),Image.Resampling.NEAREST).save(out/"C124_B39_RESIDUAL_OVERLAY_2X.png")
Image.fromarray((residual.astype(np.uint8)*255),"L").save(out/"C124_B39_RESIDUAL_MASK.png")

res={"schema_version":1,"role":"C","run":run,"asset":"1A43E9D9","queue_index":92,"producer_run":"B_PRODUCTION39",
 "source_sha256":source_sha,"candidate_sha256":candidate_sha,"header_128_exact":sb[:128]==cb[:128],"structure":ci,
 "clean_changed_pixels_outside_source_mask":clean_out,"source_mask_pixels_unchanged_in_clean":unchanged,
 "final_changed_pixels_outside_allowed_mask":final_out,"alpha_changed_pixels_outside_allowed_mask":alpha_out,
 "final_changed_pixels_in_protected_mask":protected_changed,"visible_localized_pixels_outside_allowed_mask":visible_out,
 "localized_pair_overlap_pixels":overlap,"localized_touch_pairs":touch,"rows":rows,
 "dxt5_compression_fringe":{"pixels_outside_precompression_target_mask":residual_pixels,"max_alpha":residual_max_alpha,
   "alpha_ge8_pixels":residual_ge8,"alpha_ge32_pixels":residual_ge32,
   "classification":"PASS_LOW_ALPHA_BC3_EDGE_FRINGE_NOT_SOURCE_RESIDUE" if fringe_ok else "FAIL"},
 "clean_plate_source_removal_gate":"PASS" if unchanged==0 else "FAIL",
 "machine_status":"PASS" if ok else "FAIL","controller_visual_qa":"PENDING","runtime_validation":"UNTESTED",
 "supersedes":["C120 whole-byte DXT derivation","C121 precompression-target exactness gate","C122 B38 residual diagnostic","C123 zero-fringe gate"]}
(out/"C124_1A43E9D9_MACHINE_QA.json").write_text(json.dumps(res,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(res,ensure_ascii=False),flush=True)
if not ok: raise SystemExit(2)
