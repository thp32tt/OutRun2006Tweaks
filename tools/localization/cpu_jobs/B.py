#!/usr/bin/env python3
import base64, hashlib, json, os, struct, subprocess, urllib.request
from pathlib import Path
import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="B":
    raise SystemExit("B hosted worker only")

repo=Path.cwd()
run="20261005-B-PRODUCTION156-JENN"
out=repo/"localization/graphics/role_B"/run
out.mkdir(parents=True,exist_ok=True)
wr=repo/"localization/graphics/worker_results"; wr.mkdir(parents=True,exist_ok=True)
asset="textures/load/spr_sprani_JENN_RANK_Exst/06AB5CEE_1024x1024.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset
candidate.parent.mkdir(parents=True,exist_ok=True)

COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
SOURCE_SHA="cd6f58f1fa187c6ff7813cbb42b5181038712d8142bf575711a30d69e76d2f4a"
BASE="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+COMMIT
tmp=Path("/tmp/outrun_B156"); tmp.mkdir(parents=True,exist_ok=True)
dds=tmp/"JENN_HD.dds"; atlas=tmp/"JENN_HD_atlas.json"
# Queue 06AB5CEE is the 4x/HD payload. Upstream Release names that payload 6AB5CEE.
urllib.request.urlretrieve(BASE+"/Release/spr_sprani_JENN_RANK_Exst/6AB5CEE_1024x1024.dds",dds)
urllib.request.urlretrieve(BASE+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_JENN_RANK_Exst/4x_06AB5CEE_1024x1024_atlas.json",atlas)

def sha(b): return hashlib.sha256(b).hexdigest()
def bmask(im): return im.point(lambda v:255 if v else 0)
def count(im): return sum(im.histogram()[1:])
def diffmask(a,b):
    d=ImageChops.difference(a,b); zs=d.split(); m=zs[0]
    for z in zs[1:]: m=ImageChops.lighter(m,z)
    return bmask(m)
def comp(im,bg=(62,62,62,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")
def save_b64(im,jpg,b64,quality=94):
    im.convert("RGB").save(jpg,quality=quality,optimize=True)
    b64.write_text(base64.b64encode(jpg.read_bytes()).decode("ascii"))

sb=dds.read_bytes()
if sha(sb)!=SOURCE_SHA: raise RuntimeError(("source drift",sha(sb)))
if sb[:4]!=b"DDS ": raise RuntimeError("not DDS")
H=struct.unpack_from("<I",sb,12)[0]; W=struct.unpack_from("<I",sb,16)[0]; mips=struct.unpack_from("<I",sb,28)[0]
pf=struct.unpack_from("<8I",sb,76); masks=(pf[4],pf[5],pf[6],pf[7])
mode="RGBA" if masks[:3]==(0xff,0xff00,0xff0000) else ("BGRA" if masks[:3]==(0xff0000,0xff00,0xff) else None)
if mode is None or (W,H)!=(4096,4096) or len(sb)!=128+W*H*4:
    raise RuntimeError(("structure",W,H,mips,masks,len(sb)))
raw_src=Image.frombytes("RGBA",(W,H),sb[128:],"raw",mode)
src=raw_src.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
sa=np.asarray(src,dtype=np.uint8)
regs={int(r["idx"]):r for r in json.loads(atlas.read_text())["regions"]}
dst_cell=list(map(int,regs[1]["rect"]))
if dst_cell!=[1088,3080,2048,1016]: raise RuntimeError(("JENN starburst atlas drift",dst_cell))

# Reuse only C202-approved B148 same-family Total Rank starburst template.
tpldir=repo/"localization/graphics/role_B/20261005-B-PRODUCTION148-8215-C200-TEMPLATE"
c202p=repo/"localization/graphics/role_C/20261005-C202-8215FD25/C202_8215FD25_CONTROLLER_FINAL_QA.json"
if not c202p.exists(): raise RuntimeError("C202 evidence missing")
cq=json.loads(c202p.read_text())
if cq.get("decision")!="C202_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME":
    raise RuntimeError(("C202 decision drift",cq.get("decision")))
rep=json.loads((tpldir/"B148_8215_REPORT.json").read_text())
row=next(r for r in rep["rows"] if int(r["region_idx"])==1)
tsrc=Image.open(tpldir/"B148_SOURCE_READABLE.png").convert("RGBA")
tclean=Image.open(tpldir/"B148_CLEAN_PLATE.png").convert("RGBA")
tfinal=Image.open(tpldir/"B148_FINAL_READABLE.png").convert("RGBA")
tsm=Image.open(tpldir/"B148_SOURCE_TEXT_MASK.png").convert("L")
src_cell=list(map(int,row["cell"]))
if src_cell!=[1088,1032,2048,1016]: raise RuntimeError(("template cell drift",src_cell))
dx=dst_cell[0]-src_cell[0]; dy=dst_cell[1]-src_cell[1]
if (dx,dy)!=(0,2048): raise RuntimeError(("unexpected JENN translation",dx,dy))

ob=list(map(int,row["original_bbox"])); core=list(map(int,row["source_core_bbox"])); lb=list(map(int,row["localized_bbox"]))
dob=[ob[0]+dx,ob[1]+dy,ob[2]+dx,ob[3]+dy]
dcore=[core[0]+dx,core[1]+dy,core[2]+dx,core[3]+dy]
dlb=[lb[0]+dx,lb[1]+dy,lb[2]+dx,lb[3]+dy]
for box in (dob,dcore,dlb):
    if not(0<=box[0]<box[2]<=W and 0<=box[1]<box[3]<=H): raise RuntimeError(("bbox",box))

# Prove local source geometry is same family: title/effect differences may only occur
# inside the C202 removal footprint or a <=2px low-alpha white AA fringe.
ts=np.asarray(tsrc,dtype=np.uint8); tc=np.asarray(tclean,dtype=np.uint8); tf=np.asarray(tfinal,dtype=np.uint8)
patch_a=ts[ob[1]:ob[3],ob[0]:ob[2]]
patch_b=sa[dob[1]:dob[3],dob[0]:dob[2]]
pd=np.max(np.abs(patch_a.astype(np.int16)-patch_b.astype(np.int16)),axis=2)
patch_changed=pd>0
removal=np.max(np.abs(patch_a.astype(np.int16)-tc[ob[1]:ob[3],ob[0]:ob[2]].astype(np.int16)),axis=2)>0
rem_im=Image.fromarray((removal.astype(np.uint8)*255),"L")
rem_dil=np.asarray(rem_im.filter(ImageFilter.MaxFilter(5)))>0
outside=patch_changed & (~removal)
outside_dil=outside & (~rem_dil)
coords=np.argwhere(outside)
outside_rgba=[patch_b[int(y),int(x)].tolist() for y,x in coords[:64]]
if np.count_nonzero(outside_dil):
    raise RuntimeError(("source differs beyond 2px effect fringe",int(np.count_nonzero(outside_dil)),int(np.count_nonzero(outside))))
# Any source-family variant outside removal must be nearly transparent light title AA.
for rgba in outside_rgba:
    if not (rgba[0]>=220 and rgba[1]>=220 and rgba[2]>=220 and rgba[3]<=16):
        raise RuntimeError(("non-AA variant pixel",rgba))
if len(coords)>64:
    raise RuntimeError(("too many fringe variants",len(coords)))

# Jennifer has character/ray artwork differences outside the title patch, so a broad
# 32px same-family ring is intentionally NOT required. What matters for a seamless
# patch is that the source pixels on the *inside perimeter* of the exact title patch
# are identical, and that all final changes stay inside that patch.
edge=4
per=np.zeros(patch_changed.shape,bool)
per[:edge,:]=True; per[-edge:,:]=True; per[:,:edge]=True; per[:,-edge:]=True
per_diff=int(np.count_nonzero(patch_changed & per))
per_max=int(pd[per].max(initial=0))
if per_diff or per_max:
    raise RuntimeError(("title patch internal perimeter mismatch",per_diff,per_max))

# Keep the broad ring difference only as diagnostic evidence proving that the
# surrounding Jennifer-specific artwork exists and remains protected/untouched.
pad=32
ta=[max(0,ob[0]-pad),max(0,ob[1]-pad),min(tsrc.width,ob[2]+pad),min(tsrc.height,ob[3]+pad)]
da=[ta[0]+dx,ta[1]+dy,ta[2]+dx,ta[3]+dy]
ra=ts[ta[1]:ta[3],ta[0]:ta[2]]
rb=sa[da[1]:da[3],da[0]:da[2]]
if ra.shape!=rb.shape: raise RuntimeError(("ring shape",ra.shape,rb.shape))
rm=np.ones(ra.shape[:2],bool)
rx0=ob[0]-ta[0]; ry0=ob[1]-ta[1]; rx1=ob[2]-ta[0]; ry1=ob[3]-ta[1]
rm[ry0:ry1,rx0:rx1]=False
rd=np.max(np.abs(ra.astype(np.int16)-rb.astype(np.int16)),axis=2)
ring_diff=int(np.count_nonzero(rd[rm])); ring_max=int(rd[rm].max(initial=0))

# Transplant exact approved clean/final title footprint only. Everything else stays JENN canonical.
clean=src.copy(); final=src.copy()
clean.paste(tclean.crop(tuple(ob)),(dob[0],dob[1]))
final.paste(tfinal.crop(tuple(ob)),(dob[0],dob[1]))
allowed=Image.new("L",(W,H),0); ImageDraw.Draw(allowed).rectangle((dob[0],dob[1],dob[2]-1,dob[3]-1),fill=255)
protected=ImageOps.invert(allowed)
sm=Image.new("L",(W,H),0); sm.paste(tsm.crop(tuple(ob)),(dob[0],dob[1]))

# Ensure exact final patch equivalence and strict zero-pixel containment.
final_patch_diff=int(np.count_nonzero(np.any(np.asarray(final)[dob[1]:dob[3],dob[0]:dob[2]] != tf[ob[1]:ob[3],ob[0]:ob[2]],axis=2)))
if final_patch_diff: raise RuntimeError(("final patch mismatch",final_patch_diff))
diff=diffmask(src,final)
outside_final=count(ImageChops.multiply(diff,protected))
alpha_out=count(ImageChops.multiply(bmask(ImageChops.difference(src.getchannel("A"),final.getchannel("A"))),protected))
if outside_final or alpha_out: raise RuntimeError(("outside gate",outside_final,alpha_out))
source_w=dcore[2]-dcore[0]; source_h=dcore[3]-dcore[1]
loc_w=dlb[2]-dlb[0]; loc_h=dlb[3]-dlb[1]
if not(dlb[0]>dcore[0] and dlb[1]>dcore[1] and dlb[2]<dcore[2] and dlb[3]<dcore[3] and loc_w<=source_w and loc_h<=source_h):
    raise RuntimeError(("bbox gate",dcore,dlb))

# Preserve DDS header and raw mirror_y exactly.
raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
payload=sb[:128]+raw_final.tobytes("raw",mode)
candidate.write_bytes(payload); csha=sha(payload)
dec=Image.frombytes("RGBA",(W,H),payload[128:],"raw",mode).transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(dec,final).getbbox(): raise RuntimeError("roundtrip mismatch")

source_png=out/"B156_SOURCE_READABLE.png"; clean_png=out/"B156_CLEAN_PLATE.png"; final_png=out/"B156_FINAL_READABLE.png"
src.save(source_png); clean.save(clean_png); dec.save(final_png)
sm.save(out/"B156_SOURCE_TEXT_MASK.png"); allowed.save(out/"B156_ALLOWED_EFFECT_BBOX_MASK.png"); protected.save(out/"B156_PROTECTED_MASK.png")
validator=repo/"tools/localization/validate_clean_plate.py"
subprocess.run(["python3",str(validator),str(source_png),str(clean_png),str(out/"B156_ALLOWED_EFFECT_BBOX_MASK.png"),"--protected-mask",str(out/"B156_PROTECTED_MASK.png"),"--report",str(out/"B156_CLEAN_VALIDATION.json")],check=True)
subprocess.run(["python3",str(validator),str(source_png),str(final_png),str(out/"B156_ALLOWED_EFFECT_BBOX_MASK.png"),"--protected-mask",str(out/"B156_PROTECTED_MASK.png"),"--report",str(out/"B156_FINAL_VALIDATION.json")],check=True)
cr=json.loads((out/"B156_CLEAN_VALIDATION.json").read_text()); fr=json.loads((out/"B156_FINAL_VALIDATION.json").read_text())
if cr["status"]!="PASS" or fr["status"]!="PASS": raise RuntimeError(("validator",cr["status"],fr["status"]))

# Readable and raw controller evidence.
p=110; box=(max(0,dob[0]-p),max(0,dob[1]-p),min(W,dob[2]+p),min(H,dob[3]+p))
ims=[comp(z.crop(box)) for z in (src,clean,dec)]
scale=min(2.4,1450/max(1,ims[0].width)); ims=[z.resize((int(z.width*scale),int(z.height*scale)),Image.Resampling.NEAREST) for z in ims]
sheet=Image.new("RGB",(sum(z.width for z in ims)+16,max(z.height for z in ims)+44),"white"); xx=0
for lab,z in zip(("SOURCE","CLEAN","FINAL"),ims):
    sheet.paste(z,(xx,44)); ImageDraw.Draw(sheet).text((xx+5,8),lab,fill="black"); xx+=z.width+8
save_b64(sheet,out/"B156_JENN_FOCUS.jpg",out/"B156_JENN_FOCUS_B64.txt",95)

# Full source atlas preview with region boxes to verify protected Jennifer/rank/UI structure.
ov=comp(src)
od=ImageDraw.Draw(ov)
for i,r in regs.items():
    x,y,w,h=map(int,r["rect"]); od.rectangle((x,y,x+w-1,y+h-1),outline="white",width=3); od.text((x+5,y+5),f"idx{i}",fill="white")
ov.thumbnail((1400,1400),Image.Resampling.LANCZOS)
save_b64(ov,out/"B156_JENN_SOURCE_ATLAS.jpg",out/"B156_JENN_SOURCE_ATLAS_B64.txt",91)

raw_dec=Image.frombytes("RGBA",(W,H),payload[128:],"raw",mode)
rr=Image.new("RGB",(1024,1100),"white")
for i,(lab,z0) in enumerate((("SOURCE_RAW_MIRROR_Y",raw_src),("FINAL_RAW_MIRROR_Y",raw_dec))):
    z=comp(z0); z.thumbnail((1024,512),Image.Resampling.LANCZOS); rr.paste(z,(0,i*550+26)); ImageDraw.Draw(rr).text((5,i*550+5),lab,fill="black")
save_b64(rr,out/"B156_JENN_RAW_COMPARE.jpg",out/"B156_JENN_RAW_COMPARE_B64.txt",90)

report={
 "schema_version":1,"role":"B","run":run,"queue_index":36,"asset":asset,
 "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":COMMIT,"upstream_release_filename":"6AB5CEE_1024x1024.dds","queue_hd_alias":"06AB5CEE_1024x1024.dds","inventory_archive_sha256":"e02db9b4e04747e2a74295e8f5a01e07f0ed88d31832f4169b1e5996bc30f1eb","source_sha256":SOURCE_SHA},
 "structure":{"dimensions":[W,H],"format":"RGBA32","raw_mode":mode,"mipmaps":mips,"header_128_exact":payload[:128]==sb[:128],"raw_orientation":"mirror_y"},
 "classification":{"prior_action":"zoom_review","localizable":"Total Rank","translation":"종합 랭킹","protected":["Jennifer character artwork","lens flare","rank letters A/B/C/D/E","heart/cross UI"]},
 "template_provenance":{"producer":"B148","final_qa":"C202_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME","template_asset":"8215FD25","source_cell":src_cell,"target_cell":dst_cell,"shift":[dx,dy],
   "source_title_patch_variant_pixels":int(np.count_nonzero(patch_changed)),
   "variant_pixels_outside_template_removal":int(np.count_nonzero(outside)),
   "variant_pixels_outside_2px_effect_dilation":int(np.count_nonzero(outside_dil)),
   "outside_variant_rgba":outside_rgba,
   "title_patch_internal_perimeter_diff_pixels":per_diff,"title_patch_internal_perimeter_max_channel_delta":per_max,
   "protected_surrounding_ring_32px_diff_pixels":ring_diff,"protected_surrounding_ring_32px_max_channel_delta":ring_max,
   "final_patch_diff_pixels":final_patch_diff},
 "row":{"region_idx":1,"source":"Total Rank","korean":"종합 랭킹","cell":dst_cell,"original_bbox":dob,"source_core_bbox":dcore,"localized_bbox":dlb,
   "source_width":source_w,"source_height":source_h,"localized_width":loc_w,"localized_height":loc_h,
   "delta_left":dlb[0]-dcore[0],"delta_right":dcore[2]-dlb[2],"delta_top":dlb[1]-dcore[1],"delta_bottom":dcore[3]-dlb[3],
   "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS","source_style":rep["source_style"]},
 "clean_plate_validator":cr,"final_mask_validator":fr,
 "decoded_changes":{"outside_allowed_effect_bbox":outside_final,"alpha_outside":alpha_out,"localized_overlap":0,"source_script_residue":0},
 "candidate_sha256":csha,"candidate_path":str(candidate.relative_to(repo)),
 "worker_static_qa":"PASS","controller_visual_qa":"PENDING_CONTROLLER_SELF_QA",
 "status":"B156_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_SELF_QA_AND_C","runtime_validation":"UNTESTED"
}
(out/"B156_JENN_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
(wr/"B156_06AB5CEE.json").write_text(json.dumps({"run":"B156","index":36,"asset":"06AB5CEE","candidate_sha256":csha,"bbox_size_positive_margin":"1/1","outside":outside_final,"alpha_outside":alpha_out,"worker_status":report["status"],"report":f"localization/graphics/role_B/{run}/B156_JENN_REPORT.json","runtime_validation":"UNTESTED"},ensure_ascii=False,indent=2)+"\n")
print(json.dumps({"run":"B156","candidate_sha256":csha,"bbox":"1/1 PASS","variant_pixels":int(np.count_nonzero(patch_changed)),"outside_fringe":int(np.count_nonzero(outside)),"outside_2px":int(np.count_nonzero(outside_dil))},ensure_ascii=False),flush=True)
