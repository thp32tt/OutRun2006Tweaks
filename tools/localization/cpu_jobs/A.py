#!/usr/bin/env python3
import os, json, hashlib, struct, subprocess, urllib.request
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageChops, ImageOps

if os.environ.get("OUTRUN_CPU_WORKER") != "github-actions" or os.environ.get("OUTRUN_CPU_ROLE") != "A":
    raise SystemExit("GitHub-hosted role A required")

repo = Path.cwd()
run = "20261004-A-PRODUCTION13"
out = repo / "localization/graphics/role_A" / run
out.mkdir(parents=True, exist_ok=True)
worker_out = repo / "localization/graphics/worker_results"
worker_out.mkdir(parents=True, exist_ok=True)

asset_rel = "textures/load/spr_sprani_etc_cvt_Exst/AD720950_1024x256.dds"
candidate = repo / "localization/graphics/hd_candidates" / asset_rel
candidate.parent.mkdir(parents=True, exist_ok=True)
validator = repo / "tools/localization/validate_clean_plate.py"

work = Path("/tmp/outrun_A_prod13")
work.mkdir(parents=True, exist_ok=True)
source = work / "AD720950_HD.dds"
atlas = work / "4x_AD720950_1024x256_atlas.json"

COMMIT = "3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
BLOB = "98b120d89b690068e5e50edbb1e7dcd28b9ea928"
SOURCE_SHA = "141e1f0773b82a8eca6ff49cd93d637221b96211566541f97de9ef4fc454d26f"

base = "https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/" + COMMIT
urllib.request.urlretrieve(base + "/Release/spr_sprani_etc_cvt_Exst/AD720950_1024x256.dds", source)
urllib.request.urlretrieve(base + "/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_etc_cvt_Exst/4x_AD720950_1024x256_atlas.json", atlas)

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

if sha(source) != SOURCE_SHA:
    raise RuntimeError(("source SHA", sha(source), SOURCE_SHA))

sb = source.read_bytes()
if sb[:4] != b"DDS ":
    raise RuntimeError("not DDS")
H, W, pitch, depth, mips = struct.unpack_from("<5I", sb, 12)
pf = struct.unpack_from("<8I", sb, 76)
if (W,H,pitch,depth,mips) != (4096,1024,16384,1,1):
    raise RuntimeError((W,H,pitch,depth,mips))
if pf[1:] != (65,0,32,0xff,0xff00,0xff0000,0xff000000):
    raise RuntimeError(("pixel format", pf))
if len(sb) != 128 + W*H*4:
    raise RuntimeError(("byte size", len(sb)))

raw_source = Image.frombytes("RGBA", (W,H), sb[128:], "raw", "RGBA")
source_readable = raw_source.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
aj = json.loads(atlas.read_text(encoding="utf-8"))
regions = {r["idx"]:r for r in aj["regions"]}
if len(regions) != 7:
    raise RuntimeError("unexpected atlas region count")

def count(mask):
    return sum(mask.histogram()[1:])

def binary_alpha(im):
    return im.getchannel("A").point(lambda v:255 if v else 0)

def changed_mask(a,b):
    d = ImageChops.difference(a,b)
    bands = d.split()
    m = bands[0]
    for z in bands[1:]:
        m = ImageChops.lighter(m,z)
    return m.point(lambda v:255 if v else 0)

def extract_hd_bbox(stock_bbox, region_idx, margin_x=20, margin_y=12):
    # Stock 1x boxes are discovery hints only. Measure the actual permitted bbox
    # from nonzero alpha in the authoritative 4x HD DDS, clipped to its sprite cell.
    sx1,sy1,sx2,sy2 = stock_bbox
    rr=regions[region_idx]
    rx,ry,rw,rh=rr["rect"]
    rx2,ry2=rx+rw,ry+rh
    zx1=max(rx,sx1*4-margin_x); zy1=max(ry,sy1*4-margin_y)
    zx2=min(rx2,sx2*4+margin_x); zy2=min(ry2,sy2*4+margin_y)
    zone=(zx1,zy1,zx2,zy2)
    bb=source_readable.crop(zone).getchannel("A").getbbox()
    if not bb:
        raise RuntimeError(("empty HD search zone",stock_bbox,region_idx,zone))
    gb=[zx1+bb[0],zy1+bb[1],zx1+bb[2],zy1+bb[3]]
    # Touching the artificial search edge means the discovery window is too small;
    # touching the actual sprite-cell edge is allowed because that is source evidence.
    bad_left = gb[0] <= zx1 and zx1 > rx
    bad_top = gb[1] <= zy1 and zy1 > ry
    bad_right = gb[2] >= zx2 and zx2 < rx2
    bad_bottom = gb[3] >= zy2 and zy2 < ry2
    if bad_left or bad_top or bad_right or bad_bottom:
        raise RuntimeError(("HD bbox touches search boundary",stock_bbox,region_idx,zone,gb))
    return gb

targets=[]

# Exact low-resolution source glyph/effect bboxes are used only to isolate each label.
# The final permitted boxes below are re-measured from authoritative HD source alpha.
line_specs = [
    ("symbols","Symbols","기호",4,[940,18,989,32]),
    ("shift","Shift","Shift",4,[940,44,968,55]),
    ("caps_lock","Caps Lock","대문자 고정",4,[940,69,1000,83]),
    ("accents","Accents","악센트",4,[940,94,986,105]),
    ("done","Done","완료",4,[940,119,969,130]),
]
preserved_shift_bbox=None
for key,src,kor,idx,stock_box in line_specs:
    gb=extract_hd_bbox(stock_box, idx, margin_x=24, margin_y=16)
    if key=="shift":
        preserved_shift_bbox=gb
    else:
        targets.append({"key":key,"source":src,"korean":kor,"region_idx":idx,"stock_discovery_bbox":stock_box,"original_bbox":gb})

occurrences = [
    ("backspace_r1",1,"Backspace","지우기",[216,94,276,107]),
    ("space_r1",1,"Space","공백",[66,118,100,132]),
    ("backspace_r2",2,"Backspace","지우기",[526,94,586,107]),
    ("space_r2",2,"Space","공백",[376,118,410,132]),
    ("backspace_r3",3,"Backspace","지우기",[836,94,896,107]),
    ("space_r3",3,"Space","공백",[686,118,720,132]),
    ("backspace_r5",5,"Backspace","지우기",[620,216,680,229]),
    ("space_r5",5,"Space","공백",[470,240,504,254]),
    ("backspace_r6",6,"Backspace","지우기",[930,216,990,229]),
    ("space_r6",6,"Space","공백",[780,240,814,254]),
]
for key,idx,src,kor,stock_box in occurrences:
    targets.append({"key":key,"source":src,"korean":kor,"region_idx":idx,"stock_discovery_bbox":stock_box,"original_bbox":extract_hd_bbox(stock_box, idx, margin_x=48, margin_y=20)})

if len(targets) != 14 or preserved_shift_bbox is None:
    raise RuntimeError(("target count",len(targets),preserved_shift_bbox))

# Source text mask uses exact source alpha only inside the 14 intended target bboxes.
source_text_mask=Image.new("L",(W,H),0)
allowed_bbox=Image.new("L",(W,H),0)
abd=ImageDraw.Draw(allowed_bbox)
for t in targets:
    x1,y1,x2,y2=t["original_bbox"]
    local=source_readable.crop((x1,y1,x2,y2)).getchannel("A").point(lambda v:255 if v else 0)
    source_text_mask.paste(ImageChops.lighter(source_text_mask.crop((x1,y1,x2,y2)),local),(x1,y1))
    abd.rectangle((x1,y1,x2-1,y2-1),fill=255)

source_visible=binary_alpha(source_readable)
protected_visible=ImageChops.multiply(source_visible,ImageOps.invert(allowed_bbox))
clean_protected=ImageChops.multiply(source_visible,ImageOps.invert(source_text_mask))
clean=source_readable.copy()
clean.paste(Image.new("RGBA",(W,H),(0,0,0,0)),(0,0),source_text_mask)

source_png=out/"AD720950_HD_SOURCE_READABLE.png"
clean_png=out/"AD720950_HD_CLEAN_PLATE.png"
source_readable.save(source_png)
clean.save(clean_png)
source_text_mask.save(out/"AD720950_HD_SOURCE_TEXT_MASK.png")
allowed_bbox.save(out/"AD720950_HD_ALLOWED_TEXT_REGION_MASK.png")
protected_visible.save(out/"AD720950_HD_PROTECTED_VISIBLE_MASK.png")
clean_protected.save(out/"AD720950_HD_CLEAN_PROTECTED_VISIBLE_MASK.png")

subprocess.run([
    "python3",str(validator),str(source_png),str(clean_png),
    str(out/"AD720950_HD_SOURCE_TEXT_MASK.png"),
    "--protected-mask",str(out/"AD720950_HD_CLEAN_PROTECTED_VISIBLE_MASK.png"),
    "--report",str(out/"A_PRODUCTION13_CLEAN_PLATE_VALIDATION.json")
],check=True)
clean_rep=json.loads((out/"A_PRODUCTION13_CLEAN_PLATE_VALIDATION.json").read_text())
if clean_rep["status"]!="PASS":
    raise RuntimeError("clean validator failed")

def resolve_font():
    pats=["Noto Sans CJK KR:style=Black","Noto Sans CJK KR:style=Bold","Noto Sans CJK KR"]
    for pat in pats:
        try:
            fp=subprocess.check_output(["fc-match","-f","%{file}",pat],text=True).strip()
        except Exception:
            fp=""
        if fp and Path(fp).exists() and "NotoSansCJK" in Path(fp).name:
            return fp
    subprocess.run(["sudo","apt-get","update","-qq"],check=True)
    subprocess.run(["sudo","apt-get","install","-y","-qq","fonts-noto-cjk"],check=True)
    for pat in pats:
        fp=subprocess.check_output(["fc-match","-f","%{file}",pat],text=True).strip()
        if fp and Path(fp).exists():
            return fp
    raise RuntimeError("Noto CJK Korean unavailable")
FONT=resolve_font()

def render_plain(text, ob):
    ox1,oy1,ox2,oy2=ob
    aw,ah=ox2-ox1,oy2-oy1
    # Match the source's white, no-outline text style. Fit to strict source bbox with >=2 px margins.
    max_fs=max(16,int(ah*1.22))
    for fs in range(max_fs,11,-1):
        font=ImageFont.truetype(FONT,fs)
        # Source Latin labels are heavy condensed white glyphs. Use a same-color
        # micro-stroke to match visual weight without inventing an outline effect.
        sw=max(1,fs//22)
        d=ImageDraw.Draw(Image.new("L",(8,8),0))
        tb=d.textbbox((0,0),text,font=font,stroke_width=sw)
        tw,th=tb[2]-tb[0],tb[3]-tb[1]
        pad=sw+4
        glyph=Image.new("RGBA",(tw+pad*2,th+pad*2),(0,0,0,0))
        gd=ImageDraw.Draw(glyph)
        gd.text((pad-tb[0],pad-tb[1]),text,font=font,fill=(255,255,255,255),stroke_width=sw,stroke_fill=(255,255,255,255))
        bb=glyph.getchannel("A").getbbox()
        if not bb:
            continue
        glyph=glyph.crop(bb)
        if glyph.width<=aw-4 and glyph.height<=ah-4:
            tx=ox1+(aw-glyph.width)//2
            ty=oy1+(ah-glyph.height)//2
            if tx<=ox1: tx=ox1+1
            if ty<=oy1: ty=oy1+1
            if tx+glyph.width>=ox2: tx=ox2-glyph.width-1
            if ty+glyph.height>=oy2: ty=oy2-glyph.height-1
            return glyph,(tx,ty),fs
    raise RuntimeError(("fit failed",text,ob))

final=clean.copy()
for t in targets:
    glyph,(tx,ty),fs=render_plain(t["korean"],t["original_bbox"])
    am=glyph.getchannel("A").point(lambda v:255 if v else 0)
    final.paste(glyph,(tx,ty),am)
    t["font_size"]=fs
    t["preencode_bbox"]=[tx,ty,tx+glyph.width,ty+glyph.height]

# Exact RGBA32 encode, preserving source header and raw mirror-Y orientation.
raw_final=final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
cb=sb[:128]+raw_final.tobytes("raw","RGBA")
candidate.write_bytes(cb)
candidate_sha=sha(candidate)
if cb[:128]!=sb[:128]:
    raise RuntimeError("header changed")
decoded_raw=Image.frombytes("RGBA",(W,H),cb[128:],"raw","RGBA")
decoded=decoded_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
decoded_png=out/"AD720950_HD_FINAL_DECODED_READABLE.png"
decoded.save(decoded_png)
if ImageChops.difference(decoded,final).getbbox() is not None:
    raise RuntimeError("RGBA roundtrip mismatch")

subprocess.run([
    "python3",str(validator),str(source_png),str(decoded_png),
    str(out/"AD720950_HD_ALLOWED_TEXT_REGION_MASK.png"),
    "--protected-mask",str(out/"AD720950_HD_PROTECTED_VISIBLE_MASK.png"),
    "--report",str(out/"A_PRODUCTION13_FINAL_MASK_VALIDATION.json")
],check=True)
final_rep=json.loads((out/"A_PRODUCTION13_FINAL_MASK_VALIDATION.json").read_text())
if final_rep["status"]!="PASS":
    raise RuntimeError("final validator failed")

diff=changed_mask(source_readable,decoded)
outside=count(ImageChops.multiply(diff,ImageOps.invert(allowed_bbox)))
alpha_delta=ImageChops.difference(source_readable.getchannel("A"),decoded.getchannel("A")).point(lambda v:255 if v else 0)
alpha_outside=count(ImageChops.multiply(alpha_delta,ImageOps.invert(allowed_bbox)))
protected_changed=count(ImageChops.multiply(diff,protected_visible))
clean_residue=count(ImageChops.multiply(binary_alpha(clean),source_text_mask))

# Shift must remain byte/pixel-identical in readable pixels.
sx1,sy1,sx2,sy2=preserved_shift_bbox
shift_diff=count(changed_mask(source_readable.crop((sx1,sy1,sx2,sy2)),decoded.crop((sx1,sy1,sx2,sy2))))
if shift_diff!=0:
    raise RuntimeError(("Shift changed",shift_diff))

rows=[]
for t in targets:
    ob=t["original_bbox"]
    # Localized pixels are candidate alpha in the source target bbox after exact source text removal.
    bb=decoded.crop(tuple(ob)).getchannel("A").getbbox()
    loc=[ob[0]+bb[0],ob[1]+bb[1],ob[0]+bb[2],ob[1]+bb[3]] if bb else None
    ok=loc is not None and loc[0]>=ob[0] and loc[1]>=ob[1] and loc[2]<=ob[2] and loc[3]<=ob[3]
    size_ok=loc is not None and (loc[2]-loc[0])<=(ob[2]-ob[0]) and (loc[3]-loc[1])<=(ob[3]-ob[1])
    positive=loc is not None and loc[0]>ob[0] and loc[1]>ob[1] and loc[2]<ob[2] and loc[3]<ob[3]
    raw_ob=[ob[0],H-ob[3],ob[2],H-ob[1]]
    raw_loc=[loc[0],H-loc[3],loc[2],H-loc[1]] if loc else None
    rows.append({
        "key":t["key"],"region_idx":t["region_idx"],"source":t["source"],"korean":t["korean"],
        "original_bbox":ob,"localized_bbox":loc,
        "source_width":ob[2]-ob[0],"source_height":ob[3]-ob[1],
        "localized_width":loc[2]-loc[0] if loc else None,"localized_height":loc[3]-loc[1] if loc else None,
        "delta_left":loc[0]-ob[0] if loc else None,"delta_right":ob[2]-loc[2] if loc else None,
        "delta_top":loc[1]-ob[1] if loc else None,"delta_bottom":ob[3]-loc[3] if loc else None,
        "containment":"PASS" if ok else "FAIL","size_ceiling":"PASS" if size_ok else "FAIL",
        "positive_margin":"PASS" if positive else "EDGE_TOUCH_OR_FAIL",
        "raw_original_bbox":raw_ob,"raw_localized_bbox":raw_loc,
        "raw_containment":"PASS" if ok else "FAIL",
        "font":"Noto Sans CJK KR Black/Bold","font_size":t["font_size"],
        "style":"source-matched heavy plain white antialiased text; same-color weight stroke only, no contrasting outline/shadow",
        "rework_status":"A_PRODUCTION13_NEW_HD_CANDIDATE"
    })
all_bbox=all(r["containment"]=="PASS" and r["raw_containment"]=="PASS" for r in rows)
all_size=all(r["size_ceiling"]=="PASS" for r in rows)
all_positive=all(r["positive_margin"]=="PASS" for r in rows)

# Visual evidence: full SOURCE/CLEAN/FINAL at 1/2 and target contact sheet at 1:1.
def gray(im):
    bg=Image.new("RGBA",im.size,(128,128,128,255))
    bg.alpha_composite(im)
    return bg.convert("RGB")

thumb=(2048,512)
sheet=Image.new("RGB",(thumb[0],thumb[1]*3),(80,80,80))
sheet.paste(gray(source_readable).resize(thumb,Image.Resampling.LANCZOS),(0,0))
sheet.paste(gray(clean).resize(thumb,Image.Resampling.LANCZOS),(0,thumb[1]))
sheet.paste(gray(decoded).resize(thumb,Image.Resampling.LANCZOS),(0,thumb[1]*2))
sheet.save(out/"A_PRODUCTION13_SOURCE_CLEAN_FINAL_GRAY.jpg",quality=94)
gray(decoded_raw).resize(thumb,Image.Resampling.LANCZOS).save(out/"A_PRODUCTION13_FINAL_RAW_GRAY.jpg",quality=94)

contact=[]
label_font=ImageFont.truetype(FONT,22)
for t in targets:
    ob=t["original_bbox"]; m=10
    x1=max(0,ob[0]-m);y1=max(0,ob[1]-m);x2=min(W,ob[2]+m);y2=min(H,ob[3]+m)
    a=gray(source_readable.crop((x1,y1,x2,y2)))
    b=gray(decoded.crop((x1,y1,x2,y2)))
    row=Image.new("RGB",(a.width+b.width+12,max(a.height,b.height)+28),(225,225,225))
    row.paste(a,(0,28)); row.paste(b,(a.width+12,28))
    ImageDraw.Draw(row).text((3,3),t["key"]+" SOURCE | FINAL",font=label_font,fill=(0,0,0))
    contact.append(row)
cw=max(x.width for x in contact); ch=sum(x.height for x in contact)+4*(len(contact)-1)
cs=Image.new("RGB",(cw,ch),(235,235,235)); yy=0
for x in contact:
    cs.paste(x,(0,yy)); yy+=x.height+4
cs.save(out/"A_PRODUCTION13_ROW_CONTACT.jpg",quality=94)

status_ok=(
    clean_rep["status"]=="PASS" and final_rep["status"]=="PASS"
    and all_bbox and all_size and all_positive
    and outside==0 and alpha_outside==0 and protected_changed==0 and clean_residue==0
    and shift_diff==0
)

report={
    "schema_version":1,"role":"A","run":run,"worker":os.environ.get("OUTRUN_CPU_WORKER"),
    "base_head":os.environ.get("GITHUB_SHA"),"index":47,"asset":asset_rel,
    "source_provenance":{
        "repository":"Sonic-TV/OR2006Sprites","commit":COMMIT,"git_blob_sha1":BLOB,
        "sha256":SOURCE_SHA,"path":"Release/spr_sprani_etc_cvt_Exst/AD720950_1024x256.dds",
        "classification":"authoritative high-resolution source; stale filename suffix, DDS header 4096x1024 RGBA32"
    },
    "source_sha256":SOURCE_SHA,"candidate_sha256":candidate_sha,
    "candidate_path":str(candidate.relative_to(repo)),
    "structure":{"dimensions":[W,H],"format":"RGBA32","pitch":pitch,"mipmaps":mips,"bytes":len(sb),"header_128_exact":True,"raw_orientation":"mirror_y"},
    "translation_policy":{
        "localized_unique":["Symbols->기호","Caps Lock->대문자 고정","Backspace->지우기","Accents->악센트","Done->완료","Space->공백"],
        "preserved_unchanged":["Shift"],
        "character_glyph_rows":"preserved pixel-identical; separate Hangul name-entry/font work"
    },
    "target_occurrences":14,"preserved_shift_bbox":preserved_shift_bbox,"preserved_shift_pixel_diffs":shift_diff,
    "clean_plate_validator":clean_rep,"final_mask_validator":final_rep,
    "decoded_changes":{
        "changed_pixels_total":count(diff),"changed_pixels_outside_original_bboxes":outside,
        "alpha_changed_pixels_outside_original_bboxes":alpha_outside,
        "protected_visible_pixels_changed":protected_changed,"clean_plate_source_text_residue_pixels":clean_residue
    },
    "rows":rows,"all_14_readable_and_raw_bbox_pass":all_bbox,"all_14_size_ceiling_pass":all_size,"all_14_positive_margin":all_positive,
    "controller_visual_qa":"PENDING_CONTROLLER_REVIEW","runtime_validation":"UNTESTED",
    "status":"A_PRODUCTION13_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_VISUAL_QA" if status_ok else "A_PRODUCTION13_WORKER_REWORK_REQUIRED"
}
(out/"A_PRODUCTION13_AD720950_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
summary={
    "run":run,"asset":"AD720950","index":47,"source_sha256":SOURCE_SHA,"candidate_sha256":candidate_sha,
    "source_dimensions":[W,H],"format":"RGBA32","target_occurrences":14,
    "bbox_pass":"14/14" if all_bbox else "FAIL","size_ceiling":"14/14" if all_size else "FAIL",
    "positive_margin":"14/14" if all_positive else "FAIL","shift_preserved_pixel_diffs":shift_diff,
    "clean_plate_validator":clean_rep["status"],"final_mask_validator":final_rep["status"],
    "changed_pixels_outside_original_bboxes":outside,"alpha_changed_pixels_outside_original_bboxes":alpha_outside,
    "protected_visible_pixels_changed":protected_changed,"clean_plate_source_text_residue_pixels":clean_residue,
    "worker_status":report["status"],"runtime_validation":"UNTESTED",
    "report":"localization/graphics/role_A/20261004-A-PRODUCTION13/A_PRODUCTION13_AD720950_REPORT.json"
}
(worker_out/"A_PRODUCTION13_AD720950.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False,indent=2))
if not status_ok:
    raise SystemExit(2)
