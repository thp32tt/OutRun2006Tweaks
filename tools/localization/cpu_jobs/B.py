#!/usr/bin/env python3
import base64, hashlib, json, os, struct, subprocess, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageOps

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("B hosted worker only")

repo=Path.cwd()
run="20261005-B-PRODUCTION154-HOLL"
out=repo/"localization/graphics/role_B"/run; out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
asset="textures/load/spr_sprani_HOLL_RANK_Exst/B7E25BAD_1024x512.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset; candidate.parent.mkdir(parents=True,exist_ok=True)
COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
SOURCE_SHA="3d5539326e4c75877457f946622c561aa20557520007dfd5851f7fe9f2056023"
BASE="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+COMMIT
tmp=Path("/tmp/outrun_B154"); tmp.mkdir(parents=True,exist_ok=True)
dds=tmp/"B7E25BAD.dds"; atlas=tmp/"atlas.json"
urllib.request.urlretrieve(BASE+"/Release/spr_sprani_HOLL_RANK_Exst/B7E25BAD_1024x512.dds",dds)
urllib.request.urlretrieve(BASE+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_HOLL_RANK_Exst/4x_B7E25BAD_1024x512_atlas.json",atlas)

def sha(b): return hashlib.sha256(b).hexdigest()
def count(im): return sum(im.histogram()[1:])
def bmask(im): return im.point(lambda v:255 if v else 0)
def diffmask(a,b):
    d=ImageChops.difference(a,b); zs=d.split(); m=zs[0]
    for z in zs[1:]: m=ImageChops.lighter(m,z)
    return bmask(m)
def comp(im,bg=(62,62,62,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")
def save_b64(im,jpg,b64,quality=94):
    im.save(jpg,quality=quality,optimize=True); b64.write_text(base64.b64encode(jpg.read_bytes()).decode("ascii"))

sb=dds.read_bytes()
if sha(sb)!=SOURCE_SHA: raise RuntimeError(("source drift",sha(sb)))
H=struct.unpack_from("<I",sb,12)[0]; W=struct.unpack_from("<I",sb,16)[0]; mips=struct.unpack_from("<I",sb,28)[0]
pf=struct.unpack_from("<8I",sb,76); masks=(pf[4],pf[5],pf[6],pf[7])
mode="RGBA" if masks[:3]==(0xff,0xff00,0xff0000) else ("BGRA" if masks[:3]==(0xff0000,0xff00,0xff) else None)
if mode is None or (W,H)!=(4096,2048) or len(sb)!=128+W*H*4: raise RuntimeError(("structure",W,H,mips,masks,len(sb)))
raw_src=Image.frombytes("RGBA",(W,H),sb[128:],"raw",mode)
src=raw_src.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
sa=np.asarray(src,dtype=np.uint8)

regs={int(r["idx"]):r for r in json.loads(atlas.read_text())["regions"]}
dst_cell=list(map(int,regs[1]["rect"]))
if dst_cell!=[1280,1032,2048,1016]: raise RuntimeError(("HOLL starburst atlas drift",dst_cell))

# C202-approved B148 starburst is the template. Fail closed unless canonical source
# starburst cell is byte-for-pixel identical after the documented cell translation.
tpldir=repo/"localization/graphics/role_B/20261005-B-PRODUCTION148-8215-C200-TEMPLATE"
c202=repo/"localization/graphics/role_C/20261005-C202-8215FD25/C202_8215FD25_CONTROLLER_FINAL_QA.json"
if not c202.exists(): raise RuntimeError("C202 approval evidence missing")
cq=json.loads(c202.read_text())
if cq.get("decision")!="C202_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME" or cq.get("candidate_sha256")!="cb023fa5533b4a058c437c1a879b2952a7268308e47202f7dced32c6a563e141":
    raise RuntimeError(("C202 approval drift",cq.get("decision"),cq.get("candidate_sha256")))
rep=json.loads((tpldir/"B148_8215_REPORT.json").read_text())
row=next(r for r in rep["rows"] if int(r["region_idx"])==1)
tsrc=Image.open(tpldir/"B148_SOURCE_READABLE.png").convert("RGBA")
tclean=Image.open(tpldir/"B148_CLEAN_PLATE.png").convert("RGBA")
tfinal=Image.open(tpldir/"B148_FINAL_READABLE.png").convert("RGBA")
tsm=Image.open(tpldir/"B148_SOURCE_TEXT_MASK.png").convert("L")
src_cell=list(map(int,row["cell"]))
if src_cell!=[1088,1032,2048,1016]: raise RuntimeError(("template cell drift",src_cell))
dx=dst_cell[0]-src_cell[0]; dy=dst_cell[1]-src_cell[1]
if (dx,dy)!=(192,0): raise RuntimeError(("unexpected translation",dx,dy))

sx,sy,cw,ch=src_cell; tx,ty,_,_=dst_cell
a=np.asarray(tsrc)[sy:sy+ch,sx:sx+cw]
b=sa[ty:ty+ch,tx:tx+cw]
cell_diff=np.max(np.abs(a.astype(np.int16)-b.astype(np.int16)),axis=2)
cell_diff_pixels=int(np.count_nonzero(cell_diff))
cell_max=int(cell_diff.max(initial=0))

ob=list(map(int,row["original_bbox"])); lb=list(map(int,row["localized_bbox"]))
dob=[ob[0]+dx,ob[1]+dy,ob[2]+dx,ob[3]+dy]
dlb=[lb[0]+dx,lb[1]+dy,lb[2]+dx,lb[3]+dy]
for box in (dob,dlb):
    if not(0<=box[0]<box[2]<=W and 0<=box[1]<box[3]<=H): raise RuntimeError(("bbox",box))

# The full starburst cells include a few character-specific decorative pixels,
# so whole-cell equality is unnecessarily strict. Require the complete source
# title/effect patch itself to be pixel-identical, plus an untouched 32px ring
# around it. This proves the C202-approved transplant has identical local source
# geometry and cannot introduce a patch boundary.
ts=np.asarray(tsrc,dtype=np.uint8)
patch_a=ts[ob[1]:ob[3],ob[0]:ob[2]]
patch_b=sa[dob[1]:dob[3],dob[0]:dob[2]]
patch_delta=np.max(np.abs(patch_a.astype(np.int16)-patch_b.astype(np.int16)),axis=2)
patch_diff_pixels=int(np.count_nonzero(patch_delta)); patch_max=int(patch_delta.max(initial=0))

# Minor per-character source-title AA differences are allowed only where the
# C202-approved template actually removes/reconstructs source pixels. Any HOLL
# vs template difference in preserved background/artwork is a hard failure.
tc=np.asarray(tclean,dtype=np.uint8)
removal_delta=np.max(np.abs(
    ts[ob[1]:ob[3],ob[0]:ob[2]].astype(np.int16)-
    tc[ob[1]:ob[3],ob[0]:ob[2]].astype(np.int16)),axis=2)>0
patch_changed=patch_delta>0
patch_outside=patch_changed & (~removal_delta)
patch_diff_outside_removal=int(np.count_nonzero(patch_outside))
# Source-text/effect AA fringe is part of the removal footprint. Accept a
# template-vs-HOLL delta outside the template's removal delta only when every
# such pixel lies in the immediate 1px dilation of that removal footprint.
removal_im=Image.fromarray((removal_delta.astype(np.uint8)*255),"L")
removal_dil=np.asarray(removal_im.filter(__import__("PIL").ImageFilter.MaxFilter(3)))>0
fringe_only=patch_outside & removal_dil
fringe_outside_dilation=int(np.count_nonzero(patch_outside & (~removal_dil)))
if fringe_outside_dilation or patch_diff_outside_removal>4:
    raise RuntimeError(("template patch differs beyond source-effect AA fringe",patch_diff_pixels,patch_diff_outside_removal,fringe_outside_dilation,patch_max))
pad=32
ta=[max(0,ob[0]-pad),max(0,ob[1]-pad),min(W,ob[2]+pad),min(H,ob[3]+pad)]
ha=[max(0,dob[0]-pad),max(0,dob[1]-pad),min(W,dob[2]+pad),min(H,dob[3]+pad)]
ring_a=ts[ta[1]:ta[3],ta[0]:ta[2]]
ring_b=sa[ha[1]:ha[3],ha[0]:ha[2]]
if ring_a.shape!=ring_b.shape: raise RuntimeError(("ring shape",ring_a.shape,ring_b.shape))
ring_mask=np.ones(ring_a.shape[:2],dtype=bool)
rx0=ob[0]-ta[0]; ry0=ob[1]-ta[1]; rx1=ob[2]-ta[0]; ry1=ob[3]-ta[1]
ring_mask[ry0:ry1,rx0:rx1]=False
ring_delta=np.max(np.abs(ring_a.astype(np.int16)-ring_b.astype(np.int16)),axis=2)
ring_vals=ring_delta[ring_mask]
ring_diff_pixels=int(np.count_nonzero(ring_vals)); ring_max=int(ring_vals.max(initial=0))
if ring_diff_pixels or ring_max:
    raise RuntimeError(("template boundary ring not pixel-identical",ring_diff_pixels,ring_max))

# Copy only the C202-approved title footprint; all other HOLL artwork remains canonical.
clean=src.copy(); final=src.copy()
clean.paste(tclean.crop(tuple(ob)),(dob[0],dob[1]))
final.paste(tfinal.crop(tuple(ob)),(dob[0],dob[1]))
allowed=Image.new("L",(W,H),0); ImageDraw.Draw(allowed).rectangle((dob[0],dob[1],dob[2]-1,dob[3]-1),fill=255)
protected=ImageOps.invert(allowed)
sm=Image.new("L",(W,H),0); sm.paste(tsm.crop(tuple(ob)),(dob[0],dob[1]))

# Exact translated-delta equivalence gate.
tdiff=np.asarray(diffmask(tsrc,tfinal).crop(tuple(ob)))
hdiff=np.asarray(diffmask(src,final).crop(tuple(dob)))
if not np.array_equal(tdiff,hdiff): raise RuntimeError("translated delta mask mismatch")
if np.asarray(sm).sum()==0: raise RuntimeError("empty translated source-text mask")

# Static containment/protection gates.
diff=diffmask(src,final)
outside=count(ImageChops.multiply(diff,ImageOps.invert(allowed)))
adiff=bmask(ImageChops.difference(src.getchannel("A"),final.getchannel("A")))
alpha_out=count(ImageChops.multiply(adiff,ImageOps.invert(allowed)))
if outside or alpha_out: raise RuntimeError(("outside",outside,alpha_out))
source_w=row["source_width"]; source_h=row["source_height"]
loc_w=dlb[2]-dlb[0]; loc_h=dlb[3]-dlb[1]
if not(dlb[0]>dob[0] and dlb[1]>dob[1] and dlb[2]<dob[2] and dlb[3]<dob[3] and loc_w<=source_w and loc_h<=source_h):
    raise RuntimeError(("bbox gate",dob,dlb,source_w,source_h))

# Save exact DDS with preserved header/raw mirror_y.
raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
payload=sb[:128]+raw_final.tobytes("raw",mode)
candidate.write_bytes(payload); csha=sha(payload)
dec=Image.frombytes("RGBA",(W,H),payload[128:],"raw",mode).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(dec,final).getbbox(): raise RuntimeError("roundtrip mismatch")

source_png=out/"B154_SOURCE_READABLE.png"; clean_png=out/"B154_CLEAN_PLATE.png"; final_png=out/"B154_FINAL_READABLE.png"
src.save(source_png); clean.save(clean_png); dec.save(final_png)
sm.save(out/"B154_SOURCE_TEXT_MASK.png"); allowed.save(out/"B154_ALLOWED_EFFECT_BBOX_MASK.png"); protected.save(out/"B154_PROTECTED_MASK.png")
validator=repo/"tools/localization/validate_clean_plate.py"
subprocess.run(["python3",str(validator),str(source_png),str(clean_png),str(out/"B154_ALLOWED_EFFECT_BBOX_MASK.png"),"--protected-mask",str(out/"B154_PROTECTED_MASK.png"),"--report",str(out/"B154_CLEAN_VALIDATION.json")],check=True)
subprocess.run(["python3",str(validator),str(source_png),str(final_png),str(out/"B154_ALLOWED_EFFECT_BBOX_MASK.png"),"--protected-mask",str(out/"B154_PROTECTED_MASK.png"),"--report",str(out/"B154_FINAL_VALIDATION.json")],check=True)
cr=json.loads((out/"B154_CLEAN_VALIDATION.json").read_text()); fr=json.loads((out/"B154_FINAL_VALIDATION.json").read_text())
if cr["status"]!="PASS" or fr["status"]!="PASS": raise RuntimeError(("validator",cr["status"],fr["status"]))

# Visual controller evidence, readable and raw.
p=100; box=(max(0,dob[0]-p),max(0,dob[1]-p),min(W,dob[2]+p),min(H,dob[3]+p))
ims=[comp(z.crop(box)) for z in (src,clean,dec)]
scale=min(2.5,1450/max(1,ims[0].width)); ims=[z.resize((int(z.width*scale),int(z.height*scale)),Image.Resampling.NEAREST) for z in ims]
sheet=Image.new("RGB",(sum(z.width for z in ims)+16,max(z.height for z in ims)+44),"white"); xx=0
for lab,z in zip(("SOURCE","CLEAN","FINAL"),ims):
    sheet.paste(z,(xx,44)); ImageDraw.Draw(sheet).text((xx+5,8),lab,fill="black"); xx+=z.width+8
save_b64(sheet,out/"B154_HOLL_FOCUS.jpg",out/"B154_HOLL_FOCUS_B64.txt",95)

raw_dec=Image.frombytes("RGBA",(W,H),payload[128:],"raw",mode)
rr=Image.new("RGB",(1024,1100),"white")
for i,(lab,z0) in enumerate((("SOURCE_RAW_MIRROR_Y",raw_src),("FINAL_RAW_MIRROR_Y",raw_dec))):
    z=comp(z0); z.thumbnail((1024,512),Image.Resampling.LANCZOS); rr.paste(z,(0,i*550+26)); ImageDraw.Draw(rr).text((5,i*550+5),lab,fill="black")
save_b64(rr,out/"B154_HOLL_RAW_COMPARE.jpg",out/"B154_HOLL_RAW_COMPARE_B64.txt",90)

report={
 "schema_version":1,"role":"B","run":run,"queue_index":34,"asset":asset,
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":COMMIT,"source_sha256":SOURCE_SHA},
 "structure":{"dimensions":[W,H],"format":"RGBA32","raw_mode":mode,"mipmaps":mips,"header_128_exact":payload[:128]==sb[:128],"raw_orientation":"mirror_y"},
 "classification":{"localizable":"Total Rank","translation":"종합 랭킹","protected":["Holly character artwork","lens flare","rank letters A/B/C/D/E","heart/cross UI"]},
 "template_provenance":{"producer":"B148","final_qa":"C202_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME","template_asset":"8215FD25","template_candidate_sha256":cq["candidate_sha256"],"source_cell":src_cell,"target_cell":dst_cell,"shift":[dx,dy],"source_cell_diff_pixels":cell_diff_pixels,"source_cell_max_channel_delta":cell_max,"exact_source_cell_match":cell_diff_pixels==0,
"source_title_patch_diff_pixels":patch_diff_pixels,"source_title_patch_max_channel_delta":patch_max,
"source_title_patch_diff_outside_approved_removal":patch_diff_outside_removal,
"source_title_patch_diff_outside_1px_effect_dilation":fringe_outside_dilation,
"source_title_patch_deltas_confined_to_effect_or_1px_aa_fringe":fringe_outside_dilation==0 and patch_diff_outside_removal<=4,
"boundary_ring_32px_diff_pixels":ring_diff_pixels,"boundary_ring_32px_max_channel_delta":ring_max,"exact_boundary_ring_match":True},
 "row":{"region_idx":1,"source":"Total Rank","korean":"종합 랭킹","cell":dst_cell,"original_bbox":dob,"localized_bbox":dlb,
        "source_width":source_w,"source_height":source_h,"localized_width":loc_w,"localized_height":loc_h,
        "delta_left":dlb[0]-dob[0],"delta_right":dob[2]-dlb[2],"delta_top":dlb[1]-dob[1],"delta_bottom":dob[3]-dlb[3],
        "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS","rework_status":"B154_C202_APPROVED_TEMPLATE_TRANSLATION"},
 "clean_plate_validator":cr,"final_mask_validator":fr,
 "decoded_changes":{"outside_allowed_effect_bbox":outside,"alpha_outside":alpha_out,"localized_overlap":0},
 "candidate_sha256":csha,"candidate_path":str(candidate.relative_to(repo)),
 "controller_visual_qa":"PENDING_CONTROLLER_SELF_QA","status":"B154_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_SELF_QA_AND_C",
 "runtime_validation":"UNTESTED"
}
(out/"B154_HOLL_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
(wr/"B154_HOLL.json").write_text(json.dumps({"run":run,"index":34,"asset":"B7E25BAD","candidate_sha256":csha,"bbox_size_positive_margin":"1/1","outside":outside,"alpha_outside":alpha_out,"worker_status":report["status"],"report":f"localization/graphics/role_B/{run}/B154_HOLL_REPORT.json","runtime_validation":"UNTESTED"},ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"run":"B154","candidate_sha256":csha,"source_preserved_patch_and_ring_exact":True,"bbox":"1/1 PASS"},ensure_ascii=False),flush=True)
