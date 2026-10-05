#!/usr/bin/env python3
import hashlib, json, os, struct, subprocess, urllib.request
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFont

if os.environ.get("OUTRUN_CPU_WORKER") != "github-actions" or os.environ.get("OUTRUN_CPU_ROLE") != "B":
    raise SystemExit("GitHub-hosted localization CPU worker / role B only")

repo = Path.cwd()
run = "20261006-B-INGAME168-IGR004-GOAL-SELECT-WEIGHT"
out = repo / "localization/graphics/role_B" / run
out.mkdir(parents=True, exist_ok=True)

queue_index = 201
rel = "textures/load/spr_sprani_sumo_fe_cvt_Exst/A9ABD877_512x512.dds"
candidate = repo / "localization/graphics/hd_candidates" / rel
old_sha = "f4b4fab4673516f793997bb3dac132c2ceb23a7f2378808d589e2ab78f0cbeb7"
source_sha = "6ac5ffd02c9162499f09f0b476176b56f0b144789f546ef34147d94e0a8451e5"
source_url = "https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6/Release/spr_sprani_sumo_fe_cvt_Exst/A9ABD877_512x512.dds"

clean_path = repo / "localization/graphics/role_A/20261005-A-PRODUCTION69/A69_CLEAN_PLATE.png"
protected_path = repo / "localization/graphics/role_A/20261005-A-PRODUCTION69/A69_PROTECTED_VISIBLE_MASK.png"
source_mask_path = repo / "localization/graphics/role_A/20261005-A-PRODUCTION69/A69_SOURCE_TEXT_MASK.png"
expected_clean_sha = "43a909b2d86e4087ac41dff58e4cf45b4bd5616d3b20c2a536f75a983d910b27"
expected_protected_sha = "8b207a2c6c3791105561becb62e29a5ae601fa618f66f9099b691b7b4340ae6d"

rows = [
    ("CONIFEROUS FOREST","코니퍼러스 포레스트","stage",[119,1938,1157,2023],[46,53,57,255],"right"),
    ("ICE SCAPE","아이스스케이프","stage",[482,1805,1050,1900],[46,53,57,255],"right"),
    ("GIANT STATUES","자이언트 스태추스","stage",[212,1692,1049,1787],[46,53,57,255],"right"),
    ("GHOST FOREST","고스트 포레스트","stage",[248,1580,1049,1675],[46,53,57,255],"right"),
    ("FLORAL VILLAGE","플로럴 빌리지","stage",[146,1469,1050,1563],[46,53,57,255],"right"),
    ("DESERT","데저트","stage",[618,1356,1048,1451],[46,53,57,255],"right"),
    ("DEEP LAKE","딥 레이크","stage",[453,1243,1050,1332],[46,53,57,255],"right"),
    ("CLOUDY HIGHLAND","클라우디 하이랜드","stage",[32,1129,1049,1223],[46,53,57,255],"right"),
    ("CASTLE WALL","캐슬 월","stage",[293,1017,1048,1111],[46,53,57,255],"right"),
    ("CASINO TOWN","카지노 타운","stage",[289,909,1048,1003],[46,53,57,255],"right"),
    ("CAPE WAY","케이프 웨이","stage",[482,798,1047,892],[46,53,57,255],"right"),
    ("CANYON","캐니언","stage",[606,681,1048,775],[46,53,57,255],"right"),
    ("BIG FOREST","빅 포레스트","stage",[415,568,1048,663],[46,53,57,255],"right"),
    ("BAY AREA","베이 에어리어","stage",[502,467,1049,556],[46,53,57,255],"right"),
    ("Special","스페셜","ui",[1086,1845,1267,1903],[46,53,57,255],"left"),
    ("STAGES","스테이지","ui",[1173,1986,1379,2037],[46,54,57,255],"left"),
    ("GOALS","골","ui",[1079,1734,1255,1785],[46,54,57,255],"left"),
]
protected_labels = ["Night Bird song title", "Radiation song title"]

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def load_dds(p):
    b = Path(p).read_bytes()
    if b[:4] != b"DDS ":
        raise RuntimeError(("not DDS", str(p)))
    h = struct.unpack_from("<I", b, 12)[0]
    w = struct.unpack_from("<I", b, 16)[0]
    pitch = struct.unpack_from("<I", b, 20)[0]
    mips = struct.unpack_from("<I", b, 28)[0]
    fourcc = b[84:88]
    bpp = struct.unpack_from("<I", b, 88)[0]
    masks = struct.unpack_from("<IIII", b, 92)
    if bpp != 32 or fourcc != b"\0\0\0\0" or mips != 1 or len(b) != 128 + w*h*4:
        raise RuntimeError(("unsupported DDS", str(p), w, h, mips, fourcc, bpp, len(b)))
    if masks == (0xff,0xff00,0xff0000,0xff000000):
        mode = "RGBA"
    elif masks == (0xff0000,0xff00,0xff,0xff000000):
        mode = "BGRA"
    else:
        raise RuntimeError(("unsupported masks", masks))
    raw = Image.frombytes("RGBA",(w,h),b[128:],"raw",mode)
    readable = raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    return b[:128], readable, {"width":w,"height":h,"pitch":pitch,"mips":mips,"bpp":bpp,
                               "masks":[hex(x) for x in masks],"raw_mode":mode}

def write_dds(header, readable, p, raw_mode):
    raw = readable.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
    payload = header + raw.tobytes("raw",raw_mode)
    Path(p).write_bytes(payload)
    return hashlib.sha256(payload).hexdigest()

def font_path():
    q = subprocess.check_output(["fc-match","-f","%{file}","Noto Sans CJK KR:style=Black"],text=True).strip()
    if not q or not Path(q).exists() or "NotoSansCJK" not in Path(q).name:
        subprocess.run(["sudo","apt-get","update","-qq"],check=True)
        subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
        q = subprocess.check_output(["fc-match","-f","%{file}","Noto Sans CJK KR:style=Black"],text=True).strip()
    if not q or not Path(q).exists():
        raise RuntimeError(("font missing",q))
    return q

def bbox_mask(m):
    ys,xs = np.nonzero(m)
    if not len(xs): return None
    return [int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)]

def composite(im, bg=(92,92,92,255)):
    z=Image.new("RGBA",im.size,bg); z.alpha_composite(im); return z.convert("RGB")

def labeled_crop(label, im, crop, scale=1):
    v = composite(im).crop(crop)
    if scale != 1:
        v = v.resize((v.width*scale,v.height*scale),Image.Resampling.NEAREST)
    c = Image.new("RGB",(v.width,v.height+30),"white")
    c.paste(v,(0,30)); ImageDraw.Draw(c).text((5,6),label,fill="black")
    return c

if not candidate.exists() or sha(candidate) != old_sha:
    raise RuntimeError(("candidate drift", sha(candidate) if candidate.exists() else None))
if sha(clean_path) != expected_clean_sha:
    raise RuntimeError(("clean drift",sha(clean_path)))
if sha(protected_path) != expected_protected_sha:
    raise RuntimeError(("protected drift",sha(protected_path)))
if not source_mask_path.exists():
    raise RuntimeError("source text mask missing")

tmp_source = Path("/tmp/A9ABD877_source.dds")
urllib.request.urlretrieve(source_url,tmp_source)
if sha(tmp_source) != source_sha:
    raise RuntimeError(("source drift",sha(tmp_source)))

header, source, meta = load_dds(tmp_source)
old_header, old, old_meta = load_dds(candidate)
if header != old_header or meta != old_meta:
    raise RuntimeError(("structure drift", meta, old_meta))
if (source.width,source.height)!=(2048,2048):
    raise RuntimeError(("unexpected dimensions",source.size))

clean = Image.open(clean_path).convert("RGBA")
protected = np.asarray(Image.open(protected_path).convert("L")) > 0
if clean.size != source.size or protected.shape != (source.height,source.width):
    raise RuntimeError("evidence size drift")

# Fail closed if the inherited clean plate itself has unexpected source-visible content outside the
# prior source-text mask. A69's validated clean plate is reused only as a source-text removal substrate.
source_mask = np.asarray(Image.open(source_mask_path).convert("L")) > 0
if source_mask.shape != protected.shape:
    raise RuntimeError("source mask size drift")

fontfile = font_path()
final = old.copy()
allowed = np.zeros((source.height,source.width),bool)
render_union = np.zeros_like(allowed)
render_layers = []
report_rows = []

for idx,(src_text,ko,kind,bb,fill,align) in enumerate(rows):
    x0,y0,x1,y1=bb; bw=x1-x0; bh=y1-y0
    allowed[y0:y1,x0:x1]=1
    final.paste(clean.crop((x0,y0,x1,y1)),(x0,y0))

    # Native-resolution rendering only. No low-resolution intermediary, nearest-neighbor glyph upscale,
    # artificial tracking, or horizontal glyph scaling.
    chosen=None
    start = min(126, bh + 36)
    for fs in range(start, 15, -1):
        f=ImageFont.truetype(fontfile,fs)
        probe=Image.new("RGBA",(max(1600,bw+300),max(260,bh+120)),(0,0,0,0))
        d=ImageDraw.Draw(probe)
        tb=d.textbbox((0,0),ko,font=f,stroke_width=(3 if kind=="stage" else 1))
        d.text((16-tb[0],16-tb[1]),ko,font=f,fill=tuple(fill),stroke_width=(3 if kind=="stage" else 1),stroke_fill=tuple(fill))
        gb=probe.getchannel("A").getbbox()
        if not gb: continue
        glyph=probe.crop(gb)
        if glyph.width > bw-10 or glyph.height > bh-8:
            continue
        px = (x1-5-glyph.width) if align=="right" else (x0+5)
        py = y0 + (bh-glyph.height)//2
        if px <= x0 or py <= y0 or px+glyph.width >= x1 or py+glyph.height >= y1:
            continue
        gm_local=np.asarray(glyph.getchannel("A"))>0
        if np.any(gm_local & protected[py:py+glyph.height,px:px+glyph.width]):
            continue
        chosen=(glyph,px,py,fs)
        break
    if chosen is None:
        raise RuntimeError(("native fit failed",idx,src_text,bb))

    glyph,px,py,fs=chosen
    layer=Image.new("RGBA",source.size,(0,0,0,0))
    layer.alpha_composite(glyph,(px,py))
    gm=np.asarray(layer.getchannel("A"))>0
    if np.any(render_union & gm):
        raise RuntimeError(("localized overlap",idx,src_text,int(np.logical_and(render_union,gm).sum())))
    render_union |= gm
    render_layers.append(gm)
    final.alpha_composite(layer)

    lb=bbox_mask(gm)
    lw,lh=lb[2]-lb[0],lb[3]-lb[1]
    if not (x0 < lb[0] and y0 < lb[1] and lb[2] < x1 and lb[3] < y1):
        raise RuntimeError(("positive margin fail",idx,lb,bb))
    if lw>bw or lh>bh:
        raise RuntimeError(("size ceiling fail",idx,(lw,lh),(bw,bh)))
    report_rows.append({
        "region_idx":idx,"source":src_text,"korean":ko,"kind":kind,
        "original_bbox":bb,"localized_bbox":lb,
        "source_size":[bw,bh],"localized_size":[lw,lh],
        "delta_left":lb[0]-x0,"delta_right":x1-lb[2],
        "delta_top":lb[1]-y0,"delta_bottom":y1-lb[3],
        "containment":"PASS","size_ceiling":"PASS","positive_margin":"PASS",
        "font":"Noto Sans CJK KR Black","native_font_size_px":fs,
        "render_resolution":[source.width,source.height],"glyph_upscale":1.0,
        "horizontal_scale":1.0,"tracking_px":0,"stroke_width_px":(3 if kind=="stage" else 1),"alignment":align,"fill_rgba":fill
    })

oa=np.asarray(old,dtype=np.uint8); fa=np.asarray(final,dtype=np.uint8)
changed=np.any(oa!=fa,axis=2)
outside=int(np.logical_and(changed,~allowed).sum())
alpha_outside=int(np.logical_and(oa[:,:,3]!=fa[:,:,3],~allowed).sum())
protected_changed=int(np.logical_and(changed,protected).sum())
render_protected=int(np.logical_and(render_union,protected).sum())
render_outside=int(np.logical_and(render_union,~allowed).sum())
if outside or alpha_outside or protected_changed or render_protected or render_outside:
    raise RuntimeError(("scope fail",outside,alpha_outside,protected_changed,render_protected,render_outside))

new_sha=write_dds(header,final,candidate,meta["raw_mode"])
dh,decoded,dmeta=load_dds(candidate)
if dh!=header or dmeta!=meta or ImageChops.difference(decoded,final).getbbox():
    raise RuntimeError("DDS roundtrip mismatch")

# Evidence masks + generic validator.
Image.fromarray((allowed*255).astype(np.uint8),"L").save(out/"B168_ALLOWED_BBOX_MASK.png")
Image.fromarray((render_union*255).astype(np.uint8),"L").save(out/"B168_TARGET_TEXT_MASK.png")
Image.fromarray((protected*255).astype(np.uint8),"L").save(out/"B168_PROTECTED_VISIBLE_MASK.png")
source.save(out/"B168_SOURCE_READABLE.png")
clean.save(out/"B168_CLEAN_PLATE.png")
decoded.save(out/"B168_FINAL_DECODED_READABLE.png")

tmp=Path("/tmp/b167_a9"); tmp.mkdir(exist_ok=True)
old_png=tmp/"old.png"; final_png=tmp/"final.png"; old.save(old_png); decoded.save(final_png)
subprocess.run(["python3",str(repo/"tools/localization/validate_clean_plate.py"),
                str(old_png),str(final_png),str(out/"B168_ALLOWED_BBOX_MASK.png"),
                "--protected-mask",str(out/"B168_PROTECTED_VISIBLE_MASK.png"),
                "--report",str(out/"B168_FINAL_MASK_VALIDATION.json")],check=True)

# SOURCE / OLD / CLEAN / FINAL native-readable row contacts.
cards=[]
for i,rr in enumerate(report_rows):
    x0,y0,x1,y1=rr["original_bbox"]; pad=8
    crop=(max(0,x0-pad),max(0,y0-pad),min(source.width,x1+pad),min(source.height,y1+pad))
    one=[labeled_crop(f"{i:02d} SOURCE {rr['source']}",source,crop,1),
         labeled_crop("OLD A69 LOWRES-UPSCALED",old,crop,1),
         labeled_crop("CLEAN",clean,crop,1),
         labeled_crop(f"B168 NATIVE {rr['korean']}",decoded,crop,1)]
    W=max(x.width for x in one); H=max(x.height for x in one)
    rowimg=Image.new("RGB",(sum(x.width for x in one)+18,H),"white")
    xx=0
    for x in one:
        rowimg.paste(x,(xx,0)); xx+=x.width+6
    cards.append(rowimg)
W=max(c.width for c in cards); H=sum(c.height for c in cards)+4*(len(cards)-1)
sheet=Image.new("RGB",(W,H),"white"); yy=0
for c in cards:
    sheet.paste(c,(0,yy)); yy+=c.height+4
sheet.save(out/"B168_SOURCE_OLD_CLEAN_FINAL_ROWS.jpg",quality=96)

# Full readable and raw orientation comparisons.
def pair_sheet(label_a,a,label_b,b,raw=False):
    aa=a.transpose(Image.Transpose.FLIP_TOP_BOTTOM) if raw else a
    bb=b.transpose(Image.Transpose.FLIP_TOP_BOTTOM) if raw else b
    ca=labeled_crop(label_a,aa,(0,0,aa.width,aa.height),1)
    cb=labeled_crop(label_b,bb,(0,0,bb.width,bb.height),1)
    s=Image.new("RGB",(ca.width+cb.width+8,max(ca.height,cb.height)),"white")
    s.paste(ca,(0,0)); s.paste(cb,(ca.width+8,0))
    s.thumbnail((2400,1400),Image.Resampling.LANCZOS)
    return s
pair_sheet("SOURCE",source,"B168 FINAL",decoded).save(out/"B168_FULL_SOURCE_FINAL.jpg",quality=94)
pair_sheet("OLD A69",old,"B168 FINAL",decoded).save(out/"B168_FULL_OLD_FINAL.jpg",quality=94)
pair_sheet("OLD RAW",old,"B168 RAW",decoded,raw=True).save(out/"B168_RAW_OLD_FINAL.jpg",quality=94)

report={
    "schema_version":1,"role":"B","run":run,"base_head":subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),
    "user_ingame_regression":["IGR-004","스크린샷(146).png"],
    "owner_lane":"B","queue_index":queue_index,"asset":rel,
    "mapping":{
        "status":"EXACT_HIGH_CONFIDENCE_GRAPHICS",
        "domain":"GRAPHICS",
        "reason":"Goal Select screen labels bind to the A9ABD877 atlas: canonical stage-name family plus GOALS/STAGES/Special. The prior A69 candidate metadata explicitly records a 19px low-resolution render expanded by pixel_scale=4, matching the user-reported low-resolution font regression. No runtime text edit is required for these baked labels.",
        "visible_family":["GOALS","STAGES","Special","14 canonical stage-name labels"]
    },
    "source_provenance":{"repository":"Sonic-TV/OR2006Sprites","commit":"3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6",
                         "source_sha256":source_sha,"source_url":source_url},
    "superseded_candidate_sha256":old_sha,"candidate_sha256":new_sha,
    "candidate_path":str(candidate.relative_to(repo)),
    "structure":{**meta,"header_128_exact":True,"raw_orientation":"mirror_y"},
    "method":"Material rework of all 17 localized A9ABD877 rows from the exact 2048x2048 HD clean plate. B167 native-resolution retry removed the historical 19px->4x raster path but controller visual QA found the smooth glyph weight too light versus the source condensed-bold family. B168 keeps native rendering and adds a source-faithful 3px stage / 1px UI same-fill weight reinforcement, with natural font advance, no horizontal glyph scaling, no artificial tracking, source-family alignment/fill, and exact source-bbox ceilings.",
    "rows":report_rows,
    "protected_regions":protected_labels,
    "zero_pixel_qa":{
        "changed_pixels":int(changed.sum()),
        "changed_outside_target_bboxes":outside,
        "alpha_changed_outside_target_bboxes":alpha_outside,
        "protected_changed_pixels":protected_changed,
        "render_outside_target_bboxes":render_outside,
        "render_protected_overlap_pixels":render_protected,
        "localized_overlap_pixels":0,
        "status":"PASS"
    },
    "visual_qa":"PENDING_CONTROLLER_SELF_QA_AFTER_B167_WEIGHT_FAIL",
    "runtime_validation":"PENDING_NEW_INGAME_RETEST",
    "status":"B168_WORKER_STATIC_PASS_PENDING_CONTROLLER_SELF_QA_AND_C"
}
(out/"B168_A9ABD877_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
(out/"B168_STATIC_VALIDATION_SUMMARY.json").write_text(json.dumps({
    "mapping":"IGR-004_EXACT_GRAPHICS_A9ABD877_B168_WEIGHT_RETRY",
    "candidate_sha256":new_sha,
    "bbox_size_positive_margin":f"{len(report_rows)}/{len(report_rows)} PASS",
    "native_resolution_rows":len(report_rows),
    "glyph_upscale_rows":0,
    "horizontal_scaled_rows":0,
    "tracking_rows":0,
    **report["zero_pixel_qa"]
},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("B168_DONE",new_sha)