#!/usr/bin/env python3
import os, json, hashlib, struct, subprocess, urllib.request, shutil
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageChops, ImageOps

if os.environ.get("OUTRUN_CPU_WORKER") != "github-actions" or os.environ.get("OUTRUN_CPU_ROLE") != "A":
    raise SystemExit("This deterministic job must run in the GitHub-hosted localization CPU worker as role A.")

repo = Path.cwd()
run = "20261004-A-PRODUCTION09"
out = repo / "localization/graphics/role_A" / run
out.mkdir(parents=True, exist_ok=True)
worker_out = repo / "localization/graphics/worker_results"
worker_out.mkdir(parents=True, exist_ok=True)

asset_rel = "textures/load/spr_sprani_congrats_cvt_Exst/455717B2_512x512.dds"
candidate = repo / "localization/graphics/hd_candidates" / asset_rel
candidate.parent.mkdir(parents=True, exist_ok=True)
validator = repo / "tools/localization/validate_clean_plate.py"

work = Path("/tmp/outrun_A_production09")
work.mkdir(parents=True, exist_ok=True)
source = work / "455717B2_512x512.dds"
atlas_json = work / "455717B2_512x512_atlas.json"

UPSTREAM_REPO = "Sonic-TV/OR2006Sprites"
UPSTREAM_COMMIT = "3ce344e7ed6b1b535f5e4d34c1192071ff7afbe6"
UPSTREAM_BLOB = "95cf5b669afdff12d12ebb8d1b1ab70ced87a6cc"
SOURCE_SHA = "645536f60208d35274cc7bd4b8edc041eda81a761a34603ed1e8be9af20583eb"
base = (
    "https://raw.githubusercontent.com/Sonic-TV/OR2006Sprites/"
    + UPSTREAM_COMMIT
    + "/Original%20(PC)/Original%20(Tweaks%20dumps)/spr_sprani_congrats_cvt_Exst/"
)
urllib.request.urlretrieve(base + "455717B2_512x512.dds", source)
urllib.request.urlretrieve(base + "455717B2_512x512_atlas.json", atlas_json)

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

if sha(source) != SOURCE_SHA:
    raise RuntimeError("canonical source SHA mismatch")

def resolve_font():
    pats = [
        "Noto Sans CJK KR:style=Black",
        "Noto Sans CJK KR:style=Bold",
        "Noto Sans CJK KR",
    ]
    for pat in pats:
        try:
            fp = subprocess.check_output(["fc-match", "-f", "%{file}", pat], text=True).strip()
        except Exception:
            fp = ""
        if fp and Path(fp).exists() and "NotoSansCJK" in Path(fp).name:
            return fp
    subprocess.run(["sudo", "apt-get", "update", "-qq"], check=True)
    subprocess.run(["sudo", "apt-get", "install", "-y", "-qq", "fonts-noto-cjk"], check=True)
    for pat in pats:
        fp = subprocess.check_output(["fc-match", "-f", "%{file}", pat], text=True).strip()
        if fp and Path(fp).exists():
            return fp
    raise RuntimeError("Noto CJK Korean font unavailable")

def ensure_convert():
    exe = shutil.which("convert") or shutil.which("magick")
    if exe:
        return exe
    subprocess.run(["sudo", "apt-get", "update", "-qq"], check=True)
    subprocess.run(["sudo", "apt-get", "install", "-y", "-qq", "imagemagick"], check=True)
    exe = shutil.which("convert") or shutil.which("magick")
    if not exe:
        raise RuntimeError("ImageMagick unavailable")
    return exe

fontpath = resolve_font()
convert_exe = ensure_convert()

def count(mask):
    return sum(mask.histogram()[1:])

def binary_alpha(im):
    return im.getchannel("A").point(lambda v: 255 if v else 0)

def changed_mask(a, b):
    d = ImageChops.difference(a, b)
    bands = d.split()
    m = bands[0]
    for z in bands[1:]:
        m = ImageChops.lighter(m, z)
    return m.point(lambda v: 255 if v else 0)

def shear_mask(mask, shear_px):
    w, h = mask.size
    s = max(0, int(round(shear_px)))
    if s == 0:
        return mask
    k = s / max(1, h - 1)
    return mask.transform(
        (w + s + 2, h),
        Image.Transform.AFFINE,
        (1, k, -s, 0, 1, 0),
        resample=Image.Resampling.BICUBIC,
    )

def gradient(size, stops):
    w, h = size
    im = Image.new("RGBA", size)
    px = im.load()
    stops = sorted(stops)
    for y in range(h):
        t = 0 if h <= 1 else y / (h - 1)
        i = 0
        while i + 1 < len(stops) and t > stops[i + 1][0]:
            i += 1
        if i + 1 >= len(stops):
            c = stops[-1][1]
        else:
            t0, c0 = stops[i]
            t1, c1 = stops[i + 1]
            u = 0 if t1 == t0 else (t - t0) / (t1 - t0)
            c = tuple(int(round(c0[k] + (c1[k] - c0[k]) * u)) for k in range(4))
        for x in range(w):
            px[x, y] = c
    return im

src_bytes = source.read_bytes()
if src_bytes[:4] != b"DDS " or src_bytes[84:88] != b"DXT5":
    raise RuntimeError("source is not DXT5")
if len(src_bytes) != 262272:
    raise RuntimeError(f"unexpected source size {len(src_bytes)}")

raw_source = Image.open(source).convert("RGBA")
W, H = raw_source.size
if (W, H) != (512, 512):
    raise RuntimeError((W, H))
readable_source = raw_source.transpose(Image.Transpose.FLIP_TOP_BOTTOM)

atlas = json.loads(atlas_json.read_text(encoding="utf-8"))
regions = {r["idx"]: r for r in atlas["regions"]}
bindings = [
    {"key":"continue","source":"CONTINUE","korean":"계속하기","idx":6,"style":"continue"},
    {"key":"perfect","source":"PERFECT!","korean":"완벽!","idx":5,"style":"green"},
    {"key":"congratulations","source":"CONGRATULATIONS!","korean":"축하합니다!","idx":4,"style":"gold"},
    {"key":"passed","source":"PASSED!","korean":"통과!","idx":1,"style":"green"},
]
expected_cells = {
    "continue":[0,63,175,88],
    "perfect":[0,88,353,140],
    "congratulations":[0,140,507,197],
    "passed":[0,197,425,258],
}
for item in bindings:
    x, y, w, h = regions[item["idx"]]["rect"]
    cell = [x, y, x+w, y+h]
    if cell != expected_cells[item["key"]]:
        raise RuntimeError((item["key"], cell, expected_cells[item["key"]]))
    item["cell"] = cell
    x1,y1,x2,y2 = cell
    bb = readable_source.crop((x1,y1,x2,y2)).getchannel("A").getbbox()
    if not bb:
        raise RuntimeError("empty source sprite " + item["key"])
    item["original_bbox"] = [x1+bb[0], y1+bb[1], x1+bb[2], y1+bb[3]]

# Source-text mask is the exact nonzero-alpha footprint inside the four text-only atlas regions.
source_text_mask = Image.new("L", (W,H), 0)
for item in bindings:
    x1,y1,x2,y2 = item["cell"]
    local = readable_source.crop((x1,y1,x2,y2)).getchannel("A").point(lambda v: 255 if v else 0)
    prior = source_text_mask.crop((x1,y1,x2,y2))
    source_text_mask.paste(ImageChops.lighter(prior, local), (x1,y1))

clean = readable_source.copy()
clean.paste(Image.new("RGBA",(W,H),(0,0,0,0)), (0,0), source_text_mask)

allowed_bbox = Image.new("L",(W,H),0)
ad = ImageDraw.Draw(allowed_bbox)
for item in bindings:
    x1,y1,x2,y2 = item["original_bbox"]
    ad.rectangle((x1,y1,x2-1,y2-1), fill=255)

source_visible = binary_alpha(readable_source)
protected_visible = ImageChops.multiply(source_visible, ImageOps.invert(allowed_bbox))
clean_protected = ImageChops.multiply(source_visible, ImageOps.invert(source_text_mask))

source_png = out / "455717B2_SOURCE_READABLE.png"
clean_png = out / "455717B2_CLEAN_PLATE.png"
readable_source.save(source_png)
clean.save(clean_png)
source_text_mask.save(out / "455717B2_SOURCE_TEXT_MASK.png")
allowed_bbox.save(out / "455717B2_ALLOWED_TEXT_REGION_MASK.png")
protected_visible.save(out / "455717B2_PROTECTED_VISIBLE_MASK.png")
clean_protected.save(out / "455717B2_CLEAN_PLATE_PROTECTED_VISIBLE_MASK.png")

subprocess.run([
    "python3", str(validator), str(source_png), str(clean_png),
    str(out/"455717B2_SOURCE_TEXT_MASK.png"),
    "--protected-mask", str(out/"455717B2_CLEAN_PLATE_PROTECTED_VISIBLE_MASK.png"),
    "--report", str(out/"A_PRODUCTION09_CLEAN_PLATE_VALIDATION.json")
], check=True)
clean_rep = json.loads((out/"A_PRODUCTION09_CLEAN_PLATE_VALIDATION.json").read_text())
if clean_rep["status"] != "PASS":
    raise RuntimeError("clean plate validator failed")

styles = {
    "continue": {
        "max_font":20, "outer":2, "inner":1, "shear":4, "shadow":(1,1),
        "outer_color":(248,248,245,255), "inner_color":(8,18,55,255),
        "shadow_color":(10,10,18,190),
        "stops":[(0,(255,248,190,255)),(.45,(255,231,100,255)),(1,(247,186,32,255))],
    },
    "green": {
        "max_font":43, "outer":3, "inner":2, "shear":8, "shadow":(2,2),
        "outer_color":(248,248,245,255), "inner_color":(18,24,30,255),
        "shadow_color":(12,12,16,205),
        "stops":[(0,(238,255,220,255)),(.28,(165,255,115,255)),(.60,(94,235,45,255)),(1,(43,175,8,255))],
    },
    "gold": {
        "max_font":42, "outer":3, "inner":2, "shear":8, "shadow":(2,2),
        "outer_color":(248,248,245,255), "inner_color":(30,30,35,255),
        "shadow_color":(12,12,16,205),
        "stops":[(0,(255,250,210,255)),(.26,(255,225,95,255)),(.60,(255,185,35,255)),(1,(224,132,12,255))],
    },
}

def render_style(text, ob, style_name):
    cfg = styles[style_name]
    ox1,oy1,ox2,oy2 = ob
    aw, ah = ox2-ox1, oy2-oy1
    for fs in range(cfg["max_font"], 9, -1):
        font = ImageFont.truetype(fontpath, fs)
        pad = 8
        outer = cfg["outer"]
        inner = cfg["inner"]
        # Common un-sheared canvas for aligned fill/strokes.
        tb = font.getbbox(text, stroke_width=outer)
        tw, th = tb[2]-tb[0], tb[3]-tb[1]
        cw, ch = tw+pad*2, th+pad*2
        masks = {}
        for name, sw in [("outer",outer),("inner",inner),("fill",0)]:
            m = Image.new("L",(cw,ch),0)
            d = ImageDraw.Draw(m)
            d.text((pad-tb[0],pad-tb[1]), text, font=font, fill=255, stroke_width=sw, stroke_fill=255)
            masks[name] = shear_mask(m, cfg["shear"] * fs / max(1,cfg["max_font"]))
        union = ImageChops.lighter(masks["outer"], masks["inner"])
        union = ImageChops.lighter(union, masks["fill"])
        bb = union.getbbox()
        if not bb:
            continue
        masks = {k:v.crop(bb) for k,v in masks.items()}
        mw = max(v.width for v in masks.values())
        mh = max(v.height for v in masks.values())
        # Positive one-pixel margin to avoid high-risk edge touch.
        if mw + max(0,cfg["shadow"][0]) > aw-2 or mh + max(0,cfg["shadow"][1]) > ah-2:
            continue
        lw = mw + max(0,cfg["shadow"][0])
        lh = mh + max(0,cfg["shadow"][1])
        layer = Image.new("RGBA",(lw,lh),(0,0,0,0))
        sx,sy = cfg["shadow"]
        sm = Image.new("L",(lw,lh),0)
        sm.paste(masks["outer"],(sx,sy))
        layer.paste(Image.new("RGBA",(lw,lh),cfg["shadow_color"]),(0,0),sm)
        for name,color in [("outer",cfg["outer_color"]),("inner",cfg["inner_color"])]:
            mm = Image.new("L",(lw,lh),0)
            mm.paste(masks[name],(0,0))
            layer.paste(Image.new("RGBA",(lw,lh),color),(0,0),mm)
        fm = Image.new("L",(lw,lh),0)
        fm.paste(masks["fill"],(0,0))
        layer.paste(gradient((lw,lh),cfg["stops"]),(0,0),fm)
        abb = layer.getchannel("A").getbbox()
        if not abb:
            continue
        layer = layer.crop(abb)
        if layer.width > aw-2 or layer.height > ah-2:
            continue
        tx = ox1 + (aw-layer.width)//2
        ty = oy1 + (ah-layer.height)//2
        if tx <= ox1: tx = ox1+1
        if ty <= oy1: ty = oy1+1
        if tx+layer.width >= ox2: tx = ox2-layer.width-1
        if ty+layer.height >= oy2: ty = oy2-layer.height-1
        return layer,(tx,ty),fs
    raise RuntimeError(("could not fit",text,ob,style_name))

final = clean.copy()
pre_rows = []
for item in bindings:
    layer,(tx,ty),fs = render_style(item["korean"],item["original_bbox"],item["style"])
    am = layer.getchannel("A").point(lambda v:255 if v else 0)
    final.paste(layer,(tx,ty),am)
    bb = [tx,ty,tx+layer.width,ty+layer.height]
    ob = item["original_bbox"]
    if not (bb[0]>ob[0] and bb[1]>ob[1] and bb[2]<ob[2] and bb[3]<ob[3]):
        raise RuntimeError(("preencode positive-margin fit failed", item["key"], ob, bb))
    item["font_size"] = fs
    item["preencode_bbox"] = bb
    pre_rows.append((item["key"],bb))

# Encode full readable final in raw mirror-Y orientation, then splice only target-intersecting DXT5 blocks.
raw_final = final.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
raw_png = work / "final_raw.png"
raw_final.save(raw_png)
full_encoded = work / "full_encoded.dds"
cmd = [convert_exe]
if Path(convert_exe).name == "magick":
    cmd += ["convert"]
cmd += [str(raw_png), "-define", "dds:compression=dxt5", "-define", "dds:mipmaps=0", str(full_encoded)]
subprocess.run(cmd, check=True)
enc = full_encoded.read_bytes()
if len(enc) != len(src_bytes) or enc[84:88] != b"DXT5":
    raise RuntimeError(("bad encoder output",len(enc),enc[84:88]))

bw,bh=W//4,H//4
patch_blocks=set()
for item in bindings:
    x1,y1,x2,y2=item["original_bbox"]
    # convert readable bbox to raw storage bbox
    rx1,rx2=x1,x2
    ry1,ry2=H-y2,H-y1
    for by in range(ry1//4,(ry2-1)//4+1):
        for bx in range(rx1//4,(rx2-1)//4+1):
            patch_blocks.add((bx,by))
cand_bytes=bytearray(src_bytes)
for bx,by in patch_blocks:
    p=128+(by*bw+bx)*16
    cand_bytes[p:p+16]=enc[p:p+16]
candidate.write_bytes(cand_bytes)
candidate_sha=sha(candidate)
if candidate.read_bytes()[:128] != src_bytes[:128]:
    raise RuntimeError("DDS header changed")

decoded_raw=Image.open(candidate).convert("RGBA")
decoded=decoded_raw.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
decoded_png=out/"455717B2_FINAL_DECODED_READABLE.png"
decoded.save(decoded_png)

# Actual changed-block mask from byte diff.
block_mask=Image.new("L",(W,H),0)
bd=ImageDraw.Draw(block_mask)
changed_blocks=[]
cb=candidate.read_bytes()
for by in range(bh):
    for bx in range(bw):
        p=128+(by*bw+bx)*16
        if src_bytes[p:p+16] != cb[p:p+16]:
            changed_blocks.append((bx,by))
            x1=bx*4
            y1=H-(by+1)*4
            bd.rectangle((x1,y1,x1+3,y1+3),fill=255)
block_mask.save(out/"455717B2_DXT5_EDIT_BLOCK_MASK.png")

subprocess.run([
    "python3",str(validator),str(source_png),str(decoded_png),
    str(out/"455717B2_DXT5_EDIT_BLOCK_MASK.png"),
    "--protected-mask",str(out/"455717B2_PROTECTED_VISIBLE_MASK.png"),
    "--report",str(out/"A_PRODUCTION09_FINAL_DXT5_BLOCK_VALIDATION.json")
],check=True)
block_rep=json.loads((out/"A_PRODUCTION09_FINAL_DXT5_BLOCK_VALIDATION.json").read_text())

strict_proc=subprocess.run([
    "python3",str(validator),str(source_png),str(decoded_png),
    str(out/"455717B2_ALLOWED_TEXT_REGION_MASK.png"),
    "--protected-mask",str(out/"455717B2_PROTECTED_VISIBLE_MASK.png"),
    "--report",str(out/"A_PRODUCTION09_STRICT_BBOX_DIFF_VALIDATION.json")
],check=False)
strict_rep=json.loads((out/"A_PRODUCTION09_STRICT_BBOX_DIFF_VALIDATION.json").read_text())

diff=changed_mask(readable_source,decoded)
outside_bbox=ImageChops.multiply(diff,ImageOps.invert(allowed_bbox))
outside_n=count(outside_bbox)
alpha_delta=ImageChops.difference(readable_source.getchannel("A"),decoded.getchannel("A")).point(lambda v:255 if v else 0)
alpha_outside=count(ImageChops.multiply(alpha_delta,ImageOps.invert(allowed_bbox)))
visible_union=ImageChops.lighter(binary_alpha(readable_source),binary_alpha(decoded))
visible_outside=count(ImageChops.multiply(outside_bbox,visible_union))
protected_changed=count(ImageChops.multiply(diff,protected_visible))
transparent_rgb_only_outside=outside_n-visible_outside
clean_residue=count(ImageChops.multiply(binary_alpha(clean),source_text_mask))

rows=[]
for item in bindings:
    x1,y1,x2,y2=item["cell"]
    bb=decoded.crop((x1,y1,x2,y2)).getchannel("A").getbbox()
    loc=[x1+bb[0],y1+bb[1],x1+bb[2],y1+bb[3]] if bb else None
    ob=item["original_bbox"]
    ok=loc is not None and loc[0]>=ob[0] and loc[1]>=ob[1] and loc[2]<=ob[2] and loc[3]<=ob[3]
    positive=loc is not None and loc[0]>ob[0] and loc[1]>ob[1] and loc[2]<ob[2] and loc[3]<ob[3]
    raw_ob=[ob[0],H-ob[3],ob[2],H-ob[1]]
    raw_loc=[loc[0],H-loc[3],loc[2],H-loc[1]] if loc else None
    rows.append({
        "key":item["key"],"source":item["source"],"korean":item["korean"],
        "sprite_cell":item["cell"],"original_bbox":ob,"localized_bbox":loc,
        "delta_left":loc[0]-ob[0] if loc else None,
        "delta_right":ob[2]-loc[2] if loc else None,
        "delta_top":loc[1]-ob[1] if loc else None,
        "delta_bottom":ob[3]-loc[3] if loc else None,
        "containment":"PASS" if ok else "FAIL",
        "positive_margin":"PASS" if positive else "EDGE_TOUCH_OR_FAIL",
        "raw_original_bbox":raw_ob,"raw_localized_bbox":raw_loc,
        "raw_delta_left":raw_loc[0]-raw_ob[0] if raw_loc else None,
        "raw_delta_right":raw_ob[2]-raw_loc[2] if raw_loc else None,
        "raw_delta_top":raw_loc[1]-raw_ob[1] if raw_loc else None,
        "raw_delta_bottom":raw_ob[3]-raw_loc[3] if raw_loc else None,
        "raw_containment":"PASS" if ok else "FAIL",
        "font":"Noto Sans CJK KR Black/Bold","font_size":item["font_size"],"style":item["style"],
        "rework_status":"NEW_PRODUCTION09_CANDIDATE",
    })
all_bbox=all(r["containment"]=="PASS" and r["raw_containment"]=="PASS" for r in rows)
all_positive=all(r["positive_margin"]=="PASS" for r in rows)

# Persist visual evidence.
def gray(im):
    bg=Image.new("RGBA",im.size,(100,100,100,255))
    bg.alpha_composite(im)
    return bg.convert("RGB")
sheet=Image.new("RGB",(W*3,H),(70,70,70))
sheet.paste(gray(readable_source),(0,0))
sheet.paste(gray(clean),(W,0))
sheet.paste(gray(decoded),(W*2,0))
sheet.save(out/"A_PRODUCTION09_SOURCE_CLEAN_FINAL_GRAY.jpg",quality=94)
gray(decoded_raw).save(out/"A_PRODUCTION09_FINAL_RAW_GRAY.jpg",quality=94)

# 4x contact sheet for the four rows.
contact=[]
label_font=ImageFont.truetype(fontpath,16)
for item in bindings:
    ob=item["original_bbox"]
    x1=max(0,ob[0]-6); y1=max(0,ob[1]-6); x2=min(W,ob[2]+6); y2=min(H,ob[3]+6)
    src_crop=gray(readable_source.crop((x1,y1,x2,y2)))
    fin_crop=gray(decoded.crop((x1,y1,x2,y2)))
    sc=4
    sw,sh=(x2-x1)*sc,(y2-y1)*sc
    rowim=Image.new("RGB",(sw*2+12,sh+24),(220,220,220))
    rowim.paste(src_crop.resize((sw,sh),Image.Resampling.NEAREST),(0,24))
    rowim.paste(fin_crop.resize((sw,sh),Image.Resampling.NEAREST),(sw+12,24))
    ImageDraw.Draw(rowim).text((3,3),item["key"]+" SOURCE | FINAL",font=label_font,fill=(0,0,0))
    contact.append(rowim)
cw=max(x.width for x in contact)
ch=sum(x.height for x in contact)+6*(len(contact)-1)
cs=Image.new("RGB",(cw,ch),(230,230,230))
yy=0
for x in contact:
    cs.paste(x,(0,yy)); yy+=x.height+6
cs.save(out/"A_PRODUCTION09_ROW_CONTACT.jpg",quality=94)

status_ok=(
    all_bbox and all_positive
    and clean_rep["status"]=="PASS"
    and block_rep["status"]=="PASS"
    and visible_outside==0
    and alpha_outside==0
    and protected_changed==0
    and clean_residue==0
)
report={
    "schema_version":1,"role":"A","run":run,
    "worker":os.environ.get("OUTRUN_CPU_WORKER","unknown"),
    "base_head":os.environ.get("GITHUB_SHA"),
    "index":43,"asset":asset_rel,
    "source_provenance":{
        "repository":UPSTREAM_REPO,"commit":UPSTREAM_COMMIT,"git_blob_sha1":UPSTREAM_BLOB,
        "sha256":SOURCE_SHA,
        "classification":"stock fallback because current branch HD source package has no 455717B2 entry and pinned upstream directory exposes no higher-resolution DDS for this key"
    },
    "method":"canonical stock DXT5 source -> exact nonzero-alpha text masks inside atlas text sprites -> transparent clean plate -> measured native-resolution source-family Korean render -> raw mirror_y DXT5 encode -> exact source-header selective block splice -> decoded static QA",
    "translations":[{"source":x["source"],"korean":x["korean"]} for x in bindings],
    "structure":{
        "dimensions":[W,H],"compression":"DXT5","mip_field":struct.unpack_from("<I",src_bytes,28)[0],
        "source_bytes":len(src_bytes),"candidate_bytes":len(cb),
        "header_128_exact":cb[:128]==src_bytes[:128],"raw_orientation":"mirror_y",
        "changed_dxt5_blocks":len(changed_blocks),"total_dxt5_blocks":bw*bh,
    },
    "source_sha256":SOURCE_SHA,"candidate_sha256":candidate_sha,
    "candidate_path":str(candidate.relative_to(repo)),
    "clean_plate_validator":clean_rep,
    "final_dxt5_block_validator":block_rep,
    "strict_original_bbox_all_channel_diagnostic":strict_rep,
    "decoded_changes":{
        "changed_pixels_total":count(diff),
        "changed_pixels_outside_original_bboxes":outside_n,
        "visible_changed_pixels_outside_original_bboxes":visible_outside,
        "alpha_changed_pixels_outside_original_bboxes":alpha_outside,
        "protected_visible_pixels_changed":protected_changed,
        "transparent_rgb_only_changed_pixels_outside_original_bboxes":transparent_rgb_only_outside,
        "clean_plate_source_text_residue_pixels":clean_residue,
    },
    "rows":rows,
    "all_4_readable_and_raw_bbox_pass":all_bbox,
    "all_4_positive_margin":all_positive,
    "controller_visual_qa":"PENDING_CONTROLLER_REVIEW",
    "runtime_validation":"UNTESTED",
    "status":"A_PRODUCTION09_WORKER_STATIC_QA_PASS_PENDING_CONTROLLER_VISUAL_QA" if status_ok else "A_PRODUCTION09_WORKER_REWORK_REQUIRED",
}
(out/"A_PRODUCTION09_455717B2_REPORT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
summary={
    "run":run,"asset":"455717B2","index":43,
    "source_sha256":SOURCE_SHA,"candidate_sha256":candidate_sha,
    "bbox_pass":"4/4" if all_bbox else "FAIL",
    "positive_margin":"4/4" if all_positive else "FAIL",
    "clean_plate_validator":clean_rep["status"],
    "final_dxt5_block_validator":block_rep["status"],
    "strict_original_bbox_all_channel_status":strict_rep["status"],
    "visible_changed_pixels_outside_original_bboxes":visible_outside,
    "alpha_changed_pixels_outside_original_bboxes":alpha_outside,
    "protected_visible_pixels_changed":protected_changed,
    "clean_plate_source_text_residue_pixels":clean_residue,
    "worker_status":report["status"],"runtime_validation":"UNTESTED",
    "report":"localization/graphics/role_A/20261004-A-PRODUCTION09/A_PRODUCTION09_455717B2_REPORT.json"
}
(worker_out/"A_PRODUCTION09_455717B2.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False,indent=2))
if not status_ok:
    raise SystemExit(2)
