#!/usr/bin/env python3
import os, json, hashlib, struct, subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageChops, ImageOps

if os.environ.get("OUTRUN_CPU_WORKER")!="github-actions" or os.environ.get("OUTRUN_CPU_ROLE")!="A":
    raise SystemExit("GitHub-hosted role A required")

repo=Path.cwd()
run="20261004-A-RECOVERY10"
out=repo/"localization/graphics/role_A"/run
out.mkdir(parents=True,exist_ok=True)
worker_out=repo/"localization/graphics/worker_results"
worker_out.mkdir(parents=True,exist_ok=True)

asset_rel="textures/load/spr_sprani_selector_cvt_Exst/C075FB49_512x512.dds"
source=repo/"localization/graphics/hd_source/OR2-HD-GUI-v0.25.10a"/asset_rel
candidate=repo/"localization/graphics/hd_candidates"/asset_rel
candidate.parent.mkdir(parents=True,exist_ok=True)
c_clean_path=repo/"localization/graphics/role_C/20261004-C-OVERLAP05/C075FB49_FULL_CLEAN.png"
c_report_path=repo/"localization/graphics/role_C/20261004-C-OVERLAP05/C_OVERLAP05_C075FB49_REPORT.json"
validator=repo/"tools/localization/validate_clean_plate.py"

SOURCE_SHA="a8942f076b9c3d8cddd62ba39c84a3b3abea72b2ba19a61a21e9a2bd6f8e8036"
FALLBACK_SHA="1c46037543e2e9260bf36c081884fd103543256df1ded8db95b969ee9c654a5c"
C_WORKER_COMMIT="ddfc5afbff650bfefe6e7de55d39f20a1f109450"
C_REJECTED_SHA="3e950422775def2508ea42118f41c7a1f7463e2a7106cdcfcfb907b705890c91"

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def count(mask): return sum(mask.histogram()[1:])
def changed_mask(a,b):
    d=ImageChops.difference(a,b)
    bands=d.split(); m=bands[0]
    for z in bands[1:]: m=ImageChops.lighter(m,z)
    return m.point(lambda v:255 if v else 0)
def binary_alpha(im): return im.getchannel("A").point(lambda v:255 if v else 0)

if sha(source)!=SOURCE_SHA: raise RuntimeError(("source SHA",sha(source),SOURCE_SHA))

sb=source.read_bytes()
if sb[:4]!=b"DDS ": raise RuntimeError("not DDS")
H,W,pitch,depth,mips=struct.unpack_from("<5I",sb,12)
pf=struct.unpack_from("<8I",sb,76)
if (W,H,pitch,depth,mips)!=(2048,2048,8192,1,1): raise RuntimeError((W,H,pitch,depth,mips))
if pf[1:]!=(65,0,32,0xff,0xff00,0xff0000,0xff000000): raise RuntimeError(("pixel format",pf))
if len(sb)!=128+W*H*4: raise RuntimeError(("byte size",len(sb)))
src_raw=Image.frombytes("RGBA",(W,H),sb[128:],"raw","RGBA")
src=src_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)

# Recover the C machine candidate that had safe 17/17 placement but a bad clean plate.
tmp=Path("/tmp/C075FB49_C_OVERLAP05_REJECTED.dds")
tmp.write_bytes(subprocess.check_output(["git","show",f"{C_WORKER_COMMIT}:localization/graphics/hd_candidates/{asset_rel}"]))
if sha(tmp)!=C_REJECTED_SHA: raise RuntimeError(("C rejected SHA",sha(tmp),C_REJECTED_SHA))
cb=tmp.read_bytes()
if cb[:128]!=sb[:128]: raise RuntimeError("C candidate header mismatch")
c_raw=Image.frombytes("RGBA",(W,H),cb[128:],"raw","RGBA")
c_new=c_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
c_clean=Image.open(c_clean_path).convert("RGBA")
if c_clean.size!=(W,H): raise RuntimeError(("C clean size",c_clean.size))
c_report=json.loads(c_report_path.read_text(encoding="utf-8"))
rows=list(c_report["rows"])
if len(rows)!=17: raise RuntimeError(("C row count",len(rows)))

# C visual failure is confined to the dense top localized text group. Restore that whole
# source area from canonical HD first, then remove source glyphs from their own atlas cells.
top_keys={"long_distance","keep_passing","drift","maximum_speed","transmission","dont_crash","go_gate","for_experts"}
top_cells={
 "long_distance":[568,24,1104,128],
 "keep_passing":[0,128,504,248],
 "drift":[504,128,704,248],
 "maximum_speed":[704,144,1272,248],
 "transmission":[0,248,568,368],
 "dont_crash":[568,248,1072,368],
 "go_gate":[1072,248,1576,368],
 "for_experts":[1576,264,1984,368],
}
preserved_cells={
 "OutRun2SP":[1104,24,1592,128],
 "OutRun2":[1592,24,2048,128],
 "1P":[1840,144,1992,248],
}

# Allowed region is the exact source glyph/effect bbox union recorded by C.
allowed=Image.new("L",(W,H),0); ad=ImageDraw.Draw(allowed)
row_by_key={r["key"]:r for r in rows}
for r in rows:
    x1,y1,x2,y2=map(int,r["source_bbox"])
    ad.rectangle((x1,y1,x2-1,y2-1),fill=255)

# Start from C clean because bottom nine regions already passed controller visual review.
# Remove all C top cleanup artifacts by restoring canonical source across the top source-bbox union.
clean=c_clean.copy()
# Replace the complete dense text band with canonical HD source before any removal.
# C's failed clean introduced semi-transparent reconstruction strips outside its row bboxes;
# restoring the full atlas band removes those artifacts without touching the next model-name row.
top_restore_rect=(0,0,W,368)
clean.paste(src.crop(top_restore_rect),(0,0))

# Exact top source-text mask: only nonzero source alpha inside each target's own text-only atlas cell.
top_source_mask=Image.new("L",(W,H),0)
for key,cell in top_cells.items():
    x1,y1,x2,y2=cell
    local=src.crop(cell).getchannel("A").point(lambda v:255 if v else 0)
    top_source_mask.paste(ImageChops.lighter(top_source_mask.crop(cell),local),(x1,y1))

# Every top source pixel selected for removal must be inside the policy-allowed bbox union.
top_mask_out=count(ImageChops.multiply(top_source_mask,ImageOps.invert(allowed)))
if top_mask_out!=0: raise RuntimeError(("top source mask outside allowed",top_mask_out))

# Clear only exact visible source glyph/effect pixels; hidden transparent RGB remains untouched.
clear_rgba=Image.new("RGBA",(W,H),(0,0,0,0))
clean.paste(clear_rgba,(0,0),top_source_mask)

# Protect all visible canonical source pixels outside permitted bboxes AND the three preserved source labels.
src_visible=binary_alpha(src)
protected=ImageChops.multiply(src_visible,ImageOps.invert(allowed))
for name,cell in preserved_cells.items():
    x1,y1,x2,y2=cell
    local=binary_alpha(src.crop(cell))
    protected.paste(ImageChops.lighter(protected.crop(cell),local),(x1,y1))

# Preserved source labels must be byte/pixel identical after clean reconstruction.
for name,cell in preserved_cells.items():
    if ImageChops.difference(src.crop(cell),clean.crop(cell)).getbbox() is not None:
        raise RuntimeError(("clean changed preserved source label",name))

# Clean gate: all clean changes must stay inside exact allowed bboxes and protected pixels remain exact.
src_png=out/"C075FB49_SOURCE_READABLE.png"
clean_png=out/"C075FB49_CLEAN_PLATE.png"
allowed_png=out/"C075FB49_ALLOWED_TEXT_REGION_MASK.png"
protected_png=out/"C075FB49_PROTECTED_MASK.png"
top_mask_png=out/"C075FB49_TOP_SOURCE_TEXT_MASK.png"
src.save(src_png); clean.save(clean_png); allowed.save(allowed_png); protected.save(protected_png); top_source_mask.save(top_mask_png)
subprocess.run([
 "python3",str(validator),str(src_png),str(clean_png),str(allowed_png),
 "--protected-mask",str(protected_png),
 "--report",str(out/"A_RECOVERY10_CLEAN_PLATE_VALIDATION.json")
],check=True)
clean_rep=json.loads((out/"A_RECOVERY10_CLEAN_PLATE_VALIDATION.json").read_text())
if clean_rep["status"]!="PASS": raise RuntimeError(("clean validator",clean_rep))

# Source residue in the rebuilt top group is impossible by construction before Korean compositing.
top_clean_residue=count(ImageChops.multiply(binary_alpha(clean),top_source_mask))
if top_clean_residue!=0: raise RuntimeError(("top clean residue",top_clean_residue))

# Extract only the Korean/effect delta from C's safely placed candidate relative to C's clean,
# then composite those deltas over the corrected clean plate. This preserves C's 17/17
# zero-overlap placement while discarding all source residue that was shared by C clean+candidate.
final=clean.copy()
localized_masks={}
rows_out=[]
for r in rows:
    key=r["key"]; nb=list(map(int,r["new_effect_bbox"]))
    x1,y1,x2,y2=nb
    cc=c_clean.crop(nb); cn=c_new.crop(nb)
    lm=changed_mask(cc,cn)
    if not lm.getbbox(): raise RuntimeError(("empty localized delta",key))
    shift_y=12 if key=="for_experts" else 0
    dx,dy=x1,y1+shift_y
    global_m=Image.new("L",(W,H),0); global_m.paste(lm,(dx,dy))
    localized_masks[key]=global_m
    final.paste(cn,(dx,dy),lm)
    lb=lm.getbbox()
    loc=[dx+lb[0],dy+lb[1],dx+lb[2],dy+lb[3]]
    ob=list(map(int,r["source_bbox"]))
    ok=loc[0]>=ob[0] and loc[1]>=ob[1] and loc[2]<=ob[2] and loc[3]<=ob[3]
    size_ok=(loc[2]-loc[0])<=(ob[2]-ob[0]) and (loc[3]-loc[1])<=(ob[3]-ob[1])
    pos=loc[0]>ob[0] and loc[1]>ob[1] and loc[2]<ob[2] and loc[3]<ob[3]
    rows_out.append({
      "key":key,"source":r["source"],"korean":r["korean"],
      "original_bbox":ob,"localized_bbox":loc,
      "delta_left":loc[0]-ob[0],"delta_right":ob[2]-loc[2],
      "delta_top":loc[1]-ob[1],"delta_bottom":ob[3]-loc[3],
      "source_width":ob[2]-ob[0],"source_height":ob[3]-ob[1],
      "localized_width":loc[2]-loc[0],"localized_height":loc[3]-loc[1],
      "containment":"PASS" if ok else "FAIL","size_ceiling":"PASS" if size_ok else "FAIL",
      "positive_margin":"PASS" if pos else "EDGE_TOUCH_OR_FAIL",
      "raw_original_bbox":[ob[0],H-ob[3],ob[2],H-ob[1]],
      "raw_localized_bbox":[loc[0],H-loc[3],loc[2],H-loc[1]],
      "raw_containment":"PASS" if ok else "FAIL",
      "construction":"C_OVERLAP05 localized raster delta composited onto A_RECOVERY10 corrected clean plate; For Experts shifted +12px Y to preserve 1P source label",
      "placement_adjustment":{"shift_y":shift_y},
      "rework_status":"A_RECOVERY10_TOP_CLEAN_REBUILD" if key in top_keys else "A_RECOVERY10_C_PLACEMENT_REUSED"
    })

# Pairwise localized-mask overlap must be zero for every physical occurrence.
pair_overlap={}
keys=list(localized_masks)
for i,k1 in enumerate(keys):
    for k2 in keys[i+1:]:
        n=count(ImageChops.multiply(localized_masks[k1],localized_masks[k2]))
        if n: pair_overlap[f"{k1}|{k2}"]=n
pair_overlap_total=sum(pair_overlap.values())

# Protected source pixels and preserved source labels must remain unchanged in FINAL.
diff=changed_mask(src,final)
outside=count(ImageChops.multiply(diff,ImageOps.invert(allowed)))
protected_changed=count(ImageChops.multiply(diff,protected))
alpha_delta=ImageChops.difference(src.getchannel("A"),final.getchannel("A")).point(lambda v:255 if v else 0)
alpha_outside=count(ImageChops.multiply(alpha_delta,ImageOps.invert(allowed)))
preserved_diffs={}
for name,cell in preserved_cells.items():
    preserved_diffs[name]=count(changed_mask(src.crop(cell),final.crop(cell)))

# Final candidate validator.
final_png=out/"C075FB49_FINAL_READABLE.png"; final.save(final_png)
subprocess.run([
 "python3",str(validator),str(src_png),str(final_png),str(allowed_png),
 "--protected-mask",str(protected_png),
 "--report",str(out/"A_RECOVERY10_FINAL_MASK_VALIDATION.json")
],check=True)
final_rep=json.loads((out/"A_RECOVERY10_FINAL_MASK_VALIDATION.json").read_text())
if final_rep["status"]!="PASS": raise RuntimeError(("final validator",final_rep))

# Exact RGBA32 encode with source header and mirror-Y storage.
raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
outb=sb[:128]+raw_final.tobytes("raw","RGBA")
candidate.write_bytes(outb)
candidate_sha=sha(candidate)
if candidate.read_bytes()[:128]!=sb[:128]: raise RuntimeError("header changed")
decoded_raw=Image.frombytes("RGBA",(W,H),candidate.read_bytes()[128:],"raw","RGBA")
decoded=decoded_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(decoded,final).getbbox() is not None: raise RuntimeError("RGBA roundtrip mismatch")

all_bbox=all(r["containment"]=="PASS" and r["raw_containment"]=="PASS" for r in rows_out)
all_size=all(r["size_ceiling"]=="PASS" for r in rows_out)
all_positive=all(r["positive_margin"]=="PASS" for r in rows_out)

# Evidence: full source/rejected-clean/rejected-new/final and high-resolution top-group crop.
def gray(im):
    bg=Image.new("RGBA",im.size,(72,72,72,255)); bg.alpha_composite(im); return bg.convert("RGB")
thumb=(1024,1024)
panels=[src,c_clean,c_new,decoded]
sheet=Image.new("RGB",(thumb[0]*2,thumb[1]*2),(60,60,60))
for i,p in enumerate(panels):
    sheet.paste(gray(p).resize(thumb,Image.Resampling.LANCZOS),((i%2)*thumb[0],(i//2)*thumb[1]))
sheet.save(out/"A_RECOVERY10_SOURCE_CLEAN_REJECTED_FINAL.jpg",quality=94)

crop=(0,0,2048,440)
top_sheet=Image.new("RGB",(2048,440*4),(60,60,60))
for i,p in enumerate(panels):
    top_sheet.paste(gray(p.crop(crop)),(0,i*440))
top_sheet.save(out/"A_RECOVERY10_TOP_SOURCE_CLEAN_REJECTED_FINAL.jpg",quality=95)
gray(decoded_raw).resize(thumb,Image.Resampling.LANCZOS).save(out/"A_RECOVERY10_FINAL_RAW_GRAY.jpg",quality=94)

status_ok=(
 clean_rep["status"]=="PASS" and final_rep["status"]=="PASS" and
 all_bbox and all_size and all_positive and pair_overlap_total==0 and
 outside==0 and protected_changed==0 and alpha_outside==0 and
 top_clean_residue==0 and all(v==0 for v in preserved_diffs.values())
)
report={
 "schema_version":1,"role":"A","run":run,"worker":os.environ.get("OUTRUN_CPU_WORKER"),
 "base_head":os.environ.get("GITHUB_SHA"),"index":111,"asset":asset_rel,
 "source_sha256":SOURCE_SHA,"fallback_before_sha256":FALLBACK_SHA,
 "c_overlap05_rejected_sha256":C_REJECTED_SHA,"candidate_sha256":candidate_sha,
 "candidate_path":str(candidate.relative_to(repo)),
 "structure":{"dimensions":[W,H],"format":"RGBA32","pitch":pitch,"mipmaps":mips,"header_128_exact":True,"raw_orientation":"mirror_y"},
 "method":"canonical HD restore for dense top group -> exact source-alpha removal inside 8 target atlas cells -> reuse C_OVERLAP05 17/17 zero-overlap localized raster deltas -> preserve visually accepted bottom C clean reconstruction -> exact RGBA32 encode",
 "top_rebuilt_keys":sorted(top_keys),"top_restore_rect":list(top_restore_rect),
 "preserved_source_labels":preserved_cells,
 "preserved_source_label_pixel_diffs":preserved_diffs,
 "clean_plate_validator":clean_rep,"final_mask_validator":final_rep,
 "top_source_text_mask_pixels":count(top_source_mask),"top_clean_source_residue_pixels":top_clean_residue,
 "localized_pair_overlap_pixels":pair_overlap_total,"localized_pair_overlaps":pair_overlap,
 "decoded_changes":{"changed_pixels_total":count(diff),"changed_pixels_outside_original_bboxes":outside,"alpha_changed_pixels_outside_original_bboxes":alpha_outside,"protected_visible_pixels_changed":protected_changed},
 "rows":rows_out,
 "all_17_readable_and_raw_bbox_pass":all_bbox,"all_17_size_ceiling_pass":all_size,"all_17_positive_margin":all_positive,
 "controller_visual_qa":"PENDING_CONTROLLER_REVIEW","runtime_validation":"UNTESTED",
 "status":"A_RECOVERY10_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_VISUAL_QA" if status_ok else "A_RECOVERY10_WORKER_REWORK_REQUIRED"
}
(out/"A_RECOVERY10_C075FB49_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
summary={
 "run":run,"asset":"C075FB49","index":111,"source_sha256":SOURCE_SHA,"candidate_sha256":candidate_sha,
 "top_rebuilt_count":len(top_keys),"target_occurrences":17,
 "bbox_pass":"17/17" if all_bbox else "FAIL","size_ceiling":"17/17" if all_size else "FAIL",
 "positive_margin":"17/17" if all_positive else "FAIL",
 "clean_plate_validator":clean_rep["status"],"final_mask_validator":final_rep["status"],
 "top_clean_source_residue_pixels":top_clean_residue,"localized_pair_overlap_pixels":pair_overlap_total,
 "changed_pixels_outside_original_bboxes":outside,"alpha_changed_pixels_outside_original_bboxes":alpha_outside,
 "protected_visible_pixels_changed":protected_changed,"preserved_source_label_pixel_diffs":preserved_diffs,
 "worker_status":report["status"],"runtime_validation":"UNTESTED",
 "report":"localization/graphics/role_A/20261004-A-RECOVERY10/A_RECOVERY10_C075FB49_REPORT.json"
}
(worker_out/"A_RECOVERY10_C075FB49.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False,indent=2))
if not status_ok: raise SystemExit(2)
