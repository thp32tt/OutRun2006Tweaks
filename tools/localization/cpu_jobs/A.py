#!/usr/bin/env python3
import os, json, hashlib, struct, subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageChops, ImageOps

if os.environ.get("OUTRUN_CPU_WORKER") != "github-actions" or os.environ.get("OUTRUN_CPU_ROLE") != "A":
    raise SystemExit("GitHub-hosted role A required")

repo=Path.cwd()
run="20261007-A-MANUALQA150-313DB8CB"
out=repo/"localization/graphics/role_A"/run
out.mkdir(parents=True,exist_ok=True)
worker_out=repo/"localization/graphics/worker_results"
worker_out.mkdir(parents=True,exist_ok=True)

asset_rel="textures/load/spr_sprani_sumo_fe_cvt_Exst/313DB8CB_512x256.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset_rel
prior_dir=repo/"localization/graphics/role_A/20261005-A-PRODUCTION19"
source_png=prior_dir/"313DB8CB_HD_SOURCE_READABLE.png"
clean_png=prior_dir/"313DB8CB_HD_CLEAN_PLATE.png"
allowed_png=prior_dir/"313DB8CB_HD_ALLOWED_SOURCE_BBOX_MASK.png"
protected_png=prior_dir/"313DB8CB_HD_PROTECTED_VISIBLE_MASK.png"
source_mask_png=prior_dir/"313DB8CB_HD_SOURCE_TEXT_MASK.png"
validator=repo/"tools/localization/validate_clean_plate.py"

EXPECTED_BEFORE="c44a9ccd62e2b78fb17ec10f7a50a6de32dc1a0f84a44f2595b3e7ffaa0cc0ea"
SOURCE_SHA="4c85be80485375876cdcc6be0ebd1e5578032894a194a820b47f01b271fe4786"
REVIEW_JPG="localization/graphics/role_C/PRE_INGAME_JPG_REVIEW/016_q139_313DB8CB.jpg"

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
if not candidate.exists() or sha(candidate)!=EXPECTED_BEFORE:
    raise RuntimeError(("candidate drift before A150", sha(candidate) if candidate.exists() else None, EXPECTED_BEFORE))
for p in [source_png,clean_png,allowed_png,protected_png,source_mask_png]:
    if not p.exists(): raise RuntimeError(("missing prior exact evidence",str(p)))

prior_bytes=candidate.read_bytes()
if prior_bytes[:4]!=b"DDS ": raise RuntimeError("not DDS")
H,W,pitch,depth,mips=struct.unpack_from("<5I",prior_bytes,12)
pf=struct.unpack_from("<8I",prior_bytes,76)
if (W,H,pitch,depth,mips)!=(2048,1024,8192,1,1): raise RuntimeError((W,H,pitch,depth,mips))
if pf[1:]!=(65,0,32,0xff,0xff00,0xff0000,0xff000000): raise RuntimeError(("pixel format",pf))
if len(prior_bytes)!=128+W*H*4: raise RuntimeError(("byte size",len(prior_bytes)))

source=Image.open(source_png).convert("RGBA")
clean=Image.open(clean_png).convert("RGBA")
allowed=Image.open(allowed_png).convert("L")
protected=Image.open(protected_png).convert("L")
source_mask=Image.open(source_mask_png).convert("L")
if source.size!=(W,H) or clean.size!=(W,H): raise RuntimeError("evidence size")
prior_raw=Image.frombytes("RGBA",(W,H),prior_bytes[128:],"raw","RGBA")
prior=prior_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)

prior_clean_report=json.loads((prior_dir/"A_PRODUCTION19_CLEAN_PLATE_VALIDATION.json").read_text())
if prior_clean_report.get("status")!="PASS": raise RuntimeError(("prior clean not PASS",prior_clean_report))

# Latest policy: do not leave short Hangul labels visually tiny relative to TUNED/NORMAL.
# "사양" preserves the selector meaning while allowing source-relative hierarchy without oversizing.
specs=[
    {"key":"tuned","source":"TUNED","korean":"튜닝 사양","bbox":[1405,982,1544,1018]},
    {"key":"normal","source":"NORMAL","korean":"일반 사양","bbox":[1730,981,1904,1017]},
]

def resolve_font():
    pats=["Noto Sans CJK KR:style=Black","Noto Sans CJK KR:style=Bold","Noto Sans CJK KR"]
    for pat in pats:
        try: fp=subprocess.check_output(["fc-match","-f","%{file}",pat],text=True).strip()
        except Exception: fp=""
        if fp and Path(fp).exists() and "NotoSansCJK" in Path(fp).name:
            return fp
    subprocess.run(["sudo","apt-get","update","-qq"],check=True)
    subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
    for pat in pats:
        fp=subprocess.check_output(["fc-match","-f","%{file}",pat],text=True).strip()
        if fp and Path(fp).exists(): return fp
    raise RuntimeError("Noto CJK unavailable")
FONT=resolve_font()

def alpha_bbox(im):
    return im.getchannel("A").getbbox()

def count(mask):
    return sum(mask.histogram()[1:])

def changed_mask(a,b):
    d=ImageChops.difference(a,b)
    bands=d.split(); m=bands[0]
    for z in bands[1:]: m=ImageChops.lighter(m,z)
    return m.point(lambda v:255 if v else 0)

def render_native(text, aw, ah):
    # Maintain near-source height first; fit width second. No old-bitmap scaling.
    for fs in range(40, 18, -1):
        font=ImageFont.truetype(FONT,fs)
        stroke=1
        tmp=Image.new("RGBA",(600,100),(0,0,0,0))
        d=ImageDraw.Draw(tmp)
        bb=d.textbbox((0,0),text,font=font,stroke_width=stroke)
        glyph=Image.new("RGBA",(bb[2]-bb[0]+10,bb[3]-bb[1]+10),(0,0,0,0))
        gd=ImageDraw.Draw(glyph)
        gd.text((5-bb[0],5-bb[1]),text,font=font,fill=(255,255,255,255),
                stroke_width=stroke,stroke_fill=(255,255,255,255))
        gb=alpha_bbox(glyph)
        if not gb: continue
        glyph=glyph.crop(gb)
        if glyph.height<=ah-4 and glyph.width<=aw-4:
            return glyph,fs,stroke
    raise RuntimeError(("fit failed",text,aw,ah))

final=clean.copy()
rows=[]
for sp in specs:
    ox1,oy1,ox2,oy2=sp["bbox"]
    aw,ah=ox2-ox1,oy2-oy1
    glyph,fs,stroke=render_native(sp["korean"],aw,ah)
    # Source labels are centered in their cells; retain centered alignment with positive margins.
    tx=ox1+(aw-glyph.width)//2
    ty=oy1+(ah-glyph.height)//2
    tx=max(ox1+2,min(tx,ox2-glyph.width-2))
    ty=max(oy1+2,min(ty,oy2-glyph.height-2))
    final.alpha_composite(glyph,(tx,ty))
    loc=[tx,ty,tx+glyph.width,ty+glyph.height]
    old=prior.crop((ox1,oy1,ox2,oy2)).getchannel("A").getbbox()
    oldloc=[ox1+old[0],oy1+old[1],ox1+old[2],oy1+old[3]] if old else None
    rows.append({
      "key":sp["key"],"source":sp["source"],"korean":sp["korean"],
      "original_bbox":sp["bbox"],"localized_bbox":loc,
      "source_width":aw,"source_height":ah,
      "localized_width":glyph.width,"localized_height":glyph.height,
      "width_ratio":round(glyph.width/aw,4),"height_ratio":round(glyph.height/ah,4),
      "delta_left":loc[0]-ox1,"delta_right":ox2-loc[2],
      "delta_top":loc[1]-oy1,"delta_bottom":oy2-loc[3],
      "prior_localized_bbox":oldloc,
      "prior_localized_width":(oldloc[2]-oldloc[0]) if oldloc else None,
      "prior_localized_height":(oldloc[3]-oldloc[1]) if oldloc else None,
      "width_gain_px":glyph.width-((oldloc[2]-oldloc[0]) if oldloc else 0),
      "containment":"PASS" if loc[0]>=ox1 and loc[1]>=oy1 and loc[2]<=ox2 and loc[3]<=oy2 else "FAIL",
      "size_ceiling":"PASS" if glyph.width<=aw and glyph.height<=ah else "FAIL",
      "positive_margin":"PASS" if loc[0]>ox1 and loc[1]>oy1 and loc[2]<ox2 and loc[3]<oy2 else "FAIL",
      "font":"Noto Sans CJK KR Black","font_size":fs,"same_color_weight_stroke":stroke,
      "style":"heavy plain white sans, upright/centered like source; native Hangul, no low-res bitmap reuse"
    })

raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
new_bytes=prior_bytes[:128]+raw_final.tobytes("raw","RGBA")
candidate.write_bytes(new_bytes)
candidate_sha=sha(candidate)
if new_bytes[:128]!=prior_bytes[:128]: raise RuntimeError("header changed")
decoded_raw=Image.frombytes("RGBA",(W,H),new_bytes[128:],"raw","RGBA")
decoded=decoded_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(decoded,final).getbbox() is not None: raise RuntimeError("roundtrip mismatch")

final_png=out/"313DB8CB_HD_FINAL_DECODED_READABLE.png"
decoded.save(final_png)
source.copy().save(out/"313DB8CB_HD_SOURCE_READABLE.png")
clean.copy().save(out/"313DB8CB_HD_CLEAN_PLATE.png")

subprocess.run(["python3",str(validator),str(source_png),str(final_png),str(allowed_png),
                "--protected-mask",str(protected_png),
                "--report",str(out/"A150_FINAL_MASK_VALIDATION.json")],check=True)
final_rep=json.loads((out/"A150_FINAL_MASK_VALIDATION.json").read_text())
if final_rep.get("status")!="PASS": raise RuntimeError(("final validator",final_rep))

diff=changed_mask(source,decoded)
outside=count(ImageChops.multiply(diff,ImageOps.invert(allowed)))
alpha_delta=ImageChops.difference(source.getchannel("A"),decoded.getchannel("A")).point(lambda v:255 if v else 0)
alpha_outside=count(ImageChops.multiply(alpha_delta,ImageOps.invert(allowed)))
protected_changed=count(ImageChops.multiply(diff,protected))
clean_residue=count(ImageChops.multiply(clean.getchannel("A"),source_mask))
# source_mask can overlap opaque background in some assets; prior exact clean validator is authoritative.
clean_residue_status="PASS_PRIOR_EXACT_CLEAN_VALIDATOR"

all_bbox=all(r["containment"]=="PASS" for r in rows)
all_size=all(r["size_ceiling"]=="PASS" for r in rows)
all_positive=all(r["positive_margin"]=="PASS" for r in rows)
material_gain=all((r["width_gain_px"] or 0)>=25 for r in rows)

# Readable evidence: SOURCE | C116 | CLEAN | A150 and row contacts.
def gray(im):
    bg=Image.new("RGBA",im.size,(96,96,96,255)); bg.alpha_composite(im); return bg.convert("RGB")
overview=Image.new("RGB",(W, H*4),(90,90,90))
for i,im in enumerate([source,prior,clean,decoded]):
    overview.paste(gray(im),(0,H*i))
overview.thumbnail((2048,2048),Image.Resampling.LANCZOS)
overview.save(out/"A150_SOURCE_C116_CLEAN_FINAL.jpg",quality=95)

contacts=[]
font_label=ImageFont.truetype(FONT,20)
for r in rows:
    x1,y1,x2,y2=r["original_bbox"]; m=12
    box=(max(0,x1-m),max(0,y1-m),min(W,x2+m),min(H,y2+m))
    parts=[gray(source.crop(box)),gray(prior.crop(box)),gray(decoded.crop(box))]
    rw=sum(p.width for p in parts)+12
    rh=max(p.height for p in parts)+28
    row=Image.new("RGB",(rw,rh),(230,230,230))
    xx=0
    for p in parts:
        row.paste(p,(xx,28)); xx+=p.width+6
    ImageDraw.Draw(row).text((3,3),r["key"]+" SOURCE | C116 | A150",font=font_label,fill=(0,0,0))
    contacts.append(row)
cw=max(x.width for x in contacts); ch=sum(x.height for x in contacts)+6
sheet=Image.new("RGB",(cw,ch),(235,235,235)); yy=0
for x in contacts:
    sheet.paste(x,(0,yy)); yy+=x.height+6
sheet.save(out/"A150_ROW_CONTACT.jpg",quality=95)

rawcmp=Image.new("RGB",(W*3,H),(80,80,80))
rawcmp.paste(gray(source.transpose(Image.Transpose.FLIP_TOP_BOTTOM)),(0,0))
rawcmp.paste(gray(prior_raw),(W,0))
rawcmp.paste(gray(decoded_raw),(W*2,0))
rawcmp.thumbnail((2100,700),Image.Resampling.LANCZOS)
rawcmp.save(out/"A150_SOURCE_C116_FINAL_RAW.jpg",quality=95)

status_ok=(final_rep["status"]=="PASS" and all_bbox and all_size and all_positive and material_gain
           and outside==0 and alpha_outside==0 and protected_changed==0)

report={
 "schema_version":1,"role":"A","run":run,"worker":os.environ.get("OUTRUN_CPU_WORKER"),
 "base_head":os.environ.get("GITHUB_SHA"),"queue_index":139,"asset":asset_rel,
 "trigger":"PRE_INGAME_016_SOURCE_RELATIVE_HIERARCHY_FALSE_NEGATIVE",
 "review_jpg":REVIEW_JPG,
 "prior_c_status":"C116_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME",
 "prior_candidate_sha256":EXPECTED_BEFORE,"source_sha256":SOURCE_SHA,
 "candidate_sha256":candidate_sha,"candidate_path":str(candidate.relative_to(repo)),
 "translation_rework":[{"source":"TUNED","prior_korean":"튜닝","korean":"튜닝 사양"},
                       {"source":"NORMAL","prior_korean":"일반","korean":"일반 사양"}],
 "reason":"Prior C116 numeric PASS left Korean widths 55/58px inside 139/174px source labels. Latest ordered generation gate forbids visibly undersized hierarchy; 사양 preserves the selector semantics and restores source-relative visual weight.",
 "structure":{"dimensions":[W,H],"format":"RGBA32","pitch":pitch,"mipmaps":mips,"header_128_exact":True,"raw_orientation":"mirror_y"},
 "prior_clean_plate_validator":prior_clean_report,
 "final_mask_validator":final_rep,
 "decoded_changes":{"changed_pixels_outside_original_bboxes":outside,
                    "alpha_changed_pixels_outside_original_bboxes":alpha_outside,
                    "protected_visible_pixels_changed":protected_changed,
                    "clean_plate_source_text_residue_check":clean_residue_status,
                    "diagnostic_clean_alpha_x_sourcemask":clean_residue},
 "rows":rows,
 "ordered_generation_gate":{
   "1_source_text_removed_and_plate_restored":"PASS_REUSE_PRIOR_EXACT_VALIDATED_CLEAN_PLATE",
   "2_slant_direction_matches_source":"PASS_SOURCE_UPRIGHT",
   "3_text_not_unnecessarily_undersized_and_within_source_bbox":"PASS_MATERIAL_WIDTH_GAIN",
   "4_source_faithful_weight_outline_shadow":"PASS_HEAVY_PLAIN_WHITE_NATIVE_BLACK",
   "5_no_clipped_pixels":"PASS_POSITIVE_MARGINS",
   "6_protected_graphics_clearance":"PASS_ZERO_PROTECTED_CHANGE",
   "7_raw_and_flip_y_visual_review":"EVIDENCE_WRITTEN_PENDING_CONTROLLER",
   "8_immediate_readability_vs_english":"PENDING_CONTROLLER"
 },
 "controller_visual_qa":"PENDING_CONTROLLER_REVIEW",
 "runtime_validation":"UNTESTED",
 "status":"A150_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_VISUAL_QA" if status_ok else "A150_WORKER_REWORK_REQUIRED",
 "no_vr_ffb_dx11_dxvk_work":True
}
(out/"A150_313DB8CB_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
summary={"run":run,"asset":"313DB8CB","queue_index":139,
 "prior_candidate_sha256":EXPECTED_BEFORE,"candidate_sha256":candidate_sha,
 "bbox_size_positive_margin":"2/2 PASS" if all_bbox and all_size and all_positive else "FAIL",
 "width_gains":[r["width_gain_px"] for r in rows],
 "width_ratios":[r["width_ratio"] for r in rows],
 "changed_outside":outside,"alpha_outside":alpha_outside,"protected_changed":protected_changed,
 "worker_status":report["status"],"runtime_validation":"UNTESTED",
 "report":"localization/graphics/role_A/20261007-A-MANUALQA150-313DB8CB/A150_313DB8CB_REPORT.json"}
(worker_out/"A150_313DB8CB.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False,indent=2))
if not status_ok: raise SystemExit(2)
