#!/usr/bin/env python3
import os,json,hashlib,struct,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

repo=Path.cwd()
run="20261005-C121-1A43E9D9"
out=repo/"localization/graphics/role_C"/run
out.mkdir(parents=True,exist_ok=True)
bp=repo/"localization/graphics/role_B/20261005-B-PRODUCTION38"
rep=json.loads((bp/"B_PRODUCTION38_1A43_REPORT.json").read_text(encoding="utf-8"))
source=Path("/tmp/C121_1A43E9D9_source.dds")
urllib.request.urlretrieve(rep["source_url"],source)
candidate=repo/rep["candidate_path"]

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def decode(p):
    b=Path(p).read_bytes()
    if b[:4]!=b"DDS ": raise RuntimeError(("not DDS",str(p)))
    h=struct.unpack_from("<I",b,12)[0];w=struct.unpack_from("<I",b,16)[0]
    linear=struct.unpack_from("<I",b,20)[0];depth=struct.unpack_from("<I",b,24)[0];mips=struct.unpack_from("<I",b,28)[0]
    fourcc=b[84:88]
    raw=Image.open(p).convert("RGBA")
    readable=raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    return b,np.asarray(readable),{"width":w,"height":h,"linear_size":linear,"depth":depth,"mips":mips,"format":fourcc.decode("ascii"),"raw_orientation":"mirror_y"}

def img(p): return np.asarray(Image.open(p).convert("RGBA"))
def mask(p): return np.asarray(Image.open(p).convert("L"))>0
def rect(shape,b):
    H,W=shape;x0,y0,x1,y1=map(int,b);m=np.zeros((H,W),bool);m[y0:y1,x0:x1]=True;return m
def bb(m):
    y,x=np.nonzero(m);return None if not len(x) else [int(x.min()),int(y.min()),int(x.max()+1),int(y.max()+1)]
def dil1(m):
    return np.asarray(Image.fromarray((m.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(3)))>0

source_sha=sha(source);candidate_sha=sha(candidate)
sb,src,si=decode(source);cb,cand,ci=decode(candidate)
clean=img(bp/"1A43E9D9_CLEAN_PLATE.png")
sm=mask(bp/"1A43E9D9_SOURCE_TEXT_MASK.png")
allowed=mask(bp/"1A43E9D9_ALLOWED_TEXT_REGION_MASK.png")
protected=mask(bp/"1A43E9D9_PROTECTED_MASK.png")
ptarget=mask(bp/"1A43E9D9_TARGET_TEXT_MASK.png")

source_sha_ok=source_sha==rep["source_sha256"];candidate_sha_ok=candidate_sha==rep["candidate_sha256"]
header_exact=sb[:128]==cb[:128]
structure_ok=(ci["width"],ci["height"],ci["mips"],ci["format"])==(2048,256,1,"DXT5")
shape_ok=(src.shape==cand.shape==clean.shape)

clean_changed=np.any(clean!=src,axis=2)
final_changed=np.any(cand!=src,axis=2)
clean_out=int(np.count_nonzero(clean_changed & ~sm))
source_mask_unchanged=int(np.count_nonzero(sm & np.all(clean==src,axis=2)))
final_out=int(np.count_nonzero(final_changed & ~allowed))
alpha_out=int(np.count_nonzero((cand[:,:,3]!=src[:,:,3]) & ~allowed))
protected_changed=int(np.count_nonzero(final_changed & protected))

# For BC3/DXT5, candidate-vs-clean RGB bytes are not a valid lettering mask because
# recompression changes transparent RGB throughout patched blocks. The independently
# decoded *visible alpha* over the transparent clean plate is the localized glyph/effect mask.
visible_target=(cand[:,:,3]>0) & (clean[:,:,3]==0)
visible_target_out=int(np.count_nonzero(visible_target & ~allowed))
persist_missing=int(np.count_nonzero(visible_target & ~ptarget))
persist_extra=int(np.count_nonzero(ptarget & ~visible_target))

rows=[];rowm=[]
for rr in rep["rows"]:
    ob=list(map(int,rr["original_bbox"]))
    rm=visible_target & rect(visible_target.shape,ob)
    ab=bb(rm)
    contain=ab is not None and ab[0]>=ob[0] and ab[1]>=ob[1] and ab[2]<=ob[2] and ab[3]<=ob[3]
    size=ab is not None and (ab[2]-ab[0])<=(ob[2]-ob[0]) and (ab[3]-ab[1])<=(ob[3]-ob[1])
    expected=list(map(int,rr["decoded_localized_bbox"]))
    rows.append({
      "n":rr["n"],"source":rr["source"],"korean":rr["korean"],
      "original_bbox":ob,"localized_bbox":ab,"producer_decoded_localized_bbox":expected,
      "localized_bbox_matches_producer":bool(ab==expected),
      "delta_left":None if ab is None else ab[0]-ob[0],"delta_right":None if ab is None else ob[2]-ab[2],
      "delta_top":None if ab is None else ab[1]-ob[1],"delta_bottom":None if ab is None else ob[3]-ab[3],
      "source_size":[ob[2]-ob[0],ob[3]-ob[1]],"localized_size":None if ab is None else [ab[2]-ab[0],ab[3]-ab[1]],
      "containment":"PASS" if contain else "FAIL","size_ceiling":"PASS" if size else "FAIL"
    })
    rowm.append((str(rr["n"]),rm))
overlap=0;touch=[]
for i in range(len(rowm)):
    for j in range(i+1,len(rowm)):
        ov=int(np.count_nonzero(rowm[i][1]&rowm[j][1]))
        near=int(np.count_nonzero(dil1(rowm[i][1])&rowm[j][1]))
        overlap+=ov
        if ov or near:touch.append([rowm[i][0],rowm[j][0],ov,near])

ok=(source_sha_ok and candidate_sha_ok and header_exact and structure_ok and shape_ok and
    clean_out==0 and source_mask_unchanged==0 and final_out==0 and alpha_out==0 and protected_changed==0 and
    visible_target_out==0 and overlap==0 and not touch and
    all(x["containment"]=="PASS" and x["size_ceiling"]=="PASS" and x["localized_bbox_matches_producer"] for x in rows))
res={
 "schema_version":1,"role":"C","run":run,"asset":"1A43E9D9","queue_index":92,"producer_run":"B_PRODUCTION38",
 "source_sha256":source_sha,"source_sha_matches_producer":source_sha_ok,
 "candidate_sha256":candidate_sha,"candidate_sha_matches_producer":candidate_sha_ok,
 "structure":ci,"header_128_exact":header_exact,
 "clean_changed_pixels_outside_source_mask":clean_out,
 "source_mask_pixels_unchanged_in_clean":source_mask_unchanged,
 "final_changed_pixels_outside_allowed_mask":final_out,
 "alpha_changed_pixels_outside_allowed_mask":alpha_out,
 "final_changed_pixels_in_protected_mask":protected_changed,
 "visible_localized_pixels_outside_allowed_mask":visible_target_out,
 "visible_target_pixels_missing_from_persisted_target_mask":persist_missing,
 "persisted_target_mask_only_pixels":persist_extra,
 "target_mask_note":"Visible alpha over transparent CLEAN is authoritative for decoded DXT5 glyph bbox; whole-byte candidate-vs-clean differences are invalid because BC3 recompression changes transparent RGB.",
 "localized_pair_overlap_pixels":overlap,"localized_touch_pairs":touch,
 "rows":rows,"machine_status":"PASS" if ok else "FAIL","controller_visual_qa":"PENDING","runtime_validation":"UNTESTED",
 "supersedes":"20261005-C120-1A43E9D9 whole-byte target derivation"
}
(out/"C121_1A43E9D9_MACHINE_QA.json").write_text(json.dumps(res,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(res,ensure_ascii=False),flush=True)
