#!/usr/bin/env python3
import hashlib,json,os,struct,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

repo=Path.cwd()
run="20261005-C163-2EA557B4"
out=repo/"localization/graphics/role_C"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)

asset="textures/load/spr_sprani_game_cvt_Exst/2EA557B4_512x64.dds"
cand=repo/"localization/graphics/hd_candidates"/asset
COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
SOURCE_BLOB_SHA1="bbf53949c7d9f1dc4949e661caeeaf19fe667d79"
SOURCE_SHA256="b2d5b03a8e6cc56fcb60c31f32a485854dd7ea41ed10c7b10ba185625d07a685"
CANDIDATE_SHA256="d66a110cfc5bd09201c6f1a806fd3b2fab84663294ff865415fc7fc6532d6beb"

tmp=Path("/tmp/outrun_C163"); tmp.mkdir(parents=True,exist_ok=True)
sp=tmp/"source.dds"
base="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+COMMIT
urllib.request.urlretrieve(base+"/Release/spr_sprani_game_cvt_Exst/2EA557B4_512x64.dds",sp)

def gitblob(b): return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def sha(b): return hashlib.sha256(b).hexdigest()
def bbox(m):
    yy,xx=np.nonzero(m)
    return None if not len(xx) else [int(xx.min()),int(yy.min()),int(xx.max())+1,int(yy.max())+1]
def count(m): return int(np.count_nonzero(m))
def comp(im,bg=(96,96,96,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")

sb=sp.read_bytes(); cb=cand.read_bytes()
if gitblob(sb)!=SOURCE_BLOB_SHA1 or sha(sb)!=SOURCE_SHA256 or sha(cb)!=CANDIDATE_SHA256:
    raise RuntimeError(("provenance/hash drift",gitblob(sb),sha(sb),sha(cb)))
if sb[:128]!=cb[:128] or len(sb)!=len(cb): raise RuntimeError("DDS header/length drift")
H,W=struct.unpack_from("<II",sb,12); mips=struct.unpack_from("<I",sb,28)[0]; fourcc=sb[84:88]
need=128+((W+3)//4)*((H+3)//4)*16
if (W,H)!=(2048,256) or fourcc!=b"DXT5" or mips not in (0,1) or len(sb)!=need:
    raise RuntimeError(("structure",W,H,mips,fourcc,len(sb),need))

raw_src=Image.open(sp).convert("RGBA")
raw_fin=Image.open(cand).convert("RGBA")
src=raw_src.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
fin=raw_fin.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
sa=np.asarray(src,dtype=np.uint8); fa=np.asarray(fin,dtype=np.uint8)

source_mask=sa[:,:,3]>1
ob=bbox(source_mask)
EXPECTED=[1,105,1090,248]
if ob!=EXPECTED: raise RuntimeError(("source bbox drift",ob,EXPECTED))
allowed=np.zeros((H,W),bool); allowed[ob[1]:ob[3],ob[0]:ob[2]]=True

diff=np.any(sa!=fa,axis=2); alpha_diff=sa[:,:,3]!=fa[:,:,3]
outside=count(diff & ~allowed)
alpha_out=count(alpha_diff & ~allowed)
introduced_visible_out=count((fa[:,:,3]>1)&(sa[:,:,3]<=1)&~allowed)
protected_changed=outside
if outside or alpha_out or introduced_visible_out:
    raise RuntimeError(("outside/protected drift",outside,alpha_out,introduced_visible_out))

target=fa[:,:,3]>1
lb=bbox(target)
if not lb: raise RuntimeError("localized alpha empty")
sw,sh=ob[2]-ob[0],ob[3]-ob[1]; lw,lh=lb[2]-lb[0],lb[3]-lb[1]
d=[lb[0]-ob[0],ob[2]-lb[2],lb[1]-ob[1],ob[3]-lb[3]]
if lw>sw or lh>sh or min(d)<=0:
    raise RuntimeError(("bbox/size/margin",ob,lb,d))
if lb != [263,113,828,240]:
    raise RuntimeError(("localized bbox drift",lb))

# Exact boundary-block audit: partial 4x4 blocks crossing the source bbox may
# alter alpha indices only; alpha endpoints and BC3 color bytes must remain source-exact.
bw=(W+3)//4; bh=(H+3)//4
allowed_raw=np.flipud(allowed)
changed_blocks=0; changed_wholly_outside=0; partial_changed=0; partial_endpoint_or_color_drift=0
for by in range(bh):
    for bx in range(bw):
        off=128+(by*bw+bx)*16
        sblk=sb[off:off+16]; cblk=cb[off:off+16]
        if sblk==cblk: continue
        changed_blocks+=1
        am=allowed_raw[by*4:min(H,by*4+4),bx*4:min(W,bx*4+4)]
        if not np.any(am):
            changed_wholly_outside+=1
            continue
        if not np.all(am):
            partial_changed+=1
            if sblk[:2]!=cblk[:2] or sblk[8:16]!=cblk[8:16]:
                partial_endpoint_or_color_drift+=1
if changed_wholly_outside or partial_endpoint_or_color_drift:
    raise RuntimeError(("BC3 boundary drift",changed_wholly_outside,partial_endpoint_or_color_drift))

# Source-script residue screen outside a generous Korean target guard:
# source-visible pixels that remain byte-near source are counted.
from PIL import ImageFilter
guard=np.asarray(Image.fromarray((target.astype(np.uint8)*255),"L").filter(ImageFilter.MaxFilter(9)))>0
same_rgb=np.max(np.abs(sa[:,:,:3].astype(np.int16)-fa[:,:,:3].astype(np.int16)),axis=2)<=4
source_residue=count(source_mask & ~guard & (fa[:,:,3]>8) & same_rgb)
if source_residue: raise RuntimeError(("source residue",source_residue))

Image.fromarray((source_mask.astype(np.uint8)*255),"L").save(out/"C163_SOURCE_TEXT_MASK.png")
Image.fromarray((allowed.astype(np.uint8)*255),"L").save(out/"C163_ALLOWED_BBOX_MASK.png")
Image.fromarray((target.astype(np.uint8)*255),"L").save(out/"C163_TARGET_TEXT_MASK.png")

stack=Image.new("RGB",(1024,2*170),"white")
for i,(label,im) in enumerate([("SOURCE",src),("FINAL",fin)]):
    z=comp(im).resize((1024,128),Image.Resampling.NEAREST)
    stack.paste(z,(0,i*170+28)); ImageDraw.Draw(stack).text((5,i*170+5),label,fill="black")
stack.save(out/"C163_2EA_SOURCE_FINAL.jpg",quality=96)

detail=Image.new("RGB",(2048,2*190),"white")
for i,(label,im) in enumerate([("SOURCE",src),("FINAL",fin)]):
    crop=comp(im).crop((0,95,1120,256))
    scale=1.7; z=crop.resize((int(crop.width*scale),int(crop.height*scale)),Image.Resampling.NEAREST)
    detail.paste(z,(0,i*190+20)); ImageDraw.Draw(detail).text((5,i*190+3),label,fill="black")
detail.save(out/"C163_2EA_DETAIL.jpg",quality=96)

rr=Image.new("RGB",(1024,2*170),"white")
for i,(label,im) in enumerate([("SOURCE_RAW_MIRROR_Y",raw_src),("FINAL_RAW_MIRROR_Y",raw_fin)]):
    z=comp(im).resize((1024,128),Image.Resampling.NEAREST)
    rr.paste(z,(0,i*170+28)); ImageDraw.Draw(rr).text((5,i*170+5),label,fill="black")
rr.save(out/"C163_2EA_RAW_COMPARE.jpg",quality=96)

report={
 "schema_version":1,"role":"C","run":run,"queue_index":55,"asset":asset,
 "producer_run":"20261005-A-PRODUCTION17 / A26 reconciliation",
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":COMMIT,"git_blob_sha1":SOURCE_BLOB_SHA1,"source_sha256":SOURCE_SHA256},
 "candidate_sha256":CANDIDATE_SHA256,"candidate_changed_by_C":False,
 "independent_method":"C re-downloaded pinned canonical DXT5 source, decoded canonical/current reconciled candidate independently, re-derived source alpha bbox directly from canonical decoded pixels, recomputed decoded outside/alpha/introduced-visible protection and localized bbox/size/margins, audited every changed BC3 boundary block for source-exact alpha endpoints+color bytes, and generated independent source/final readable+raw evidence without producer masks.",
 "structure":{"dimensions":[W,H],"format":"DXT5","mipmaps":mips,"header_128_exact":True,"raw_orientation":"mirror_y"},
 "semantic_binding":{"source":"NEXT ROUND","korean":"다음 라운드"},
 "original_bbox":ob,"localized_bbox":lb,"source_size":[sw,sh],"localized_size":[lw,lh],
 "delta_left":d[0],"delta_right":d[1],"delta_top":d[2],"delta_bottom":d[3],
 "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS",
 "machine_checks":{"decoded_changed_outside":outside,"alpha_outside":alpha_out,"introduced_visible_outside":introduced_visible_out,
   "protected_changed":protected_changed,"source_residue":source_residue,
   "changed_bc3_blocks":changed_blocks,"changed_bc3_blocks_wholly_outside_allowed":changed_wholly_outside,
   "partial_boundary_changed_blocks":partial_changed,"partial_endpoint_or_color_drift":partial_endpoint_or_color_drift},
 "machine_status":"PASS","controller_visual_qa":"PENDING","decision":"PENDING_CONTROLLER_VISUAL_QA","RUNTIME_VALIDATION":"UNTESTED"
}
(out/"C163_2EA_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
summary={"run":run,"asset":"2EA557B4","index":55,"source_sha256":SOURCE_SHA256,"candidate_sha256":CANDIDATE_SHA256,
 "machine_status":"PASS","bbox_size_positive_margin":"1/1","decoded_changed_outside":outside,"alpha_outside":alpha_out,
 "introduced_visible_outside":introduced_visible_out,"protected_changed":protected_changed,"source_residue":source_residue,
 "changed_bc3_blocks":changed_blocks,"changed_bc3_blocks_wholly_outside_allowed":changed_wholly_outside,
 "partial_boundary_changed_blocks":partial_changed,"partial_endpoint_or_color_drift":partial_endpoint_or_color_drift,
 "runtime_validation":"UNTESTED","report":f"localization/graphics/role_C/{run}/C163_2EA_MACHINE_QA.json"}
(wr/"C163_2EA557B4.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n")
print(json.dumps(summary,ensure_ascii=False),flush=True)
