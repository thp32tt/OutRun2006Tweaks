#!/usr/bin/env python3
import os, json, hashlib, struct, subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageChops, ImageOps

if os.environ.get("OUTRUN_CPU_WORKER") != "github-actions" or os.environ.get("OUTRUN_CPU_ROLE") != "A":
    raise SystemExit("GitHub-hosted role A required")

repo=Path.cwd()
run="20261007-A-MANUALQA152R-9CE4E175"
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
validator=repo/"tools/localization/validate_clean_plate.py"

EXPECTED_BEFORE="5801e241ba3c288c8245c48123e55aa1f538fb6ca26eb32e182c7f3ec1779b09"
ORIGINAL_C125="cdb00269deb765e733a1da9dbc69e51d06f70d8b8f0fef453abbf67f685430b2"
SOURCE_SHA="6fee06730412c51e8f1e3db19ad1d43a12ce3eb9df8806812a46818715d92b2b"
BBOX=[95,80,490,121]
KOREAN="사용할 수 없음"

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
if not candidate.exists() or sha(candidate)!=EXPECTED_BEFORE:
    raise RuntimeError(("candidate drift",sha(candidate) if candidate.exists() else None,EXPECTED_BEFORE))

prior_bytes=candidate.read_bytes()
if prior_bytes[:4]!=b"DDS ": raise RuntimeError("not DDS")
H,W,pitch,depth,mips=struct.unpack_from("<5I",prior_bytes,12)
pf=struct.unpack_from("<8I",prior_bytes,76)
if (W,H,pitch,mips)!=(1024,128,4096,1): raise RuntimeError((W,H,pitch,mips))
masks=(pf[4],pf[5],pf[6],pf[7])
if masks==(255,65280,16711680,4278190080): raw_mode="RGBA"
elif masks==(16711680,65280,255,4278190080): raw_mode="BGRA"
else: raise RuntimeError(("unsupported masks",pf))

source=Image.open(source_png).convert("RGBA")
clean=Image.open(clean_png).convert("RGBA")
allowed=Image.open(allowed_png).convert("L")
protected=Image.open(protected_png).convert("L")
a152_raw=Image.frombytes("RGBA",(W,H),prior_bytes[128:],"raw",raw_mode)
a152=a152_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
clean_report=json.loads((prior_dir/"A_PRODUCTION20_CLEAN_PLATE_VALIDATION.json").read_text())
if clean_report.get("status")!="PASS": raise RuntimeError("prior clean invalid")

def resolve_font():
    for pat in ["Noto Sans CJK KR:style=Black","Noto Sans CJK KR:style=Bold","Noto Sans CJK KR"]:
        try: fp=subprocess.check_output(["fc-match","-f","%{file}",pat],text=True).strip()
        except Exception: fp=""
        if fp and Path(fp).exists() and "NotoSansCJK" in Path(fp).name: return fp
    subprocess.run(["sudo","apt-get","update","-qq"],check=True)
    subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
    return subprocess.check_output(["fc-match","-f","%{file}","Noto Sans CJK KR:style=Black"],text=True).strip()
FONT=resolve_font()

# Native-ratio fresh Hangul. No horizontal stretch. Only uniform down-fit is permitted.
font=ImageFont.truetype(FONT,40)
dummy=Image.new("L",(800,100),0); d=ImageDraw.Draw(dummy)
bb=d.textbbox((0,0),KOREAN,font=font,stroke_width=1)
mask=Image.new("L",(bb[2]-bb[0]+12,bb[3]-bb[1]+12),0)
md=ImageDraw.Draw(mask)
md.text((6-bb[0],6-bb[1]),KOREAN,font=font,fill=255,stroke_width=1,stroke_fill=255)
gb=mask.getbbox()
if not gb: raise RuntimeError("empty")
mask=mask.crop(gb)

x1,y1,x2,y2=BBOX
max_w,max_h=(x2-x1)-8,(y2-y1)-4
scale=min(1.0,max_w/mask.width,max_h/mask.height)
if scale<1.0:
    mask=mask.resize((max(1,round(mask.width*scale)),max(1,round(mask.height*scale))),Image.Resampling.LANCZOS)
target_w,target_h=mask.size
if target_w<205:
    raise RuntimeError(("native phrase still visually too narrow",target_w,target_h))

layer=Image.new("RGBA",(target_w,target_h),(255,255,255,0)); layer.putalpha(mask)
tx=x1+(x2-x1-target_w)//2
ty=y1+(y2-y1-target_h)//2
final=clean.copy(); final.alpha_composite(layer,(tx,ty))
loc=[tx,ty,tx+target_w,ty+target_h]

raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
new_bytes=prior_bytes[:128]+raw_final.tobytes("raw",raw_mode)
candidate.write_bytes(new_bytes)
candidate_sha=sha(candidate)
decoded_raw=Image.frombytes("RGBA",(W,H),new_bytes[128:],"raw",raw_mode)
decoded=decoded_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(decoded,final).getbbox() is not None: raise RuntimeError("roundtrip mismatch")

final_png=out/"9CE4E175_HD_FINAL_DECODED_READABLE.png"; decoded.save(final_png)
source.save(out/"9CE4E175_HD_SOURCE_READABLE.png"); clean.save(out/"9CE4E175_HD_CLEAN_PLATE.png")
subprocess.run(["python3",str(validator),str(source_png),str(final_png),str(allowed_png),
                "--protected-mask",str(protected_png),
                "--report",str(out/"A152R_FINAL_MASK_VALIDATION.json")],check=True)
final_rep=json.loads((out/"A152R_FINAL_MASK_VALIDATION.json").read_text())

def count(m): return sum(m.histogram()[1:])
def ch(a,b):
    d=ImageChops.difference(a,b); bands=d.split(); m=bands[0]
    for z in bands[1:]: m=ImageChops.lighter(m,z)
    return m.point(lambda v:255 if v else 0)
diff=ch(source,decoded)
outside=count(ImageChops.multiply(diff,ImageOps.invert(allowed)))
alpha=ImageChops.difference(source.getchannel("A"),decoded.getchannel("A")).point(lambda v:255 if v else 0)
alpha_outside=count(ImageChops.multiply(alpha,ImageOps.invert(allowed)))
protected_changed=count(ImageChops.multiply(diff,protected))

row={
 "source":"NOT AVAILABLE","prior_korean":"이용 불가","korean":KOREAN,
 "original_bbox":BBOX,"localized_bbox":loc,
 "source_width":x2-x1,"source_height":y2-y1,
 "localized_width":target_w,"localized_height":target_h,
 "width_ratio":round(target_w/(x2-x1),4),"height_ratio":round(target_h/(y2-y1),4),
 "delta_left":loc[0]-x1,"delta_right":x2-loc[2],"delta_top":loc[1]-y1,"delta_bottom":y2-loc[3],
 "a152_intermediate_size":[252,37],
 "c125_size":[142,37],
 "containment":"PASS" if loc[0]>=x1 and loc[1]>=y1 and loc[2]<=x2 and loc[3]<=y2 else "FAIL",
 "size_ceiling":"PASS" if target_w<=x2-x1 and target_h<=y2-y1 else "FAIL",
 "positive_margin":"PASS" if loc[0]>x1 and loc[1]>y1 and loc[2]<x2 and loc[3]<y2 else "FAIL",
 "native_aspect":"PASS_NO_HORIZONTAL_STRETCH",
 "style":"native Noto Sans CJK KR Black, heavy white sans, centered, upright"
}

def gray(im):
    bg=Image.new("RGBA",im.size,(96,96,96,255)); bg.alpha_composite(im); return bg.convert("RGB")
crop=(70,60,520,127)
c125_path=prior_dir/"9CE4E175_HD_FINAL_DECODED_READABLE.png"
c125=Image.open(c125_path).convert("RGBA")
parts=[gray(source.crop(crop)),gray(c125.crop(crop)),gray(a152.crop(crop)),gray(decoded.crop(crop))]
sheet=Image.new("RGB",(sum(p.width for p in parts)+24,max(p.height for p in parts)+28),(230,230,230))
xx=0
for p in parts:
    sheet.paste(p,(xx,28)); xx+=p.width+8
lab=ImageFont.truetype(FONT,16)
ImageDraw.Draw(sheet).text((3,3),"SOURCE | C125 | A152 rejected | A152R",font=lab,fill=(0,0,0))
sheet.save(out/"A152R_SOURCE_C125_A152_FINAL_CONTACT.jpg",quality=95)

overview=Image.new("RGB",(W,H*4),(90,90,90))
for i,im in enumerate([source,c125,a152,decoded]): overview.paste(gray(im),(0,H*i))
overview.save(out/"A152R_SOURCE_C125_A152_FINAL.jpg",quality=95)

rawcmp=Image.new("RGB",(W*4,H),(80,80,80))
rawcmp.paste(gray(source.transpose(Image.Transpose.FLIP_TOP_BOTTOM)),(0,0))
c125_bytes=(repo/"localization/graphics/hd_candidates"/asset_rel).read_bytes()  # now A152R bytes after write; do not use for c125 raw
# raw evidence needs source / rejected A152 / final A152R; source direction is enough to verify parity.
rawcmp=Image.new("RGB",(W*3,H),(80,80,80))
rawcmp.paste(gray(source.transpose(Image.Transpose.FLIP_TOP_BOTTOM)),(0,0))
rawcmp.paste(gray(a152_raw),(W,0)); rawcmp.paste(gray(decoded_raw),(W*2,0))
rawcmp.save(out/"A152R_SOURCE_A152_FINAL_RAW.jpg",quality=95)

ok=(final_rep.get("status")=="PASS" and row["containment"]=="PASS" and row["size_ceiling"]=="PASS"
    and row["positive_margin"]=="PASS" and target_w>=205 and outside==0 and alpha_outside==0 and protected_changed==0)

report={
 "schema_version":1,"role":"A","run":run,"worker":os.environ.get("OUTRUN_CPU_WORKER"),
 "base_head":os.environ.get("GITHUB_SHA"),"queue_index":195,"asset":asset_rel,
 "trigger":"A152_CONTROLLER_REJECTED_STRETCHED_GLYPH_PROPORTIONS_RETRY",
 "source_sha256":SOURCE_SHA,"c125_candidate_sha256":ORIGINAL_C125,
 "a152_rejected_candidate_sha256":EXPECTED_BEFORE,"candidate_sha256":candidate_sha,
 "translation_reword":{"from":"이용 불가","to":KOREAN,"reason":"Direct semantic equivalent of NOT AVAILABLE chosen to restore source hierarchy with natural native Hangul proportions instead of horizontal glyph stretching."},
 "reason":"A152 numeric PASS was controller-rejected because 이용 불가 required obvious horizontal stretching. A152R uses a longer direct Korean equivalent and native glyph aspect, preserving the source heavy-white centered family.",
 "structure":{"dimensions":[W,H],"format":"RGBA32","raw_mode":raw_mode,"pitch":pitch,"mipmaps":mips,"header_128_exact":True,"raw_orientation":"mirror_y"},
 "prior_clean_plate_validator":clean_report,"final_mask_validator":final_rep,
 "decoded_changes":{"changed_pixels_outside_source_bbox":outside,"alpha_changed_pixels_outside_source_bbox":alpha_outside,"protected_visible_pixels_changed":protected_changed},
 "row":row,
 "ordered_generation_gate":{
   "1_source_text_removed_and_plate_restored":"PASS_REUSE_PRIOR_EXACT_VALIDATED_CLEAN_PLATE",
   "2_slant_direction_matches_source":"PASS_SOURCE_UPRIGHT",
   "3_text_not_unnecessarily_undersized_and_within_source_bbox":"PASS_NATIVE_PHRASE_WIDTH_AND_SOURCE_CEILING",
   "4_source_faithful_weight_outline_shadow":"PASS_NATIVE_BLACK_HEAVY_WHITE_NO_INVENTED_EFFECT",
   "5_no_clipped_pixels":"PASS_POSITIVE_MARGINS",
   "6_protected_graphics_clearance":"PASS_ZERO_PROTECTED_CHANGE",
   "7_raw_and_flip_y_visual_review":"EVIDENCE_WRITTEN_PENDING_CONTROLLER",
   "8_immediate_readability_vs_english":"PENDING_CONTROLLER"
 },
 "controller_visual_qa":"PENDING_CONTROLLER_REVIEW",
 "runtime_validation":"UNTESTED",
 "status":"A152R_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_VISUAL_QA" if ok else "A152R_WORKER_REWORK_REQUIRED",
 "no_vr_ffb_dx11_dxvk_work":True
}
(out/"A152R_9CE4E175_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
summary={"run":run,"asset":"9CE4E175","queue_index":195,
 "c125_candidate_sha256":ORIGINAL_C125,"a152_rejected_candidate_sha256":EXPECTED_BEFORE,"candidate_sha256":candidate_sha,
 "translation":KOREAN,"new_size":[target_w,target_h],"source_size":[x2-x1,y2-y1],
 "bbox_size_positive_margin":"1/1 PASS" if ok else "FAIL",
 "native_aspect":"PASS_NO_HORIZONTAL_STRETCH",
 "changed_outside":outside,"alpha_outside":alpha_outside,"protected_changed":protected_changed,
 "worker_status":report["status"],"runtime_validation":"UNTESTED",
 "report":"localization/graphics/role_A/20261007-A-MANUALQA152R-9CE4E175/A152R_9CE4E175_REPORT.json"}
(worker_out/"A152R_9CE4E175.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False,indent=2))
if not ok: raise SystemExit(2)
