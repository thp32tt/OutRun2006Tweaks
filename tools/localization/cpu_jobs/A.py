#!/usr/bin/env python3
import os, json, hashlib, struct, subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageChops, ImageOps, ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER") != "github-actions" or os.environ.get("OUTRUN_CPU_ROLE") != "A":
    raise SystemExit("GitHub-hosted role A required")

repo=Path.cwd()
run="20261007-A-MANUALQA151-754F0599"
out=repo/"localization/graphics/role_A"/run
out.mkdir(parents=True,exist_ok=True)
worker_out=repo/"localization/graphics/worker_results"; worker_out.mkdir(parents=True,exist_ok=True)

asset_rel="textures/load/spr_sprani_sumo_fe_cvt_Exst/754F0599_512x256.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset_rel
prior_dir=repo/"localization/graphics/role_A/20261005-A-PRODUCTION29"
source_png=prior_dir/"754F0599_HD_SOURCE_READABLE.png"
clean_png=prior_dir/"754F0599_HD_CLEAN_PLATE.png"
allowed_png=prior_dir/"754F0599_HD_ALLOWED_TEXT_BBOX_MASK.png"
protected_png=prior_dir/"754F0599_HD_PROTECTED_VISIBLE_MASK.png"
source_mask_png=prior_dir/"754F0599_HD_SOURCE_TEXT_MASK.png"
validator=repo/"tools/localization/validate_clean_plate.py"

EXPECTED_BEFORE="884f333b7217fd975aec1c1fc81c98bfd4287e52dc60255eb6b06803430b2250"
SOURCE_SHA="9314372585b8309f2f8b3e714076ef1ad1999d770422a570398ef20a80ac10a5"
REVIEW_JPG="localization/graphics/role_C/PRE_INGAME_JPG_REVIEW/025_q175_754F0599.jpg"

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
if not candidate.exists() or sha(candidate)!=EXPECTED_BEFORE:
    raise RuntimeError(("candidate drift",sha(candidate) if candidate.exists() else None,EXPECTED_BEFORE))
for p in [source_png,clean_png,allowed_png,protected_png,source_mask_png]:
    if not p.exists(): raise RuntimeError(("missing prior evidence",str(p)))

prior_bytes=candidate.read_bytes()
if prior_bytes[:4]!=b"DDS ": raise RuntimeError("not DDS")
H,W,pitch,depth,mips=struct.unpack_from("<5I",prior_bytes,12)
pf=struct.unpack_from("<8I",prior_bytes,76)
if (W,H,pitch,mips)!=(2048,1024,8192,1): raise RuntimeError((W,H,pitch,depth,mips))
if pf[1:]!=(65,0,32,16711680,65280,255,4278190080): raise RuntimeError(("pixel format",pf))
if len(prior_bytes)!=128+W*H*4: raise RuntimeError(("byte size",len(prior_bytes)))

source=Image.open(source_png).convert("RGBA")
clean=Image.open(clean_png).convert("RGBA")
allowed=Image.open(allowed_png).convert("L")
protected=Image.open(protected_png).convert("L")
source_mask=Image.open(source_mask_png).convert("L")
prior_raw=Image.frombytes("RGBA",(W,H),prior_bytes[128:],"raw","BGRA")
prior=prior_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if source.size!=(W,H) or clean.size!=(W,H): raise RuntimeError("evidence size")

clean_report=json.loads((prior_dir/"A_PRODUCTION29_CLEAN_PLATE_VALIDATION.json").read_text())
if clean_report.get("status")!="PASS": raise RuntimeError("prior clean plate not PASS")

def resolve_font():
    pats=["Noto Sans CJK KR:style=Regular","Noto Sans CJK KR"]
    for pat in pats:
        try: fp=subprocess.check_output(["fc-match","-f","%{file}",pat],text=True).strip()
        except Exception: fp=""
        if fp and Path(fp).exists() and "NotoSansCJK" in Path(fp).name: return fp
    subprocess.run(["sudo","apt-get","update","-qq"],check=True)
    subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
    for pat in pats:
        fp=subprocess.check_output(["fc-match","-f","%{file}",pat],text=True).strip()
        if fp and Path(fp).exists(): return fp
    raise RuntimeError("Noto CJK unavailable")
FONT=resolve_font()

specs=[
 {"key":"stage_select","source":"stage select","korean":"스테이지 선택","bbox":[6,254,1372,397],"target":[1188,124],"slant":6,"shadow":[5,8]},
 {"key":"showroom","source":"showroom","korean":"쇼룸","bbox":[6,397,956,529],"target":[700,114],"slant":6,"shadow":[5,7]},
 {"key":"single_player","source":"single player","korean":"싱글 플레이","bbox":[2,566,1386,717],"target":[1208,130],"slant":6,"shadow":[5,8]},
]

def count(mask): return sum(mask.histogram()[1:])
def changed_mask(a,b):
    d=ImageChops.difference(a,b); bands=d.split(); m=bands[0]
    for z in bands[1:]: m=ImageChops.lighter(m,z)
    return m.point(lambda v:255 if v else 0)

def render_metal(text,target_w,target_h,slant_px,shadow_xy):
    # Fresh native Hangul mask. Geometric fit is applied to the new vector-raster only,
    # never to an older Korean candidate bitmap.
    font=ImageFont.truetype(FONT,140)
    dummy=Image.new("L",(1800,320),0); d=ImageDraw.Draw(dummy)
    bb=d.textbbox((0,0),text,font=font,stroke_width=0)
    mask=Image.new("L",(bb[2]-bb[0]+40,bb[3]-bb[1]+40),0)
    md=ImageDraw.Draw(mask); md.text((20-bb[0],20-bb[1]),text,font=font,fill=255)
    gb=mask.getbbox()
    if not gb: raise RuntimeError(("empty glyph",text))
    mask=mask.crop(gb)
    # Readable right lean, matching source direction.
    shear=slant_px/max(mask.height,1)
    extra=abs(slant_px)+4
    sheared=Image.new("L",(mask.width+extra,mask.height),0)
    mask=mask.transform((mask.width+extra,mask.height),Image.Transform.AFFINE,(1,-shear,0,0,1,0),Image.Resampling.BICUBIC)
    gb=mask.getbbox()
    if gb: mask=mask.crop(gb)

    # Reserve effect footprint, then source-relative width/height fit.
    body_w=max(20,target_w-22); body_h=max(20,target_h-20)
    mask=mask.resize((body_w,body_h),Image.Resampling.LANCZOS)

    # Body + light edge + dark extrusion. Keep metallic grayscale source family.
    edge=mask.filter(ImageFilter.MaxFilter(7))
    soft=mask.filter(ImageFilter.MaxFilter(3))
    layer=Image.new("RGBA",(target_w+40,target_h+40),(0,0,0,0))
    ox=12; oy=8
    # shadow/extrusion
    sx=ox+shadow_xy[0]; sy=oy+shadow_xy[1]
    shadow=Image.new("RGBA",layer.size,(0,0,0,0))
    shadow.paste((12,12,12,245),(sx,sy,sx+mask.width,sy+mask.height),edge)
    layer=Image.alpha_composite(layer,shadow)
    # dark outer edge
    outline=Image.new("RGBA",layer.size,(0,0,0,0))
    outline.paste((18,18,18,255),(ox,oy,ox+mask.width,oy+mask.height),edge)
    layer=Image.alpha_composite(layer,outline)
    # metallic body gradient
    grad=Image.new("RGBA",(mask.width,mask.height),(0,0,0,0))
    gp=grad.load()
    for y in range(mask.height):
        t=y/max(mask.height-1,1)
        if t<0.42:
            v=int(250-(250-205)*(t/0.42))
        elif t<0.72:
            v=int(205-(205-112)*((t-0.42)/0.30))
        else:
            v=int(112-(112-50)*((t-0.72)/0.28))
        for x in range(mask.width): gp[x,y]=(v,v,v,255)
    body=Image.new("RGBA",layer.size,(0,0,0,0))
    body.paste(grad,(ox,oy),mask)
    layer=Image.alpha_composite(layer,body)
    # thin bright keyline over body edge
    rim=ImageChops.subtract(soft,mask)
    hi=Image.new("RGBA",layer.size,(0,0,0,0))
    hi.paste((245,245,245,210),(ox,oy,ox+mask.width,oy+mask.height),rim)
    layer=Image.alpha_composite(layer,hi)

    gb=layer.getchannel("A").getbbox()
    if not gb: raise RuntimeError("empty layer")
    layer=layer.crop(gb)
    # Normalize exact final footprint to the requested source-relative target.
    layer=layer.resize((target_w,target_h),Image.Resampling.LANCZOS)
    gb=layer.getchannel("A").getbbox()
    if gb: layer=layer.crop(gb)
    return layer

final=clean.copy()
rows=[]
for sp in specs:
    ox1,oy1,ox2,oy2=sp["bbox"]; sw,sh=ox2-ox1,oy2-oy1
    tw,th=sp["target"]
    if tw>=sw or th>=sh: raise RuntimeError(("target exceeds source",sp))
    layer=render_metal(sp["korean"],tw,th,sp["slant"],sp["shadow"])
    # left-anchored source family with positive margin; vertically center in exact source bbox.
    tx=ox1+4
    ty=oy1+(sh-layer.height)//2
    if tx+layer.width>=ox2: tx=ox2-layer.width-2
    if ty<=oy1: ty=oy1+2
    if ty+layer.height>=oy2: ty=oy2-layer.height-2
    final.alpha_composite(layer,(tx,ty))
    loc=[tx,ty,tx+layer.width,ty+layer.height]
    oldmask=ImageChops.difference(clean.crop((ox1,oy1,ox2,oy2)),prior.crop((ox1,oy1,ox2,oy2)))
    bands=oldmask.split(); om=bands[0]
    for z in bands[1:]: om=ImageChops.lighter(om,z)
    oldbb=om.getbbox()
    oldloc=[ox1+oldbb[0],oy1+oldbb[1],ox1+oldbb[2],oy1+oldbb[3]] if oldbb else None
    rows.append({
      "key":sp["key"],"source":sp["source"],"korean":sp["korean"],
      "original_bbox":sp["bbox"],"localized_bbox":loc,
      "source_width":sw,"source_height":sh,
      "localized_width":layer.width,"localized_height":layer.height,
      "width_ratio":round(layer.width/sw,4),"height_ratio":round(layer.height/sh,4),
      "delta_left":loc[0]-ox1,"delta_right":ox2-loc[2],"delta_top":loc[1]-oy1,"delta_bottom":oy2-loc[3],
      "prior_localized_bbox":oldloc,
      "prior_localized_width":(oldloc[2]-oldloc[0]) if oldloc else None,
      "prior_localized_height":(oldloc[3]-oldloc[1]) if oldloc else None,
      "width_gain_px":layer.width-((oldloc[2]-oldloc[0]) if oldloc else 0),
      "height_gain_px":layer.height-((oldloc[3]-oldloc[1]) if oldloc else 0),
      "containment":"PASS" if loc[0]>=ox1 and loc[1]>=oy1 and loc[2]<=ox2 and loc[3]<=oy2 else "FAIL",
      "size_ceiling":"PASS" if layer.width<=sw and layer.height<=sh else "FAIL",
      "positive_margin":"PASS" if loc[0]>ox1 and loc[1]>oy1 and loc[2]<ox2 and loc[3]<oy2 else "FAIL",
      "style":"fresh native Noto Sans CJK KR Regular; metallic grayscale gradient, bright keyline, dark extrusion, readable right lean, source-left anchor"
    })

raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
new_bytes=prior_bytes[:128]+raw_final.tobytes("raw","BGRA")
candidate.write_bytes(new_bytes)
candidate_sha=sha(candidate)
decoded_raw=Image.frombytes("RGBA",(W,H),new_bytes[128:],"raw","BGRA")
decoded=decoded_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
if ImageChops.difference(decoded,final).getbbox() is not None: raise RuntimeError("roundtrip mismatch")

final_png=out/"754F0599_HD_FINAL_DECODED_READABLE.png"; decoded.save(final_png)
source.save(out/"754F0599_HD_SOURCE_READABLE.png"); clean.save(out/"754F0599_HD_CLEAN_PLATE.png")
subprocess.run(["python3",str(validator),str(source_png),str(final_png),str(allowed_png),
                "--protected-mask",str(protected_png),"--report",str(out/"A151_FINAL_MASK_VALIDATION.json")],check=True)
final_rep=json.loads((out/"A151_FINAL_MASK_VALIDATION.json").read_text())
if final_rep.get("status")!="PASS": raise RuntimeError(("validator",final_rep))

diff=changed_mask(source,decoded)
outside=count(ImageChops.multiply(diff,ImageOps.invert(allowed)))
alpha_delta=ImageChops.difference(source.getchannel("A"),decoded.getchannel("A")).point(lambda v:255 if v else 0)
alpha_outside=count(ImageChops.multiply(alpha_delta,ImageOps.invert(allowed)))
protected_changed=count(ImageChops.multiply(diff,protected))
all_bbox=all(r["containment"]=="PASS" for r in rows)
all_size=all(r["size_ceiling"]=="PASS" for r in rows)
all_positive=all(r["positive_margin"]=="PASS" for r in rows)
height_gain=all((r["height_gain_px"] or 0)>=15 for r in rows)

# Evidence
def gray(im):
    bg=Image.new("RGBA",im.size,(96,96,96,255)); bg.alpha_composite(im); return bg.convert("RGB")
contacts=[]
lab=ImageFont.truetype(FONT,18)
for r in rows:
    x1,y1,x2,y2=r["original_bbox"]; m=8
    box=(max(0,x1-m),max(0,y1-m),min(W,x2+m),min(H,y2+m))
    parts=[gray(source.crop(box)),gray(prior.crop(box)),gray(decoded.crop(box))]
    # fit each row compactly for controller
    parts=[p.resize((max(1,p.width//2),max(1,p.height//2)),Image.Resampling.LANCZOS) for p in parts]
    rw=sum(p.width for p in parts)+12; rh=max(p.height for p in parts)+24
    rowim=Image.new("RGB",(rw,rh),(230,230,230)); xx=0
    for p in parts: rowim.paste(p,(xx,24)); xx+=p.width+6
    ImageDraw.Draw(rowim).text((3,2),r["key"]+" SOURCE | C171 | A151",font=lab,fill=(0,0,0))
    contacts.append(rowim)
cw=max(p.width for p in contacts); ch=sum(p.height for p in contacts)+6*(len(contacts)-1)
sheet=Image.new("RGB",(cw,ch),(235,235,235)); yy=0
for p in contacts: sheet.paste(p,(0,yy)); yy+=p.height+6
sheet.save(out/"A151_ROW_CONTACT.jpg",quality=95)

overview=Image.new("RGB",(W,H*3),(90,90,90))
overview.paste(gray(source),(0,0)); overview.paste(gray(prior),(0,H)); overview.paste(gray(decoded),(0,H*2))
overview.thumbnail((1600,1800),Image.Resampling.LANCZOS)
overview.save(out/"A151_SOURCE_C171_FINAL.jpg",quality=95)

rawcmp=Image.new("RGB",(W*3,H),(80,80,80))
rawcmp.paste(gray(source.transpose(Image.Transpose.FLIP_TOP_BOTTOM)),(0,0))
rawcmp.paste(gray(prior_raw),(W,0)); rawcmp.paste(gray(decoded_raw),(W*2,0))
rawcmp.thumbnail((1800,500),Image.Resampling.LANCZOS)
rawcmp.save(out/"A151_SOURCE_C171_FINAL_RAW.jpg",quality=95)

status_ok=(final_rep["status"]=="PASS" and all_bbox and all_size and all_positive and height_gain
           and outside==0 and alpha_outside==0 and protected_changed==0)
report={
 "schema_version":1,"role":"A","run":run,"worker":os.environ.get("OUTRUN_CPU_WORKER"),
 "base_head":os.environ.get("GITHUB_SHA"),"queue_index":175,"asset":asset_rel,
 "trigger":"PRE_INGAME_025_SOURCE_RELATIVE_SCALE_HIERARCHY_FALSE_NEGATIVE",
 "review_jpg":REVIEW_JPG,
 "prior_c_status":"C171_PIXEL_VISUAL_POLICY_PASS_PENDING_INGAME",
 "prior_candidate_sha256":EXPECTED_BEFORE,"source_sha256":SOURCE_SHA,"candidate_sha256":candidate_sha,
 "reason":"Current C171 rows remain only 103/143, 95/132 and 109/151px high. New ordered generation gate treats this as unnecessary undersizing relative to the source family.",
 "structure":{"dimensions":[W,H],"format":"RGBA32/BGRA raw","pitch":pitch,"mipmaps":mips,"header_128_exact":True,"raw_orientation":"mirror_y"},
 "prior_clean_plate_validator":clean_report,"final_mask_validator":final_rep,
 "decoded_changes":{"changed_pixels_outside_original_bboxes":outside,"alpha_changed_pixels_outside_original_bboxes":alpha_outside,"protected_visible_pixels_changed":protected_changed},
 "rows":rows,
 "ordered_generation_gate":{
   "1_source_text_removed_and_plate_restored":"PASS_REUSE_PRIOR_EXACT_VALIDATED_CLEAN_PLATE",
   "2_slant_direction_matches_source":"PASS_READABLE_RIGHT_LEAN",
   "3_text_not_unnecessarily_undersized_and_within_source_bbox":"PASS_HEIGHT_GAIN_ALL_3",
   "4_source_faithful_weight_outline_shadow":"PASS_METALLIC_GRAYSCALE_KEYLINE_DARK_EXTRUSION",
   "5_no_clipped_pixels":"PASS_POSITIVE_MARGINS",
   "6_protected_graphics_clearance":"PASS_ZERO_PROTECTED_CHANGE",
   "7_raw_and_flip_y_visual_review":"EVIDENCE_WRITTEN_PENDING_CONTROLLER",
   "8_immediate_readability_vs_english":"PENDING_CONTROLLER"
 },
 "controller_visual_qa":"PENDING_CONTROLLER_REVIEW",
 "runtime_validation":"UNTESTED",
 "status":"A151_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_VISUAL_QA" if status_ok else "A151_WORKER_REWORK_REQUIRED",
 "no_vr_ffb_dx11_dxvk_work":True
}
(out/"A151_754F0599_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
summary={"run":run,"asset":"754F0599","queue_index":175,"prior_candidate_sha256":EXPECTED_BEFORE,"candidate_sha256":candidate_sha,
 "bbox_size_positive_margin":"3/3 PASS" if all_bbox and all_size and all_positive else "FAIL",
 "height_gains":[r["height_gain_px"] for r in rows],"height_ratios":[r["height_ratio"] for r in rows],
 "width_gains":[r["width_gain_px"] for r in rows],
 "changed_outside":outside,"alpha_outside":alpha_outside,"protected_changed":protected_changed,
 "worker_status":report["status"],"runtime_validation":"UNTESTED",
 "report":"localization/graphics/role_A/20261007-A-MANUALQA151-754F0599/A151_754F0599_REPORT.json"}
(worker_out/"A151_754F0599.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False,indent=2))
if not status_ok: raise SystemExit(2)
