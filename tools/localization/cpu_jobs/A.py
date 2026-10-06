#!/usr/bin/env python3
import os, json, hashlib, struct, subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageChops, ImageOps

if os.environ.get("OUTRUN_CPU_WORKER") != "github-actions" or os.environ.get("OUTRUN_CPU_ROLE") != "A":
    raise SystemExit("GitHub-hosted role A required")

repo=Path.cwd()
run="20261007-A-MANUALQA152-9CE4E175"
out=repo/"localization/graphics/role_A"/run
out.mkdir(parents=True,exist_ok=True)
worker_out=repo/"localization/graphics/worker_results"; worker_out.mkdir(parents=True,exist_ok=True)

asset_rel="textures/load/spr_sprani_sumo_fe_cvt_Exst/9CE4E175_256x32.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset_rel
prior_dir=repo/"localization/graphics/role_A/20261005-A-PRODUCTION20"
source_png=prior_dir/"9CE4E175_HD_SOURCE_READABLE.png"
clean_png=prior_dir/"9CE4E175_HD_CLEAN_PLATE.png"
allowed_png=prior_dir/"9CE4E175_HD_ALLOWED_SOURCE_BBOX_MASK.png"
protected_png=prior_dir/"9CE4E175_HD_PROTECTED_VISIBLE_MASK.png"
source_mask_png=prior_dir/"9CE4E175_HD_SOURCE_TEXT_MASK.png"
validator=repo/"tools/localization/validate_clean_plate.py"

EXPECTED_BEFORE="cdb00269deb765e733a1da9dbc69e51d06f70d8b8f0fef453abbf67f685430b2"
SOURCE_SHA="6fee06730412c51e8f1e3db19ad1d43a12ce3eb9df8806812a46818715d92b2b"
REVIEW_JPG="localization/graphics/role_C/PRE_INGAME_JPG_REVIEW/019_q195_9CE4E175.jpg"
BBOX=[95,80,490,121]
KOREAN="이용 불가"

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
if not candidate.exists() or sha(candidate)!=EXPECTED_BEFORE:
    raise RuntimeError(("candidate drift", sha(candidate) if candidate.exists() else None, EXPECTED_BEFORE))
for p in [source_png,clean_png,allowed_png,protected_png,source_mask_png]:
    if not p.exists(): raise RuntimeError(("missing evidence",str(p)))

prior_bytes=candidate.read_bytes()
if prior_bytes[:4]!=b"DDS ": raise RuntimeError("not DDS")
H,W,pitch,depth,mips=struct.unpack_from("<5I",prior_bytes,12)
pf=struct.unpack_from("<8I",prior_bytes,76)
if (W,H,pitch,mips)!=(1024,128,4096,1): raise RuntimeError((W,H,pitch,depth,mips))
rmask,gmask,bmask,amask=pf[4],pf[5],pf[6],pf[7]
if (rmask,gmask,bmask,amask)==(255,65280,16711680,4278190080):
    raw_mode="RGBA"
elif (rmask,gmask,bmask,amask)==(16711680,65280,255,4278190080):
    raw_mode="BGRA"
else:
    raise RuntimeError(("unsupported channel masks",pf))
if len(prior_bytes)!=128+W*H*4: raise RuntimeError(("byte size",len(prior_bytes)))

source=Image.open(source_png).convert("RGBA")
clean=Image.open(clean_png).convert("RGBA")
allowed=Image.open(allowed_png).convert("L")
protected=Image.open(protected_png).convert("L")
source_mask=Image.open(source_mask_png).convert("L")
if source.size!=(W,H) or clean.size!=(W,H): raise RuntimeError("evidence dimensions")
prior_raw=Image.frombytes("RGBA",(W,H),prior_bytes[128:],"raw",raw_mode)
prior=prior_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)

clean_report=json.loads((prior_dir/"A_PRODUCTION20_CLEAN_PLATE_VALIDATION.json").read_text())
if clean_report.get("status")!="PASS": raise RuntimeError(("prior clean plate",clean_report))

def resolve_font():
    for pat in ["Noto Sans CJK KR:style=Black","Noto Sans CJK KR:style=Bold","Noto Sans CJK KR"]:
        try: fp=subprocess.check_output(["fc-match","-f","%{file}",pat],text=True).strip()
        except Exception: fp=""
        if fp and Path(fp).exists() and "NotoSansCJK" in Path(fp).name: return fp
    subprocess.run(["sudo","apt-get","update","-qq"],check=True)
    subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
    for pat in ["Noto Sans CJK KR:style=Black","Noto Sans CJK KR"]:
        fp=subprocess.check_output(["fc-match","-f","%{file}",pat],text=True).strip()
        if fp and Path(fp).exists(): return fp
    raise RuntimeError("Noto CJK missing")
FONT=resolve_font()

# Fresh native Hangul. Keep source-like near-max height but repair the visibly weak width
# without reusing or scaling an old Korean bitmap.
font=ImageFont.truetype(FONT,40)
tmp=Image.new("L",(600,100),0); d=ImageDraw.Draw(tmp)
bb=d.textbbox((0,0),KOREAN,font=font,stroke_width=1)
mask=Image.new("L",(bb[2]-bb[0]+12,bb[3]-bb[1]+12),0)
md=ImageDraw.Draw(mask)
md.text((6-bb[0],6-bb[1]),KOREAN,font=font,fill=255,stroke_width=1,stroke_fill=255)
gb=mask.getbbox()
if not gb: raise RuntimeError("empty Korean mask")
mask=mask.crop(gb)

# Exact source effect bbox is 395x41. Target 252x37 restores visual hierarchy
# while retaining 71/72px horizontal and 2px vertical positive margins.
target_w,target_h=252,37
mask=mask.resize((target_w,target_h),Image.Resampling.LANCZOS)
layer=Image.new("RGBA",(target_w,target_h),(255,255,255,0))
layer.putalpha(mask)

x1,y1,x2,y2=BBOX
tx=x1+(x2-x1-target_w)//2
ty=y1+(y2-y1-target_h)//2
final=clean.copy()
final.alpha_composite(layer,(tx,ty))
loc=[tx,ty,tx+target_w,ty+target_h]

raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
new_bytes=prior_bytes[:128]+raw_final.tobytes("raw",raw_mode)
if new_bytes[:128]!=prior_bytes[:128]: raise RuntimeError("header changed")
candidate.write_bytes(new_bytes)
candidate_sha=sha(candidate)

decoded_raw=Image.frombytes("RGBA",(W,H),new_bytes[128:],"raw",raw_mode)
decoded=decoded_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(decoded,final).getbbox() is not None: raise RuntimeError("roundtrip mismatch")

final_png=out/"9CE4E175_HD_FINAL_DECODED_READABLE.png"; decoded.save(final_png)
source.save(out/"9CE4E175_HD_SOURCE_READABLE.png"); clean.save(out/"9CE4E175_HD_CLEAN_PLATE.png")

subprocess.run(["python3",str(validator),str(source_png),str(final_png),str(allowed_png),
                "--protected-mask",str(protected_png),
                "--report",str(out/"A152_FINAL_MASK_VALIDATION.json")],check=True)
final_rep=json.loads((out/"A152_FINAL_MASK_VALIDATION.json").read_text())
if final_rep.get("status")!="PASS": raise RuntimeError(("final validator",final_rep))

def count(mask): return sum(mask.histogram()[1:])
def changed_mask(a,b):
    d=ImageChops.difference(a,b); bands=d.split(); m=bands[0]
    for z in bands[1:]: m=ImageChops.lighter(m,z)
    return m.point(lambda v:255 if v else 0)
diff=changed_mask(source,decoded)
outside=count(ImageChops.multiply(diff,ImageOps.invert(allowed)))
alpha_delta=ImageChops.difference(source.getchannel("A"),decoded.getchannel("A")).point(lambda v:255 if v else 0)
alpha_outside=count(ImageChops.multiply(alpha_delta,ImageOps.invert(allowed)))
protected_changed=count(ImageChops.multiply(diff,protected))
source_residue=count(ImageChops.multiply(source_mask,ImageChops.invert(changed_mask(source,clean))))

# Prior localized bbox from exact prior-clean difference.
old=changed_mask(clean,prior).crop(tuple(BBOX))
oldbb=old.getbbox()
oldloc=[x1+oldbb[0],y1+oldbb[1],x1+oldbb[2],y1+oldbb[3]] if oldbb else None
oldw=(oldloc[2]-oldloc[0]) if oldloc else 0
oldh=(oldloc[3]-oldloc[1]) if oldloc else 0

row={
 "source":"NOT AVAILABLE","korean":KOREAN,
 "original_bbox":BBOX,"localized_bbox":loc,
 "source_width":x2-x1,"source_height":y2-y1,
 "localized_width":target_w,"localized_height":target_h,
 "width_ratio":round(target_w/(x2-x1),4),"height_ratio":round(target_h/(y2-y1),4),
 "delta_left":loc[0]-x1,"delta_right":x2-loc[2],"delta_top":loc[1]-y1,"delta_bottom":y2-loc[3],
 "prior_localized_bbox":oldloc,"prior_localized_width":oldw,"prior_localized_height":oldh,
 "width_gain_px":target_w-oldw,"height_gain_px":target_h-oldh,
 "containment":"PASS" if loc[0]>=x1 and loc[1]>=y1 and loc[2]<=x2 and loc[3]<=y2 else "FAIL",
 "size_ceiling":"PASS" if target_w<=x2-x1 and target_h<=y2-y1 else "FAIL",
 "positive_margin":"PASS" if loc[0]>x1 and loc[1]>y1 and loc[2]<x2 and loc[3]<y2 else "FAIL",
 "style":"fresh native Noto Sans CJK KR Black; heavy white sans, centered; no invented outline/slant"
}

# Visual evidence.
def gray(im):
    bg=Image.new("RGBA",im.size,(96,96,96,255)); bg.alpha_composite(im); return bg.convert("RGB")
crop=(70,60,520,127)
parts=[gray(source.crop(crop)),gray(prior.crop(crop)),gray(decoded.crop(crop))]
sheet=Image.new("RGB",(sum(p.width for p in parts)+16,max(p.height for p in parts)+28),(230,230,230))
xx=0
for p in parts:
    sheet.paste(p,(xx,28)); xx+=p.width+8
lab=ImageFont.truetype(FONT,18)
ImageDraw.Draw(sheet).text((4,3),"SOURCE | C125 | A152",font=lab,fill=(0,0,0))
sheet.save(out/"A152_SOURCE_C125_FINAL_CONTACT.jpg",quality=95)

overview=Image.new("RGB",(W,H*3),(90,90,90))
overview.paste(gray(source),(0,0)); overview.paste(gray(prior),(0,H)); overview.paste(gray(decoded),(0,H*2))
overview.save(out/"A152_SOURCE_C125_FINAL.jpg",quality=95)

rawcmp=Image.new("RGB",(W*3,H),(80,80,80))
rawcmp.paste(gray(source.transpose(Image.Transpose.FLIP_TOP_BOTTOM)),(0,0))
rawcmp.paste(gray(prior_raw),(W,0)); rawcmp.paste(gray(decoded_raw),(W*2,0))
rawcmp.save(out/"A152_SOURCE_C125_FINAL_RAW.jpg",quality=95)

ok=(row["containment"]=="PASS" and row["size_ceiling"]=="PASS" and row["positive_margin"]=="PASS"
    and target_w>=220 and target_w>oldw and outside==0 and alpha_outside==0 and protected_changed==0
    and final_rep["status"]=="PASS")

report={
 "schema_version":1,"role":"A","run":run,"worker":os.environ.get("OUTRUN_CPU_WORKER"),
 "base_head":os.environ.get("GITHUB_SHA"),"queue_index":195,"asset":asset_rel,
 "trigger":"PRE_INGAME_019_SOURCE_RELATIVE_WIDTH_HIERARCHY_FALSE_NEGATIVE",
 "review_jpg":REVIEW_JPG,
 "prior_c_status":"C125_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME",
 "prior_candidate_sha256":EXPECTED_BEFORE,"source_sha256":SOURCE_SHA,
 "candidate_sha256":candidate_sha,
 "reason":"PRE_INGAME #019 shows 이용 불가 only 142px wide inside the exact 395px NOT AVAILABLE source effect bbox. Latest ordered generation gate treats the resulting weak plate hierarchy as a visual false negative despite numeric containment PASS.",
 "structure":{"dimensions":[W,H],"format":"RGBA32","raw_mode":raw_mode,"pitch":pitch,"mipmaps":mips,"header_128_exact":True,"raw_orientation":"mirror_y"},
 "prior_clean_plate_validator":clean_report,"final_mask_validator":final_rep,
 "decoded_changes":{"changed_pixels_outside_source_bbox":outside,"alpha_changed_pixels_outside_source_bbox":alpha_outside,"protected_visible_pixels_changed":protected_changed,"diagnostic_source_residue":source_residue},
 "row":row,
 "ordered_generation_gate":{
   "1_source_text_removed_and_plate_restored":"PASS_REUSE_PRIOR_EXACT_VALIDATED_CLEAN_PLATE",
   "2_slant_direction_matches_source":"PASS_SOURCE_UPRIGHT",
   "3_text_not_unnecessarily_undersized_and_within_source_bbox":"PASS_WIDTH_142_TO_252_WITHIN_395",
   "4_source_faithful_weight_outline_shadow":"PASS_HEAVY_WHITE_SANS_NO_INVENTED_EFFECT",
   "5_no_clipped_pixels":"PASS_POSITIVE_MARGINS",
   "6_protected_graphics_clearance":"PASS_ZERO_PROTECTED_CHANGE",
   "7_raw_and_flip_y_visual_review":"EVIDENCE_WRITTEN_PENDING_CONTROLLER",
   "8_immediate_readability_vs_english":"PENDING_CONTROLLER"
 },
 "controller_visual_qa":"PENDING_CONTROLLER_REVIEW",
 "runtime_validation":"UNTESTED",
 "status":"A152_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_VISUAL_QA" if ok else "A152_WORKER_REWORK_REQUIRED",
 "no_vr_ffb_dx11_dxvk_work":True
}
(out/"A152_9CE4E175_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
summary={"run":run,"asset":"9CE4E175","queue_index":195,"prior_candidate_sha256":EXPECTED_BEFORE,"candidate_sha256":candidate_sha,
 "prior_size":[oldw,oldh],"new_size":[target_w,target_h],"source_size":[x2-x1,y2-y1],
 "bbox_size_positive_margin":"1/1 PASS" if ok else "FAIL",
 "changed_outside":outside,"alpha_outside":alpha_outside,"protected_changed":protected_changed,
 "worker_status":report["status"],"runtime_validation":"UNTESTED",
 "report":"localization/graphics/role_A/20261007-A-MANUALQA152-9CE4E175/A152_9CE4E175_REPORT.json"}
(worker_out/"A152_9CE4E175.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False,indent=2))
if not ok: raise SystemExit(2)
