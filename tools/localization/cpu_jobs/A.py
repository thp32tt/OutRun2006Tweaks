#!/usr/bin/env python3
import os, json, hashlib, struct, subprocess, urllib.request
from pathlib import Path
from statistics import median
from PIL import Image, ImageDraw, ImageFont, ImageChops, ImageOps, ImageFilter

if os.environ.get("OUTRUN_CPU_WORKER") != "github-actions" or os.environ.get("OUTRUN_CPU_ROLE") != "A":
    raise SystemExit("GitHub-hosted role A required")

repo=Path.cwd()
run="20261004-A-PRODUCTION16"
RETRY_CONTEXT="prior hosted worker run cancelled by concurrent branch push after job fix; retry on latest HEAD"
out=repo/"localization/graphics/role_A"/run
out.mkdir(parents=True,exist_ok=True)
worker_out=repo/"localization/graphics/worker_results"
worker_out.mkdir(parents=True,exist_ok=True)

asset_rel="textures/load/spr_sprani_selector_cvt_Exst/841E796B_512x128.dds"
candidate=repo/"localization/graphics/hd_candidates"/asset_rel
candidate.parent.mkdir(parents=True,exist_ok=True)
validator=repo/"tools/localization/validate_clean_plate.py"

work=Path("/tmp/outrun_A_prod16"); work.mkdir(parents=True,exist_ok=True)
source=work/"841E796B_HD.dds"
atlas=work/"4x_841E796B_512x128_atlas.json"

COMMIT="3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
BLOB="ec97eb9ea50bc6f54356e9238353045842c80e79"
SOURCE_SHA="112f47e7b16ecf21f722738f7fc9053d1a9852d66da9ef9d29fd25dadf2f567e"
base="https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"+COMMIT
urllib.request.urlretrieve(base+"/Release/spr_sprani_selector_cvt_Exst/841E796B_512x128.dds",source)
urllib.request.urlretrieve(base+"/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_selector_cvt_Exst/4x_841E796B_512x128_atlas.json",atlas)

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
if sha(source)!=SOURCE_SHA:
    raise RuntimeError(("source SHA mismatch",sha(source),SOURCE_SHA))

sb=source.read_bytes()
if sb[:4]!=b"DDS ": raise RuntimeError("not DDS")
H,W,pitch,depth,mips=struct.unpack_from("<5I",sb,12)
pf=struct.unpack_from("<8I",sb,76)
if (W,H,pitch,depth,mips)!=(2048,512,8192,1,1):
    raise RuntimeError((W,H,pitch,depth,mips))
if pf[1:]!=(65,0,32,0xff,0xff00,0xff0000,0xff000000):
    raise RuntimeError(("pixel format",pf))
if len(sb)!=128+W*H*4:
    raise RuntimeError(("byte size",len(sb)))

raw_source=Image.frombytes("RGBA",(W,H),sb[128:],"raw","RGBA")
source_readable=raw_source.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
aj=json.loads(atlas.read_text(encoding="utf-8"))
regions={r["idx"]:r for r in aj["regions"]}
if len(regions)!=10: raise RuntimeError(("region count",len(regions)))
target_region=regions[9]
if target_region["rect"]!=[1476,212,360,200]:
    raise RuntimeError(("target cell drift",target_region))

cx,cy,cw,ch=target_region["rect"]
cell=source_readable.crop((cx,cy,cx+cw,cy+ch))
pix=cell.load()

# No Handicap is the only localizable text. The other nine vehicle/model cards are protected.
# Build a text-effect mask from the orange source fills and the nearby dark shadow/antialias
# pixels. The yellow badge border/background is intentionally excluded.
orange_seed=Image.new("L",(cw,ch),0); sp=orange_seed.load()
for yy in range(20,170):
    for xx in range(40,325):
        r,g,b,a=pix[xx,yy]
        if a and r>180 and r-g>25 and g<200 and b<60:
            sp[xx,yy]=255
if orange_seed.getbbox()!=(58,46,291,137):
    raise RuntimeError(("orange seed drift",orange_seed.getbbox()))

near=orange_seed.filter(ImageFilter.MaxFilter(17))
npix=near.load()
effect=Image.new("L",(cw,ch),0); ep=effect.load()
for yy in range(ch):
    for xx in range(cw):
        if not npix[xx,yy]:
            continue
        r,g,b,a=pix[xx,yy]
        # Orange/black source lettering + nearby antialias/shadow only. Do not
        # absorb the white/yellow badge highlight or border into the text mask.
        if a and (((r-g)>2 and b<100) or (g<212 and b<80)):
            ep[xx,yy]=255

effect_bbox=effect.getbbox()
if effect_bbox!=(58,46,292,141):
    raise RuntimeError(("source effect bbox drift",effect_bbox))

# Reliable per-line split between "No" and "Handicap".
top_mask=Image.new("L",(cw,ch),0)
bottom_mask=Image.new("L",(cw,ch),0)
top_mask.paste(effect.crop((0,0,cw,90)),(0,0))
bottom_mask.paste(effect.crop((0,90,cw,ch)),(0,90))
top_bb=top_mask.getbbox(); bottom_bb=bottom_mask.getbbox()
if not top_bb or not bottom_bb:
    raise RuntimeError(("line masks missing",top_bb,bottom_bb))

# Convert local exact source line bboxes to atlas coordinates.
def glob(bb): return [cx+bb[0],cy+bb[1],cx+bb[2],cy+bb[3]]
top_g=glob(top_bb); bottom_g=glob(bottom_bb); block_g=glob(effect_bbox)

source_text_mask=Image.new("L",(W,H),0)
source_text_mask.paste(effect,(cx,cy))
allowed_line_bboxes=Image.new("L",(W,H),0)
ad=ImageDraw.Draw(allowed_line_bboxes)
for bb in (top_g,bottom_g):
    ad.rectangle((bb[0],bb[1],bb[2]-1,bb[3]-1),fill=255)

source_visible=source_readable.getchannel("A").point(lambda v:255 if v else 0)
protected_visible=ImageChops.multiply(source_visible,ImageOps.invert(allowed_line_bboxes))
clean_protected=ImageChops.multiply(source_visible,ImageOps.invert(source_text_mask))

# Reconstruct the yellow badge under the exact source glyph/effect footprint. The badge
# interior is flat/near-flat by row; untouched yellow pixels provide a robust row median.
clean_cell=cell.copy(); cp=clean_cell.load()
for yy in range(ch):
    xs=[xx for xx in range(cw) if ep[xx,yy]]
    if not xs: continue
    yellow=[]
    for xx in range(24,336):
        if ep[xx,yy]:
            continue
        r,g,b,a=pix[xx,yy]
        if a>200 and r>170 and g>170 and b<80:
            yellow.append((r,g,b,a))
    if len(yellow)<12:
        raise RuntimeError(("insufficient yellow reconstruction samples",yy,len(yellow)))
    fill=tuple(int(median([v[k] for v in yellow])) for k in range(4))
    for xx in xs:
        cp[xx,yy]=fill

clean=source_readable.copy()
clean.paste(clean_cell,(cx,cy))

source_png=out/"841E796B_HD_SOURCE_READABLE.png"
clean_png=out/"841E796B_HD_CLEAN_PLATE.png"
source_readable.save(source_png); clean.save(clean_png)
source_text_mask.save(out/"841E796B_HD_SOURCE_TEXT_MASK.png")
allowed_line_bboxes.save(out/"841E796B_HD_ALLOWED_LINE_BBOX_MASK.png")
protected_visible.save(out/"841E796B_HD_PROTECTED_VISIBLE_MASK.png")
clean_protected.save(out/"841E796B_HD_CLEAN_PROTECTED_VISIBLE_MASK.png")

subprocess.run([
    "python3",str(validator),str(source_png),str(clean_png),
    str(out/"841E796B_HD_SOURCE_TEXT_MASK.png"),
    "--protected-mask",str(out/"841E796B_HD_CLEAN_PROTECTED_VISIBLE_MASK.png"),
    "--report",str(out/"A_PRODUCTION16_CLEAN_PLATE_VALIDATION.json")
],check=True)
clean_rep=json.loads((out/"A_PRODUCTION16_CLEAN_PLATE_VALIDATION.json").read_text())
if clean_rep["status"]!="PASS":
    raise RuntimeError(("clean validator",clean_rep))

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
    raise RuntimeError("Noto CJK Korean unavailable")
FONT=resolve_font()

def shear_rgba(im, shear=0.18):
    extra=max(6,int(abs(shear)*im.height)+6)
    canvas=Image.new("RGBA",(im.width+extra*2,im.height),(0,0,0,0))
    canvas.alpha_composite(im,(extra,0))
    coeff=(1,-shear,shear*canvas.height,0,1,0)
    outi=canvas.transform(canvas.size,Image.Transform.AFFINE,coeff,resample=Image.Resampling.BICUBIC)
    bb=outi.getchannel("A").getbbox()
    return outi.crop(bb) if bb else outi

def render_line(text, box_w, box_h, size_ratio):
    # Orange italic fill + dark lower-right shadow, matching the two-line source badge.
    max_fs=max(12,int(box_h*size_ratio))
    for fs in range(max_fs,11,-1):
        font=ImageFont.truetype(FONT,fs)
        d=ImageDraw.Draw(Image.new("L",(8,8),0))
        tb=d.textbbox((0,0),text,font=font,stroke_width=0)
        pad=8
        fill=Image.new("RGBA",(tb[2]-tb[0]+pad*2,tb[3]-tb[1]+pad*2),(0,0,0,0))
        ImageDraw.Draw(fill).text((pad-tb[0],pad-tb[1]),text,font=font,fill=(255,150,0,255))
        fb=fill.getchannel("A").getbbox()
        fill=fill.crop(fb)
        fill=shear_rgba(fill,0.16)

        # Source has a compact dark shadow/effect just down-right of the orange glyph.
        shx=max(1,round(fs*0.055)); shy=max(1,round(fs*0.060))
        rgba=Image.new("RGBA",(fill.width+shx+4,fill.height+shy+4),(0,0,0,0))
        alpha=fill.getchannel("A")
        shadow=Image.new("RGBA",fill.size,(33,33,0,255))
        shadow.putalpha(alpha)
        rgba.alpha_composite(shadow,(shx+2,shy+2))
        rgba.alpha_composite(fill,(2,2))
        bb=rgba.getchannel("A").getbbox()
        rgba=rgba.crop(bb)
        if rgba.width<=box_w-2 and rgba.height<=box_h-2:
            return rgba,fs,shx,shy
    raise RuntimeError(("line fit failed",text,box_w,box_h))

# Preserve source line hierarchy: source "No" is the smaller upper line; source
# "Handicap" is the larger lower line. Korean syntax is split as "없음" / "핸디캡"
# to preserve corresponding source-line semantics and typography.
line_specs=[
    ("no","No","없음",top_g,1.12),
    ("handicap","Handicap","핸디캡",bottom_g,1.16),
]
final=clean.copy()
line_rows=[]
for key,src_txt,ko_txt,bb,ratio in line_specs:
    x1,y1,x2,y2=bb; bw,bh=x2-x1,y2-y1
    render_w=(bw-10) if key=="no" else bw
    glyph,fs,shx,shy=render_line(ko_txt,render_w,bh,ratio)
    if key=="no":
        # Source "No" sits near the left badge highlight. Current zero-overlap
        # policy requires positive separation, so keep the Korean upper line
        # inside the same source bbox but right-shift it away from that highlight.
        tx=x2-glyph.width-1
    else:
        tx=x1+(bw-glyph.width)//2
    ty=y1+(bh-glyph.height)//2
    tx=max(x1+1,min(tx,x2-glyph.width-1)); ty=max(y1+1,min(ty,y2-glyph.height-1))
    final.alpha_composite(glyph,(tx,ty))
    line_rows.append({
        "key":key,"source":src_txt,"korean":ko_txt,"original_bbox":bb,
        "preencode_bbox":[tx,ty,tx+glyph.width,ty+glyph.height],
        "font":"Noto Sans CJK KR Black/Bold","font_size":fs,
        "style":"source-matched orange italic fill + dark lower-right shadow",
        "shadow_offset":[shx,shy]
    })

raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
cb=sb[:128]+raw_final.tobytes("raw","RGBA")
candidate.write_bytes(cb)
candidate_sha=sha(candidate)
if cb[:128]!=sb[:128]: raise RuntimeError("DDS header changed")

decoded_raw=Image.frombytes("RGBA",(W,H),cb[128:],"raw","RGBA")
decoded=decoded_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
decoded_png=out/"841E796B_HD_FINAL_DECODED_READABLE.png"
decoded.save(decoded_png)
if ImageChops.difference(decoded,final).getbbox() is not None:
    raise RuntimeError("RGBA roundtrip mismatch")

subprocess.run([
    "python3",str(validator),str(source_png),str(decoded_png),
    str(out/"841E796B_HD_ALLOWED_LINE_BBOX_MASK.png"),
    "--protected-mask",str(out/"841E796B_HD_PROTECTED_VISIBLE_MASK.png"),
    "--report",str(out/"A_PRODUCTION16_FINAL_MASK_VALIDATION.json")
],check=True)
final_rep=json.loads((out/"A_PRODUCTION16_FINAL_MASK_VALIDATION.json").read_text())
if final_rep["status"]!="PASS":
    raise RuntimeError(("final validator",final_rep))

def changed_mask(a,b):
    d=ImageChops.difference(a,b)
    bands=d.split(); m=bands[0]
    for z in bands[1:]: m=ImageChops.lighter(m,z)
    return m.point(lambda v:255 if v else 0)
def count(mask): return sum(mask.histogram()[1:])

diff=changed_mask(source_readable,decoded)
outside=count(ImageChops.multiply(diff,ImageOps.invert(allowed_line_bboxes)))
alpha_delta=ImageChops.difference(source_readable.getchannel("A"),decoded.getchannel("A")).point(lambda v:255 if v else 0)
alpha_outside=count(ImageChops.multiply(alpha_delta,ImageOps.invert(allowed_line_bboxes)))
protected_changed=count(ImageChops.multiply(diff,protected_visible))

# Ensure all nine vehicle/model cards are byte/pixel-identical in readable orientation.
target_cell_mask=Image.new("L",(W,H),0)
ImageDraw.Draw(target_cell_mask).rectangle((cx,cy,cx+cw-1,cy+ch-1),fill=255)
other_cards_changed=count(ImageChops.multiply(diff,ImageOps.invert(target_cell_mask)))

# Current zero-overlap policy: localized glyph/effect pixels must overlap neither other
# localized labels nor preserved source text/icons/decorative foreground/protected art.
localized_mask=changed_mask(clean,decoded)
source_clean_changed=changed_mask(source_readable,clean)
residue_selected=ImageChops.multiply(source_text_mask,ImageOps.invert(source_clean_changed))
source_text_residue_pixels=count(residue_selected)
localized_preserved_source_text_overlap_pixels=count(ImageChops.multiply(localized_mask,residue_selected))

# Preserve all visible content outside the target card, and within the yellow card preserve
# non-background decorative foreground (white/black border/shadow). Source text is excluded
# because it is intentionally reconstructed before Korean lettering.
protected_foreground=ImageChops.multiply(source_visible,ImageOps.invert(target_cell_mask))
badge_fg_local=Image.new("L",(cw,ch),0); bfp=badge_fg_local.load()
for yy in range(ch):
    for xx in range(cw):
        if ep[xx,yy]:
            continue
        r0,g0,b0,a0=pix[xx,yy]
        if not a0:
            continue
        yellow_background=(r0>165 and g0>165 and b0<110)
        if not yellow_background:
            bfp[xx,yy]=255
badge_fg=Image.new("L",(W,H),0); badge_fg.paste(badge_fg_local,(cx,cy))
protected_foreground=ImageChops.lighter(protected_foreground,badge_fg)
localized_protected_foreground_overlap_pixels=count(ImageChops.multiply(localized_mask,protected_foreground))
# One-pixel positive separation from protected foreground where the source card provides it.
localized_protected_foreground_touch_pixels=count(ImageChops.multiply(localized_mask.filter(ImageFilter.MaxFilter(3)),protected_foreground))

rows=[]
line_masks_global=[]
for row in line_rows:
    ob=row["original_bbox"]
    # Localized text is exactly the clean->final delta inside the line source bbox.
    lm=changed_mask(clean.crop(tuple(ob)),decoded.crop(tuple(ob)))
    bb=lm.getbbox()
    loc=[ob[0]+bb[0],ob[1]+bb[1],ob[0]+bb[2],ob[1]+bb[3]] if bb else None
    ok=loc is not None and loc[0]>=ob[0] and loc[1]>=ob[1] and loc[2]<=ob[2] and loc[3]<=ob[3]
    size_ok=loc is not None and loc[2]-loc[0]<=ob[2]-ob[0] and loc[3]-loc[1]<=ob[3]-ob[1]
    positive=loc is not None and loc[0]>ob[0] and loc[1]>ob[1] and loc[2]<ob[2] and loc[3]<ob[3]
    lg=Image.new("L",(W,H),0)
    lg.paste(lm,(ob[0],ob[1]))
    line_masks_global.append((row["key"],lg))
    row.update({
        "localized_bbox":loc,
        "source_width":ob[2]-ob[0],"source_height":ob[3]-ob[1],
        "localized_width":loc[2]-loc[0] if loc else None,"localized_height":loc[3]-loc[1] if loc else None,
        "delta_left":loc[0]-ob[0] if loc else None,"delta_right":ob[2]-loc[2] if loc else None,
        "delta_top":loc[1]-ob[1] if loc else None,"delta_bottom":ob[3]-loc[3] if loc else None,
        "containment":"PASS" if ok else "FAIL","size_ceiling":"PASS" if size_ok else "FAIL",
        "positive_margin":"PASS" if positive else "EDGE_TOUCH_OR_FAIL",
        "raw_original_bbox":[ob[0],H-ob[3],ob[2],H-ob[1]],
        "raw_localized_bbox":[loc[0],H-loc[3],loc[2],H-loc[1]] if loc else None,
        "raw_containment":"PASS" if ok else "FAIL",
        "rework_status":"A_PRODUCTION16_NEW_HD_CANDIDATE"
    })
    rows.append(row)

# Whole-block gate in addition to per-line gates.
block_delta=changed_mask(clean.crop(tuple(block_g)),decoded.crop(tuple(block_g)))
bbb=block_delta.getbbox()
block_loc=[block_g[0]+bbb[0],block_g[1]+bbb[1],block_g[0]+bbb[2],block_g[1]+bbb[3]] if bbb else None
block_ok=block_loc is not None and block_loc[0]>=block_g[0] and block_loc[1]>=block_g[1] and block_loc[2]<=block_g[2] and block_loc[3]<=block_g[3]
block_size_ok=block_loc is not None and block_loc[2]-block_loc[0]<=block_g[2]-block_g[0] and block_loc[3]-block_loc[1]<=block_g[3]-block_g[1]

all_bbox=all(r["containment"]=="PASS" and r["raw_containment"]=="PASS" for r in rows) and block_ok
all_size=all(r["size_ceiling"]=="PASS" for r in rows) and block_size_ok
all_positive=all(r["positive_margin"]=="PASS" for r in rows)

localized_label_overlap_pixels=0
localized_label_touch_pixels=0
for i,(ka,ma) in enumerate(line_masks_global):
    for kb,mb in line_masks_global[i+1:]:
        localized_label_overlap_pixels += count(ImageChops.multiply(ma,mb))
        localized_label_touch_pixels += count(ImageChops.multiply(ma.filter(ImageFilter.MaxFilter(3)),mb))

zero_overlap_pass=(
    localized_label_overlap_pixels==0
    and localized_label_touch_pixels==0
    and localized_protected_foreground_overlap_pixels==0
    and localized_protected_foreground_touch_pixels==0
    and localized_preserved_source_text_overlap_pixels==0
    and source_text_residue_pixels==0
)

# Visual evidence: full readable/raw atlas, source-clean-final target cell, and line contacts.
def gray(im):
    bg=Image.new("RGBA",im.size,(96,96,96,255)); bg.alpha_composite(im); return bg.convert("RGB")
gray(source_readable).save(out/"A_PRODUCTION16_SOURCE_FULL_GRAY.jpg",quality=94)
gray(decoded).save(out/"A_PRODUCTION16_FINAL_FULL_GRAY.jpg",quality=94)
gray(decoded_raw).save(out/"A_PRODUCTION16_FINAL_RAW_GRAY.jpg",quality=94)

src_cell=gray(source_readable.crop((cx,cy,cx+cw,cy+ch)))
cln_cell=gray(clean.crop((cx,cy,cx+cw,cy+ch)))
fin_cell=gray(decoded.crop((cx,cy,cx+cw,cy+ch)))
trip=Image.new("RGB",(cw*3+24,ch+30),(230,230,230))
trip.paste(src_cell,(0,30)); trip.paste(cln_cell,(cw+12,30)); trip.paste(fin_cell,(cw*2+24,30))
ImageDraw.Draw(trip).text((4,5),"SOURCE             CLEAN              FINAL",fill=(0,0,0))
trip.save(out/"A_PRODUCTION16_TARGET_SOURCE_CLEAN_FINAL.jpg",quality=95)

contacts=[]
for r in rows:
    ob=r["original_bbox"]; m=8
    x1=max(0,ob[0]-m);y1=max(0,ob[1]-m);x2=min(W,ob[2]+m);y2=min(H,ob[3]+m)
    a=gray(source_readable.crop((x1,y1,x2,y2))); b=gray(decoded.crop((x1,y1,x2,y2)))
    rowim=Image.new("RGB",(a.width+b.width+12,max(a.height,b.height)+24),(235,235,235))
    rowim.paste(a,(0,24)); rowim.paste(b,(a.width+12,24))
    ImageDraw.Draw(rowim).text((3,2),r["key"]+" SOURCE | FINAL",fill=(0,0,0))
    contacts.append(rowim)
sw=max(x.width for x in contacts); sh=sum(x.height for x in contacts)+4*(len(contacts)-1)
sheet=Image.new("RGB",(sw,sh),(235,235,235)); yy=0
for c in contacts: sheet.paste(c,(0,yy)); yy+=c.height+4
sheet.save(out/"A_PRODUCTION16_LINE_CONTACT.jpg",quality=95)

status_ok=(clean_rep["status"]=="PASS" and final_rep["status"]=="PASS" and all_bbox and all_size and all_positive and outside==0 and alpha_outside==0 and protected_changed==0 and other_cards_changed==0 and zero_overlap_pass)

report={
    "schema_version":1,"role":"A","run":run,"worker":os.environ.get("OUTRUN_CPU_WORKER"),"base_head":os.environ.get("GITHUB_SHA"),
    "retry_context":RETRY_CONTEXT,
    "index":107,"asset":asset_rel,
    "source_provenance":{
        "repository":"Sonic-TV/OR2006Sprites","commit":COMMIT,"git_blob_sha1":BLOB,"sha256":SOURCE_SHA,
        "path":"Release/spr_sprani_selector_cvt_Exst/841E796B_512x128.dds",
        "classification":"authoritative high-resolution source; stale filename suffix, DDS header 2048x512 RGBA32"
    },
    "source_sha256":SOURCE_SHA,"candidate_sha256":candidate_sha,"candidate_path":str(candidate.relative_to(repo)),
    "structure":{"dimensions":[W,H],"format":"RGBA32","pitch":pitch,"mipmaps":mips,"bytes":len(sb),"header_128_exact":True,"raw_orientation":"mirror_y"},
    "translation":{
        "catalog":"No Handicap -> 핸디캡 없음",
        "raster_line_mapping":[{"source":"No","korean":"없음"},{"source":"Handicap","korean":"핸디캡"}],
        "reason":"preserve source two-line semantics and intentional upper-small/lower-large typography"
    },
    "protected_content":"all nine Ferrari vehicle/model cards, names, pictograms, blue card art and non-target pixels",
    "source_effect_bbox":block_g,"source_line_bboxes":{"No":top_g,"Handicap":bottom_g},
    "clean_plate_validator":clean_rep,"final_mask_validator":final_rep,
    "decoded_changes":{
        "changed_pixels_total":count(diff),"changed_pixels_outside_source_line_bboxes":outside,
        "alpha_changed_pixels_outside_source_line_bboxes":alpha_outside,
        "protected_visible_pixels_changed":protected_changed,
        "other_vehicle_model_card_pixels_changed":other_cards_changed,
        "source_text_residue_pixels":source_text_residue_pixels
    },
    "zero_overlap_gate":{
        "localized_label_overlap_pixels":localized_label_overlap_pixels,
        "localized_label_touch_pixels":localized_label_touch_pixels,
        "localized_protected_foreground_overlap_pixels":localized_protected_foreground_overlap_pixels,
        "localized_protected_foreground_touch_pixels":localized_protected_foreground_touch_pixels,
        "localized_preserved_source_text_overlap_pixels":localized_preserved_source_text_overlap_pixels,
        "source_text_residue_pixels":source_text_residue_pixels,
        "status":"PASS" if zero_overlap_pass else "FAIL"
    },
    "rows":rows,
    "whole_block":{"original_bbox":block_g,"localized_bbox":block_loc,"containment":"PASS" if block_ok else "FAIL","size_ceiling":"PASS" if block_size_ok else "FAIL"},
    "all_2_lines_plus_block_readable_and_raw_bbox_pass":all_bbox,
    "all_2_lines_plus_block_size_ceiling_pass":all_size,
    "all_2_lines_positive_margin":all_positive,
    "controller_visual_qa":"PENDING_CONTROLLER_REVIEW",
    "runtime_validation":"UNTESTED",
    "status":"A_PRODUCTION16_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_VISUAL_QA" if status_ok else "A_PRODUCTION16_WORKER_REWORK_REQUIRED"
}
(out/"A_PRODUCTION16_841E796B_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
summary={
    "run":run,"asset":"841E796B","index":107,"source_sha256":SOURCE_SHA,"candidate_sha256":candidate_sha,
    "source_dimensions":[W,H],"format":"RGBA32","localized_label":"No Handicap -> 핸디캡 없음",
    "line_bbox_pass":"2/2 + whole block" if all_bbox else "FAIL",
    "size_ceiling":"2/2 + whole block" if all_size else "FAIL","positive_margin":"2/2" if all_positive else "FAIL",
    "clean_plate_validator":clean_rep["status"],"final_mask_validator":final_rep["status"],
    "changed_pixels_outside_source_line_bboxes":outside,"alpha_changed_pixels_outside_source_line_bboxes":alpha_outside,
    "protected_visible_pixels_changed":protected_changed,"other_vehicle_model_card_pixels_changed":other_cards_changed,
    "zero_overlap_status":"PASS" if zero_overlap_pass else "FAIL",
    "localized_label_overlap_pixels":localized_label_overlap_pixels,
    "localized_label_touch_pixels":localized_label_touch_pixels,
    "localized_protected_foreground_overlap_pixels":localized_protected_foreground_overlap_pixels,
    "localized_protected_foreground_touch_pixels":localized_protected_foreground_touch_pixels,
    "localized_preserved_source_text_overlap_pixels":localized_preserved_source_text_overlap_pixels,
    "source_text_residue_pixels":source_text_residue_pixels,
    "worker_status":report["status"],"runtime_validation":"UNTESTED",
    "report":"localization/graphics/role_A/20261004-A-PRODUCTION16/A_PRODUCTION16_841E796B_REPORT.json"
}
(worker_out/"A_PRODUCTION16_841E796B.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False,indent=2))
if not status_ok: raise SystemExit(2)
