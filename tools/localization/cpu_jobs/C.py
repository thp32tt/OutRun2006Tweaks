#!/usr/bin/env python3
import os,json,hashlib,urllib.request
from pathlib import Path
import numpy as np
from PIL import Image,ImageChops,ImageDraw

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

repo=Path.cwd(); run="20261005-C209-B7E25BAD"
out=repo/"localization/graphics/role_C"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
pr=json.loads((repo/"localization/graphics/role_B/20261005-B-PRODUCTION154-HOLL/B154_HOLL_REPORT.json").read_text(encoding="utf-8"))
cand=repo/pr["candidate_path"]; asset=pr["asset"]
COMMIT=pr["source_provenance"]["commit"]; SOURCE_SHA=pr["source_provenance"]["source_sha256"]
tmp=Path("/tmp/c209"); tmp.mkdir(exist_ok=True); srcdds=tmp/"source.dds"
base=f"https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/{COMMIT}"
urllib.request.urlretrieve(base+"/Release/spr_sprani_HOLL_RANK_Exst/B7E25BAD_1024x512.dds",srcdds)

def sha(b): return hashlib.sha256(b).hexdigest()
def bmask(im): return im.point(lambda v:255 if v else 0)
def diffmask(a,b):
    d=ImageChops.difference(a,b); zs=d.split(); m=zs[0]
    for z in zs[1:]: m=ImageChops.lighter(m,z)
    return bmask(m)
def count(im): return sum(im.histogram()[1:])
def bbox(mask):
    yy,xx=np.nonzero(mask)
    return None if len(xx)==0 else [int(xx.min()),int(yy.min()),int(xx.max())+1,int(yy.max())+1]
def comp(im,bg=(62,62,62,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")

sb=srcdds.read_bytes(); cb=cand.read_bytes()
if sha(sb)!=SOURCE_SHA or sha(cb)!=pr["candidate_sha256"] or sb[:128]!=cb[:128]:
    raise RuntimeError(("identity/header",sha(sb),sha(cb),sb[:128]==cb[:128]))
import struct
H,W=2048,4096
raws=Image.frombytes("RGBA",(W,H),sb[128:],"raw","RGBA")
rawf=Image.frombytes("RGBA",(W,H),cb[128:],"raw","RGBA")
src=raws.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
fin=rawf.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
sa=np.asarray(src,dtype=np.uint8); fa=np.asarray(fin,dtype=np.uint8)

# Rebuild the clean plate independently from the already C202-approved same-family B148 template.
tpl=repo/"localization/graphics/role_B/20261005-B-PRODUCTION148-8215-C200-TEMPLATE"
c202=json.loads((repo/"localization/graphics/role_C/20261005-C202-8215FD25/C202_8215FD25_CONTROLLER_FINAL_QA.json").read_text())
if c202.get("decision")!="C202_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME":
    raise RuntimeError(("C202 approval drift",c202.get("decision")))
trep=json.loads((tpl/"B148_8215_REPORT.json").read_text())
row=next(r for r in trep["rows"] if int(r["region_idx"])==1)
tsrc=Image.open(tpl/"B148_SOURCE_READABLE.png").convert("RGBA")
tclean=Image.open(tpl/"B148_CLEAN_PLATE.png").convert("RGBA")
ts=np.asarray(tsrc,dtype=np.uint8); tc=np.asarray(tclean,dtype=np.uint8)
src_cell=list(map(int,row["cell"])); dst_cell=list(map(int,pr["row"]["cell"]))
dx=dst_cell[0]-src_cell[0]
if dx!=192 or dst_cell[1]!=src_cell[1]:
    raise RuntimeError(("template shift",src_cell,dst_cell,dx))
ob=list(map(int,row["original_bbox"])); core=list(map(int,row["source_core_bbox"]))
dob=[ob[0]+dx,ob[1],ob[2]+dx,ob[3]]
dcore=[core[0]+dx,core[1],core[2]+dx,core[3]]
if dob!=list(map(int,pr["row"]["original_bbox"])) or dcore!=list(map(int,pr["row"]["source_core_bbox"])):
    raise RuntimeError(("producer bbox drift",dob,dcore,pr["row"]))

tsp=ts[ob[1]:ob[3],ob[0]:ob[2]]
tcp=tc[ob[1]:ob[3],ob[0]:ob[2]]
hp=sa[dob[1]:dob[3],dob[0]:dob[2]]
removal=np.any(tsp!=tcp,axis=2)
variant=np.any(tsp!=hp,axis=2)
extra=variant & (~removal)
extra_rgba=hp[extra]
if int(np.count_nonzero(variant))!=240 or int(np.count_nonzero(extra))!=1:
    raise RuntimeError(("unexpected template/HOLL delta",int(np.count_nonzero(variant)),int(np.count_nonzero(extra))))
px=extra_rgba[0].tolist()
if not (px[3]>0 and px[0]>135 and px[1]>135 and px[2]>135):
    raise RuntimeError(("extra delta not title-family",px))
hremove=removal|extra
clean_arr=sa.copy()
sub=clean_arr[dob[1]:dob[3],dob[0]:dob[2]]
sub[hremove]=tcp[hremove]
clean_arr[dob[1]:dob[3],dob[0]:dob[2]]=sub
clean=Image.fromarray(clean_arr,"RGBA")

# Independently measure localized text as CLEAN -> FINAL decoded delta.
loc=np.asarray(diffmask(clean,fin))>0
lbb=bbox(loc)
decl=list(map(int,pr["row"]["localized_bbox"]))
lbb_exact=(lbb==decl)
if lbb is None: raise RuntimeError("empty localized delta")
x0,y0,x1,y1=lbb
contain=x0>=dcore[0] and y0>=dcore[1] and x1<=dcore[2] and y1<=dcore[3]
sizeok=(x1-x0)<=dcore[2]-dcore[0] and (y1-y0)<=dcore[3]-dcore[1]
margins=[x0-dcore[0],dcore[2]-x1,y0-dcore[1],dcore[3]-y1]
positive=min(margins)>0

effect=np.zeros((H,W),bool); effect[dob[1]:dob[3],dob[0]:dob[2]]=True
chg=np.any(fa!=sa,axis=2); ach=fa[:,:,3]!=sa[:,:,3]; intro=fa[:,:,3]>sa[:,:,3]
outside=int(np.count_nonzero(chg & (~effect)))
alpha_out=int(np.count_nonzero(ach & (~effect)))
intro_out=int(np.count_nonzero(intro & (~effect)))
# Every opaque source-title/effect pixel in the proven removal mask must differ after cleaning.
gm=np.zeros((H,W),bool); gm[dob[1]:dob[3],dob[0]:dob[2]]=hremove
exact_clean=np.all(clean_arr==sa,axis=2)
residue=int(np.count_nonzero(gm & exact_clean & (sa[:,:,3]>0)))
machine_status="PASS" if (lbb_exact and contain and sizeok and positive and outside==0 and alpha_out==0 and intro_out==0 and residue==0) else "FAIL"

# Controller evidence: source | independent clean | final and raw.
pad=110; box=(max(0,dob[0]-pad),max(0,dob[1]-pad),min(W,dob[2]+pad),min(H,dob[3]+pad))
ims=[comp(z.crop(box)) for z in (src,clean,fin)]
scale=min(2.4,1450/max(1,ims[0].width)); ims=[z.resize((int(z.width*scale),int(z.height*scale)),Image.Resampling.NEAREST) for z in ims]
sheet=Image.new("RGB",(sum(z.width for z in ims)+16,max(z.height for z in ims)+44),"white"); xx=0
for lab,z in zip(("SOURCE","CLEAN","FINAL"),ims):
    sheet.paste(z,(xx,44)); ImageDraw.Draw(sheet).text((xx+5,8),lab,fill="black"); xx+=z.width+8
sheet.save(out/"C209_SOURCE_CLEAN_FINAL.jpg",quality=95)
rr=Image.new("RGB",(1024,1100),"white")
for i,(lab,z0) in enumerate((("SOURCE_RAW_MIRROR_Y",raws),("FINAL_RAW_MIRROR_Y",rawf))):
    z=comp(z0); z.thumbnail((1024,512),Image.Resampling.LANCZOS); rr.paste(z,(0,i*550+26)); ImageDraw.Draw(rr).text((5,i*550+5),lab,fill="black")
rr.save(out/"C209_RAW_COMPARE.jpg",quality=92)

rep={
 "schema_version":1,"role":"C","run":run,"qa_id":"C209","queue_index":34,"asset":asset,
 "producer_run":pr["run"],"source_sha256":SOURCE_SHA,"candidate_sha256":pr["candidate_sha256"],
 "structure":{"dimensions":[W,H],"format":"RGBA32","header_exact":True,"raw_orientation":"mirror_y"},
 "template_reference":{"approval":"C202_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME","shift":[dx,0],"template_vs_holl_variant_pixels":int(np.count_nonzero(variant)),"extra_title_aa_pixels":int(np.count_nonzero(extra)),"extra_rgba":extra_rgba.tolist()},
 "independent_original_bbox":dob,"independent_source_core_bbox":dcore,
 "independent_localized_bbox":lbb,"producer_localized_bbox":decl,"candidate_bbox_exact_match_producer":lbb_exact,
 "bbox_gate":{"containment":"PASS" if contain else "FAIL","size_ceiling":"PASS" if sizeok else "FAIL","positive_margin":"PASS" if positive else "FAIL","margins":margins,
              "source_width":dcore[2]-dcore[0],"source_height":dcore[3]-dcore[1],"localized_width":x1-x0,"localized_height":y1-y0,
              "width_ratio":round((x1-x0)/(dcore[2]-dcore[0]),4),"height_ratio":round((y1-y0)/(dcore[3]-dcore[1]),4)},
 "machine_checks":{"decoded_changed_outside_effect_bbox":outside,"alpha_changed_outside_effect_bbox":alpha_out,"introduced_visible_outside_effect_bbox":intro_out,"opaque_source_title_residue_pixels":residue},
 "machine_status":machine_status,"controller_visual_qa":"PENDING_CONTROLLER_REVIEW",
 "decision":"PENDING_CONTROLLER_VISUAL_QA" if machine_status=="PASS" else "C209_REWORK_REQUIRED_MACHINE_GATE",
 "runtime_validation":"UNTESTED",
 "preview_files":[f"localization/graphics/role_C/{run}/C209_SOURCE_CLEAN_FINAL.jpg",f"localization/graphics/role_C/{run}/C209_RAW_COMPARE.jpg"]
}
(out/"C209_B7E25BAD_MACHINE_QA.json").write_text(json.dumps(rep,ensure_ascii=False,indent=2)+"\n")
(wr/"C209_B7E25BAD.json").write_text(json.dumps({"run":run,"qa_id":"C209","index":34,"asset":"B7E25BAD","candidate_sha256":pr["candidate_sha256"],"machine_status":machine_status,"bbox_gate":rep["bbox_gate"],"machine_checks":rep["machine_checks"],"report":f"localization/graphics/role_C/{run}/C209_B7E25BAD_MACHINE_QA.json","runtime_validation":"UNTESTED"},ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"C209":{"machine_status":machine_status,"localized_bbox":lbb,"bbox_gate":rep["bbox_gate"],"machine_checks":rep["machine_checks"]}},ensure_ascii=False),flush=True)
