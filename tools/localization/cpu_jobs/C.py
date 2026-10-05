#!/usr/bin/env python3
import os, json, hashlib, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="C":
    raise SystemExit("GitHub-hosted localization CPU worker / role C only")

repo=Path.cwd()
run="20261005-C205-DCC7B488"
out=repo/"localization/graphics/role_C"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)

def sha(b): return hashlib.sha256(b).hexdigest()
def bbox(mask):
    yy,xx=np.nonzero(mask)
    if len(xx)==0:return None
    return [int(xx.min()),int(yy.min()),int(xx.max())+1,int(yy.max())+1]
def count(mask): return int(np.count_nonzero(mask))
def comp(im,bg=(62,62,62,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")

pr=json.loads((repo/"localization/graphics/role_B/20261005-B-PRODUCTION152-DCC7/B152_DCC7_REPORT.json").read_text(encoding="utf-8"))
sp=pr["source_provenance"]; asset=pr["asset"]; cand=repo/pr["candidate_path"]
tmp=Path("/tmp/c205"); tmp.mkdir(exist_ok=True); srcdds=tmp/"source.dds"
folder=asset.split("/")[-2]; name=asset.split("/")[-1]
url=f"https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/{sp['commit']}/Release/{folder}/{name}"
urllib.request.urlretrieve(url,srcdds)
sb=srcdds.read_bytes(); cb=cand.read_bytes()
if sha(sb)!=sp["source_sha256"]: raise RuntimeError(("source SHA",sha(sb),sp["source_sha256"]))
if sha(cb)!=pr["candidate_sha256"]: raise RuntimeError(("candidate SHA",sha(cb),pr["candidate_sha256"]))
if cb[:128]!=sb[:128]: raise RuntimeError("header mismatch")

raws=Image.open(srcdds).convert("RGBA"); rawf=Image.open(cand).convert("RGBA")
src=raws.transpose(Image.Transpose.FLIP_TOP_BOTTOM); fin=rawf.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
sa=np.asarray(src,dtype=np.uint8); fa=np.asarray(fin,dtype=np.uint8)
H,W=sa.shape[:2]
if (W,H)!=(2048,1024): raise RuntimeError((W,H))

base=repo/"localization/graphics/role_B/20261005-B-PRODUCTION152-DCC7"
clean=Image.open(base/"B152_CLEAN_PLATE.png").convert("RGBA")
sourcepng=Image.open(base/"B152_SOURCE_READABLE.png").convert("RGBA")
finalpng=Image.open(base/"B152_FINAL_READABLE.png").convert("RGBA")
allow=Image.open(base/"B152_ALLOWED_EFFECT_BBOX_MASK.png").convert("L")
prot=Image.open(base/"B152_PROTECTED_MASK.png").convert("L")
ca=np.asarray(clean,dtype=np.uint8); spa=np.asarray(sourcepng,dtype=np.uint8); fpa=np.asarray(finalpng,dtype=np.uint8)
am=np.asarray(allow)>0; pm=np.asarray(prot)>0
if count(np.any(spa!=sa,axis=2)): raise RuntimeError("source evidence mismatch")
if count(np.any(fpa!=fa,axis=2)): raise RuntimeError("final evidence mismatch")

row=pr["rows"][0]; orig=list(map(int,row["original_bbox"])); producer_core=list(map(int,row["source_core_bbox"]))
x0,y0,x1,y1=orig
# Independent high-confidence title script mask. The title is isolated inside the exact
# effect bbox: near-white fill plus the dark navy outline connected within 8 px.
sub=sa[y0:y1,x0:x1]
r=sub[:,:,0].astype(np.int16); g=sub[:,:,1].astype(np.int16); b=sub[:,:,2].astype(np.int16); a=sub[:,:,3]
spread=np.maximum.reduce([r,g,b])-np.minimum.reduce([r,g,b])
white=(a>80)&(r>180)&(g>180)&(b>180)&(spread<70)
if count(white)<10000: raise RuntimeError(("too few white title pixels",count(white)))
wimg=Image.fromarray((white.astype(np.uint8)*255),"L")
near=np.asarray(wimg.filter(ImageFilter.MaxFilter(17)))>0
navy=(a>80)&(r<80)&(g<90)&(b<125)&near
script_local=white|navy
script=np.zeros((H,W),dtype=bool); script[y0:y1,x0:x1]=script_local
corebb=bbox(script)
if corebb is None: raise RuntimeError("empty script")
# The independent high-confidence mask must lie within and substantially cover the producer core.
if not(corebb[0]>=producer_core[0]-8 and corebb[1]>=producer_core[1]-8 and corebb[2]<=producer_core[2]+8 and corebb[3]<=producer_core[3]+8):
    raise RuntimeError(("core disagreement",corebb,producer_core))

# C204 false-positive source-residue counter used B152_SOURCE_TEXT_MASK.png, but B152's
# worker writes the full rectangular clean_scope to that filename. Adjudicate against
# independently detected title colors/components instead.
eq_clean_source=np.all(ca==sa,axis=2)
exact_script_residue=count(script & eq_clean_source)
cs=ca[y0:y1,x0:x1]
cr=cs[:,:,0].astype(np.int16); cg=cs[:,:,1].astype(np.int16); cbg=cs[:,:,2].astype(np.int16); cspread=np.maximum.reduce([cr,cg,cbg])-np.minimum.reduce([cr,cg,cbg])
clean_white=(cs[:,:,3]>80)&(cr>180)&(cg>180)&(cbg>180)&(cspread<70)&near
clean_navy=(cs[:,:,3]>80)&(cr<80)&(cg<90)&(cbg<125)&near
source_colored_residue=count(clean_white|clean_navy)

render=np.any(fpa!=ca,axis=2); renderbb=bbox(render)
decl=list(map(int,row["localized_bbox"]))
changed=np.any(fa!=sa,axis=2); ach=fa[:,:,3]!=sa[:,:,3]
ring=np.zeros((H,W),dtype=bool)
ring[y0:y0+1,x0:x1]=True; ring[y1-1:y1,x0:x1]=True; ring[y0:y1,x0:x0+1]=True; ring[y0:y1,x1-1:x1]=True
clean_changed=np.any(ca!=sa,axis=2)
m={
 "decoded_source_vs_evidence_diff_pixels":count(np.any(sa!=spa,axis=2)),
 "decoded_final_vs_evidence_diff_pixels":count(np.any(fa!=fpa,axis=2)),
 "independent_high_conf_source_script_bbox":corebb,
 "producer_source_core_bbox":producer_core,
 "independent_high_conf_exact_source_pixels_surviving_in_clean":exact_script_residue,
 "independent_high_conf_source_colored_pixels_surviving_in_clean":source_colored_residue,
 "localized_bbox_exact_match_producer":bool(renderbb==decl),
 "decoded_changed_outside_allowed_effect_bbox":count(changed&~am),
 "alpha_changed_outside_allowed_effect_bbox":count(ach&~am),
 "localized_render_outside_allowed_effect_bbox":count(render&~am),
 "protected_region_changed_pixels":count(changed&pm),
 "clean_outer_boundary_ring_changed_pixels":count(ring&clean_changed)
}
if renderbb is None:
    contain=size_ok=positive=False; dl=dr=dt=db=-1
else:
    aa,bb,cc,dd=renderbb; dl=aa-x0; dr=x1-cc; dt=bb-y0; db=y1-dd
    contain=aa>=x0 and bb>=y0 and cc<=x1 and dd<=y1
    size_ok=(cc-aa)<=x1-x0 and (dd-bb)<=y1-y0
    positive=min(dl,dr,dt,db)>0
status="PASS" if all([
    exact_script_residue==0,source_colored_residue==0,m["localized_bbox_exact_match_producer"],
    m["decoded_changed_outside_allowed_effect_bbox"]==0,m["alpha_changed_outside_allowed_effect_bbox"]==0,
    m["localized_render_outside_allowed_effect_bbox"]==0,m["protected_region_changed_pixels"]==0,
    m["clean_outer_boundary_ring_changed_pixels"]==0,contain,size_ok,positive
]) else "FAIL"

focus=Image.new("RGB",(1800,600),"white"); crop=(430,100,1180,330)
for j,(lab,im) in enumerate([("SOURCE",src),("CLEAN",clean),("FINAL",fin)]):
    z=comp(im).crop(crop).resize((600,550),Image.Resampling.LANCZOS)
    focus.paste(z,(j*600,30)); ImageDraw.Draw(focus).text((j*600+5,5),lab,fill="black")
focus.save(out/"C205_DCC7_ADJUDICATED_FOCUS.jpg",quality=96)
report={
 "schema_version":1,"role":"C","run":run,"qa_id":"C205","queue_index":32,"asset":asset,
 "producer_run":pr["run"],"source_sha256":sp["source_sha256"],"candidate_sha256":pr["candidate_sha256"],
 "structure":{"dimensions":[W,H],"header_exact":True,"raw_orientation":"mirror_y","format":pr["structure"]["format"]},
 "classification":{"source":"Total Rank","korean":"종합 랭킹","prior_queue_action":"zoom_review","positive_localize_text":True},
 "c204_adjudication":{"c204_flagged_exact_pixels_in_rectangular_clean_scope":1418,"finding":"FALSE_POSITIVE_SCOPE_MASK_NOT_PRECISE_TEXT_MASK","detail":"B152_SOURCE_TEXT_MASK.png stores the full rectangular clean_scope in the producer script. C205 independently detects high-confidence white-fill/dark-navy title components instead."},
 "row_checks":[{"original_bbox":orig,"independent_localized_bbox":renderbb,"producer_localized_bbox":decl,"delta_left":dl,"delta_right":dr,"delta_top":dt,"delta_bottom":db,"containment":"PASS" if contain else "FAIL","size_ceiling":"PASS" if size_ok else "FAIL","positive_margin":"PASS" if positive else "FAIL"}],
 "row_gate":"1/1 PASS" if contain and size_ok and positive else "0/1 FAIL",
 "machine_checks":m,"machine_status":status,
 "controller_visual_qa":"PENDING_CONTROLLER_REVIEW",
 "decision":"PENDING_CONTROLLER_VISUAL_QA" if status=="PASS" else "C205_REWORK_REQUIRED_MACHINE_OR_POLICY_GATE",
 "runtime_validation":"UNTESTED",
 "preview_files":[f"localization/graphics/role_C/{run}/C205_DCC7_ADJUDICATED_FOCUS.jpg"]
}
(out/"C205_DCC7B488_ADJUDICATED_MACHINE_QA.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(wr/"C205_DCC7B488.json").write_text(json.dumps({
 "run":run,"qa_id":"C205","index":32,"asset":"DCC7B488","candidate_sha256":pr["candidate_sha256"],
 "machine_status":status,"row_gate":report["row_gate"],"machine_checks":m,
 "report":f"localization/graphics/role_C/{run}/C205_DCC7B488_ADJUDICATED_MACHINE_QA.json","runtime_validation":"UNTESTED"
},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"C205":{"machine_status":status,"row_gate":report["row_gate"],"machine_checks":m}},ensure_ascii=False),flush=True)
